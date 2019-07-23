"""
Created on Jan 21 13:05 2019

@author: nishit
"""
import time

from prediction.offlineProcessingData import OfflineProcessingData
from prediction.rawDataReader import RawDataReader

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class OfflinePrediction:

    def __init__(self, control_frequency, horizon_in_steps, num_timesteps, hidden_size, batch_size, num_epochs, raw_data_file,
                 model_file_container_temp, model_file_container, in_q, out_q, topic_name, id, dT_in_seconds, output_size):
        super().__init__()
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.dT_in_seconds = dT_in_seconds
        self.batch_size = batch_size
        self.num_epochs = num_epochs  # 10
        self.raw_data_file = raw_data_file
        self.processingData = OfflineProcessingData()
        self.model_file_container_temp = model_file_container_temp
        self.model_file_container = model_file_container
        self.in_q = in_q
        self.out_q = out_q
        from prediction.Models import Models
        self.models = Models(self.num_timesteps, self.hidden_size, self.batch_size, self.model_file_container,
                        self.model_file_container_temp)
        self.topic_name = topic_name
        self.id = id
        self.output_size = output_size

    def predict(self):
        try:
            #data = self.raw_data.get_raw_data(train=False, topic_name=self.topic_name)
            data = RawDataReader.get_raw_data(self.raw_data_file, 7200, self.topic_name)
            logger.debug("len data = " + str(len(data)))
            data = self.processingData.expand_and_resample(data, self.dT_in_seconds)
            logger.debug("len resample data = " + str(len(data)))
            true_data = data
            if len(data) >= self.num_timesteps:
                test_predictions = []
                model, model_temp, temp_flag, graph = self.models.get_model(self.id+"_"+self.topic_name)
                if temp_flag:
                    logger.debug("temp flag true")
                    model = model_temp
                if model is not None:
                    try:
                        Xtests, scaling, latest_timestamp = self.processingData.preprocess_data_predict(data, self.num_timesteps, self.output_size)
                        from prediction.predictModel import PredictModel
                        predictModel = PredictModel(self.stop_request_status)
                        for i in range(len(Xtests)-1):
                            Xtest = Xtests[i:i+1]
                            in_data = self.processingData.postprocess_data(Xtest.copy(), latest_timestamp,
                                                                        self.dT_in_seconds, scaling)
                            self.in_q.put(in_data)
                            test_predictions = predictModel.predict_next_horizon(model, Xtest, self.batch_size, graph)
                            data = self.processingData.postprocess_data(test_predictions, latest_timestamp+(self.num_timesteps*self.dT_in_seconds), self.dT_in_seconds, scaling)
                            self.out_q.put(data)
                            logger.debug(str(self.topic_name) + " predictions " + str(len(test_predictions)))
                            time.sleep(5)
                            i += self.num_timesteps
                    except Exception as e:
                        logger.error(str(e))
                else:
                    logger.info("prediction model is none, extending the known values")
        except Exception as e:
            logger.error(str(self.topic_name) + " prediction thread exception " + str(e))

    def stop_request_status(self):
        return False