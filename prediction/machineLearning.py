import os

from IO.redisDB import RedisDB
from prediction.Models import Models
from prediction.processingData import ProcessingData
from utils_intern.messageLogger import MessageLogger


class MachineLearning:

    def __init__(self, horizon_in_steps, topic_name, dT_in_seconds, id):
        super(MachineLearning, self).__init__()
        self.logger = MessageLogger.get_logger(__name__, id)

        self.horizon_in_steps = horizon_in_steps
        self.topic_name = topic_name
        self.dT_in_seconds = dT_in_seconds
        self.id = id

        self.model_data_dT = 60
        self.input_size = 1440
        self.hidden_size = 100
        self.batch_size = 1
        self.num_epochs = 10
        self.output_size = 1440

        base_path = "/usr/src/app/prediction/resources"
        dir_data = os.path.join(base_path, self.id)
        if not os.path.exists(dir_data):
            os.makedirs(dir_data)

        self.raw_data_file_container = os.path.join(base_path, self.id,
                                                    "raw_data_" + str(topic_name) + ".csv")
        self.model_file_container = os.path.join(base_path, self.id,
                                                 "model_" + str(topic_name) + ".h5")
        self.model_file_container_temp = os.path.join(base_path, self.id,
                                                      "model_temp_" + str(topic_name) + ".h5")
        self.model_file_container_train = os.path.join(base_path, self.id,
                                                       "model_train_" + str(topic_name) + ".h5")
        self.model_file_container_base = os.path.join("/usr/src/app/prediction/model", "model_base.h5")

        self.processingData = ProcessingData()
        self.redisDB = RedisDB()

        self.load_forecast_pub = None
        self.prediction_thread = None
        self.training_thread = None
        self.raw_data = None
        self.models = Models(self.model_file_container, self.model_file_container_temp, self.model_file_container_base)
