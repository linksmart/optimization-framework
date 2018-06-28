"""
Created on Jun 28 14:40 2018

@author: nishit
"""

from math import sqrt

from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.callbacks import EarlyStopping
from keras.callbacks import ReduceLROnPlateau

class ModelPrediction:

    def __init__(self):
        pass

    def predict(self, model, Xvals, model_batch_size):
        # Predicting for the test data
        pred = model.predict(Xvals, batch_size=model_batch_size)
        return pred

    def evaluate(self, model, Xtest, Ytest, model_batch_size):

        score, _ = model.evaluate(Xtest, Ytest, batch_size=model_batch_size)
        rmse = sqrt(score)
        print("\nMSE: {:.3f}, RMSE: {:.3f}".format(score, rmse))
