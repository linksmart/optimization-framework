"""
Created on Dez 07 16:08 2018

@author: nishit
"""
from shutil import copyfile

from prediction.offlineProcessingData import OfflineProcessingData

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

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
        self.min_training_size = num_timesteps + output_size + 5
        self.model_file_container = model_file_container
        self.model_file_container_train = model_file_container_train
        self.processingData = OfflineProcessingData()
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
            data, merged = self.processingData.expand_and_resample_into_blocks(data, self.dT_in_seconds, self.horizon_in_steps,
                                                                       self.num_timesteps, self.output_size)
            if merged or self.sufficient_data_available(data):
                logger.info("start training")
                Xtrain, Xtest, Ytrain, Ytest = self.processingData.preprocess_data_train(data, self.num_timesteps, self.output_size)
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

    def sufficient_data_available(self, data_blocks):
        for block in data_blocks:
            logger.info("length of block = "+str(len(block)))
            if len(block) >= self.min_training_size:
                return True
        return False

    def stop_request_status(self):
        return False