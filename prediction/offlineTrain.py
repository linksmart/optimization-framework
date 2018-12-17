"""
Created on Dez 07 16:08 2018

@author: nishit
"""
import logging

from shutil import copyfile

from prediction.processingData import ProcessingData

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class OfflineTrain:

    def __init__(self, horizon_in_steps, num_timesteps, hidden_size, batch_size, num_epochs,
                 raw_data_file, model_file_container, model_file_container_train,
                 topic_name, id, dT_in_seconds, output_size):
        super().__init__()
        self.horizon_in_steps = horizon_in_steps
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.num_epochs = num_epochs  # 10
        self.min_training_size = self.num_timesteps + 30
        self.model_file_container = model_file_container
        self.model_file_container_train = model_file_container_train
        self.processingData = ProcessingData()
        self.raw_data_file = raw_data_file
        self.training_lock_key = "training_lock"
        self.topic_name = topic_name
        self.id = id
        self.dT_in_seconds = dT_in_seconds
        self.output_size = output_size


    def train(self):
        try:
            from prediction.rawDataReader import RawDataReader
            data = RawDataReader.get_raw_data(self.raw_data_file, 7200, self.topic_name)
            logger.debug("raw data ready " + str(len(data)))
            data = self.processingData.expand_and_resample(data, self.dT_in_seconds)
            logger.debug("resampled data ready " + str(len(data)))
            if len(data) > self.min_training_size:
                logger.info("start training")
                Xtrain, Xtest, Ytrain, Ytest = self.processingData.preprocess_data_train(data, self.num_timesteps,
                                                                                         self.output_size)
                logger.info("pre proc done")
                # preprocess data
                try:
                    from prediction.trainModel import TrainModel
                    trainModel = TrainModel(self.stop_request_status)
                    trainModel.train_and_evaluate(Xtrain, Ytrain, self.num_epochs, self.batch_size, self.hidden_size,
                                     self.num_timesteps, self.output_size, self.model_file_container_train, Xtest, Ytest)
                    copyfile(self.model_file_container_train, self.model_file_container)
                    logger.info("trained successfully")
                except Exception as e:
                    logger.error("error training model " + str(e))
        except Exception as e:
            logger.error("training thread exception " + str(e))

    def stop_request_status(self):
        return False