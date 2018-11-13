import datetime
import json
import logging
import threading
from queue import Queue
import time

import os
from shutil import copyfile

from IO.redisDB import RedisDB
from prediction.processingData import ProcessingData

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

"""
Creates a thread for prediction and a thread for training
"""
class LoadPrediction:

    def __init__(self, config, control_frequency, horizon_in_steps, topic_name, topic_param, dT_in_seconds, id, predictionFlag):
        self.stopRequest = threading.Event()

        self.predictionFlag = predictionFlag

        self.topic_name = topic_name
        self.control_frequency = control_frequency  # determines minute or hourly etc
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.num_timesteps = 25
        self.hidden_size = 40
        self.batch_size = 1
        self.num_epochs = 2  # 10
        self.id = id

        self.raw_data_file_container = os.path.join("/usr/src/app", "res", "raw_data_"+str(topic_name)+".csv")
        self.model_file_container = os.path.join("/usr/src/app", "res", "model_"+str(topic_name)+".h5")
        self.model_file_container_temp = os.path.join("/usr/src/app", "res", "model_temp_"+str(topic_name)+".h5")
        self.model_file_container_train = os.path.join("/usr/src/app", "res", "model_train_"+str(topic_name)+".h5")

        self.processingData = ProcessingData()

        self.load_forecast_pub = None
        self.prediction_thread = None
        self.training_thread = None

        total_mins = int(float(self.horizon_in_steps * self.dT_in_seconds)/60.0) + 1
        if total_mins < self.num_timesteps:
            total_mins = self.num_timesteps

        if self.predictionFlag:
            from prediction.rawLoadDataReceiver import RawLoadDataReceiver
            self.raw_data = RawLoadDataReceiver(topic_param, config, total_mins, self.horizon_in_steps * 25,
                                                self.raw_data_file_container)

            self.q = Queue(maxsize=0)

            from optimization.loadForecastPublisher import LoadForecastPublisher
            load_forecast_topic = config.get("IO", "load.forecast.topic")
            load_forecast_topic = json.loads(load_forecast_topic)
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
                                        self.model_file_container_train, self.topic_name, self.id, self.dT_in_seconds)
        self.training_thread.start()

    def startPrediction(self):
        self.prediction_thread = Prediction(self.control_frequency, self.horizon_in_steps, self.num_timesteps,
                                            self.hidden_size, self.batch_size, self.num_epochs,
                                            self.raw_data, self.processingData, self.model_file_container_temp,
                                            self.model_file_container, self.q, self.topic_name, self.id, self.dT_in_seconds)
        self.prediction_thread.start()


    def Stop(self):
        logger.info("start load controller thread exit")
        logger.info("Stopping load forecast thread")
        self.stopRequest.set()
        if self.prediction_thread:
            self.prediction_thread.Stop()
        if self.training_thread:
            self.training_thread.Stop()
        if self.load_forecast_pub:
            self.load_forecast_pub.Stop()
        if self.raw_data:
            self.raw_data.exit()
        logger.info("load controller thread exit")


class Training(threading.Thread):
    """
    - Load data points from file
    - Wait till 55 points to train for the first time
    - After initial training, Train model once in 24 hr
    - Create a new model, compile, and train
    - Save the checkpoints model in model_train.h5
    - After training is completed, copy the model_train.h5 to model.h5
    """

    def __init__(self, control_frequency, horizon_in_steps, num_timesteps, hidden_size, batch_size, num_epochs, raw_data_file, processingData,
                 model_file_container, model_file_container_train, topic_name, id, dT_in_seconds):
        super().__init__()
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.num_epochs = num_epochs  # 10
        self.min_training_size = self.num_timesteps + 30
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

    def run(self):
        while not self.stopRequest.isSet():
            try:
                train = self.checktime()
                self.today = datetime.datetime.now()
                if train:
                    # get raw data from file
                    from prediction.rawDataReader import RawDataReader
                    # atmost last 5 days' data
                    data = RawDataReader.get_raw_data(self.raw_data_file, 7200, self.topic_name)
                    logger.debug("raw data ready " + str(len(data)))
                    data = self.processingData.resample(data, self.dT_in_seconds)
                    logger.debug("resampled data ready " + str(len(data)))
                    if len(data) > self.min_training_size:
                        self.trained = True
                        logger.info("start training")
                        Xtrain, Xtest, Ytrain, Ytest = self.processingData.preprocess_data(data, self.num_timesteps, True)

                        # preprocess data
                        try:
                            if self.redisDB.get_lock(self.training_lock_key, self.id+"_"+self.topic_name):
                                from prediction.trainModel import TrainModel
                                trainModel = TrainModel()
                                trainModel.train(Xtrain, Ytrain, self.num_epochs, self.batch_size, self.hidden_size,
                                                 self.num_timesteps, self.model_file_container_train)
                                copyfile(self.model_file_container_train, self.model_file_container)
                                logger.info("trained successfully")
                        except Exception as e:
                            self.trained = False
                            logger.error("error training model " + str(e))
                        finally:
                            self.redisDB.release_lock(self.training_lock_key, self.id+"_"+self.topic_name)
                time.sleep(1)
            except Exception as e:
                logger.error("training thread exception "+str(e))

    def checktime(self):
        return (not self.trained or datetime.datetime.now().day > self.today.day
                or datetime.datetime.now().month > self.today.month
                or datetime.datetime.now().year > self.today.year)

    def Stop(self):
        logger.info("start load controller thread exit")
        logger.info("Stopping load forecast thread")
        self.stopRequest.set()
        if self.isAlive():
            self.join()
        logger.info("load controller thread exit")

