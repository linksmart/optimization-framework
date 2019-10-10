from datetime import datetime

import numpy as np
import pandas as pd

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

def monte_carlo_simulation_old(time_resolution, horizon, repetition, unplugged_mean, unplugged_std, plugged_mean,
                           plugged_std,
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

    logger.info("Running monte-carlo model")

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

def monte_carlo_simulation(time_resolution, horizon, repetition, unplugged_mean, unplugged_std, plugged_mean,
                           plugged_std,
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

    logger.debug("Running monte-carlo model")

    start = datetime(2018, 1, 1, 0, 0, 0)
    d_range = pd.date_range(start, periods=horizon, freq=pd.Timedelta(seconds=time_resolution))
    timestamps = []
    position_proof = {}
    number_of_days = 0
    for dt in d_range:
        # Iterate through the date range (for which we will calculate the markov model)
        mstr = str(dt).split(' ')[1][:5]
        day = (dt - start).days
        number_of_days = day
        timestamps.append((day,mstr))  # Generate a list that contains the day times in HH:MM format
        for carNo in range(max_number_of_cars + 1):
            position_proof[(day, mstr) , carNo] = 0  # Number of the proofs of hosting "carNo" numbers of cars at the park

    for n in range(repetition):
        # Simulate many times
        departure = {}
        arrival = {}
        for day in range(number_of_days+1):
            overlap = True

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
                        departure[day, car_label + 1] = "%02d:%02d" % (hou_dep[car_label], min_dep[car_label])
                        arrival[day, car_label + 1] = "%02d:%02d" % (hou_arr[car_label], min_arr[car_label])

        for nb in range(len(timestamps)):
            # Iterates trough every HH:MM of the horizon
            current_time_step = timestamps[nb]
            total_parking_cars = 0
            day = current_time_step[0]

            # Checks how many cars are at home state
            for car_label in range(1, max_number_of_cars + 1):

                if departure[day, car_label] < current_time_step[1] < arrival[day, car_label]:
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

def markov_model_simulation_old(time_resolution, horizon, repetition, unplugged_mean, unplugged_std,
                            plugged_mean, plugged_std):
    """
    Runs a Markov model simulation with given statistical parameters
    Returns a dictionary of markov model

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

    logger.info("Running markov model")

    max_number_of_cars = 1


    start = datetime(2018, 1, 1, 0, 0, 0)
    d_range = pd.date_range(start, periods=horizon, freq=pd.Timedelta(seconds=time_resolution))
    timestamps = []
    transition_proof = {}
    position_proof = {}

    for dt in d_range:
        # Iterate through the date range (for which we will calculate the markov model)
        mstr = str(dt).split(' ')[1]
        timestamps.append(mstr[:5])  # Generate a list that contains the day times in HH:MM format
        # For two positions
        for position in range(2):
            position_proof[mstr[:5], position] = 0  # Number of the proofs of "position" (car home  0 and car away 1)
            for next_position in range(2):
                transition_proof[mstr[:5], position, next_position] = 0

    for n in range(repetition):
        # Simulate many times
        overlap = True
        departure = None
        arrival = None

        while overlap:
            cand_dep = np.random.normal(unplugged_mean, unplugged_std)
            cand_arr = np.random.normal(plugged_mean, plugged_std)

            # If departure<arrival
            if cand_dep < cand_arr:
                overlap = False
                min_dep = cand_dep * 60
                hou_dep, min_dep = divmod(min_dep, 60)
                min_arr = cand_arr * 60
                hou_arr, min_arr = divmod(min_arr, 60)

                departure = "%02d:%02d" % (hou_dep, min_dep)
                arrival = "%02d:%02d" % (hou_arr, min_arr)

        for nb in range(len(timestamps)):
            # Iterates trough every HH:MM of the horizon

            current_time_step = timestamps[nb]
            next_time_step = timestamps[nb + 1] if nb < len(timestamps) - 1 else '24:00'

            # Checks how many cars are at home state
            if current_time_step < departure:  # If this HH:MM is smaller than my departure time

                position_proof[
                    current_time_step, 1] += 1  # Counts as one proof for Home state at HH:MM
                if next_time_step < departure:  # If next hour (of HH:MM) is smaller than my departure time
                    transition_proof[
                        current_time_step, 1, 1] += 1  # Counts as one proof for transition from home to home state
                    # during
                    # HH:MM
                else:  # Otherwise
                    transition_proof[
                        current_time_step, 1, 0] += 1  # Counts as one proof for transition from home to away state
                    # during
                    # HH:MM

            elif departure < current_time_step < arrival:  # If this HH:MM is between my departure and arrival times
                position_proof[current_time_step, 0] += 1  # Counts as one proof for Away state at HH:MM
                if next_time_step < arrival:  # If next hour (of HH:MM) is smaller than my arrival time
                    transition_proof[
                        current_time_step, 0, 0] += 1  # Counts as one proof for transition from away to away state
                    # during
                    # HH:MM
                else:  # Otherwise
                    transition_proof[
                        current_time_step, 0, 1] += 1  # Counts as one proof for transition from away to home state
                    # during
                    # HH:MM

            elif arrival <= current_time_step:  # If this HH:MM is greater than my arrival time
                position_proof[current_time_step, 1] += 1  # Counts as one proof for Home state at HH:MM
                transition_proof[
                    current_time_step, 1, 1] += 1  # Counts as one proof for transition from home to home state
                # during
                # HH:MM

    markov_model = {}
    for i, (time_step, position, next_position) in enumerate(transition_proof.keys()):
        row = i // 4
        if position_proof[time_step, position] != 0:
            markov_model[row, position, next_position] = transition_proof[time_step, position, next_position] / \
                                                         position_proof[time_step, position]
        else:
            markov_model[row, position, next_position] = 0.5

    return markov_model

def markov_model_simulation(time_resolution, horizon, repetition, unplugged_mean, unplugged_std,
                            plugged_mean, plugged_std):
    """
       Runs a Markov model simulation with given statistical parameters
       Returns a dictionary of markov model

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

    logger.debug("Running markov model")

    max_number_of_cars = 1


    start = datetime(2018, 1, 1, 0, 0, 0)
    d_range = pd.date_range(start, periods=horizon, freq=pd.Timedelta(seconds=time_resolution))
    timestamps = []
    transition_proof = {}
    position_proof = {}
    number_of_days = 0
    for dt in d_range:
        # Iterate through the date range (for which we will calculate the markov model)
        mstr = str(dt).split(' ')[1][:5]
        day = (dt - start).days
        number_of_days = day
        timestamps.append((day, mstr))  # Generate a list that contains the day times in HH:MM format
        # For two positions
        for position in range(2):
            position_proof[(day, mstr), position] = 0  # Number of the proofs of "position" (car home  0 and car away 1)
            for next_position in range(2):
                transition_proof[(day, mstr), position, next_position] = 0

    for n in range(repetition):
        # Simulate many times
        departure = {}
        arrival = {}
        for day in range(number_of_days + 1):
            overlap = True

            while overlap:
                cand_dep = np.random.normal(unplugged_mean, unplugged_std)
                cand_arr = np.random.normal(plugged_mean, plugged_std)

                # If departure<arrival
                if cand_dep < cand_arr:
                    overlap = False
                    min_dep = cand_dep * 60
                    hou_dep, min_dep = divmod(min_dep, 60)
                    min_arr = cand_arr * 60
                    hou_arr, min_arr = divmod(min_arr, 60)

                    departure[day] = "%02d:%02d" % (hou_dep, min_dep)
                    arrival[day] = "%02d:%02d" % (hou_arr, min_arr)

        for nb in range(len(timestamps)):
            # Iterates trough every HH:MM of the horizon

            current_time_step = timestamps[nb]
            day = current_time_step[0]
            current_time_step_value = current_time_step[1]
            next_time_step = timestamps[nb + 1] if nb < len(timestamps) - 1 else (day, '24:00')
            day_next = next_time_step[0]
            next_time_step_value = next_time_step[1]

            # Checks how many cars are at home state
            if current_time_step_value < departure[day]:  # If this HH:MM is smaller than my departure time

                position_proof[
                    current_time_step, 1] += 1  # Counts as one proof for Home state at HH:MM
                if next_time_step_value < departure[day_next]:  # If next hour (of HH:MM) is smaller than my departure time
                    transition_proof[
                        current_time_step, 1, 1] += 1  # Counts as one proof for transition from home to home state
                    # during
                    # HH:MM
                else:  # Otherwise
                    transition_proof[
                        current_time_step, 1, 0] += 1  # Counts as one proof for transition from home to away state
                    # during
                    # HH:MM

            elif departure[day] < current_time_step_value < arrival[day]:  # If this HH:MM is between my departure and arrival times
                position_proof[current_time_step, 0] += 1  # Counts as one proof for Away state at HH:MM
                if next_time_step_value < arrival[day_next]:  # If next hour (of HH:MM) is smaller than my arrival time
                    transition_proof[
                        current_time_step, 0, 0] += 1  # Counts as one proof for transition from away to away state
                    # during
                    # HH:MM
                else:  # Otherwise
                    transition_proof[
                        current_time_step, 0, 1] += 1  # Counts as one proof for transition from away to home state
                    # during
                    # HH:MM

            elif arrival[day] <= current_time_step_value:  # If this HH:MM is greater than my arrival time
                position_proof[current_time_step, 1] += 1  # Counts as one proof for Home state at HH:MM
                transition_proof[
                    current_time_step, 1, 1] += 1  # Counts as one proof for transition from home to home state
                # during
                # HH:MM

    markov_model = {}
    for i, (time_step, position, next_position) in enumerate(transition_proof.keys()):
        row = i // 4
        if position_proof[time_step, position] != 0:
            markov_model[row, position, next_position] = transition_proof[time_step, position, next_position] / \
                                                         position_proof[time_step, position]
        else:
            markov_model[row, position, next_position] = 0.5

    return markov_model



def simulate(time_resolution, horizon, repetition, unplugged_mean, unplugged_std, plugged_mean, plugged_std,
             max_number_of_cars=1, single_ev=False):
    if single_ev:
        return markov_model_simulation(time_resolution, horizon, repetition, unplugged_mean, unplugged_std,
                                       plugged_mean, plugged_std)
    else:
        return monte_carlo_simulation(time_resolution, horizon, repetition, unplugged_mean, unplugged_std,
                                      plugged_mean, plugged_std, max_number_of_cars)
