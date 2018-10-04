import datetime
import json
import logging
import threading
from queue import Queue
import time

import os
from shutil import copyfile

from prediction.processingData import ProcessingData

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

"""
Creates a thread for prediction and a thread for training
"""
class LoadPrediction:

    def __init__(self, config, timesteps, horizon, topic_name, topic_param, id, predictionFlag):
        self.stopRequest = threading.Event()

        self.predictionFlag = predictionFlag

        self.topic_name = topic_name
        self.length = timesteps
        self.length = 24
        self.horizon = horizon
        self.num_timesteps = 25
        self.hidden_size = 40
        self.batch_size = 1
        self.num_epochs = 2  # 10
        self.min_training_size = self.num_timesteps+10
        self.id = id

        self.raw_data_file_container = os.path.join("/usr/src/app", "res", "raw_data_"+str(topic_name)+".csv")
        self.model_file_container = os.path.join("/usr/src/app", "res", "model_"+str(topic_name)+".h5")
        self.model_file_container_temp = os.path.join("/usr/src/app", "res", "model_temp_"+str(topic_name)+".h5")
        self.model_file_container_train = os.path.join("/usr/src/app", "res", "model_train_"+str(topic_name)+".h5")

        self.processingData = ProcessingData()

        self.load_forecast_pub = None
        self.prediction_thread = None
        self.training_thread = None

        if self.predictionFlag:
            from prediction.rawLoadDataReceiver import RawLoadDataReceiver
            self.raw_data = RawLoadDataReceiver(topic_param, config, self.num_timesteps, 24 * 10,
                                                self.raw_data_file_container)

            self.q = Queue(maxsize=0)

            from optimization.loadForecastPublisher import LoadForecastPublisher
            load_forecast_topic = config.get("IO", "load.forecast.topic")
            load_forecast_topic = json.loads(load_forecast_topic)
            self.load_forecast_pub = LoadForecastPublisher(load_forecast_topic, config, self.q, 60, self.topic_name, self.id)
            self.load_forecast_pub.start()

            self.startPrediction()
        else:
            self.startTraining()

    def startTraining(self):
        self.training_thread = Training(self.length, self.horizon, self.num_timesteps,
                                        self.hidden_size, self.batch_size, self.num_epochs,
                                        self.raw_data_file_container, self.processingData, self.model_file_container,
                                        self.model_file_container_train)
        self.training_thread.start()

    def startPrediction(self):
        self.prediction_thread = Prediction(self.length, self.horizon, self.num_timesteps,
                                            self.hidden_size, self.batch_size, self.num_epochs,
                                            self.raw_data, self.processingData, self.model_file_container_temp,
                                            self.model_file_container, self.q, self.topic_name)
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

    def __init__(self, timesteps, horizon, num_timesteps, hidden_size, batch_size, num_epochs, raw_data_file, processingData,
                 model_file_container, model_file_container_train):
        super().__init__()
        self.length = timesteps
        self.length = 24
        self.horizon = horizon
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

    def run(self):
        while not self.stopRequest.isSet():
            try:
                train = self.checktime()
                self.today = datetime.datetime.now()
                if train:
                    # get raw data from file
                    from prediction.rawDataReader import RawDataReader
                    data = RawDataReader.get_raw_data(self.raw_data_file, 1000)
                    #data = self.raw_data.get_raw_data(train=True)
                    logger.debug("raw data ready " + str(len(data)))
                    if len(data) > self.min_training_size:
                        self.trained = True
                        logger.info("start training")
                        Xtrain, Xtest, Ytrain, Ytest = self.processingData.preprocess_data(data, self.num_timesteps, True)

                        # preprocess data
                        try:
                            from prediction.trainModel import TrainModel
                            trainModel = TrainModel()
                            trainModel.train(Xtrain, Ytrain, self.num_epochs, self.batch_size, self.hidden_size,
                                             self.num_timesteps, self.model_file_container_train)
                            copyfile(self.model_file_container_train, self.model_file_container)
                            logger.info("trained successfully")
                        except Exception as e:
                            self.trained = False
                            logger.error("error training model " + str(e))
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
    def __init__(self, timesteps, horizon, num_timesteps, hidden_size, batch_size, num_epochs, raw_data, processingData,
                 model_file_container_temp, model_file_container, q, topic):
        super().__init__()
        self.length = timesteps
        self.length = 24
        self.horizon = horizon
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.num_epochs = num_epochs  # 10
        self.min_training_size = self.num_timesteps + 30
        self.raw_data = raw_data
        self.processingData = processingData
        self.model_file_container_temp = model_file_container_temp
        self.model_file_container = model_file_container
        self.q = q
        self.stopRequest = threading.Event()
        from prediction.Models import Models
        self.models = Models(self.num_timesteps, self.hidden_size, self.batch_size, self.model_file_container,
                        self.model_file_container_temp)

    def run(self):
        ctr = 0
        while not self.stopRequest.isSet():
            try:
                data = self.raw_data.get_raw_data(train=False)
                logger.info("len data = " + str(len(data)))
                if len(data) >= self.num_timesteps:
                    ctr += 1
                    if ctr > 0:
                        logger.info("in predict")
                        test_predictions = []
                        model, model_temp, temp_flag, graph = self.models.get_model()
                        if temp_flag:
                            logger.info("temp flag true")
                            model = model_temp
                        if model is not None:
                            Xtest = self.processingData.preprocess_data(data, self.num_timesteps, False)
                            from prediction.predictModel import PredictModel
                            predictModel = PredictModel()
                            test_predictions = predictModel.predict_next_day(model, Xtest, self.batch_size, self.length, graph)
                            data = self.processingData.to_dict_with_datetime(test_predictions,
                                                                             datetime.datetime(datetime.datetime.now().year, 12, 11,
                                                                                               6, 0), 60)
                            self.q.put(data)
                        else:
                            logger.info("prediction  model is none")
                        logger.debug("predictions " + str(len(test_predictions)))
                time.sleep(1)
            except Exception as e:
                logger.error("prediction thread exception " + str(e))

    def Stop(self):
        logger.info("start load controller thread exit")
        logger.info("Stopping load forecast thread")
        self.stopRequest.set()
        if self.isAlive():
            self.join()
        logger.info("load controller thread exit")