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


    def preprocess_data(self, raw_data, num_timesteps, output_size, train):
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
        if train:
            nb_samples = data.shape[0] - num_timesteps - output_size
        else:
            nb_samples = data.shape[0] - num_timesteps
        x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
        y_train_reshaped = np.zeros((nb_samples, output_size))
        logger.info("data dim = "+str(data.shape))
        for i in range(nb_samples):
            y_position_start = i + look_back
            x_train_reshaped[i] = data[i:y_position_start]
            if train:
                y_position_end = y_position_start + output_size
                l = data[y_position_start:y_position_end]
                y_train_reshaped[i] = [item for sublist in l for item in sublist]

        if train:
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
            Xtrain, Ytrain = x_train_reshaped[-sp:], y_train_reshaped[-sp:]
            # TODO: check the capacity of RPi to operate with more data size
            return Xtrain, Ytrain
        else:
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
