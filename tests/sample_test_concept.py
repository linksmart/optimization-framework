import datetime

from math import floor

dT_in_seconds = 900
steps_in_day = 96
horizon_in_steps = 40

def get_current_bucket():
    start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    current_time = datetime.datetime.now()
    bucket = floor((current_time - start_of_day).total_seconds() / dT_in_seconds)
    if bucket >= steps_in_day:
        bucket = steps_in_day - 1
    bucket = bucket % horizon_in_steps
    return bucket

print(get_current_bucket())