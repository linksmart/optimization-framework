"""
Created on Jun 11 12:57 2018

@author: nishit
"""
import logging
import zmq
import time

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class ZMQClient:
    def __init__(self, host, zmqPort):
        self.host = host
        self.port = zmqPort
        self.context = zmq.Context()
        self.url = 'tcp://{}:{}'.format(self.host, self.port)

    def init_publisher(self):
        try:
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind(self.url)
            time.sleep(1)
        except Exception as e:
            logger.error(e)

    def stop(self):
        self.publisher.unbind(self.url)

    def init_subscriber(self, topic):
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(self.url)
        filter = bytes(topic, 'ascii')
        self.subscriber.setsockopt(zmq.SUBSCRIBE, filter)

    def publish_message(self, message):
        try:
            self.publisher.send(message)
        except Exception as e:
            logger.error(e)

    def receive_message(self):
        self.subscriber.recv()