import datetime
import json
import threading
from queue import Queue
import time

import os
from shutil import copyfile

from IO.redisDB import RedisDB
from prediction.processingData import ProcessingData
from utils_intern.messageLogger import MessageLogger


"""
Creates a thread for prediction and a thread for training
"""
class LoadPrediction:

    def __init__(self, config, control_frequency, horizon_in_steps, topic_name, topic_param, dT_in_seconds, id, predictionFlag):
        self.logger = MessageLogger.get_logger(__name__, id)
        
        self.predictionFlag = predictionFlag

        self.topic_name = topic_name
        self.control_frequency = control_frequency  # determines minute or hourly etc
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        # removing this and keeping constant input size
        """
        self.num_timesteps = horizon_in_steps + 1
        if self.num_timesteps > 60:
            self.num_timesteps = 60
        """
        self.num_timesteps = 24
        self.hidden_size = 100
        self.batch_size = 1
        self.num_epochs = 10  # 10
        self.output_size = int(self.horizon_in_steps-1)
        if self.output_size < 1:
            self.output_size = 1
        self.id = id

        dir_data = os.path.join("/usr/src/app", "prediction/resources", self.id)
        if not os.path.exists(dir_data):
            os.makedirs(dir_data)

        self.raw_data_file_container = os.path.join("/usr/src/app", "prediction/resources", self.id, "raw_data_"+str(topic_name)+".csv")
        self.model_file_container = os.path.join("/usr/src/app", "prediction/resources", self.id, "model_"+str(topic_name)+".h5")
        self.model_file_container_temp = os.path.join("/usr/src/app", "prediction/resources", "model_temp_"+str(topic_name)+".h5")
        self.model_file_container_train = os.path.join("/usr/src/app", "prediction/resources", self.id, "model_train_"+str(topic_name)+".h5")

        self.processingData = ProcessingData()

        self.load_forecast_pub = None
        self.prediction_thread = None
        self.training_thread = None
        self.raw_data = None

        total_mins = int(float(self.num_timesteps * self.dT_in_seconds)/60.0) + 1

        if self.predictionFlag:
            from prediction.rawLoadDataReceiver import RawLoadDataReceiver
            self.raw_data = RawLoadDataReceiver(topic_param, config, total_mins, self.horizon_in_steps * 25,
                                                self.raw_data_file_container, self.topic_name, self.id)

            self.q = Queue(maxsize=0)

            from optimization.loadForecastPublisher import LoadForecastPublisher
            load_forecast_topic = config.get("IO", "forecast.topic")
            load_forecast_topic = json.loads(load_forecast_topic)
            load_forecast_topic["topic"] = load_forecast_topic["topic"] + self.topic_name
            self.load_forecast_pub = LoadForecastPublisher(load_forecast_topic, config, self.q,
                                                           self.control_frequency, self.topic_name, self.id,
                                                           self.horizon_in_steps, self.dT_in_seconds)
            self.load_forecast_pub.start()

            self.startPrediction()
        else:
            self.startTraining()

    def startTraining(self):
        self.training_thread = Training(self.control_frequency, self.horizon_in_steps, self.num_timesteps,
                                        self.hidden_size, self.batch_size, self.num_epochs,
                                        self.raw_data_file_container, self.processingData, self.model_file_container,
                                        self.model_file_container_train, self.topic_name, self.id, self.dT_in_seconds, self.output_size, self.logger)
        self.training_thread.start()

    def startPrediction(self):
        self.prediction_thread = Prediction(self.control_frequency, self.horizon_in_steps, self.num_timesteps,
                                            self.hidden_size, self.batch_size, self.num_epochs,
                                            self.raw_data, self.processingData, self.model_file_container_temp,
                                            self.model_file_container, self.q, self.topic_name, self.id, self.dT_in_seconds, self.output_size, self.logger)
        self.prediction_thread.start()


    def Stop(self):
        self.logger.info("start load controller thread exit")
        if self.prediction_thread:
            self.prediction_thread.Stop()
        if self.training_thread:
            self.training_thread.Stop()
        if self.load_forecast_pub:
            self.logger.info("Stopping load forecast thread")
            self.load_forecast_pub.Stop()
        if self.raw_data:
            self.raw_data.exit()
        self.logger.info("load controller thread exited")


