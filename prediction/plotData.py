"""
Created on Jun 28 15:14 2018

@author: nishit
"""
import matplotlib.pyplot as plt

class PlotData:

    def plot_test(self, test_actual):
        # Plot for test data
        fig = plt.figure()
        fig.set_size_inches(18.5, 10.5)
        pred1 = plt.plot(test_actual, color='red', label='Original')
        plt.legend(loc='upper left')

    def plot_predictions(self, test_predictions):
        # Plot for predictions
        fig = plt.figure()
        fig.set_size_inches(18.5, 10.5)
        orig = plt.plot(test_predictions, color='blue', label='predictions')
        plt.legend(loc='upper left')