class Prediction(threading.Thread):

    """
    - As soon as the number of data points is 25, prediction starts
    - If model.h5 present in disk
        then present then use model.h5
        else load model_temp.h5 from disk (temp pre-trained model)
    - predict for next 24 points (24 predictions)
    """
    def __init__(self, control_frequency, horizon_in_steps, num_timesteps, hidden_size, batch_size, num_epochs, raw_data, processingData,
                 model_file_container_temp, model_file_container, q, topic_name, id, dT_in_seconds):
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

    def mock_data(self):
        vals = [-2658.819940570742,-2213.156421120333,-2293.300383523349,-2511.985862220086,
                -2599.873615357683,-2046.833423637462,-2236.293011239444,-2511.570352025292,
                -2424.498109073549,-2824.992998080974,-2824.558536866195,-1953.771180819606,
                -1800.771180819606,-1700.771180819606,-2000.771180819606,-2200.771180819606,
                -2500.771180819606,-2400.771180819606,-2800.771180819606,-2700.771180819606,
                -1950.771180819606,-2200.771180819606,-2500.771180819606,-2600.771180819606,
                -2300.771180819606]

        date = datetime.datetime.now().replace(second=0, microsecond=0)
        new_data = []
        for val in reversed(vals):
            new_data.append([int(date.timestamp()), val])
            date = date - datetime.timedelta(seconds=self.dT_in_seconds)
        new_data.reverse()
        return new_data

    def run(self):
        while not self.stopRequest.isSet():
            try:
                data = self.raw_data.get_raw_data(train=False, topic_name=self.topic_name)
                logger.debug("len data = " + str(len(data)))
                data = self.processingData.resample(data, self.dT_in_seconds)
                logger.debug("len resample data = " + str(len(data)))
                if len(data) > 0:
                    data = self.processingData.append_mock_data(data, self.num_timesteps, self.dT_in_seconds)
                    logger.debug("len appended data = " + str(len(data)))
                #data = self.mock_data()
                if len(data) >= self.num_timesteps:
                    st = time.time()
                    test_predictions = []
                    model, model_temp, temp_flag, graph = self.models.get_model(self.id+"_"+self.topic_name)
                    if temp_flag:
                        logger.debug("temp flag true")
                        model = model_temp
                    if model is not None:
                        try:
                            Xtest, scaling, latest_timestamp = self.processingData.preprocess_data(data, self.num_timesteps, False)
                            from prediction.predictModel import PredictModel
                            predictModel = PredictModel()
                            test_predictions = predictModel.predict_next_day(model, Xtest, self.batch_size, self.horizon_in_steps, graph, data)
                            data = self.processingData.postprocess_data(test_predictions, latest_timestamp, self.dT_in_seconds, scaling)
                            self.q.put(data)
                        except Exception as e:
                            logger.error(str(e))
                    else:
                        logger.info("prediction  model is none")
                    logger.debug(str(self.topic_name)+" predictions " + str(len(test_predictions)))
                    st = time.time() - st
                    ss = self.control_frequency - st
                    if ss < 0:
                        ss = 0
                    time.sleep(ss)
                else:
                    time.sleep(1)
            except Exception as e:
                logger.error(str(self.topic_name) + " prediction thread exception " + str(e))

    def Stop(self):
        logger.info("start load controller thread exit")
        logger.info("Stopping load forecast thread")
        self.stopRequest.set()
        if self.isAlive():
            self.join()
        logger.info("load controller thread exit")