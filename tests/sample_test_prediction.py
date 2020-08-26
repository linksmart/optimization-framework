import logging
import os
from configparser import RawConfigParser
from prediction.prediction import Prediction
from prediction.processingData import ProcessingData
from prediction.rawDataReader import RawDataReader
from prediction.rawLoadDataReceiver import RawLoadDataReceiver
from utils_intern.messageLogger import MessageLogger
from utils_intern.timeSeries import TimeSeries

control_frequency = 60
horizon_in_steps = 24
topic_param = {"topic":"/Fronius/SMX/W_Load","qos":1,"mqtt.port":1883}
dT_in_seconds = 3600
topic_name = "P_Load"
id = "asdf"
logger = MessageLogger.set_and_get_logger_parent(id, "DEBUG", "ofw")

config = RawConfigParser()
config.read("ConfigFile.properties")

input_size = 1440
hidden_size = 100
batch_size = 1
num_epochs = 10
output_size = 1440

base_path = ""
dir_data = os.path.join(base_path, id)
if not os.path.exists(dir_data):
    os.makedirs(dir_data)

raw_data_file_container = os.path.join(base_path, id,
                                            "raw_data_" + str(topic_name) + ".csv")
model_file_container = os.path.join(base_path, id,
                                         "model_" + str(topic_name) + ".h5")
model_file_container_temp = os.path.join(base_path, id,
                                              "model_temp_" + str(topic_name) + ".h5")
model_file_container_train = os.path.join(base_path, id,
                                               "model_train_" + str(topic_name) + ".h5")
model_file_container_base = os.path.join(base_path, "model_base.h5")

processingData = ProcessingData()

total_mins = int(float(input_size * dT_in_seconds) / 60.0) + 1
max_file_size_mins = config.getint("IO", "load.raw.data.file.size", fallback=10800)

data = RawDataReader.get_raw_data(raw_data_file_container, topic_name)

print("len data = " + str(len(data)))
#data = TimeSeries.expand_and_resample(data, 60)
print("len resample data = " + str(len(data)))
data = data[-(input_size):]
print(data)
Xtest, Xmax, Xmin, latest_timestamp = processingData.preprocess_data_predict(data,input_size)

print(Xtest)

test_predictions = Xtest
result = processingData.postprocess_data(test_predictions, latest_timestamp,
                                                    dT_in_seconds, Xmax, Xmin)

print(len(result))


