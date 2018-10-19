"""
Created on Jun 28 10:39 2018

@author: nishit
"""
import datetime
import json

import pandas as pd
import numpy as np
import logging

from sklearn.preprocessing import MinMaxScaler


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class ProcessingData:

    def __init__(self):
        self.new_df = None

    def preprocess_data(self, raw_data, num_timesteps, train):
        # Loading Data
        """
        col_heads = raw_data[0]
        raw_data = raw_data[1:]
        """
        #df = pd.DataFrame(raw_data, columns=col_heads)
        df = pd.DataFrame(raw_data)
        df = df[df.columns[:2]]
        df.columns = ['Time', 'Electricity']

        new_df = df['Time'].str.split('  ', 1, expand=True)
        new_df.columns = ['Date', 'Time']

        new_df = df['Time'].str.split('  ', 1, expand=True)
        new_df.columns = ['Date', 'Time']

        new_df1 = new_df.Time.str.split(':', 1, expand=True)
        new_df1.columns = ['Hour', 'Min&Sec']
        new_df1 = new_df1.Hour.astype(str).astype(int)
        new_df1 = new_df1 - 1
        new_df1 = new_df1.astype(str)
        new_df2 = new_df1 + ':' + '00:00'
        new_df['DateTime'] = new_df['Date'] + ' ' + new_df2  # ['Time']

        new_df = new_df.drop('Date', axis=1)
        new_df = new_df.drop('Time', axis=1)
        new_df['Electricity'] = df['Electricity']

        # Changing dtype to pandas datetime format
        new_df['DateTime'] = pd.to_datetime('2018/' + new_df['DateTime'].str.strip(), format='%Y/%m/%d %H:%M:%S')
        # new_df['DateTime'].astype(str)
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
        #logger.debug("initial X" + str(x_train_reshaped.shape))
        #logger.debug("initial Y" + str(y_train_reshaped.shape))

        for i in range(nb_samples):
            y_position = i + look_back
            x_train_reshaped[i] = data[i:y_position]
            if train:
                y_train_reshaped[i] = data[y_position]
        #logger.debug("x later" + str(x_train_reshaped.shape))
        #logger.debug("y later" + str(y_train_reshaped.shape))

        if train:
            # split into training and test sets
            sp = int(0.7 * len(x_train_reshaped))
            logger.info("sp = "+str(sp))
            Xtrain, Xtest, Ytrain, Ytest = x_train_reshaped[0:sp], x_train_reshaped[sp:], y_train_reshaped[
                                                                                          0:sp], y_train_reshaped[sp:]
            #logger.debug(str(Xtrain.shape) + " " + str(Xtest.shape) + " " + str(Ytrain.shape) + " " + str(Ytest.shape))
            self.new_df = new_df
            return Xtrain[0:1000], Xtest[0:500], Ytrain[0:1000], Ytest[0:500]
        else:
            Xtest = x_train_reshaped[:1]
            logger.debug(str(Xtest.shape))
            self.new_df = new_df
            return Xtest

    def add_date_time_test(self, Ytest):
        # Adding datetime to original test data
        new_df = self.new_df
        new_df_date = new_df[-len(Ytest):]
        test_act = new_df_date.reset_index()
        test_act = test_act.drop('Electricity', axis=1)
        test_actual = pd.DataFrame(Ytest)
        test_actual.columns = ['Electricity']
        test_actual['DateTime'] = test_act['DateTime']
        test_actual = test_actual.set_index('DateTime')
        return test_actual, test_act

    def add_date_time_pred(self, pred):
        # Adding datetime to predictions and changing to dataframe
        new_df = self.new_df
        new_df_date = new_df[-len(pred):]
        test_act = new_df_date.reset_index()
        test_act = test_act.drop('Electricity', axis=1)
        test_predictions = pd.DataFrame(pred)
        test_predictions.columns = ['Electricity']
        test_predictions['DateTime'] = test_act['DateTime']
        test_predictions = test_predictions.set_index('DateTime')
        return test_predictions

    def hour_range(self):
        date = datetime.datetime.now()
        startHour = datetime.datetime(datetime.datetime.now().year, 12, 11, 5, 0) + \
            datetime.timedelta(hours=1)
        endHr = datetime.datetime(datetime.datetime.now().year, 12, 11, 5, 0) + \
                      datetime.timedelta(hours=25)
        return startHour, endHr

    def to_python_dict_data(self, prediction):
            starthr, endhr = self.hour_range()
            data = {}
            start_date = pd.Timestamp(starthr.year, starthr.month, starthr.day, starthr.hour)
            end_date = pd.Timestamp(endhr.year, endhr.month, endhr.day, endhr.hour)
            filtered_data = prediction[start_date:end_date]
            filtered_data = filtered_data.to_dict("split")
            index = filtered_data["index"]
            value = filtered_data["data"]
            for i in range(len(index)):
                date = index[i]
                date = date.to_pydatetime()
                data[date] = value[i][0]
            return data

    def to_dict_with_datetime(self, prediction, startTime, deltaMinutes):
        data = {}
        for pred in prediction:
            data[startTime] = pred
            startTime += datetime.timedelta(minutes=deltaMinutes)
        return data