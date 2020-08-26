import datetime
import os
import time

from prediction.rawDataReader import RawDataReader
from utils_intern.messageLogger import MessageLogger

control_frequency = 60
horizon_in_steps = 24
topic_param = {"topic":"/Fronius/SMX/W_Load","qos":1,"mqtt.port":1883}
dT_in_seconds = 3600
topic_name = "P_Load"
id = "asdf"
logger = MessageLogger.set_and_get_logger_parent(id, "DEBUG", "ofw")


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

data = RawDataReader.get_raw_data(raw_data_file_container, topic_name)

final = []
for t, v in data:
    ts = datetime.datetime.fromtimestamp(t).replace(second=0, microsecond=0)
    final.append([int(ts.timestamp()), v])

RawDataReader.save_to_file(raw_data_file_container, topic_name, final, overwrite=True)