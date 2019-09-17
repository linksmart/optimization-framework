"""
Created on Sep 13 11:18 2019

@author: nishit
"""
import signal
import threading

import os
import psutil
import time

import subprocess

from optimization.idStatusManager import IDStatusManager
from utils_intern.constants import Constants
from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class PyroServerManagement:
    
    @staticmethod
    def start_name_servers(redisDB):
        logger.debug("Starting name_server and dispatch_server")
        while True:
            pid = redisDB.get(Constants.name_server_key)
            if pid is None:
                PyroServerManagement.subprocess_server_start(redisDB, Constants.name_server_command, "name server", Constants.name_server_key, True)
            elif not psutil.pid_exists(int(pid)):
                logger.debug("Restarting name_server")
                PyroServerManagement.subprocess_server_start(redisDB, Constants.name_server_command, "name server", None, True)
            pid = redisDB.get(Constants.dispatch_server_key)
            if pid is None:
                PyroServerManagement.subprocess_server_start(redisDB, Constants.dispatch_server_command, "dispatch server", Constants.dispatch_server_key, True)
            elif not psutil.pid_exists(int(pid)):
                logger.debug("Restarting dispatch_server")
                PyroServerManagement.subprocess_server_start(redisDB, Constants.dispatch_server_command, "dispatch server", None, True)
            time.sleep(60)

    @staticmethod
    def subprocess_server_start(redisDB, command, server_name, redis_key=None, log_output=False):
        pid = redisDB.get(redis_key)
        if pid is None:
            try:
                logger.debug("Trying to start " + server_name)
                process = subprocess.Popen([command], preexec_fn=os.setsid, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                pid = process.pid
                logger.debug(server_name + "  started, pid = " + str(pid))
                if redis_key is not None:
                    redisDB.set(redis_key, pid)
                if log_output:
                    threading.Thread(target=PyroServerManagement.log_subprocess_output, args=(process,)).start()
            except Exception as e:
                logger.error(server_name + " already exists error")
        return pid

    @staticmethod
    def log_subprocess_output(process):
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            elif len(output.strip()) > 0:
                logger.debug("######## "+str(output.strip()))
        #rc = process.poll()
        #return rc

    @staticmethod
    def stop_name_servers(redisDB):
        if IDStatusManager.number_of_active_ids_redis(redisDB) == 0:
            pid = redisDB.get(Constants.name_server_key)
            PyroServerManagement.os_proc_stop(redisDB, pid, "name server", Constants.name_server_key)
            pid = redisDB.get(Constants.dispatch_server_key)
            PyroServerManagement.os_proc_stop(redisDB, pid, "dispatch server", Constants.dispatch_server_key)

    @staticmethod
    def os_proc_stop(redisDB, pid, server_name, redis_key=None):
        if pid is not None:
            try:
                os.killpg(os.getpgid(int(pid)), signal.SIGTERM)
                logger.debug(server_name + " stoped : " + str(pid))
                if redis_key is not None:
                    redisDB.remove(redis_key)
            except Exception as e:
                logger.error(server_name + " kill error " + str(e))

    @staticmethod
    def stop_pyro_servers(redisDB):
        logger.info("stop pyro server init")
        num_of_active_ids = IDStatusManager.number_of_active_ids_redis(redisDB)
        logger.debug("active ids = " + str(num_of_active_ids))
        count = 0
        if num_of_active_ids == 0:
            redisDB.set(Constants.pyro_mip, 0)
            keys = redisDB.get_keys_for_pattern(Constants.pyro_mip_pid + ":*")
            if keys is not None:
                for key in keys:
                    pid = int(redisDB.get(key))
                    PyroServerManagement.os_proc_stop(redisDB, pid, "mip server " + str(pid), key)
                    count += 1
                active_pyro_servers = int(redisDB.get(Constants.pyro_mip, 0))
                active_pyro_servers -= count
                if active_pyro_servers < 0:
                    active_pyro_servers = 0
                redisDB.set(Constants.pyro_mip, active_pyro_servers)
            else:
                logger.info("keys is none")
    
    @staticmethod
    def start_pryo_mip_servers(redisDB, base_num_of_servers):
        active_pyro_servers = PyroServerManagement.active_pyro_mip_servers(redisDB)
        for i in range(base_num_of_servers - active_pyro_servers):
            PyroServerManagement.start_pyro_mip_server(active_pyro_servers, i, redisDB)
        while True:
            active_pyro_servers = PyroServerManagement.active_pyro_mip_servers(redisDB)
            required = IDStatusManager.num_of_required_pyro_mip_servers_redis(redisDB)
            number_of_servers_to_start = 0
            if active_pyro_servers < required:
                number_of_servers_to_start = required - active_pyro_servers
            if number_of_servers_to_start + active_pyro_servers < base_num_of_servers:
                number_of_servers_to_start += base_num_of_servers - (active_pyro_servers+number_of_servers_to_start)
            for i in range(number_of_servers_to_start):
                PyroServerManagement.start_pyro_mip_server(active_pyro_servers, i, redisDB)
            time.sleep(60)
    
    @staticmethod
    def active_pyro_mip_servers(redisDB):
        active_pyro_servers = int(redisDB.get(Constants.pyro_mip, 0))
        keys = redisDB.get_keys_for_pattern(Constants.pyro_mip_pid + ":*")
        crashed = 0
        if keys is not None:
            for key in keys:
                pid = int(redisDB.get(key))
                if not psutil.pid_exists(int(pid)):
                    crashed += 1
                    redisDB.remove(key)
                    logger.debug("pyro mip server crashed "+str(key))
        active = active_pyro_servers - crashed
        if active < 0:
            active = 0
        redisDB.set(Constants.pyro_mip, active)
        return active

    @staticmethod
    def start_pyro_mip_server(active_pyro_servers, i, redisDB):
        pyro_mip_server_pid = PyroServerManagement.subprocess_server_start(redisDB, Constants.pyro_mip_server_command,
                                                                           "mip server", log_output=True)
        redisDB.set(Constants.pyro_mip, active_pyro_servers + i + 1)
        redisDB.set(Constants.pyro_mip_pid + ":" + str(pyro_mip_server_pid), pyro_mip_server_pid)
        logger.info("started pyro mip server " + str(pyro_mip_server_pid))