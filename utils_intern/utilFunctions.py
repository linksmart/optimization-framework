import datetime
import shlex
import subprocess


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

    @staticmethod
    def execute_command(command, service_name, msg):
        try:
            command = shlex.split(command)
            print("command "+str(command))
            process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
            out, err = process.communicate()
            pid = process.pid
            print(service_name + " " + msg + " , pid = " + str(pid))
            print("Output: "+str(out.decode('utf-8')))
            print("Error: " + str(err))
            return True
        except Exception as e:
            print("error running the command " + str(command) + " " + str(e))
            return False