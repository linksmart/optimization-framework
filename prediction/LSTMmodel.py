# -*- coding: utf-8 -*-
"""
Created on Wed Jul  4 16:10:43 2018

@author: puri
"""


import logging
import os
import numpy as np
import random as rn
import tensorflow as tf
os.environ['PYTHONHASHSEED'] = '0'
np.random.seed(42)
rn.seed(12345)
session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)
import keras as k
from keras import backend as K
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from trainModel import TrainModel
tf.set_random_seed(1234)
sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
K.set_session(sess)


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class LSTMmodel:

    def __init__(self, num_timesteps, hidden_size, batch_size):
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.trainModel = TrainModel()
        self.model = None
        

    def model_setup(self):
        # Creating LSTM's structure
        # check if model present in file or create new model
        new = False
        model = self.trainModel.load_saved_model()
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