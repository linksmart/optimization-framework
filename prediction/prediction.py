import datetime
import json
import os
import threading
import time
from queue import Queue

from optimization.forecastPublisher import ForecastPublisher
from prediction.errorReporting import ErrorReporting
from prediction.machineLearning import MachineLearning
from prediction.predictionDataManager import PredictionDataManager
from prediction.rawLoadDataReceiver import RawLoadDataReceiver
from utils_intern.constants import Constants
from utils_intern.timeSeries import TimeSeries
from utils_intern.utilFunctions import UtilFunctions


class Prediction(MachineLearning, threading.Thread):
    """
    - As soon as the number of data points is num_timesteps, prediction starts
    - If model_base.h5 present in disk
        then present then use model_base.h5
        else load model_temp.h5 from disk (temp pre-trained model)
    - predict for next horizon points (eg. 24 predictions)
    """

    def __init__(self, config, control_frequency, horizon_in_steps, topic_name, topic_param, dT_in_seconds, id,
                 output_config, type, opt_values):
        super(Prediction, self).__init__(config, horizon_in_steps, topic_name, dT_in_seconds, id, type, opt_values)

        self.stopRequest = threading.Event()
        self.control_frequency = 60
        self.output_config = output_config

        self.prediction_data_file_container = os.path.join("/usr/src/app", "prediction/resources", self.id,
                                                           "prediction_data_" + str(topic_name) + ".csv")
        self.error_result_file_path = os.path.join("/usr/src/app", "prediction/resources", self.id,
                                                   "error_data_" + str(topic_name) + ".csv")

        self.max_file_size_mins = config.getint("IO", str(self.type)+".raw.data.file.size", fallback=10800)

        total_mins = int(float(self.input_size * self.model_data_dT) / 60.0) + 1
        self.raw_data = RawLoadDataReceiver(topic_param, config, total_mins,
                                            self.raw_data_file_container, self.topic_name, self.id, True,
                                            self.max_file_size_mins)

        self.q = Queue(maxsize=0)

        forecast_topic = config.get("IO", "forecast.topic")
        forecast_topic = json.loads(forecast_topic)
        forecast_topic["topic"] = forecast_topic["topic"] + self.topic_name
        self.forecast_pub = ForecastPublisher(forecast_topic, config, self.q,
                                              60, self.topic_name, self.id,
                                              self.horizon_in_steps, self.dT_in_seconds)
        self.forecast_pub.start()

        error_topic_params = config.get("IO", "error.topic")
        error_topic_params = json.loads(error_topic_params)
        error_topic_params["topic"] = error_topic_params["topic"] + self.topic_name
        self.error_reporting = ErrorReporting(config, id, topic_name, dT_in_seconds, control_frequency,
                                              horizon_in_steps, self.prediction_data_file_container,
                                              self.raw_data_file_container, error_topic_params,
                                              self.error_result_file_path, self.output_config)
        self.error_reporting.start()

        self.old_predictions = []
        self.prediction_save_thread = threading.Thread(target=self.save_to_file_cron)
        self.prediction_save_thread.start()

    def run(self):
        while not self.stopRequest.is_set():
            if not self.redisDB.get_bool(Constants.get_data_flow_key(self.id)):
                time.sleep(30)
                continue
            try:
                data = self.raw_data.get_raw_data()
                self.logger.debug("len data = " + str(len(data)))
                data = TimeSeries.expand_and_resample(data, 60)
                self.logger.debug("len resample data = " + str(len(data)))
                true_data = data
                if len(data) > 0:
                    data = self.processingData.append_mock_data(data, self.input_size, 60)
                    self.logger.debug("len appended data = " + str(len(data)))
                if len(data) > self.input_size:
                    st = time.time()
                    test_predictions = []
                    model, graph = self.models.get_model(self.id + "_" + self.topic_name, True)
                    predicted_flag = False
                    if model is not None and graph is not None:
                        if self.type == "load":
                            Xtest, Xmax, Xmin, latest_timestamp = self.processingData.preprocess_data_predict_load(data,
                                                                                                              self.input_size)
                        else:
                            Xtest, Xmax, Xmin, latest_timestamp = self.processingData.preprocess_data_predict_pv(data,
                                                                                                              self.input_size,
                                                                                                              self.input_size_hist)
                        try:
                            self.logger.debug(
                                "model present, so predicting data for " + str(self.id) + " " + str(self.topic_name))
                            from prediction.predictModel import PredictModel
                            predictModel = PredictModel(self.stop_request_status)
                            prediction_time = time.time()
                            test_predictions = predictModel.predict_next_horizon(model, Xtest, self.batch_size, graph, self.type)
                            self.logger.debug("Prediction successful for " + str(self.id) + " " + str(self.topic_name) +
                                              " which took "+str(time.time()-prediction_time) + " seconds")
                            predicted_flag = True
                        except Exception as e:
                            predicted_flag = False
                            self.models.remove_saved_model()
                            self.logger.error("exception when prediction using model : " + str(e))

                        if predicted_flag:
                            test_predictions = self.processingData.postprocess_data(test_predictions, latest_timestamp,
                                                                                    self.dT_in_seconds,
                                                                                    self.horizon_in_steps, Xmax, Xmin)
                            self.logger.debug("predictions values Xmax "+str(Xmax)+" Xmin "+str(Xmin))
                            self.q.put(test_predictions)
                            self.old_predictions.append(test_predictions)

                    if not predicted_flag:
                        self.logger.info("prediction model is none, extending the known values")
                        data = TimeSeries.expand_and_resample(true_data, self.dT_in_seconds)
                        test_predictions = self.processingData.get_regression_values(data, self.input_size,
                                                                                     self.output_size + 1,
                                                                                     self.dT_in_seconds)
                        self.q.put(test_predictions)

                    self.logger.debug(str(self.topic_name) + " predictions " + str(len(test_predictions)))
                    st = time.time() - st
                    ss = self.control_frequency - st
                    if ss < 0:
                        ss = 0
                    time.sleep(ss)
                else:
                    time.sleep(1)
            except Exception as e:
                self.logger.error(str(self.topic_name) + " prediction thread exception " + str(e))

    def save_to_file_cron(self):
        self.logger.debug("Started save file cron")
        while True and not self.stopRequest.is_set():
            self.old_predictions = PredictionDataManager.save_predictions_to_file(self.old_predictions,
                                                                                  self.horizon_in_steps,
                                                                                  self.prediction_data_file_container,
                                                                                  self.topic_name)
            time.sleep(UtilFunctions.get_sleep_secs(1, 0, 0))

    def Stop(self):
        self.logger.info("start prediction thread exit")
        if self.forecast_pub:
            self.logger.info("Stopping load forecast thread")
            self.forecast_pub.Stop()
        if self.error_reporting:
            self.error_reporting.Stop()
        if self.raw_data:
            self.raw_data.exit()
        self.stopRequest.set()
        if self.isAlive():
            self.join(4)
        self.logger.info("prediction thread exited")

    def stop_request_status(self):
        return self.stopRequest.is_set()
