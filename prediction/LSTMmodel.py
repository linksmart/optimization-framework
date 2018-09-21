"""
Created on Jun 28 14:41 2018

@author: nishit
"""
import logging
import os
import numpy as np
import random as rn

os.environ['PYTHONHASHSEED'] = '0'
np.random.seed(42)
rn.seed(12345)
import keras as k
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class LSTMmodel:

    @staticmethod
    def model_setup(hidden_size, batch_size, num_timesteps):
        # Creating LSTM's structure
        try:
            model = Sequential()
            model.add(LSTM(hidden_size, stateful=True,
                           batch_input_shape=(batch_size, num_timesteps, 1),
                           return_sequences=False))
            model.add(Dense(1))
            adam = k.optimizers.Adam(lr=0.01)
            model.compile(loss="mean_squared_error", optimizer=adam,
                          metrics=["mean_squared_error"])
            return model
        except Exception as e:
            print(e)
            raise e