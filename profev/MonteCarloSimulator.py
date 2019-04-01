from datetime import datetime

import numpy as np
import pandas as pd


def simulate(time_resolution, horizon, repetition, unplugged_mean, unplugged_std, plugged_mean, plugged_std,
             max_number_of_cars):
    """
    Runs a Monte-Carlo simulation with given statistical parameters
    Returns a dictionary of pmf model

    inputs
    -------
    time_resolution: number of seconds in one time step
    horizon       : total number of time steps in the prediction horizon
           time_resolution=3600 ->1 hour resolution
           horizon= 24 if time_resolution=3600 ->1 day horizon with 24 time steps
    repetition      : number of repetition of MC simulation
    unplugged_mean         : Mean departure time of EV
    unplugged_std        : Standard variation of departure hour
    plugged_mean         : Mean arrival time of EV
    plugged_std        : Standard variation of arrival hour
            unplugged_mean= 7.75 stands for 07:45 mean departure hour
                   1.0 equals 60 minutes
    max_number_of_cars      : Number of cars in the fleet
    """

    start = datetime(2018, 1, 1, 0, 0, 0)
    d_range = pd.date_range(start, periods=horizon, freq=pd.Timedelta(seconds=time_resolution))
    timestamps = []
    position_proof = {}
    for dt in d_range:
        # Iterate through the date range (for which we will calculate the markov model)
        mstr = str(dt).split(' ')[1]
        timestamps.append(mstr[:5])  # Generate a list that contains the day times in HH:MM format
        for carNo in range(max_number_of_cars + 1):
            position_proof[mstr[:5], carNo] = 0  # Number of the proofs of hosting "carNo" numbers of cars at the park

    for n in range(repetition):
        # Simulate many times
        overlap = True
        departure = {}
        arrival = {}

        while overlap:
            cand_dep = np.random.normal(unplugged_mean, unplugged_std, max_number_of_cars)
            cand_arr = np.random.normal(plugged_mean, plugged_std, max_number_of_cars)

            # If departure<arrival
            if all(cand_dep < cand_arr):
                overlap = False
                min_dep = cand_dep * 60
                hou_dep, min_dep = divmod(min_dep, 60)
                min_arr = cand_arr * 60
                hou_arr, min_arr = divmod(min_arr, 60)

                for car_label in range(max_number_of_cars):
                    # Convert float to HH:MM format
                    departure[car_label + 1] = "%02d:%02d" % (hou_dep[car_label], min_dep[car_label])
                    arrival[car_label + 1] = "%02d:%02d" % (hou_arr[car_label], min_arr[car_label])

        for nb in range(len(timestamps)):
            # Iterates trough every HH:MM of the horizon

            current_time_step = timestamps[nb]
            total_parking_cars = 0

            # Checks how many cars are at home state
            for car_label in range(1, max_number_of_cars + 1):

                if departure[car_label] < current_time_step < arrival[car_label]:
                    total_parking_cars += 0
                else:
                    total_parking_cars += 1

            # Use this as a proof for hosting n cars at HH:MM
            position_proof[current_time_step, total_parking_cars] += 1 / repetition

    behaviour_model = {}
    row = 0
    for time_step, car_label in position_proof.keys():
        next_item = row // (max_number_of_cars + 1)
        behaviour_model[next_item] = {}
        for car in range(max_number_of_cars + 1):
            behaviour_model[next_item][car] = position_proof[time_step, car]

        row += 1

    return behaviour_model
