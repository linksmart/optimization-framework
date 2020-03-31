"""
Created on Nov 12 11:21 2019

@author: nishit
"""
import pandas as pd

class TimeSeries:

    @staticmethod
    def expand_and_resample(raw_data, dT, append_next_dT = False):
        if TimeSeries.valid_time_series(raw_data):
            if append_next_dT:
                raw_data = TimeSeries.append_next_dT_value(raw_data, dT)
            step = float(dT)
            j = len(raw_data) - 1
            new_data = []
            if j > 0:
                start_time = raw_data[j][0]
                start_value = raw_data[j][1]
                new_data.append([start_time, start_value])
                prev_time = start_time
                prev_value = start_value
                required_diff = step
                j -= 1
                while j >= 0:
                    end_time = raw_data[j][0]
                    end_value = raw_data[j][1]
                    diff_sec = prev_time - end_time
                    if diff_sec >= required_diff:
                        ratio = required_diff / diff_sec
                        inter_time = prev_time - required_diff
                        inter_value = prev_value - (prev_value - end_value) * ratio
                        new_data.append([inter_time, inter_value])
                        prev_time = inter_time
                        prev_value = inter_value
                        required_diff = step
                    else:
                        required_diff -= diff_sec
                        prev_time = end_time
                        prev_value = end_value
                        j -= 1
            else:
                new_data = raw_data
            new_data.reverse()
        else:
            new_data = raw_data
        return new_data

    @staticmethod
    def append_next_dT_value(raw_data, dT):
        if len(raw_data) > 1:
            new_data = []
            new_data.extend(raw_data)
            start_time = raw_data[0][0]
            end_time = raw_data[-1][0]
            time_diff = end_time - start_time
            time_diff = time_diff + time_diff/(len(raw_data)-1)
            changed_time_data = TimeSeries.increment_time(raw_data, time_diff)
            i = 0
            dt_diff = 0
            while dt_diff < dT and i < len(changed_time_data):
                dt_diff = changed_time_data[i][0] - end_time
                new_data.append(changed_time_data[i])
                i += 1
            return new_data
        return raw_data

    @staticmethod
    def increment_time(raw_data, time_diff):
        if len(raw_data) > 0:
            new_data = []
            for t, v in raw_data:
                new_data.append([t+time_diff,v])
            return new_data
        return raw_data


    @staticmethod
    def valid_time_series(raw_data):
        try:
            if isinstance(raw_data, list):
                if len(raw_data) > 0:
                    sample = raw_data[0]
                    if len(sample) == 2:
                        if (isinstance(sample[0], float) or isinstance(sample[0], int)) and (isinstance(sample[1], float) or isinstance(sample[1], int)):
                            return True
            return False
        except Exception:
            return False

    @staticmethod
    def panda_resample(raw_data, dT, append_next_dT = False):
        # Not working as expected
        if TimeSeries.valid_time_series(raw_data):
            if append_next_dT:
                raw_data = TimeSeries.append_next_dT_value(raw_data, dT)

            df = pd.DataFrame(raw_data, columns=["time", "val"])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)

            ratio = str(dT) + "S"

            df_result = df.resample(ratio).mean()
            if df_result.isnull().values.any():
                df_result = df.resample(ratio).interpolate()
            if df_result.isnull().values.any():
                df_result = df.resample(ratio).mean().interpolate()
                df_result.fillna(method='pad')

            df_result.reset_index(level=0, inplace=True)
            df_result["time"] = (df_result["time"] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')

            new_data = []
            for row in df_result.values:
                new_data.append([int(row[0]), float(row[1])])

            new_t = new_data[0][0]
            raw_t = raw_data[0][0]

            if new_t < raw_t:
                new_data = new_data[1:]

            return new_data
        else:
            return raw_data