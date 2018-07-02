"""
Created on Jun 28 14:41 2018

@author: nishit
"""
import logging

import keras as k
import os
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.models import load_model

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class LSTMmodel:

    def __init__(self, num_timesteps, hidden_size, batch_size):
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.model = None
        self.model_meta_path = os.path.join("/usr/src/app", "prediction", "model.json")
        self.model_weights_path = os.path.join("/usr/src/app", "prediction", "model.h5")

    def model_setup(self):
        # Creating LSTM's structure
        # check if model present in file or create new model
        new = False
        """
        if self.model:
            return self.model, new
        """
        model = self.load_model()
        if not model:
            new = True
            model = Sequential()
            model.add(LSTM(self.hidden_size, stateful=True,
                           batch_input_shape=(self.batch_size, self.num_timesteps, 1),
                           return_sequences=False))
            model.add(Dense(1))
            adam = k.optimizers.Adam(lr=0.01)
            model.compile(loss="mean_squared_error", optimizer=adam,
                          metrics=["mean_squared_error"])

        return model, new

    def persist_model(self, model):
        model.save(self.model_weights_path)
        logger.info("Saved model to disk")
        self.model = model

    def load_model(self):
        try:
            model = load_model(self.model_weights_path)
            logger.info("Loaded model from disk")
            return model
        except Exception as e:
            logger.error(e)
        return None
