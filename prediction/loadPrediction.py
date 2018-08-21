import datetime
import json
import logging
import threading
from queue import Queue
import time

import os

from prediction.utils import Utils
from optimization.loadForecastPublisher import LoadForecastPublisher
from prediction.LSTMmodel import LSTMmodel
from prediction.modelPrediction import ModelPrediction
from prediction.processingData import ProcessingData
from prediction.rawLoadDataReceiver import RawLoadDataReceiver
from prediction.trainModel import TrainModel

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class LoadPrediction(threading.Thread):

    def __init__(self, config, input_config_parser, timesteps, horizon, topic):
        super().__init__()
        self.stopRequest = threading.Event()

        self.topic = topic
        self.length = timesteps
        self.length = 24
        self.horizon = horizon
        self.num_timesteps = 25
        self.hidden_size = 40
        self.batch_size = 1
        self.num_epochs = 1  # 10
        self.min_training_size = self.num_timesteps+10

        self.utils = Utils()
        self.raw_data_file_container = os.path.join("/usr/src/app", "prediction", "raw_data.csv")
        self.raw_data_file_host = os.path.join("/usr/src/app", "prediction/resources", "raw_data.csv")
        self.model_file_container = os.path.join("/usr/src/app", "prediction", "model.h5")
        self.model_file_container_temp = os.path.join("/usr/src/app", "prediction", "model_temp.h5")
        self.model_file_host = os.path.join("/usr/src/app", "prediction/resources", "model.h5")
        self.utils.copy_files_from_host(self.raw_data_file_host, self.raw_data_file_container)
        self.utils.copy_files_from_host(self.model_file_host, self.model_file_container)

        self.input_config_parser = input_config_parser

        topic = self.input_config_parser.get_params("P_Load")
        self.raw_data = RawLoadDataReceiver(topic, config, self.num_timesteps, 24 * 10, self.raw_data_file_container)
        self.processingData = ProcessingData()

        self.q = Queue(maxsize=0)

        load_forecast_topic = config.get("IO", "load.forecast.topic")
        load_forecast_topic = json.loads(load_forecast_topic)
        self.load_forecast_pub = LoadForecastPublisher(load_forecast_topic, config, self.q, 60, self.topic)
        self.load_forecast_pub.start()

        self.predicted_data = None

        self.lstmModel = LSTMmodel(self.num_timesteps, self.hidden_size, self.batch_size, self.model_file_container, self.model_file_container_temp)
        self.trainModel = TrainModel(self.model_file_container)
        self.modelPrediction = ModelPrediction()

        self.trained = False
        self.today = datetime.datetime.now().day
        self.train_thread = None

    def run(self):
        while not self.stopRequest.is_set():
            model, model_temp, created, temp_flag = self.lstmModel.model_setup()
            train = created or self.checktime()
            self.today = datetime.datetime.now()
            # get raw data from mqtt/zmq
            data = self.raw_data.get_raw_data(train)
            logger.debug("raw data ready " + str(len(data)))
            test_predictions = []
            if train:
                self.train_thread = threading.Thread(target=self.train_model, args=(data, model,))
                self.train_thread.start()
            else:
                # preprocess data
                logger.info("len data = "+str(len(data)))
                if len(data) >= self.num_timesteps:
                    if temp_flag:
                        model = model_temp
                    if model is not None:
                        Xtest = self.processingData.preprocess_data(data, self.num_timesteps, False)
                        test_predictions = self.modelPrediction.predict_next_day(model, Xtest, self.batch_size, self.length)
                        data = self.processingData.to_dict_with_datetime(test_predictions,
                                                                         datetime.datetime(datetime.datetime.now().year, 12, 11,
                                                                                           6, 0), 60)
                    else:
                        logger.info("prediction  model is none")
                        self.q.put(data)
            logger.debug("predictions "+str(test_predictions))

            time.sleep(1)
            # for testing

    def checktime(self):
        return (not self.trained or datetime.datetime.now().day > self.today.day
                or datetime.datetime.now().month > self.today.month
                or datetime.datetime.now().year > self.today.year)

    def Stop(self):
        logger.info("start load controller thread exit")
        logger.info("Stopping load forecast thread")
        self.stopRequest.set()
        self.load_forecast_pub.Stop()
        self.trainModel.Stop()
        if self.isAlive():
            self.join()
        logger.info("load controller thread exit")

    def save_file_to_host(self):
        self.utils.copy_files_to_host(self.raw_data_file_container, self.raw_data_file_host)
        pass

    def train_model(self, data, model):
        # preprocess data
        try:
            if len(data) > self.min_training_size:
                self.trained = True
                logger.info("start training")
                Xtrain, Xtest, Ytrain, Ytest = self.processingData.preprocess_data(data, self.num_timesteps, True)
                # train if required
                self.trainModel.train(model, Xtrain, Ytrain, self.num_epochs, self.batch_size)
                # evaluate if required
                self.modelPrediction.evaluate(model, Xtest, Ytest, self.batch_size)
                self.save_file_to_host()
        except Exception as e:
            self.trained = False
            logger.error("error training model "+str(e))