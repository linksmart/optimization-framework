import datetime

import pandas as pd
import numpy as np

def read_data(filename):
    df = pd.read_csv(filename, header=None)
    df.columns = ['Time', 'PV']
    df['Time'] = pd.to_datetime(df["Time"], errors='coerce')
    df.index = df["Time"]
    df = df.drop(columns=['Time'])
    print("read csv")
    print(df.head())

    return df

def compute_error(start_date):
    start_date_hist = datetime.datetime.fromtimestamp(start_date.timestamp()).replace(year=2016)
    end_date = start_date + datetime.timedelta(days=1)
    end_date_copy = datetime.datetime.fromtimestamp(end_date.timestamp())
    real_data = real.loc[start_date.strftime("%Y-%m-%d %H:%M:%S"): end_date.strftime("%Y-%m-%d %H:%M:%S")]
    real_data.columns = ['real']

    end_date_hist = start_date_hist + datetime.timedelta(days=1)
    if end_date_hist.year == 2016:
        historical_data = historical.loc[
                          start_date_hist.strftime("%Y-%m-%d %H:%M:%S"): end_date_hist.strftime("%Y-%m-%d %H:%M:%S")]
    else:
        end_date_hist = end_date_hist.replace(year=2016)
        historical_data = historical.loc[
                          start_date_hist.strftime("%Y-%m-%d %H:%M:%S"): "2016-12-31 23:59:00"]
        historical_data_2 = historical.loc[
                          "2016-01-01 00:00:00": end_date_hist.strftime("%Y-%m-%d %H:%M:%S")]

        historical_data = historical_data.append(historical_data_2)

    historical_data.columns = ['hist']
    if len(real_data) < 1441:
        print(len(real_data))
        return end_date_copy, None

    real_data = real_data.to_numpy().flatten()
    historical_data = historical_data.to_numpy().flatten()

    error = np.sqrt(((real_data - historical_data) ** 2).mean())
    return end_date_copy, error

pv_max_power = 5.0

historical = read_data("pv_data_fur_denmark_minute_data.csv")
real = read_data("pv_data_house_20.csv")
real['PV'] /= pv_max_power

start_date = datetime.datetime.strptime(str(real.index[0]), "%Y-%m-%d %H:%M:%S")
end_date = datetime.datetime.strptime(str(real.index[-1]), "%Y-%m-%d %H:%M:%S")

errors = []
while True:
    new_date, error = compute_error(start_date)
    if error != None:
        errors.append([start_date, error])
    if new_date >= end_date:
        break
    new_date += datetime.timedelta(minutes=1)
    start_date = new_date

with open("pv_error.csv", "w+") as f:
    for t, v in errors:
        s = t.strftime("%Y-%m-%d %H:%M:%S") + "," + str(v) + "\n"
        f.write(s)


