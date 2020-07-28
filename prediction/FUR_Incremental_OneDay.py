import datetime
import time
import pandas as pd
import numpy as np
import tensorflow as tf
import random as rn
import os

import keras
from keras import Input
from keras.models import Sequential, Model
from keras.layers import concatenate
from keras.layers import Dense
from keras.layers import LSTM, Dropout
from keras.callbacks import EarlyStopping
from keras.callbacks import ReduceLROnPlateau
from keras.callbacks import ModelCheckpoint
from keras.models import load_model
from keras import regularizers
import keras as k
os.environ['PYTHONHASHSEED'] = '0'
np.random.seed(42)
rn.seed(12345)
# Restricting operation to 1 thread for reproducible results.
session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)
from keras import backend as K
# Setting the graph-level random seed.
tf.set_random_seed(1234)
sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
K.set_session(sess)



def read_data(filename):
    df = pd.read_csv(filename, header=None)
    df.columns = ['Time', 'PV']
    df['Time'] = pd.to_datetime(df["Time"], errors='coerce')
    df.index = df["Time"]
    df = df.drop(columns=['Time'])
    print(df.head())

    return df

def pre_processing_data(real_file, hist_file):

    df = pd.read_csv(real_file, header=None)
    df.columns = ['Time', 'Values']
    df['Time'] = pd.to_datetime(df["Time"], errors='coerce')
    df.index = df["Time"]
    df = df.drop(columns=['Time'])
    print("read csv")
    print(df.head())

    #Changing Frequency of Data to Minutes
    df = df.resample('T').mean()
    
    #checking for null values and if any, replacing them with last valid observation
    df.isnull().sum()
    df.Values.fillna(method='pad', inplace=True)    
    data = df.values.reshape(-1, 1)    
    flat_list = [item for sublist in data for item in sublist]
    #Quantile Normalization
    s = pd.Series(flat_list)
    quant = s.quantile(0.75)
    Xmin = np.amin(data)
    Xmax = quant
    X_std = (data - Xmin) / (Xmax - Xmin)    
    max = 1
    min = 0
    X_scaled = X_std * (max - min) + min

    hist_data = []
    start_date_hist = datetime.datetime.strptime("2016-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
    with open(hist_file, "r") as f:
        data = f.readlines()
        data.insert(0, data[-1])
        for v in data:
            hist_data.append([start_date_hist.strftime("%Y-%m-%d %H:%M:%S"), float(v)])
            start_date_hist += datetime.timedelta(hours=1)

    hd = pd.DataFrame(hist_data, columns=['Time', 'Values'])
    hd['Time'] = pd.to_datetime(hd["Time"], errors='coerce')
    hd.index = hd["Time"]
    hd = hd.drop(columns=['Time'])
    print(hd.head(20))

    data = hd.values.reshape(-1, 1)
    Xmin = np.amin(data)
    Xmax = np.amax(data)
    X_std = (data - Xmin) / (Xmax - Xmin)
    max = 1
    min = 0
    X_scaled_hist = X_std * (max - min) + min

    return X_scaled, df, X_scaled_hist, hd

def train_model(realXtrain, histXtrain, Ytrain, model, input_size_real, input_size_hist, hidden_size, batch_size,
                output_size, Num_Epochs):
    
    #Creating LSTM's structure
    if model is None:
        print("Training the model..........")
        real_input = Input(batch_shape=(batch_size, input_size_real, 1), name="real")
        real_features = LSTM(hidden_size, stateful=True, return_sequences=True)(real_input)

        hist_input = Input(batch_shape=(batch_size, input_size_hist, 1), name="hist")
        hist_features = LSTM(hidden_size, stateful=True, return_sequences=True)(hist_input)

        x = concatenate([real_features, hist_features], axis=1)
        x = Dropout(0.3)(x)
        x = LSTM(hidden_size, stateful=True)(x)
        output_layer = Dense(output_size)(x)

        model = Model(inputs=[real_input, hist_input], outputs=output_layer)

        model.summary()

        adam = k.optimizers.Adam(lr=0.01)
        model.compile(loss="mean_squared_error", optimizer=adam,
                      metrics=["mean_squared_error"])

        model.compile(loss="mean_squared_error", optimizer=adam,
                      metrics=["mean_squared_error"])
    
    
    # define reduceLROnPlateau and early stopping callback
    reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.2,
                                  patience=3, min_lr=0.001)
    earlystop = EarlyStopping(monitor='loss', min_delta=0.0001, patience=3, verbose=1, mode='auto')
    
    # define the checkpoint
    filepath = "model.h5"
    checkpoint = ModelCheckpoint(filepath, monitor='loss', verbose=0, save_best_only=True, mode='min')
    
    callbacks_list = [reduce_lr,earlystop,checkpoint]
    
    #Training a stateful LSTM
    for i in range(Num_Epochs):
            print("Epoch {:d}/{:d}".format(i+1, Num_Epochs))
            model.fit({"real": realXtrain, "hist": histXtrain}, Ytrain, batch_size=Batch_Size, epochs=1, verbose=2, callbacks=callbacks_list, shuffle=False)
            model.reset_states()
    
    return model


