from __future__ import unicode_literals

import logging
# import multiprocessing
import psutil
import gunicorn.app.base

from gunicorn.six import iteritems

from swagger_server.__main__ import create_app as web

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

def number_of_workers():
    cpu = psutil.cpu_count(logical=False)
    if cpu is None:
        cpu = psutil.cpu_count()
    return (cpu * 2) + 1
    # return multiprocessing.cpu_count()


class StandaloneApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def main():
    options = {
        'bind': '%s:%s' % ('0.0.0.0', '8080'),
        'workers': int(number_of_workers()),
        'timeout': 300,
        #'loglevel': 'debug',
    }
    StandaloneApplication(web(), options).run()
    logger.debug("Number of cores: " + str(number_of_workers()))


if __name__ == '__main__':
    main()
