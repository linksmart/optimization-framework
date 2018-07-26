"""
 Created by Gustavo Aragón on 14.03.2018

"""

import  os, logging
import subprocess # just to call an arbitrary command e.g. 'ls'
import time

#import swagger_server.__main__ as webserver
import swagger_server.wsgi as webserver

from optparse import OptionParser

import sh as sh

from optimization.controller import OptController


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

"""
Get the address of the data.dat
"""




def startOfw(options):
    # code to start a daemon
    init=0

def parseArgs():
    mandatoryArgs=0


def main():
    global OPTIONS

    logger.info("Optiframework started")

    logger.info("Starting webserver")
    webserver.main()


    #while True:

       #results=opt.start()
       #print(results)
       #time.sleep(5)


if __name__ == "__main__":
        # execute only if run as a script
        main()