class Training(threading.Thread):
    """
    - Load data points from file
    - Wait till num_timesteps + output_size + 5 points to train for the first time
    - After initial training, Train model once in 24 hr
    - Create a new model, compile, and train
    - Save the checkpoints model in model_train.h5
    - After training is completed, copy the model_train.h5 to model.h5
    """

    def __init__(self, control_frequency, horizon_in_steps, num_timesteps, hidden_size, batch_size, num_epochs, raw_data_file, processingData,
                 model_file_container, model_file_container_train, topic_name, id, dT_in_seconds, output_size, log):
        super().__init__()
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.num_epochs = num_epochs  # 10
        self.min_training_size = num_timesteps + output_size + 5
        self.model_file_container = model_file_container
        self.model_file_container_train = model_file_container_train
        self.today = datetime.datetime.now().day
        self.processingData = processingData
        self.trained = False
        self.raw_data_file = raw_data_file
        self.stopRequest = threading.Event()
        self.redisDB = RedisDB()
        self.training_lock_key = "training_lock"
        self.topic_name = topic_name
        self.id = id
        self.dT_in_seconds = dT_in_seconds
        self.output_size = output_size
        self.logger = log

    def run(self):
        while not self.stopRequest.is_set():
            try:
                train = self.checktime()
                self.today = datetime.datetime.now()
                if train:
                    # get raw data from file
                    from prediction.rawDataReader import RawDataReader
                    # at-most last 5 days' data
                    data = RawDataReader.get_raw_data(self.raw_data_file, 7200, self.topic_name) #7200 = 5 days data
                    self.logger.debug("raw data ready " + str(len(data)))
                    data, merged = self.processingData.expand_and_resample_into_blocks(data, self.dT_in_seconds, self.horizon_in_steps,
                                                                               self.num_timesteps, self.output_size)
                    if self.sufficient_data_available(data):
                        self.trained = True
                        self.logger.info("start training")
                        Xtrain, Ytrain = self.processingData.preprocess_data_train(data, self.num_timesteps, self.output_size)
                        self.logger.info("pre proc done")
                        try:
                            if self.redisDB.get_lock(self.training_lock_key, self.id+"_"+self.topic_name):
                                from prediction.trainModel import TrainModel
                                trainModel = TrainModel(self.stop_request_status)
                                trainModel.train(Xtrain, Ytrain, self.num_epochs, self.batch_size, self.hidden_size,
                                                 self.num_timesteps, self.output_size, self.model_file_container_train)
                                copyfile(self.model_file_container_train, self.model_file_container)
                                self.logger.info("trained successfully")
                        except Exception as e:
                            self.trained = False
                            self.logger.error("error training model " + str(e))
                        finally:
                            self.redisDB.release_lock(self.training_lock_key, self.id+"_"+self.topic_name)
                    else:
                        time.sleep(600)
                time.sleep(60)
            except Exception as e:
                self.logger.error("training thread exception "+str(e))

    def checktime(self):
        return (not self.trained or datetime.datetime.now().day > self.today.day
                or datetime.datetime.now().month > self.today.month
                or datetime.datetime.now().year > self.today.year)

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
            self.logger.info("length of block = "+str(len(block)))
            if len(block) >= self.min_training_size:
                return True
        return False

class Prediction(threading.Thread):

    """
    - As soon as the number of data points is num_timesteps, prediction starts
    - If model.h5 present in disk
        then present then use model.h5
        else load model_temp.h5 from disk (temp pre-trained model)
    - predict for next horizon points (eg. 24 predictions)
    """
    def __init__(self, control_frequency, horizon_in_steps, num_timesteps, hidden_size, batch_size, num_epochs, raw_data, processingData,
                 model_file_container_temp, model_file_container, q, topic_name, id, dT_in_seconds, output_size, log):
        super().__init__()
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.dT_in_seconds = dT_in_seconds
        self.batch_size = batch_size
        self.num_epochs = num_epochs  # 10
        self.raw_data = raw_data
        self.processingData = processingData
        self.model_file_container_temp = model_file_container_temp
        self.model_file_container = model_file_container
        self.q = q
        self.stopRequest = threading.Event()
        from prediction.Models import Models
        self.models = Models(self.num_timesteps, self.hidden_size, self.batch_size, self.model_file_container,
                        self.model_file_container_temp)
        self.topic_name = topic_name
        self.id = id
        self.output_size = output_size
        self.logger = log

    def run(self):
        while not self.stopRequest.is_set():
            try:
                data = self.raw_data.get_raw_data(train=False, topic_name=self.topic_name)
                self.logger.debug("len data = " + str(len(data)))
                data = self.processingData.expand_and_resample(data, self.dT_in_seconds)
                self.logger.debug("len resample data = " + str(len(data)))
                true_data = data
                if len(data) > 0:
                    data = self.processingData.append_mock_data(data, self.num_timesteps, self.dT_in_seconds)
                    self.logger.debug("len appended data = " + str(len(data)))
                if len(data) >= self.num_timesteps:
                    st = time.time()
                    test_predictions = []
                    model, model_temp, temp_flag, graph = self.models.get_model(self.id+"_"+self.topic_name)
                    if temp_flag:
                        self.logger.debug("temp flag true")
                        model = model_temp
                    if model is not None:
                        try:
                            Xtest, scaling, latest_timestamp = self.processingData.preprocess_data_predict(data, self.num_timesteps, self.output_size)
                            from prediction.predictModel import PredictModel
                            predictModel = PredictModel(self.stop_request_status)
                            test_predictions = predictModel.predict_next_horizon(model, Xtest, self.batch_size, graph)
                            data = self.processingData.postprocess_data(test_predictions, latest_timestamp, self.dT_in_seconds, scaling)
                            self.q.put(data)
                        except Exception as e:
                            self.logger.error(str(e))
                    else:
                        self.logger.info("prediction model is none, extending the known values")
                        test_predictions = self.processingData.get_regression_values(true_data, self.num_timesteps, self.output_size + 1, self.dT_in_seconds)
                        self.q.put(test_predictions)
                    self.logger.debug(str(self.topic_name)+" predictions " + str(len(test_predictions)))
                    st = time.time() - st
                    ss = self.control_frequency - st
                    if ss < 0:
                        ss = 0
                    time.sleep(ss)
                else:
                    time.sleep(1)
            except Exception as e:
                self.logger.error(str(self.topic_name) + " prediction thread exception " + str(e))

    def Stop(self):
        self.logger.info("start prediction thread exit")
        self.stopRequest.set()
        if self.isAlive():
            self.join(4)
        self.logger.info("prediction thread exited")

    def stop_request_status(self):
        return self.stopRequest.is_set()