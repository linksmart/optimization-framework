"""
Created on Jun 28 10:39 2018

@author: nishit
"""
import datetime
import time
import math
import pandas as pd
import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler

from utils_intern.messageLogger import MessageLogger
from utils_intern.timeSeries import TimeSeries

logger = MessageLogger.get_logger_parent()


class ProcessingData:

    #pv hist data is 2016 data
    def __init__(self, type, hist_data=None):
        self.new_df = None
        self.max = 1
        self.min = 0
        self.start_date_hist = datetime.datetime.strptime("2016-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        self.type = type
        if self.type == "pv":
            self.preprocess_hist_data(hist_data)

    def preprocess_hist_data(self, hist_data):
        hist_data_new = []
        hist_data.insert(0, hist_data[-1])
        for t, v in hist_data:
            hist_data_new.append([datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S"), float(v)])

        hd = pd.DataFrame(hist_data_new, columns=['Time', 'Values'])
        hd['Time'] = pd.to_datetime(hd["Time"], errors='coerce')
        hd.index = hd["Time"]
        hd = hd.drop(columns=['Time'])

        data = hd.values.reshape(-1, 1)
        Xmin = np.amin(data)
        Xmax = np.amax(data)
        X_std = (data - Xmin) / (Xmax - Xmin)
        max = 1
        min = 0
        self.X_scaled_hist = X_std * (max - min) + min

    def preprocess_data_predict_load(self, raw_data, num_timesteps):
        # Loading Data
        # taking the last timestamp since we are going to use only the last data vector
        latest_timestamp = raw_data[-1:][0][0]
        logger.debug(latest_timestamp)
        # df = pd.DataFrame(raw_data, columns=col_heads)
        df = pd.DataFrame(raw_data)
        df = df[df.columns[:2]]
        df.columns = ['Time', 'Electricity']

        new_df = df
        new_df.columns = ['DateTime', 'Electricity']
        # Changing dtype to pandas datetime format
        new_df['DateTime'] = pd.to_datetime(new_df['DateTime'], unit='s')
        new_df = new_df.set_index('DateTime')

        # checking for null values and if any, replacing them with last valid observation
        new_df.isnull().sum()
        new_df.Electricity.fillna(method='pad', inplace=True)

        # scale the data to be in the range (0, 1)
        data = new_df.values.reshape(-1, 1)
        # scaler = MinMaxScaler(feature_range=(0, 1), copy=False)
        # data = scaler.fit_transform(data)

        flat_list = [item for sublist in data for item in sublist]
        # Quantile Normalization
        s = pd.Series(flat_list)
        quant = s.quantile(0.75)
        Xmin = np.amin(data)
        Xmax = quant
        if Xmax <= Xmin:
            Xmax = Xmin + 0.001
        X_std = (data - Xmin) / (Xmax - Xmin)
        data = X_std * (self.max - self.min) + self.min

        look_back = num_timesteps
        num_features = 1
        logger.debug("data dim = " + str(data.shape))
        logger.debug("input shape = " + str(num_timesteps))
        nb_samples = data.shape[0] - num_timesteps + 1
        if nb_samples > 0:
            logger.debug("nb samples is " + str(nb_samples))
            x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
            for i in range(nb_samples):
                y_position_start = i + look_back
                x_train_reshaped[i] = data[i:y_position_start]

            Xtest = x_train_reshaped[-1:]
            logger.debug("shape : " + str(Xtest.shape))
            return Xtest, Xmax, Xmin, latest_timestamp
        return None, None, None, None

    def preprocess_data_predict_pv(self, raw_data, num_timesteps, input_size_hist):
        # Loading Data
        # taking the last timestamp since we are going to use only the last data vector
        latest_timestamp = raw_data[-1:][0][0]
        logger.debug(latest_timestamp)
        # df = pd.DataFrame(raw_data, columns=col_heads)
        df = pd.DataFrame(raw_data)
        df = df[df.columns[:2]]
        df.columns = ['Time', 'Electricity']

        new_df = df
        new_df.columns = ['DateTime', 'Electricity']
        # Changing dtype to pandas datetime format
        new_df['DateTime'] = pd.to_datetime(new_df['DateTime'], unit='s')
        new_df = new_df.set_index('DateTime')

        # checking for null values and if any, replacing them with last valid observation
        new_df.isnull().sum()
        new_df.Electricity.fillna(method='pad', inplace=True)

        # scale the data to be in the range (0, 1)
        data = new_df.values.reshape(-1, 1)
        # scaler = MinMaxScaler(feature_range=(0, 1), copy=False)
        # data = scaler.fit_transform(data)

        flat_list = [item for sublist in data for item in sublist]
        # Quantile Normalization
        s = pd.Series(flat_list)
        quant = s.quantile(0.75)
        Xmin = np.amin(data)
        Xmax = quant
        if Xmax <= Xmin:
            Xmax = Xmin + 0.001
        X_std = (data - Xmin) / (Xmax - Xmin)
        data = X_std * (self.max - self.min) + self.min

        look_back = num_timesteps
        num_features = 1
        logger.debug("data dim = " + str(data.shape))
        logger.debug("input shape = " + str(num_timesteps))
        nb_samples = data.shape[0] - num_timesteps + 1
        if nb_samples > 0:
            logger.debug("nb samples is " + str(nb_samples))
            x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
            h_train_reshaped = np.zeros((nb_samples, input_size_hist, num_features))
            for i in range(nb_samples):
                y_position_start = i + look_back
                x_train_reshaped[i] = data[i:y_position_start]
                start_date_index = self.find_nearest_hour_index(
                    datetime.datetime.strptime(str(new_df.index[i]), "%Y-%m-%d %H:%M:%S"))
                end_date_index = start_date_index + input_size_hist
                histXtrain = self.X_scaled_hist[start_date_index:end_date_index]
                if end_date_index >= len(self.X_scaled_hist):
                    histXtrain = histXtrain + self.X_scaled_hist[0:len(self.X_scaled_hist) - end_date_index]
                h_train_reshaped[i] = histXtrain

            Xtest = x_train_reshaped[-1:]
            Htest = h_train_reshaped[-1:]
            logger.debug("shape : " + str(Xtest.shape))
            return {"real": Xtest, "hist": Htest}, Xmax, Xmin, latest_timestamp
        return None, None, None, None

    def postprocess_data(self, prediction, startTimestamp, delta, horizon_steps, Xmax, Xmin):
        data = prediction.reshape(-1, 1)
        # data = scaler.inverse_transform(data)

        data = (data - self.min) / (self.max - self.min)
        data = data * (Xmax - Xmin) + Xmin

        data = data.reshape(-1)
        startTime = datetime.datetime.fromtimestamp(startTimestamp)
        result = []
        for pred in data:
            result.append([startTime.timestamp(), pred])
            startTime += datetime.timedelta(seconds=60)
        result = TimeSeries.expand_and_resample_reversed(result, delta, False)
        result = result[:horizon_steps]
        logger.debug("pred out start val = " + str(result[0]))
        output = {}
        for t, v in result:
            output[datetime.datetime.fromtimestamp(t)] = v
        return output

    def append_mock_data(self, data, num_timesteps, dT):
        l = len(data)
        diff = num_timesteps - l + 1
        if l == 0:
            earliest_timestamp = time.time()
        else:
            earliest_timestamp = data[0][0]
        new_data = data
        for i in range(diff):
            earliest_timestamp -= dT
            new_data.insert(0, [earliest_timestamp, 0.000001])
        return new_data

    def break_series_into_countinous_blocks(self, raw_data, dT, steps):
        allowed_continous_gap_percent = 0.1
        duration_of_one_data_set = steps * dT
        required_mins = math.ceil(duration_of_one_data_set / 60.0)
        allowed_continous_gap_mins = required_mins * allowed_continous_gap_percent
        continous_series = []
        temp_data = []
        logger.info("allowed " + str(allowed_continous_gap_mins))
        prev_time = raw_data[0][0]
        for i in range(len(raw_data)):
            curr_time = raw_data[i][0]
            minute_diff = (curr_time - prev_time) / 60.0
            if minute_diff > allowed_continous_gap_mins:
                continous_series.append(temp_data.copy())
                temp_data = []
            temp_data.append(raw_data[i])
            prev_time = curr_time
        if len(temp_data) > 0:
            continous_series.append(temp_data.copy())
        return continous_series

    def expand_and_resample_into_blocks(self, raw_data, model_data_dT, input_size, output_size):
        if len(raw_data) > 0:
            min_length = input_size + output_size
            blocks = self.break_series_into_countinous_blocks(raw_data, model_data_dT, min_length)
            logger.info("num blocks = " + str(len(blocks)))
            resampled_blocks = []
            block_has_min_length = []
            merged = False
            for block in blocks:
                resampled_block = TimeSeries.expand_and_resample(block, model_data_dT)
                if len(resampled_block) > 0:
                    resampled_blocks.append(resampled_block)
                    logger.info("block size = " + str(len(resampled_block)))
                    if len(resampled_block) >= min_length:
                        block_has_min_length.append(True)
                    else:
                        block_has_min_length.append(False)
            if len(block_has_min_length) > 0 and not any(block_has_min_length):
                logger.info("merging block because insufficient data")
                new_block = []
                end_time = resampled_blocks[-1][-1][0]
                # TODO : check logic
                for i in reversed(range(len(resampled_blocks))):
                    rsb = resampled_blocks[i]
                    start_time = rsb[0][0]
                    if end_time - start_time < min_length * model_data_dT:
                        rsb.extend(new_block)
                        new_block = rsb
                        merged = True
                    else:
                        rsb.extend(new_block)
                        new_block = rsb
                        merged = True
                        break
                if merged:
                    new_block = TimeSeries.expand_and_resample(new_block, model_data_dT)
                    logger.info("length of merged blocks after expand = " + str(len(new_block)))
                resampled_blocks = [new_block]
            return resampled_blocks, merged
        else:
            return [], False

    def preprocess_data_train_load(self, blocks, dT, input_size, output_size, sp):
        x_list = []
        y_list = []
        look_back = input_size
        num_features = 1
        count = 0
        lastest_input_timestep_data_point = 0
        for raw_data in blocks:
            # Loading Data
            if len(raw_data) >= input_size + output_size:
                # raw_data = raw_data[-7200:]
                latest_timestamp = raw_data[-1:][0][0]
                logger.debug(latest_timestamp)
                if latest_timestamp > lastest_input_timestep_data_point:
                    lastest_input_timestep_data_point = latest_timestamp
                # df = pd.DataFrame(raw_data, columns=col_heads)
                df = pd.DataFrame(raw_data)
                df = df[df.columns[:2]]
                df.columns = ['Time', 'Electricity']

                new_df = df
                new_df.columns = ['DateTime', 'Electricity']
                # Changing dtype to pandas datetime format
                new_df['DateTime'] = pd.to_datetime(new_df['DateTime'], unit='s')
                new_df = new_df.set_index('DateTime')

                # checking for null values and if any, replacing them with last valid observation
                new_df.isnull().sum()
                new_df.Electricity.fillna(method='pad', inplace=True)

                # scale the data to be in the range (0, 1)
                data = new_df.values.reshape(-1, 1)
                # scaler = MinMaxScaler(feature_range=(0, 1), copy=False)
                # data = scaler.fit_transform(data)

                flat_list = [item for sublist in data for item in sublist]
                # Quantile Normalization
                s = pd.Series(flat_list)
                quant = s.quantile(0.75)
                Xmin = np.amin(data)
                Xmax = quant
                if Xmax <= Xmin:
                    Xmax = Xmin + 0.001
                X_std = (data - Xmin) / (Xmax - Xmin)
                max = 1
                min = 0
                data = X_std * (max - min) + min

                nb_samples = data.shape[0] - (input_size + output_size) + 1
                logger.info("nb samples = " + str(nb_samples))
                x_train_reshaped = np.zeros((nb_samples, look_back, num_features))
                y_train_reshaped = np.zeros((nb_samples, output_size))
                logger.info("data dim = " + str(data.shape))
                for i in range(nb_samples):
                    y_position_start = i + look_back
                    x_train_reshaped[i] = data[i:y_position_start]
                    y_position_end = y_position_start + output_size
                    l = data[y_position_start:y_position_end]
                    y_train_reshaped[i] = [item for sublist in l for item in sublist]

                x_list.append(x_train_reshaped)
                y_list.append(y_train_reshaped)
                count += len(x_train_reshaped)
                logger.info("count = " + str(count))
        Xtrain = np.zeros((count, look_back, num_features))
        Ytrain = np.zeros((count, output_size))
        j = 0
        for x_train in x_list:
            for item in x_train:
                Xtrain[j] = item
                j += 1
        j = 0
        for y_train in y_list:
            for item in y_train:
                Ytrain[j] = item
                j += 1
        logger.debug("fixing data size upper limit to " + str(sp))
        Xtrain, Ytrain = Xtrain[-sp:], Ytrain[-sp:]
        # TODO: check the capacity of RPi to operate with more data size
        lastest_input_timestep_data_point -= ((input_size + output_size) * dT)
        return Xtrain, Ytrain, lastest_input_timestep_data_point

    def find_nearest_hour_index(self, t):
        if t.minute > 30:
            t = t.replace(year=2016, minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        else:
            t = t.replace(year=2016, minute=0, second=0, microsecond=0)
        index = int((t - self.start_date_hist).total_seconds() / 3600)
        return index

    def preprocess_data_train_pv(self, blocks, dT, input_size, input_size_hist, output_size, sp):
        x_list = []
        y_list = []
        h_list = []
        logger.debug("sizes "+str(input_size)+ " "+str(input_size_hist)+ " "+str(output_size))
        num_features = 1
        count = 0
        lastest_input_timestep_data_point = 0
        for raw_data in blocks:
            # Loading Data
            if len(raw_data) >= input_size + output_size:
                # raw_data = raw_data[-7200:]
                latest_timestamp = raw_data[-1:][0][0]
                logger.debug(latest_timestamp)
                if latest_timestamp > lastest_input_timestep_data_point:
                    lastest_input_timestep_data_point = latest_timestamp
                # df = pd.DataFrame(raw_data, columns=col_heads)
                df = pd.DataFrame(raw_data)
                df = df[df.columns[:2]]
                df.columns = ['Time', 'Electricity']

                new_df = df
                new_df.columns = ['DateTime', 'Electricity']
                # Changing dtype to pandas datetime format
                new_df['DateTime'] = pd.to_datetime(new_df['DateTime'], unit='s')
                new_df = new_df.set_index('DateTime')

                # checking for null values and if any, replacing them with last valid observation
                new_df.isnull().sum()
                new_df.Electricity.fillna(method='pad', inplace=True)

                # scale the data to be in the range (0, 1)
                data = new_df.values.reshape(-1, 1)
                # scaler = MinMaxScaler(feature_range=(0, 1), copy=False)
                # data = scaler.fit_transform(data)

                flat_list = [item for sublist in data for item in sublist]

                # Quantile Normalization
                s = pd.Series(flat_list)
                quant = s.quantile(0.75)
                Xmin = np.amin(data)
                Xmax = quant
                if Xmax <= Xmin:
                    Xmax = Xmin + 0.001
                X_std = (data - Xmin) / (Xmax - Xmin)
                max = 1
                min = 0
                data = X_std * (max - min) + min



                nb_samples = data.shape[0] - (input_size + output_size) + 1
                logger.info("nb samples = " + str(nb_samples))
                x_train_reshaped = np.zeros((nb_samples, input_size, num_features))
                h_train_reshaped = np.zeros((nb_samples, input_size_hist, num_features))
                y_train_reshaped = np.zeros((nb_samples, output_size))
                logger.info("data dim = " + str(data.shape))
                for i in range(nb_samples):
                    y_position_start = i + input_size
                    x_train_reshaped[i] = data[i:y_position_start]
                    y_position_end = y_position_start + output_size
                    l = data[y_position_start:y_position_end]
                    y_train_reshaped[i] = [item for sublist in l for item in sublist]
                    start_date_index = self.find_nearest_hour_index(
                        datetime.datetime.strptime(str(new_df.index[i]), "%Y-%m-%d %H:%M:%S"))
                    end_date_index = start_date_index + input_size_hist
                    histXtrain = self.X_scaled_hist[start_date_index:end_date_index]
                    if end_date_index >= len(self.X_scaled_hist):
                        histXtrain = histXtrain + self.X_scaled_hist[0:len(self.X_scaled_hist) - end_date_index]
                    h_train_reshaped[i] = histXtrain

                x_list.append(x_train_reshaped)
                y_list.append(y_train_reshaped)
                h_list.append(h_train_reshaped)
                count += len(x_train_reshaped)
                logger.info("count = " + str(count))
        Xtrain = np.zeros((count, input_size, num_features))
        Htrain = np.zeros((count, input_size_hist, num_features))
        Ytrain = np.zeros((count, output_size))
        j = 0
        for x_train in x_list:
            for item in x_train:
                Xtrain[j] = item
                j += 1
        j = 0
        for y_train in y_list:
            for item in y_train:
                Ytrain[j] = item
                j += 1
        j = 0
        for h_train in h_list:
            for item in h_train:
                Htrain[j] = item
                j += 1
        logger.debug("fixing data size upper limit to " + str(sp))
        logger.debug("shape of Xtrain "+str(Xtrain.shape))
        logger.debug("shape of Htrain " + str(Htrain.shape))
        logger.debug("shape of Ytrain " + str(Ytrain.shape))
        Xtrain, Ytrain, Htrain = Xtrain[-sp:], Ytrain[-sp:], Htrain[-sp:]
        # TODO: check the capacity of RPi to operate with more data size
        lastest_input_timestep_data_point -= ((input_size + output_size) * dT)
        return {"real": Xtrain, "hist": Htrain}, Ytrain, lastest_input_timestep_data_point

    def check_for_nan_and_inf(self, arr, s):
        if np.any(np.isnan(arr)):
            logger.debug(s+" nan "+str(arr))
            return True
        if np.any(np.isinf(arr)):
            logger.debug(s+" inf "+str(arr))
            return True
        return False

    def get_regression_values(self, train_data, input_size, output_size, dT):
        new_data = np.array(train_data[-input_size:])

        x = new_data[:, 0]
        x = x.reshape(-1, 1)
        last_timestamp = x[-1][0]

        logger.info("last timestamp load = " + str(last_timestamp))

        y = new_data[:, 1]
        y = y.reshape(-1, 1)

        reg = LinearRegression().fit(x, y)

        prediction_input = []
        for i in range(output_size):
            prediction_input.append([last_timestamp])
            last_timestamp += dT

        prediction_input = np.array(prediction_input)
        prediction_input = prediction_input.reshape(-1, 1)

        prediction_output = reg.predict(prediction_input)

        prediction_input = prediction_input.reshape(-1)
        prediction_output = prediction_output.reshape(-1)

        new_data = {}

        for i in range(output_size):
            new_data[prediction_input[i]] = prediction_output[i]

        return new_data
