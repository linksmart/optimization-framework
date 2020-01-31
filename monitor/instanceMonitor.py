"""
Created on Jan 28 13:24 2020

@author: nishit
"""
import json
import threading
import time
import subprocess
import os

from monitor.status import Status
from utils_intern.messageLogger import MessageLogger


class InstanceMonitor:

    def __init__(self, config):
        self.logger = MessageLogger.get_logger(__name__, None)
        self.config = config
        self.topic_params = json.loads(config.get("IO", "monitor.mqtt.topic"))
        self.check_frequency = config.getint("IO", "monitor.frequency.sec", fallback=60)
        self.allowed_delay_count = config.getfloat("IO", "allowed.delay.count", fallback=2)
        docker_typ = config.get("IO", "docker.typ")
        self.docker_file_names = self.get_docker_file_names()
        self.status = Status(False, self.topic_params, config)
        if docker_typ == "ofw":
            self.start_profev(docker_typ)
        elif docker_typ == "connector":
            self.start_connector(docker_typ)
        self.check_status_thread = threading.Thread(target=self.check_status)
        self.check_status_thread.start()

    def get_docker_file_names(self):
        docker_file_name = {}
        for key, value in self.config.items("Docker_File"):
            docker_file_name[key] = os.path.join("/usr/src/app/monitor/resources/docker-compose/", value)
        return docker_file_name

    def start_profev(self, docker_typ):
        flag = self.execute_command("docker-compose -f " + self.docker_file_names[docker_typ] + " up -d",
                                    docker_typ, "running", False)

        if not flag:
            self.logger.error(
                "cannot start service " + str(docker_typ) + " because no docker-compose file name in config")
        else:
            self.logger.info("OFW started")

    def start_connector(self, docker_typ):
        flag = self.execute_command("docker-compose -f " + self.docker_file_names[docker_typ] + " up -d",
                                    docker_typ, "running", False)

        if not flag:
            self.logger.error(
                "cannot start service " + str(docker_typ) + " because no docker-compose file name in config")
        else:
            self.logger.info("Connector started")

    def check_status(self):
        while True:
            start_time = time.time()
            completed_instance_ids = []
            data = self.status.get_data(require_updated=2)
            self.logger.info(data)
            current_time = int(time.time())
            for instance_id, instance_data in data.items():
                last_time = instance_data["last_time"]
                freq = instance_data["freq"]
                if freq == -9:  # instance completed
                    completed_instance_ids.append(instance_id)
                elif freq > 0 and current_time - last_time > self.allowed_delay_count * freq:
                    self.logger.info("Instance " + str(instance_id) + " has stopped working. Restarting the service")
                    self.restart_service(instance_id)
                    completed_instance_ids.append(instance_id)
            self.status.remove_entries(completed_instance_ids)
            sleep_time = self.check_frequency - (time.time() - start_time)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def restart_service(self, instance_id):
        service_name = self.get_service_name(instance_id)
        flag = False
        if service_name in self.docker_file_names.keys():
            try:
                log_path = os.path.join("/usr/src/app/monitor/resources/", "log_ofw_"+str(int(time.time()))+".log")
                command_to_write = "docker logs " + self.docker_file_names[service_name] + " &> " + str(log_path)
                self.logger.debug("Command: "+str(command_to_write))
                flag = self.execute_command(command_to_write, service_name, "logs", False)
                if flag:
                    self.logger.debug("Logs stored on the memory")
                else:
                    self.logger.error("Logs couldn't be taken")
            except Exception as e:
                self.logger.error("Problems while storing logs. "+str(e))
                
            flag = self.execute_command("docker-compose -f " + self.docker_file_names[service_name] + " down",
                                        service_name, "stopped", False)
            if flag:
                time.sleep(60)
                flag = self.execute_command("docker-compose -f " + self.docker_file_names[service_name] + " up -d",
                                            service_name, "started", False)
        if not flag:
            self.logger.error(
                "cannot stop service " + str(service_name) + " because no docker-compose file name in config")

    def execute_command(self, command, service_name, msg, log_output):
        try:
            process = subprocess.Popen([command, service_name], shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            pid = process.pid
            self.logger.info(service_name + " " + msg + " , pid = " + str(pid))
            if log_output:
                self.logger.debug("Logging thread started")
                #threading.Thread(target=InstanceMonitor.log_subprocess_output, args=(process,)).start()
            return True
        except Exception as e:
            self.logger.error("error running the command " + str(command) + " " + str(e))
            return False

    @staticmethod
    def log_subprocess_output(process):
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            elif len(output.strip()) > 0:
                print("######## " + str(output.strip()))
        # rc = process.poll()
        # return rc

    def get_service_name(self, instance_id):
        if instance_id == "connector":
            return "connector"
        else:
            return "ofw"
