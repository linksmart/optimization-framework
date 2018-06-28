"""
Created on Jun 28 14:41 2018

@author: nishit
"""

import keras as k
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM

class LSTMmodel:

    def __init__(self, num_timesteps, hidden_size, batch_size):
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.model = None

    def model_setup(self):
        # Creating LSTM's structure
        # check if model present in file or create new model

        model = Sequential()
        model.add(LSTM(self.hidden_size, stateful=True,
                       batch_input_shape=(self.batch_size, self.num_timesteps, 1),
                       return_sequences=False))
        model.add(Dense(1))

        adam = k.optimizers.Adam(lr=0.01)
        model.compile(loss="mean_squared_error", optimizer=adam,
                      metrics=["mean_squared_error"])

        return model

    def persist_model(self):
        pass

    def load_model(self):
        pass