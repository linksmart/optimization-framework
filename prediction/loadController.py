"""
Created on Jun 28 11:22 2018

@author: nishit
"""
import datetime
import json
import logging
import threading
from queue import Queue

import time

from optimization.loadForecastPublisher import LoadForecastPublisher
from prediction.LSTMmodel import LSTMmodel
from prediction.modelPrediction import ModelPrediction
from prediction.processingData import ProcessingData
from prediction.rawDataReceiver import RawDataReceiver
from prediction.trainModel import TrainModel

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class LoadController(threading.Thread):

    def __init__(self, config):
        super().__init__()
        self.stopRequest = threading.Event()

        raw_data_topic = config.get("IO", "raw.data.topic")
        raw_data_topic = json.loads(raw_data_topic)
        topics = [raw_data_topic]
        self.raw_data = RawDataReceiver(topics, config)
        self.processingData = ProcessingData()

        self.q = Queue(maxsize=0)

        load_forecast_topic = config.get("IO", "load.forecast.topic")
        load_forecast_topic = json.loads(load_forecast_topic)
        self.load_forecast_pub = LoadForecastPublisher(load_forecast_topic, config, self.q)
        self.load_forecast_pub.start()

        self.predicted_data = None

        self.num_timesteps = 200
        self.hidden_size = 10
        self.batch_size = 1
        self.num_epochs = 1

        self.lstmModel = LSTMmodel(self.num_timesteps, self.hidden_size, self.batch_size)
        self.trainModel = TrainModel()
        self.modelPrediction = ModelPrediction()

        self.train = False
        self.today = datetime.datetime.now().day

    def run(self):
        while not self.stopRequest.is_set():
            # get raw data from mqtt/zmq
            data = self.raw_data.get_data(1)
            logger.debug("raw data ready")

            model, created = self.lstmModel.model_setup()
            train = created or self.checktime()
            self.today = datetime.datetime.now()
            if train:
                # preprocess data
                Xtrain, Xtest, Ytrain, Ytest = self.processingData.preprocess_data(data, self.num_timesteps, True)

                # train if required
                self.trainModel.train(model, Xtrain, Ytrain, self.num_epochs, self.batch_size)

                # evaluate if required
                self.modelPrediction.evaluate(model, Xtest, Ytest, self.batch_size)

                # save model
                self.lstmModel.persist_model(model)

                self.train = True
            else:
                # preprocess data
                Xtest = self.processingData.preprocess_data(data, self.num_timesteps, False)

            # predict if required
            prediction = self.modelPrediction.predict(model, Xtest, self.batch_size)

            #post processing
            test_actual, test_act = self.processingData.add_date_time_test(Ytest)
            test_predictions = self.processingData.add_date_time_pred(prediction, test_act)

            logger.debug("predictions "+str(test_predictions))
            self.predicted_data = test_predictions

            data = self.processingData.to_python_dict_data(self.predicted_data)

            self.q.put(data)

            time.sleep(60)
            # for testing

    def checktime(self):
        return (not self.train or datetime.datetime.now().day > self.today.day
        or datetime.datetime.now().month > self.today.month
        or datetime.datetime.now().year > self.today.year)

    def Stop(self):
        logger.info("start load controller thread exit")
        logger.info("Stopping load forecast thread")
        #self.load_forecast_pub.Stop()
        self.stopRequest.set()
        if self.isAlive():
            self.join()
        logger.info("load controller thread exit")