def predict_model(model, realXtest, histXtest, Batch_Size):
    
    #Predicting for the test data
    start_time = time.clock()
    pred = model.predict({"real": realXtest, "hist": histXtest},batch_size=Batch_Size)
    end_time = time.clock()
    time_taken = end_time - start_time

    return pred[0], time_taken

def find_nearest_hour_index(t):
    start_date_hist = datetime.datetime.strptime("2016-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
    if t.minute > 30:
        t = t.replace(year=2016, minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
    else:
        t = t.replace(year=2016, minute=0, second=0, microsecond=0)
    index = int((t - start_date_hist).total_seconds()/3600)
    return index


def incremental_algorithm(X_scaled, df, X_scaled_hist, Hist_input_size, look_back, Hidden_Size, Batch_Size, Num_Epochs):

    num_features = 1
    prediction_horizon = 1440
    nb_samples = X_scaled.shape[0] - look_back - prediction_horizon
    x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
    y_train_reshaped = np.zeros((nb_samples, prediction_horizon))
    print("----",  X_scaled.shape[0])
    print("initial X",x_train_reshaped.shape)
    print("initial Y",y_train_reshaped.shape)
    
    train_time = []
    prediction_time = []
    prediction_error = []
    prediction_median = []
    prediction_std = []

    for i in range(nb_samples):
        start_date_index = find_nearest_hour_index(datetime.datetime.strptime(str(df.index[i]), "%Y-%m-%d %H:%M:%S"))

        end_date_index = start_date_index + Hist_input_size
        histXtrain = X_scaled_hist[start_date_index:end_date_index]
        if end_date_index >= len(X_scaled_hist):
            histXtrain = histXtrain + X_scaled_hist[0:len(X_scaled_hist)-end_date_index]

        histXtrain = np.reshape(histXtrain, (1,) + histXtrain.shape)
        print("hist shape "+str(histXtrain.shape))
        y_position = i + look_back
        y_position_end = y_position + prediction_horizon
        x_train_reshaped[i] = X_scaled[i:y_position]
        y__re = X_scaled[y_position:y_position_end]
        y_train_reshaped[i] = [item for sublist in y__re for item in sublist]
        realXtrain = np.reshape(x_train_reshaped[i], (1,) + x_train_reshaped[i].shape)
        ytrain = np.reshape(y_train_reshaped[i], (1,) + y_train_reshaped[i].shape)

        print("realX train shape : "+str(realXtrain.shape))

        start_time = time.clock()
        if i == 0:
            trained_model = train_model(realXtrain, histXtrain, ytrain, None, look_back, Hist_input_size, Hidden_Size, Batch_Size,
                                        prediction_horizon, Num_Epochs)
        else:
            trained_model = train_model(realXtrain, histXtrain, ytrain, trained_model, look_back, Hist_input_size, Hidden_Size, Batch_Size,
                                        prediction_horizon, Num_Epochs)
        end_time = time.clock()
        time_taken = end_time - start_time
        predicted_value, predTime = predict_model(trained_model, realXtrain, histXtrain, Batch_Size)
        error = abs(ytrain[0] - predicted_value)
        error_median = np.median(error)
        error_std = np.std(error)
        error_mean = np.mean(error)
        prediction_median.append(error_median)
        prediction_std.append(error_std)
        prediction_error.append(error_mean)
        train_time.append(time_taken)
        prediction_time.append(predTime)
        print("The iteration is **** ", i)

    return prediction_error, prediction_median, train_time, prediction_time

def post_processing_data(df, prediction_error, prediction_median, train_time, prediction_time):

    pred_new_df = df[1440:]                               # instead of 24 now 1440
    new_df_date = pred_new_df[-len(pred_new_df):]
    test_act = new_df_date.reset_index()
    test_act = test_act.drop('Values', axis =1)
    
    #Adding datetime to prediction error and changing to dataframe
    test_predictions_date = pd.DataFrame(prediction_error)
    test_predictions_date.columns = ['Values']
    test_predictions_date['Time'] = test_act['Time']
    
    #Adding datetime to prediction error median and changing to dataframe
    test_predictions_medianError = pd.DataFrame(prediction_median)
    test_predictions_medianError.columns = ['Values']
    test_predictions_medianError['Time'] = test_act['Time']
    
    print("Average Error is", test_predictions_date['Values'].mean())
    
    #Writing predicitons to a csv file
    test_predictions_date.to_csv('MAE_House20.csv')
    test_predictions_medianError.to_csv('MedianError_House20.csv')
    
    train_time_date = pd.DataFrame(train_time)
    prediction_time_date = pd.DataFrame(prediction_time)
    train_time_date.columns = ['Values']
    prediction_time_date.columns = ['Values']
    train_new_df = df[1:]
    new_df_date = df[-len(train_new_df):]
    train_act = new_df_date.reset_index()
    train_act = train_act.drop('Values', axis =1)
    train_time_date['Time'] = train_act['Time']
    prediction_time_date['Time'] = test_act['Time']
    
    train_time_date.to_csv('TrainTime_BestModel_House20.csv')
    prediction_time_date.to_csv('PredTime_BestModel_House20.csv')

    """
    #Generating the Plots
    f1 = plt.figure()
    f2 = plt.figure()
    f3 = plt.figure()
    f1.set_size_inches(18.5, 10.5)
    f2.set_size_inches(18.5, 10.5)
    f3.set_size_inches(18.5, 10.5)
    
    ax1 = f1.add_subplot(111)
    ax1.set_xlabel('Months')
    ax1.set_ylabel('Error')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax1.xaxis_date()
    fit1 = np.polyfit(np.arange(len(test_predictions_date.Time)),test_predictions_date.Values,1)
    fit_fn1 = np.poly1d(fit1)
    ax1.plot(test_predictions_date.Time,test_predictions_date.Values,'yo',label='Error')
    ax1.plot(test_predictions_date.Time, fit_fn1(np.arange(len(test_predictions_date.Time))), '--k',label='Regression')
    
    ax2 = f2.add_subplot(111)
    ax2.set_xlabel('Months')
    ax2.set_ylabel('Time [Sec]')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax2.xaxis_date()
    ax2.plot(train_time_date.Time,train_time_date.Values,label='Training Time')
    
    ax3 = f3.add_subplot(111)
    ax3.set_xlabel('Months')
    ax3.set_ylabel('Time [Sec]')
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax3.xaxis_date()
    ax3.plot(prediction_time_date.Time,prediction_time_date.Values,label='Prediction Time')
    
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper left')
    ax3.legend(loc='upper left')
    plt.show()
    """

if __name__ == "__main__":
    X_scaled, new_df, X_scaled_hist, new_hd = pre_processing_data("/usr/src/app/prediction/pv_data_house_20.csv",
                                           "/usr/src/app/prediction/pv_data_bolzano_italy.txt")
    X_scaled, new_df = X_scaled[0:3000], new_df[0:3000]
    #Defining Hyperparameters
    Num_Timesteps = 1      # instead of 24 now lookback 1440
    Hidden_Size = 48
    Batch_Size = 1
    Num_Epochs = 5
    Hist_input_size = 24
    
    Error_List, Error_Median, Train_Time, Prediction_Time = incremental_algorithm(X_scaled, new_df, X_scaled_hist,
                                                                                  Hist_input_size,
                                                                                  Num_Timesteps, Hidden_Size,
                                                                                  Batch_Size, Num_Epochs)
    post_processing_data(new_df, Error_List, Error_Median, Train_Time, Prediction_Time)