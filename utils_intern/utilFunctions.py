import datetime


class UtilFunctions:

    @staticmethod
    def get_sleep_secs(repeat_hour, repeat_min, repeat_sec, min_delay=10):
        current_time = datetime.datetime.now()
        repeat_sec = repeat_hour*3600 + repeat_min*60 + repeat_sec
        if repeat_sec <= min_delay:
            return min_delay
        start_of_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_since_start_of_day = (current_time - start_of_day).total_seconds()
        sec_diff = repeat_sec - seconds_since_start_of_day%repeat_sec
        if sec_diff < min_delay:
            sec_diff = min_delay
        return int(sec_diff)
