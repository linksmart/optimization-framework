# -*- coding: utf-8 -*-
"""
Created on Wed Jul  4 16:06:27 2018

@author: puri
"""
import logging
import os
from keras.callbacks import EarlyStopping
from keras.callbacks import ReduceLROnPlateau
from keras.callbacks import ModelCheckpoint
from keras.models import load_model

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class TrainModel:
    
    def __init__(self):
        self.model_weights_path = os.path.join("/usr/src/app", "prediction", "model.h5")

    def train(self, model, Xtrain, Ytrain, num_epochs, batch_size):
        # define reduceLROnPlateau and early stopping callback
        reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.2,
                                      patience=3, min_lr=0.001)
        earlystop = EarlyStopping(monitor='loss', min_delta=0, patience=4, verbose=1, mode='auto')
        
        #Saving the model with checkpoint callback
        checkpoint = ModelCheckpoint(self.model_weights_path, monitor='loss', verbose=1, save_best_only=True, mode='min')
        callbacks_list = [reduce_lr, earlystop,checkpoint]

        # Training a stateful LSTM
        for i in range(num_epochs):
            print("Epoch {:d}/{:d}".format(i + 1, num_epochs))
            model.fit(Xtrain, Ytrain, batch_size=batch_size, epochs=1, verbose=1, callbacks=callbacks_list,
                      shuffle=False)
            model.reset_states()
        return model
    
    def load_saved_model(self):
        try:
            model = load_model(self.model_weights_path)
            logger.info("Loaded model from disk")
            return model
        except Exception as e:
            logger.error(e)
        return None