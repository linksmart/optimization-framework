
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 26 14:42:24 2018

@author: puri
"""
'''
import json
import threading

import pandas as pd
import numpy as np
import keras as k
from sklearn.preprocessing import MinMaxScaler
from math import sqrt
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.callbacks import EarlyStopping
from keras.callbacks import ReduceLROnPlateau
import os


"""lstm model/ file for test purposes"""

class LSTMLookBack:

    def format_data(self, data=[]):
        new_data = []
        i = 0
        for row in data:
            cols = row.replace('\n', '').strip().split(",")
            if not i == 0:
                dateTime = cols[0]
                cols = cols[1:]
                cols = list(map(float, cols))
                cols.insert(0, dateTime)
            if i < 2:
                print(cols)
                i += 1
            new_data.append(cols)
        print("cols size " + str(len(new_data)) + " " + str(len(new_data[0])))
        return new_data

    def dm(self, file_path):
        with open(file_path) as f:
            data = json.dumps(f.readlines())

        data = json.loads(data)
        data = self.format_data(data)
        return data

    def a(self):
        Xtrain, Xtest, Ytrain, Ytest = self.rr()
        self.train_thread = threading.Thread(target=self.r, args=(Xtrain, Xtest, Ytrain, Ytest))
        self.train_thread.start()

    @staticmethod
    def t():
        NUM_TIMESTEPS = 25
        HIDDEN_SIZE = 10
        BATCH_SIZE = 1
        NUM_EPOCHS = 2
        # Creating LSTM's structure
        model = Sequential()
        model.add(LSTM(HIDDEN_SIZE, stateful=True,
                       batch_input_shape=(BATCH_SIZE, NUM_TIMESTEPS, 1),
                       return_sequences=False))
        model.add(Dense(1))

        adam = k.optimizers.Adam(lr=0.01)
        model.compile(loss="mean_squared_error", optimizer=adam,
                      metrics=["mean_squared_error"])
        return model

    def rr(self):
        # Loading Data
        file = os.path.join("/usr/src/app", "prediction", "USA_AK_King.Salmon.703260_TMY2.csv")

        # Loading Data
        # file = 'USA_AK_King.Salmon.703260_TMY2.csv'
        df = pd.read_csv(file)
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

        NUM_TIMESTEPS = 25
        HIDDEN_SIZE = 10
        BATCH_SIZE = 1
        NUM_EPOCHS = 2

        # scale the data to be in the range (0, 1)
        data = new_df.values.reshape(-1, 1)
        scaler = MinMaxScaler(feature_range=(0, 1), copy=False)
        data = scaler.fit_transform(data)

        look_back = NUM_TIMESTEPS
        num_features = 1
        nb_samples = data.shape[0] - NUM_TIMESTEPS
        x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
        y_train_reshaped = np.zeros((nb_samples))
        print("initial X", x_train_reshaped.shape)
        print("initial Y", y_train_reshaped.shape)

        for i in range(nb_samples):
            y_position = i + look_back
            x_train_reshaped[i] = data[i:y_position]
            y_train_reshaped[i] = data[y_position]
        print("x later", x_train_reshaped.shape)
        print("y later", y_train_reshaped.shape)

        # split into training and test sets
        sp = int(0.7 * len(data))
        Xtrain, Xtest, Ytrain, Ytest = x_train_reshaped[0:sp], x_train_reshaped[sp:], y_train_reshaped[
                                                                                      0:sp], y_train_reshaped[sp:]

        Xtrain, Xtest, Ytrain, Ytest = Xtrain[0:100], Xtest[0:10], Ytrain[0:100], Ytest[0:10]

        print(Xtrain.shape, Xtest.shape, Ytrain.shape, Ytest.shape)
        return Xtrain, Xtest, Ytrain, Ytest

    def r(self, Xtrain, Xtest, Ytrain, Ytest):
        NUM_TIMESTEPS = 25
        HIDDEN_SIZE = 10
        BATCH_SIZE = 1
        NUM_EPOCHS = 2

        model = LSTMLookBack.t()
        ts = TSP()
        ts.train(BATCH_SIZE, NUM_EPOCHS, Xtrain, Ytrain, model)

        # Predicting for the test data
        pred = model.predict(Xtest, batch_size=BATCH_SIZE)
        print(pred)
        score, _ = model.evaluate(Xtest, Ytest, batch_size=BATCH_SIZE)
        rmse = sqrt(score)
        print("\nMSE: {:.3f}, RMSE: {:.3f}".format(score, rmse))

        """
        # Adding datetime to original test data
        new_df_date = new_df[-len(Ytest):]
        test_act = new_df_date.reset_index()
        test_act = test_act.drop('Electricity', axis=1)
        test_actual = pd.DataFrame(Ytest)
        test_actual.columns = ['Electricity']
        test_actual['DateTime'] = test_act['DateTime']
        test_actual = test_actual.set_index('DateTime')

        # Adding datetime to predictions and changing to dataframe
        test_predictions = pd.DataFrame(pred)
        test_predictions.columns = ['Electricity']
        test_predictions['DateTime'] = test_act['DateTime']
        test_predictions = test_predictions.set_index('DateTime')

        print(test_predictions)
        
        # Writing predicitons to a csv file
        test_predictions.to_csv('test_lstm_timesteps.csv')

        # Plot for test data
        fig = plt.figure()
        fig.set_size_inches(18.5, 10.5)
        pred1 = plt.plot(test_actual, color='red', label='Original')
        plt.legend(loc='upper left')

        # Plot for predictions
        fig = plt.figure()
        fig.set_size_inches(18.5, 10.5)
        orig = plt.plot(test_predictions, color='blue', label='predictions')
        plt.legend(loc='upper left')
        
        """


class TSP:

    def train(self, BATCH_SIZE, NUM_EPOCHS, Xtrain, Ytrain, model):
        # define reduceLROnPlateau and early stopping callback
        reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.2,
                                      patience=3, min_lr=0.001)
        earlystop = EarlyStopping(monitor='loss', min_delta=0, patience=4, verbose=1, mode='auto')
        callbacks_list = [reduce_lr, earlystop]
        # Training a stateful LSTM
        for i in range(NUM_EPOCHS):
            print("Epoch {:d}/{:d}".format(i + 1, NUM_EPOCHS))
            model.fit(Xtrain, Ytrain, batch_size=BATCH_SIZE, epochs=1, verbose=1, callbacks=callbacks_list,
                      shuffle=False)
            model.reset_states() '''