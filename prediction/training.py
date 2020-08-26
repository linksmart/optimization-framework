
import datetime
import threading
import time

from shutil import copyfile

from IO.influxDBmanager import InfluxDBManager
from prediction.machineLearning import MachineLearning
from utils_intern.utilFunctions import UtilFunctions


class Training(MachineLearning, threading.Thread):
    """
    - Load data points from file
    - Wait till input_size + output_size + 5 points to train for the first time
    - After initial training, Train model once in 24 hr
    - Create a new model, compile, and train
    - Save the checkpoints model in model_train.h5
    - After training is completed, copy the model_train.h5 to model_base.h5
    """

    def __init__(self, config, horizon_in_steps, topic_name, dT_in_seconds, id, type, opt_values):
        super(Training, self).__init__(config, horizon_in_steps, topic_name, dT_in_seconds, id, type, opt_values)

        self.today = datetime.datetime.now().day
        self.stopRequest = threading.Event()
        self.training_lock_key = "training_lock"
        self.frequency = config.getint("IO", str(self.type)+".training.frequency.sec", fallback=86400)  # one day
        self.min_training_size = self.input_size + self.output_size
        self.initial_wait_time = config.getint("IO", str(self.type)+".training.initial.wait.sec", fallback=0)
        # samples given to ml model
        self.max_training_samples = config.getint("IO", str(self.type)+".max.training.samples", fallback=250)
        # number of data points to read from file
        self.max_raw_data_to_read = config.getint("IO", str(self.type)+".max.raw.data.samples", fallback=7200)
        self.logger.debug("max_training_samples " + str(self.max_training_samples))

    def run(self):
        # initial wait
        time.sleep(self.initial_wait_time)
        while not self.stopRequest.is_set():
            try:
                # get raw data from file
                from prediction.rawDataReader import RawDataReader
                data = RawDataReader.get_raw_data_influx(self.influxDB, self.topic_name, self.id,
                                                  self.max_raw_data_to_read)
                self.logger.debug("raw data ready " + str(len(data)))
                data, merged = self.processingData.expand_and_resample_into_blocks(data, 60, self.input_size,
                                                                                   self.output_size)
                if self.sufficient_data_available(data):
                    self.logger.info("start training, wait for lock")
                    trained = False
                    lastest_input_timestep_data_point = 0
                    try:
                        if self.redisDB.get_lock(self.training_lock_key, self.id + "_" + self.topic_name):
                            self.logger.info("lock granted")
                            if self.type == "load":
                                Xtrain, Ytrain, lastest_input_timestep_data_point = self.processingData.preprocess_data_train_load(
                                    data, self.model_data_dT, self.input_size, self.output_size,
                                    self.max_training_samples)
                            elif self.type == "pv":
                                Xtrain, Ytrain, lastest_input_timestep_data_point = self.processingData.preprocess_data_train_pv(
                                    data, self.model_data_dT, self.input_size, self.input_size_hist, self.output_size,
                                    self.max_training_samples)
                            self.logger.info("pre proc done")
                            model, graph = self.models.get_model(self.id + "_" + self.topic_name, False, self.redisDB)
                            from prediction.trainModel import TrainModel
                            trainModel = TrainModel(self.stop_request_status)
                            train_time = time.time()
                            if self.type == "load":
                                trainModel.train_load(Xtrain, Ytrain, self.num_epochs, self.batch_size, self.hidden_size,
                                                      self.input_size, self.output_size, self.model_file_container_train,
                                                      model)
                            elif self.type == "pv":
                                trainModel.train_pv(Xtrain, Ytrain, self.num_epochs, self.batch_size, self.hidden_size,
                                                    self.input_size, self.input_size_hist, self.output_size,
                                                    self.model_file_container_train, model)
                            self.logger.debug("Training time "+str(time.time()-train_time))
                            if self.redisDB.get_lock("ml_model_rw", "copy_"+str(self.id) + "_" + self.topic_name, log=True):
                                try:
                                    copyfile(self.model_file_container_train, self.model_file_container)
                                    copyfile(self.model_file_container_train, self.model_file_container_temp)
                                    trained = True
                                    self.logger.info("trained successfully")
                                except Exception as e:
                                    print("error copying trained model "+str(e))
                                finally:
                                    self.redisDB.release_lock("ml_model_rw", "copy_"+str(self.id) + "_" + self.topic_name, log=True)
                    except Exception as e:
                        trained = False
                        self.logger.error("error training model " + str(e))
                    finally:
                        self.redisDB.release_lock(self.training_lock_key, self.id + "_" + self.topic_name)
                    if trained:
                        pass
                        #self.logger.info("remove used raw data")
                        #RawDataReader.removed_data_before_timestamp(self.raw_data_file_container, self.topic_name,
                                                  #lastest_input_timestep_data_point)
                    time.sleep(UtilFunctions.get_sleep_secs(0, 0, self.frequency))
                else:
                    time.sleep(600)
            except Exception as e:
                self.logger.error("training thread exception " + str(e))
                time.sleep(600)

    def Stop(self):
        self.logger.info("start training thread exit")
        self.stopRequest.set()
        if self.isAlive():
            self.join(4)
        self.logger.info("training thread exited")

    def stop_request_status(self):
        return self.stopRequest.is_set()

    def sufficient_data_available(self, data_blocks):
        for block in data_blocks:
            self.logger.info("length of block = " + str(len(block)))
            if len(block) >= self.min_training_size:
                return True
        return False

