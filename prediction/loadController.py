"""
Created on Jun 28 11:22 2018

@author: nishit
"""
import json
import logging
import threading

from prediction.LSTM_LookBack import LSTMLookBack
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
        

        self.num_timesteps = 200
        self.hidden_size = 10
        self.batch_size = 1
        self.num_epochs = 1

        self.lstmModel = LSTMmodel(self.num_timesteps, self.hidden_size, self.batch_size)
        self.trainModel = TrainModel()
        self.modelPrediction = ModelPrediction()


    def run(self):
        while not self.stopRequest.is_set():
            # get raw data from mqtt/zmq
            data = self.raw_data.get_data()
            logger.info("raw data ready")
            # preprocess data
            Xtrain, Xtest, Ytrain, Ytest = self.processingData.preprocess_data(data, self.num_timesteps)


            model = self.lstmModel.model_setup()
            # train if required
            self.trainModel.train(model, Xtrain, Ytrain, self.num_epochs, self.batch_size)

            # evaluate if required
            self.modelPrediction.evaluate(model, Xtest, Ytest, self.batch_size)


            # predict if required
            prediction = self.modelPrediction.predict(model, Xtest, self.batch_size)

            logger.info("predictions "+str(prediction))

            #post processing
            test_actual, test_act = self.processingData.add_date_time_test(Ytest)
            test_predictions = self.processingData.add_date_time_pred(prediction, test_act)

            logger.info("predictions "+str(test_predictions))

            # for testing
            break

    """
    def run(self):
        lstm = LSTMLookBack()
        lstm.r()
    """

    def Stop(self):
        logger.info("start load controller thread exit")
        self.stopRequest.set()
        if self.isAlive():
            self.join()
        logger.info("load controller thread exit")