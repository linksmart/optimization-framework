"""
 Created by Gustavo Aragón on 14.03.2018

"""

import  os, logging
import subprocess # just to call an arbitrary command e.g. 'ls'
import time
import configparser
import optimization.models as models

from optparse import OptionParser

import sh as sh

from optimization.controller import OptController


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

"""
Get the address of the data.dat
"""

def getFilePath(file_name):
    project_dir = os.path.dirname(os.path.realpath(__file__))
    #print("project dir: "+project_dir)
    data_file = project_dir+file_name
    #print("data_file: "+data_file)
    return data_file


def startOfw(options):
    # code to start a daemon
    init=0

def parseArgs():
    mandatoryArgs=0


def main():
    global OPTIONS

    logger.info("Optiframework started")


    # Creating an object of the configuration file
    config = configparser.RawConfigParser()
    config.read(getFilePath("/utils/ConfigFile.properties"))

    model_name = config.get("SolverSection", "model.name")

    # Taking the data file name from the configuration file
    data_file_name = config.get("SolverSection", "data.file")
    data_path = getFilePath(data_file_name)

    # Taking
    solver_name = config.get("SolverSection", "solver.name")
    print("Problem solved with: " + solver_name)

    opt=OptController("obj1",solver_name,data_path,model_name)

    while True:

        results=opt.start()
        print(results)
        time.sleep(5)


if __name__ == "__main__":
        # execute only if run as a script
        main()