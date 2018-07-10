"""
Created on Jun 28 14:41 2018

@author: nishit
"""


import logging
import os
import numpy as np
import random as rn
import tensorflow as tf

from prediction.trainModel import TrainModel

os.environ['PYTHONHASHSEED'] = '0'
np.random.seed(42)
rn.seed(12345)
session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)
import keras as k
from keras import backend as K
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.models import load_model
tf.set_random_seed(1234)
sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
#K.set_session(sess)


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class LSTMmodel:

    def __init__(self, num_timesteps, hidden_size, batch_size, save_path):
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.model = None
        self.model_weights_path = save_path


    def model_setup(self):
        # Creating LSTM's structure
        # check if model present in file or create new model
        new = False
        if self.model:
            logger.info("model present in memory")
            return self.model, new
        model = self.load_saved_model()
        if not model:
            logger.info("create new model")
            new = True
            model = Sequential()
            model.add(LSTM(self.hidden_size, stateful=True,
                           batch_input_shape=(self.batch_size, self.num_timesteps, 1),
                           return_sequences=False))
            model.add(Dense(1))
            adam = k.optimizers.Adam(lr=0.01)
            model.compile(loss="mean_squared_error", optimizer=adam,
                          metrics=["mean_squared_error"])
        self.model = model
        return model, new

    def load_saved_model(self):
        try:
            model = load_model(self.model_weights_path)
            logger.info("Loaded model from disk")
            return model
        except Exception as e:
            return None