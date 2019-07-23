"""
Created on Jun 28 10:39 2018

@author: nishit
"""
import time
import math
import pandas as pd
import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class OfflineProcessingData:

    def __init__(self):
        self.new_df = None

    def expand_and_resample(self, raw_data, dT):
        step = float(dT)
        j = len(raw_data) - 1
        new_data = []
        if j > 0:
            start_time = raw_data[j][0]
            start_value = raw_data[j][1]
            new_data.append([start_time, start_value])
            prev_time = start_time
            prev_value = start_value
            required_diff = step
            j -= 1
            while j >= 0:
                end_time = raw_data[j][0]
                end_value = raw_data[j][1]
                diff_sec = prev_time - end_time
                if diff_sec >= required_diff:
                    ratio = required_diff / diff_sec
                    inter_time = prev_time - required_diff
                    inter_value = prev_value - (prev_value - end_value) * ratio
                    new_data.append([inter_time, inter_value])
                    prev_time = inter_time
                    prev_value = inter_value
                    required_diff = step
                else:
                    required_diff -= diff_sec
                    prev_time = end_time
                    prev_value = end_value
                    j -= 1
        else:
            new_data = raw_data
        new_data.reverse()
        return new_data

    def preprocess_data_predict(self, raw_data, num_timesteps, output_size):
        # Loading Data

        # df = pd.DataFrame(raw_data, columns=col_heads)
        df = pd.DataFrame(raw_data)
        df = df[df.columns[:2]]
        df.columns = ['Time', 'Electricity']

        new_df = df
        new_df.columns = ['DateTime', 'Electricity']
        # Changing dtype to pandas datetime format
        new_df['DateTime'] = pd.to_datetime(new_df['DateTime'], unit='s')
        new_df = new_df.set_index('DateTime')

        # checking for null values and if any, replacing them with last valid observation
        new_df.isnull().sum()
        new_df.Electricity.fillna(method='pad', inplace=True)

        # scale the data to be in the range (0, 1)
        data = new_df.values.reshape(-1, 1)
        scaler = MinMaxScaler(feature_range=(0, 1), copy=False)
        data = scaler.fit_transform(data)

        look_back = num_timesteps
        num_features = 1
        nb_samples = data.shape[0] - num_timesteps
        x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
        # y_train_reshaped = np.zeros((nb_samples, output_size))
        logger.info("data dim = "+str(data.shape))
        for i in range(nb_samples):
            y_position_start = i + look_back
            x_train_reshaped[i] = data[i:y_position_start]

        Xtest = x_train_reshaped
        logger.debug(str(Xtest.shape))
        return Xtest, scaler, 0

    def postprocess_data(self, prediction, startTimestamp, delta, scaler):
        data = prediction.reshape(-1, 1)
        data = scaler.inverse_transform(data)
        data = data.reshape(-1)
        startTime = startTimestamp
        result = {}
        for pred in data:
            result[startTime] = pred
            startTime += delta
        return result

    def append_mock_data(self, data, num_timesteps, dT):
        l = len(data)
        diff = num_timesteps - l
        if l == 0:
            earliest_timestamp = time.time()
        else:
            earliest_timestamp = data[0][0]
        new_data = data
        for i in range(diff):
            earliest_timestamp -= dT
            new_data.insert(0, [earliest_timestamp, - 0.000001])
        return new_data

    def break_series_into_countinous_blocks(self, raw_data, dT, horizon_steps):
        allowed_continous_gap_percent = 0.1
        duration_of_one_data_set = horizon_steps * dT
        required_mins = math.ceil(duration_of_one_data_set / 60.0)
        allowed_continous_gap_mins = required_mins * allowed_continous_gap_percent
        continous_series = []
        temp_data = []
        logger.info("allowed "+str(allowed_continous_gap_mins))
        prev_time = raw_data[0][0]
        for i in range(len(raw_data)):
            curr_time = raw_data[i][0]
            minute_diff = (curr_time - prev_time) / 60.0
            if minute_diff > allowed_continous_gap_mins:
                continous_series.append(temp_data.copy())
                temp_data = []
            temp_data.append(raw_data[i])
            prev_time = curr_time
        if len(temp_data) > 0:
            continous_series.append(temp_data.copy())
        return continous_series

    def expand_and_resample_into_blocks(self, raw_data, dT, horizon_steps, num_timesteps, output_size):
        if len(raw_data) > 0:
            blocks = self.break_series_into_countinous_blocks(raw_data, dT, horizon_steps)
            logger.info("num blocks = "+str(len(blocks)))
            resampled_blocks = []
            block_has_min_length = []
            merged = False
            min_length = num_timesteps + output_size
            for block in blocks:
                resampled_block = self.expand_and_resample(block, dT)
                if len(resampled_block) > 0:
                    resampled_blocks.append(resampled_block)
                    logger.info("block size = "+str(len(resampled_block)))
                    if len(resampled_block) >= min_length:
                        block_has_min_length.append(True)
                    else:
                        block_has_min_length.append(False)
            if len(block_has_min_length) > 0 and not any(block_has_min_length):
                logger.info("merging block because insufficient data")
                new_block = []
                end_time = resampled_blocks[-1][-1][0]
                # TODO : check logic
                for i in reversed(range(len(resampled_blocks))):
                    rsb = resampled_blocks[i]
                    start_time = rsb[0][0]
                    if end_time - start_time < min_length * dT:
                        rsb.extend(new_block)
                        new_block = rsb
                        merged = True
                    else:
                        rsb.extend(new_block)
                        new_block = rsb
                        merged = True
                        break
                logger.info(new_block)
                if merged:
                    new_block = self.expand_and_resample(new_block, dT)
                    logger.info(new_block)
                    logger.info("length of merged blocks after expand = "+str(len(new_block)))
                new_blocks = [new_block]
                resampled_blocks = new_blocks
            return resampled_blocks, merged
        else:
            return [], False

    def preprocess_data_train(self, blocks, num_timesteps, output_size):
        x_list = []
        y_list = []
        look_back = num_timesteps
        num_features = 1
        count = 0
        for raw_data in blocks:
            # Loading Data
            if len(raw_data) >= num_timesteps + output_size + 5:
                raw_data = raw_data[-7200:]
                latest_timestamp = raw_data[-1:][0][0]
                logger.debug(latest_timestamp)
                # df = pd.DataFrame(raw_data, columns=col_heads)
                df = pd.DataFrame(raw_data)
                df = df[df.columns[:2]]
                df.columns = ['Time', 'Electricity']

                new_df = df
                new_df.columns = ['DateTime', 'Electricity']
                # Changing dtype to pandas datetime format
                new_df['DateTime'] = pd.to_datetime(new_df['DateTime'], unit='s')
                new_df = new_df.set_index('DateTime')

                # checking for null values and if any, replacing them with last valid observation
                new_df.isnull().sum()
                new_df.Electricity.fillna(method='pad', inplace=True)

                # scale the data to be in the range (0, 1)
                data = new_df.values.reshape(-1, 1)
                scaler = MinMaxScaler(feature_range=(0, 1), copy=False)
                data = scaler.fit_transform(data)

                nb_samples = data.shape[0] - num_timesteps - output_size
                logger.info("nb samples = "+str(nb_samples))
                x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
                y_train_reshaped = np.zeros((nb_samples, output_size))
                logger.info("data dim = " + str(data.shape))
                for i in range(nb_samples):
                    y_position_start = i + look_back
                    x_train_reshaped[i] = data[i:y_position_start]
                    y_position_end = y_position_start + output_size
                    l = data[y_position_start:y_position_end]
                    y_train_reshaped[i] = [item for sublist in l for item in sublist]

                x_list.append(x_train_reshaped)
                y_list.append(y_train_reshaped)
                count += len(x_train_reshaped)
                logger.info("count = "+str(count))
        Xtrain = np.zeros((count, look_back, num_features))
        Ytrain = np.zeros((count, output_size))

        j = 0
        for x_train in x_list:
            for item in x_train:
                Xtrain[j] = item
                j += 1

        j = 0
        for y_train in y_list:
            for item in y_train:
                Ytrain[j] = item
                j += 1

        # split into training and test sets
        ct = 8000
        Xtrain, Ytrain = Xtrain[0:ct], Ytrain[0:ct]
        sp = int(0.7 * len(Xtrain))
        logger.info("sp = " + str(sp))
        Xtrain, Xtest, Ytrain, Ytest = Xtrain[0:sp], Xtrain[sp:], Ytrain[0:sp], Ytrain[sp:]
        return Xtrain, Xtest, Ytrain, Ytest

    def get_regression_values(self, train_data, input_size, output_size, dT):
        new_data = np.array(train_data[-input_size:])

        x = new_data[:,0]
        x = x.reshape(-1, 1)
        last_timestamp = x[-1][0]

        logger.info("last timestamp load = "+str(last_timestamp))

        y = new_data[:, 1]
        y = y.reshape(-1, 1)

        reg = LinearRegression().fit(x, y)

        prediction_input = []
        for i in range(output_size):
            prediction_input.append([last_timestamp])
            last_timestamp += dT

        prediction_input = np.array(prediction_input)
        prediction_input = prediction_input.reshape(-1, 1)

        prediction_output = reg.predict(prediction_input)

        prediction_input = prediction_input.reshape(-1)
        prediction_output = prediction_output.reshape(-1)

        new_data = {}

        for i in range(output_size):
            new_data[prediction_input[i]] = prediction_output[i]



        return new_data
