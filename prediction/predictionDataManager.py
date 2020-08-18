"""
Created on Nov 28 16:03 2019

@author: nishit
"""
import os

from utils_intern.messageLogger import MessageLogger

logger = MessageLogger.get_logger_parent()


class PredictionDataManager:

    @staticmethod
    def get_prediction_by_time(file_path, timestamp):
        if os.path.exists(file_path):
            line = None
            with open(file_path, "r") as f:
                data = f.readlines()
                for row in data:
                    start_time = float(row.split(",")[0])
                    if start_time < timestamp:
                        continue
                    else:
                        line = row
                        break
            if line:
                values = line.split(",")
                start_time = float(values[0])
                values = values[1:]
                return start_time, values
        return None, None

    @staticmethod
    def read_from_file(file_path, topic_name):
        try:
            if os.path.exists(file_path):
                with open(file_path) as file:
                    data = file.readlines()
                file.close()
                return data
            else:
                logger.info("Prediction data not available " + str(topic_name))
                return []
        except Exception as e:
            logger.error(e)
        return []

    @staticmethod
    def get_prediction_data(file_path, topic_name):
        data = PredictionDataManager.read_from_file(file_path, topic_name)
        new_data = {}
        for line in data:
            values = line.split(",")
            start_time = float(values[0])
            values = values[1:]
            new_data[start_time] = values
        return new_data

    @staticmethod
    def get_predictions_before_timestamp(file_path, topic_name, timestamp):
        data = PredictionDataManager.read_from_file(file_path, topic_name)
        new_data = {}
        for line in data:
            values = line.split(",")
            start_time = float(values[0])
            if start_time > timestamp:
                break
            values = values[1:]
            new_data[start_time] = values
        return new_data

    @staticmethod
    def save_predictions_to_file(predictions, horizon_in_steps, prediction_data_file_container, topic_name):
        try:
            if len(predictions) > 0:
                old_data = PredictionDataManager.read_from_file(prediction_data_file_container, topic_name)
                for prediction in predictions:
                    result = prediction.items()
                    result = sorted(result)
                    start_time = float(result[0][0].timestamp())
                    data = []
                    for i in range(horizon_in_steps):
                        value = result[i][1]
                        if value < 0:
                            value = 0
                        data.append(str(value))
                    values = ",".join(data)
                    values = str(start_time) + "," + values + "\n"
                    old_data.append(values)
                old_data = old_data[-4320:] #3 days data, assuming 1 prediction every min
                logger.info("Saving prediction data to file "+str(prediction_data_file_container))
                with open(prediction_data_file_container, 'w+') as file:
                    file.writelines(old_data)
                return []
        except Exception as e:
            logger.error("failed to save_predictions_to_file "+ str(e))
        return predictions

    @staticmethod
    def del_predictions_to_file(prediction_data_file_container, topic_name):
        try:
            if os.path.exists(prediction_data_file_container):
                os.remove(prediction_data_file_container)
        except Exception as e:
            logger.error("failed to del_predictions_to_file " + str(e) +" " + str(topic_name))

    @staticmethod
    def save_predictions_dict_to_file(predictions, horizon_in_steps, prediction_data_file_container, topic_name):
        try:
            if len(predictions) > 0:
                old_data = PredictionDataManager.read_from_file(prediction_data_file_container, topic_name)
                print(predictions)
                for start_time, result in predictions.items():
                    data = []
                    for i in range(horizon_in_steps):
                        value = result[i][1]
                        data.append(str(value))
                    values = ",".join(data)
                    values = str(start_time) + "," + values + "\n"
                    old_data.append(values)
                old_data = old_data[-5600:]  # 4 days data, assuming 1 prediction every min
                logger.info("Saving prediction data to file " + str(prediction_data_file_container))
                with open(prediction_data_file_container, 'w+') as file:
                    file.writelines(old_data)
                return {}
        except Exception as e:
            logger.error("failed to save_predictions_to_file " + str(e))
        return predictions

    @staticmethod
    def del_predictions_from_file(start_times, prediction_data_file_container, topic_name):
        try:
            if len(start_times) > 0:
                old_data = PredictionDataManager.read_from_file(prediction_data_file_container, topic_name)
                index = []
                for i, line in enumerate(old_data):
                    start_time = float(line.split(",")[0])
                    if start_time in start_times:
                        index.append(i)
                shift = 0
                logger.debug("count of del predictions "+str(len(index)))
                for i in index:
                    old_data.pop(i+shift)
                    shift -=1
                old_data = old_data[-5600:]  # 4 days data, assuming 1 prediction every min
                logger.info("Saving prediction data to file " + str(prediction_data_file_container))
                with open(prediction_data_file_container, 'w+') as file:
                    file.writelines(old_data)
        except Exception as e:
            logger.error("failed to del_predictions_to_file " + str(e))

    @staticmethod
    def get_predictions_before_timestamp_influx(influxdb, topic_name, end_time, id):
        new_data = []
        if end_time:
            new_data = influxdb.read(topic_name, "prediction", instance_id=id, end_time=end_time)
        return new_data

    @staticmethod
    def save_predictions_to_influx(influxdb, predictions, horizon_in_steps, topic_name, id):
        try:
            if len(predictions) > 0:
                pred_data = []
                for prediction in predictions:
                    result = prediction.items()
                    result = sorted(result)
                    start_time = float(result[0][0].timestamp())
                    data = []
                    for i in range(horizon_in_steps):
                        value = result[i][1]
                        if value < 0:
                            value = 0
                        data.append(str(value))
                    values = ",".join(data)
                    pred_data.append([start_time, values])
                json_body = influxdb.timeseries_list_to_influx_json(pred_data, topic_name, "prediction", id)
                if not influxdb.write(json_body):
                    return predictions
                else:
                    return []
        except Exception as e:
            logger.error("failed to save_predictions_to_influx " + str(e))
        return predictions

    @staticmethod
    def save_predictions_dict_to_influx(influxdb, predictions, horizon_in_steps, topic_name, id):
        try:
            if len(predictions) > 0:
                pred_data = []
                for start_time, result in predictions.items():
                    data = []
                    #logger.debug("°°° "+str(start_time)+" "+str(result))
                    for i in range(horizon_in_steps):
                        value = result[i]
                        data.append(str(value).replace("\n","").strip())
                    values = ",".join(data)
                    pred_data.append([start_time, values])
                json_body = influxdb.timeseries_list_to_influx_json(pred_data, topic_name, "prediction", id)
                if not influxdb.write(json_body):
                    return predictions
                else:
                    return {}
        except Exception as e:
            logger.error("failed to save_predictions_dict_to_influx " + str(e))
        return predictions

    @staticmethod
    def del_predictions_from_influx(influxdb, start_times, topic_name, id):
        try:
            if len(start_times) > 0:
                empty_data = []
                for start_time in start_times:
                    empty_data.append([start_time, ""])
                json_body = influxdb.timeseries_list_to_influx_json(empty_data, topic_name, "prediction", id)
                influxdb.write(json_body)
        except Exception as e:
            logger.error("failed to del_predictions_from_influx " + str(e))