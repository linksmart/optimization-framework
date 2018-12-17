"""
Created on Jun 28 10:39 2018

@author: nishit
"""
import datetime
import time
import math
import pandas as pd
import numpy as np
import logging

from sklearn.preprocessing import MinMaxScaler

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class ProcessingData:

    def __init__(self):
        self.new_df = None

    def expand_and_resample(self, raw_data, dT):
        step = float(dT)
        j = len(raw_data)
        new_data = []
        sec_diff = 0
        current_step = 0
        first = True
        if j > 1:
            while j > 0:
                if current_step <= 0:
                    j -= 1
                    start_date = datetime.datetime.fromtimestamp(raw_data[j][0])
                    start_val = float(raw_data[j][1])
                    end_date = datetime.datetime.fromtimestamp(raw_data[j - 1][0])
                    end_val = float(raw_data[j - 1][1])
                    sec_diff = start_date - end_date
                    sec_diff = sec_diff.total_seconds()
                    current_step = sec_diff
                if current_step >= step or first:
                    ratio = float(current_step / sec_diff)
                    sec = sec_diff - current_step
                    date = start_date - datetime.timedelta(seconds=sec)
                    val = end_val + (start_val - end_val) * ratio
                    new_data.append([date.timestamp(), val])
                    first = False
                current_step -= step
        new_data.reverse()
        return new_data

    def resampling_calculations(self, dT, train, input_length, output_length):
        if train:
            num_timesteps_required = input_length + output_length
        else:
            num_timesteps_required = input_length
        total_minute_steps_necessary = math.ceil(num_timesteps_required * (dT / 60.0))
        allowed_interpolation_percentage = 0.20
        total_minute_steps_sufficient = int(total_minute_steps_necessary * (1.0 - allowed_interpolation_percentage))
        return total_minute_steps_sufficient, total_minute_steps_necessary


    def preprocess_data_predict(self, raw_data, num_timesteps, output_size):
        # Loading Data
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

        look_back = num_timesteps
        num_features = 1
        nb_samples = data.shape[0] - num_timesteps
        x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
        y_train_reshaped = np.zeros((nb_samples, output_size))
        logger.info("data dim = "+str(data.shape))
        for i in range(nb_samples):
            y_position_start = i + look_back
            x_train_reshaped[i] = data[i:y_position_start]

        Xtest = x_train_reshaped[-1:]
        logger.debug(str(Xtest.shape))
        return Xtest, scaler, latest_timestamp

    def postprocess_data(self, prediction, startTimestamp, delta, scaler):
        data = prediction.reshape(-1, 1)
        data = scaler.inverse_transform(data)
        data = data.reshape(-1)
        startTime = datetime.datetime.fromtimestamp(startTimestamp)
        result = {}
        for pred in data:
            startTime += datetime.timedelta(seconds=delta)
            result[startTime] = pred
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
        return continous_series

    def expand_and_resample_into_blocks(self, raw_data, dT, horizon_steps):
        blocks = self.break_series_into_countinous_blocks(raw_data, dT, horizon_steps)
        logger.info("num blocks = "+str(len(blocks)))
        resampled_blocks = []
        for block in blocks:
            resampled_block = self.expand_and_resample(block, dT)
            if len(resampled_block) > 0:
                resampled_blocks.append(resampled_block)
                logger.info("block size = "+str(len(resampled_block)))
        return blocks

    def preprocess_data_train(self, blocks, num_timesteps, output_size):
        x_list = []
        y_list = []
        look_back = num_timesteps
        num_features = 1
        count = 0
        for raw_data in blocks:
            # Loading Data
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

        """
        # split into training and test sets
        sp = int(0.7 * len(x_train_reshaped))
        logger.info("sp = " + str(sp))
        Xtrain, Xtest, Ytrain, Ytest = x_train_reshaped[0:sp], x_train_reshaped[sp:], y_train_reshaped[
                                                                                      0:sp], y_train_reshaped[sp:]
        return Xtrain, Xtest, Ytrain, Ytest
        # logger.debug(str(Xtrain.shape) + " " + str(Xtest.shape) + " " + str(Ytrain.shape) + " " + str(Ytest.shape))
        """
        sp = 250
        Xtrain, Ytrain = Xtrain[-sp:], Ytrain[-sp:]
        # TODO: check the capacity of RPi to operate with more data size
        return Xtrain, Ytrain