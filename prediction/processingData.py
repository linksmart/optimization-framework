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

    def resample(self, raw_data, dT):
        step = float(dT / 60.0)
        j = float(len(raw_data) - 1)
        new_data = []
        while j > 0:
            if j.is_integer():
                i = int(j)
                new_data.append(raw_data[i])
            else:
                i = math.ceil(j)
                ratio = i - j
                startdate = datetime.datetime.fromtimestamp(raw_data[i][0])
                sec = int(60.0 * ratio)
                date = startdate + datetime.timedelta(seconds=sec)
                start = float(raw_data[i][1])
                end = float(raw_data[i - 1][1])
                val = start + (end - start) * ratio
                new_data.append([date.timestamp(), val])
            j -= step
        return new_data

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
        return new_data

    def preprocess_data(self, raw_data, num_timesteps, train):
        # Loading Data
        latest_timestamp = raw_data[-1:][0][0]
        print(latest_timestamp)
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
        if not train:
            nb_samples += 1
        x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
        y_train_reshaped = np.zeros((nb_samples))

        for i in range(nb_samples):
            y_position = i + look_back
            x_train_reshaped[i] = data[i:y_position]
            if train:
                y_train_reshaped[i] = data[y_position]

        if train:
            # split into training and test sets
            sp = int(0.7 * len(x_train_reshaped))
            logger.info("sp = " + str(sp))
            Xtrain, Xtest, Ytrain, Ytest = x_train_reshaped[0:sp], x_train_reshaped[sp:], y_train_reshaped[
                                                                                          0:sp], y_train_reshaped[sp:]
            # logger.debug(str(Xtrain.shape) + " " + str(Xtest.shape) + " " + str(Ytrain.shape) + " " + str(Ytest.shape))
            # TODO: check the capacity of RPi to operate with more data size
            return Xtrain[0:1000], Xtest[0:500], Ytrain[0:1000], Ytest[0:500]
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
