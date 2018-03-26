"""
 Created by Gustavo Aragón on 14.03.2018

"""

import sys, os, logging
import subprocess # just to call an arbitrary command e.g. 'ls'


from optparse import OptionParser

import sh as sh

import optimization.controller as opt
#import optimization.controller as optObject
#from myAgent import main as tavo

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class frameworkAdapter(object):
    def __init__(self):
        logger.info("Initializing OptiFramework object.")

    def parseArgs(self):
        mandatoryArgs = ['bname', 'bpath']
        parser = OptionParser()
        parser.add_option("--bname", help="name of backend module")
        parser.add_option("--bpath", help="path to backend module (python script)")
        parser.add_option("--host", default="localhost", help="hostname to bind server on")
        parser.add_option("--port", type="int", default=0, help="port to bind server on (0=random)")
        parser.add_option("--nathost", help="the external host name to use in case of NAT")
        parser.add_option("--natport", type="int", help="the external port use in case of NAT")
        parser.add_option("--ns", dest="nameserver", action="store_true", default=False,
                          help="register the server into pyro nameserver")
        parser.add_option("--rname", default="python-agent-0", help="name used for registration into pyro nameserver")
        options, args = parser.parse_args()
        # check mangatory args
        for opt in mandatoryArgs:
            if not getattr(options, opt):
                logger.error("Argument `{}` not given.".format(opt))
                parser.print_help()
                sys.exit(2)

        return options

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


def main():
    global OPTIONS
    print("PATH")
    for p in sys.path:
        print(p)
    print("Optiframework")
    print(sh.which("glpsol"))
    print(sh.which("ipopt"))
    print(sh.which("bonmin"))
    with cd("/usr/src/app"):
        # we are in ~/Library
        subprocess.call("ls")

    #kandw=optObject.Controller('prueba1')
    #results = kandw.startOpt()
    #print(results)
    opt.start()
    #tavo.main()
    sys.exit(0)

if __name__ == "__main__":
        # execute only if run as a script
        main()