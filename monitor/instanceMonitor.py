"""
Created on Jan 28 13:24 2020

@author: nishit
"""
import json
import sys
import threading
import time
import subprocess
import os
from subprocess import Popen, PIPE
import shlex

from monitor.status import Status
from utils_intern.messageLogger import MessageLogger

from IO.redisDB import RedisDB


class InstanceMonitor:

    def __init__(self, config):
        self.logger = MessageLogger.get_logger(__name__, None)
        self.config = config
        self.docker_file_names = self.get_docker_file_names()
        if len(self.docker_file_names) > 0:
            self.topic_params = json.loads(config.get("IO", "monitor.mqtt.topic"))
            self.check_frequency = config.getint("IO", "monitor.frequency.sec", fallback=60)
            self.allowed_delay_count = config.getfloat("IO", "allowed.delay.count", fallback=2)
            self.timeout = config.getint("IO", "timeout", fallback=60)
            self.status = Status(False, self.topic_params, config)
            self.service_status = {}
            self.log_persisted = {}
            self.start_services()
            self.check_status_thread = threading.Thread(target=self.check_status)
            self.check_status_thread.start()

    def start_services(self):
        for service in self.docker_file_names.keys():
            self.service_status[service] = self.start_service(service, "started")

    def Stop(self):
        for service, status in self.service_status.items():
            command_to_write = "docker-compose -f " + self.docker_file_names[service] + " down -t "+str(self.timeout)
            args = shlex.split(command_to_write)
            flag = self.execute_command(args, service, "down", False)
            time.sleep(10)
            redisDB = RedisDB()
            while service == "ofw" and redisDB.get("End ofw") == "True":
                pass
        if self.check_status_thread.isAlive():
            self.check_status_thread.join(4)
        self.logger.debug("Monitor thread stopped")
        sys.exit(0)

    def get_docker_file_names(self):
        docker_file_name = {}
        for key, value in self.config.items("Docker_File"):
            docker_file_name[key] = os.path.join("/usr/src/app/monitor/resources/docker-compose/", value)
        if len(docker_file_name) == 0:
            self.logger.error("Please register a service name = docker-compose-file path in properties file under section Docker_File")
        return docker_file_name

    def start_service(self, service, msg):
        command_to_write="docker-compose -f " + self.docker_file_names[service] + " up -d"
        args = shlex.split(command_to_write)
        flag = self.execute_command(args, service, msg, False)
        self.log_persisted[service] = False
        if not flag:
            self.logger.error("cannot start service " + str(service))
            return False
        else:
            self.logger.info(service + " started")
            return True

    def check_status(self):
        while True:
            start_time = time.time()
            completed_instance_ids = []
            data = self.status.get_data(require_updated=2)
            self.logger.info(data)
            current_time = int(time.time())
            instance_list = self.existing_instances(data)
            ofw_restarted = False
            for instance_id, instance_data in data.items():
                if ofw_restarted and instance_id in instance_list:
                    continue
                last_time = instance_data["last_time"]
                freq = instance_data["freq"]
                if freq == -9:  # instance completed
                    completed_instance_ids.append(instance_id)
                elif freq > 0 and current_time - last_time > self.allowed_delay_count * freq:
                    self.logger.info("Instance " + str(instance_id) + " has stopped working. Restarting the service")
                    serice, flag = self.restart_service(instance_id)
                    if serice == "ofw":
                        ofw_restarted = flag
                    else:
                        completed_instance_ids.append(instance_id)
            self.status.remove_entries(completed_instance_ids)
            if ofw_restarted:
                self.status.set_to_current_time(instance_list)
            sleep_time = self.check_frequency - (time.time() - start_time)
            if sleep_time > 0:
                for i in range(int(sleep_time)):
                    time.sleep(1)

    def existing_instances(self, data):
        instance_list = []
        for key in data.keys():
            if self.get_service_name(key) == "ofw":
                instance_list.append(key)
        return instance_list

    def restart_service(self, instance_id):
        service = self.get_service_name(instance_id)
        flag = False
        if service in self.docker_file_names.keys():
            self.save_log(service)
            command_to_write = "docker-compose -f " + self.docker_file_names[service] + " down -t "+str(self.timeout)
            args = shlex.split(command_to_write)
            flag = self.execute_command(args, service, "stopped", False)
            if not self.service_status[service]:
                time.sleep(self.timeout + 5)
                self.start_service(service, "restarted")
        if not flag:
            self.logger.error("cannot stop/restart service " + str(service))
        return service, flag

    def save_log(self, service):
        try:
            if self.service_status[service] and not self.log_persisted[service]:
                log_path = os.path.join("/usr/src/app/monitor/resources/",
                                        "log_" + str(service) + "_" + str(int(time.time())) + ".log")
                command_to_write = "docker logs " + str(service)
                self.logger.debug("Command: " + str(command_to_write))
                self.execute_command_output(command_to_write, log_path)
                self.log_persisted[service] = True
                time.sleep(30)
        except Exception as e:
            self.logger.error("Problems while storing logs. " + str(e))

    def execute_command_output(self, command, filename):
        try:
            p = subprocess.Popen(shlex.split(command), shell=False, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
            out, err = p.communicate()
            with open(filename, 'w+') as f:
                f.write(out.decode('utf-8'))
            self.logger.debug("Logs stored on the memory")
        except Exception as e:
            self.logger.error("Error while writing the file. "+str(e))

    def execute_command(self, command, service_name, msg, log_output):
        try:
            self.logger.debug("command "+str(command))
            process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
            out, err = process.communicate()
            pid = process.pid
            self.logger.info(service_name + " " + msg + " , pid = " + str(pid))
            self.logger.debug("Output: "+str(out.decode('utf-8')))
            self.logger.debug("Error: " + str(err))
            if log_output:
                self.logger.debug("Logging thread started")
            return True
        except Exception as e:
            self.logger.error("error running the command " + str(command) + " " + str(e))
            return False

    def get_service_name(self, instance_id):
        if instance_id == "connector":
            return "connector"
        else:
            return "ofw"
