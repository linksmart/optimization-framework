"""
Created on Jun 28 14:40 2018

@author: nishit
"""
import logging

import numpy as np
from math import sqrt

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


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

    def predict_next_day(self, model, Xvals, model_batch_size, length, graph):
        # predict, pop first xval and push the predicted result
        # repeat
        prediction = np.zeros(length)
        for i in range(length):
            with graph.as_default():
                pred = self.predict(model, Xvals, model_batch_size)
                Xvals = self.getDF(pred, Xvals)
                prediction.put(indices=i, values=pred)
        return prediction

    def getDF(self, pred, Xvals):
        Xvals = np.roll(Xvals, -1, axis=1)
        Xvals.put(indices=Xvals.size-1, values=[pred])
        return Xvals