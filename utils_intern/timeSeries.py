"""
Created on Nov 12 11:21 2019

@author: nishit
"""

class TimeSeries:

    @staticmethod
    def expand_and_resample(raw_data, dT):
        if TimeSeries.valid_time_series(raw_data):
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