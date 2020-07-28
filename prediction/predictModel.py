"""
Created on Jun 28 14:40 2018

@author: nishit
"""
import os
import numpy as np
from math import sqrt

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class PredictModel:

    def __init__(self, callback_stop_request):
        self.callback_stop_request = callback_stop_request

    def predict(self, model, Xvals, model_batch_size):
        # Predicting for the test data
        pred = model.predict(Xvals, batch_size=model_batch_size)
        return pred

    def evaluate(self, model, Xtest, Ytest, model_batch_size):
        score, _ = model.evaluate(Xtest, Ytest, batch_size=model_batch_size)
        rmse = sqrt(score)
        print("\nMSE: {:.3f}, RMSE: {:.3f}".format(score, rmse))

    def predict_next_horizon(self, model, Xvals, model_batch_size, graph, type):
        with graph.as_default():
            pred = self.predict(model, Xvals, model_batch_size)
        if type == "load":
            pred = np.append(np.array(Xvals[0][-1:]), pred)
        elif type == "pv":
            pred = np.append(np.array(Xvals["real"][0][-1:]), pred)
        return pred

    def save_to_file(self, input, output, raw_data):
        try:
            path = os.path.join("/usr/src/app", "prediction/resources", "output_data" + ".csv")
            with open(path, "a+") as file:
                file.write("raw:\n")
                for line in raw_data:
                    for item in line:
                        file.write(str(item)+",")
                    file.write("\n")
                file.write("input:\n")
                file.writelines(np.array2string(input, precision=6, separator=',', suppress_small=True))
                file.write("\noutput\n")
                file.writelines(np.array2string(output, precision=6, separator=',', suppress_small=True))
                file.write("\n")
        except Exception as e:
            logger.error("error writing to file "+str(e))