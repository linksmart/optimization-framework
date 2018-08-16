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
        if isinstance(self.port, list):
            self.url = []
            for p in self.port:
                self.url.append('tcp://{}:{}'.format(self.host, p))
        else:
            self.url = 'tcp://{}:{}'.format(self.host, self.port)
        logger.info("Initialize ZMQClient")

    def init_publisher(self):
        try:
            logger.info("Initialize zmq publisher")
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind(self.url)
            time.sleep(1)
            logger.info("publisher initialized")
        except Exception as e:
            logger.error(e)

    def stop(self):
        self.publisher.unbind(self.url)

    def init_subscriber(self, topic):
        try:
            logger.info("Initialize zmq subscriber")
            self.subscriber = self.context.socket(zmq.SUB)
            if isinstance(self.url, list):
                for url in self.url:
                    self.subscriber.connect(url)
            else:
                self.subscriber.connect(self.url)
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)
            logger.info("subscriber initialized")
        except Exception as e:
            logger.error(e)

    def init_subscriber_byte(self, topic):
        try:
            logger.info("Initialize zmq subscriber byte")
            self.subscriber = self.context.socket(zmq.SUB)
            if isinstance(self.url, list):
                for url in self.url:
                    self.subscriber.connect(url)
            else:
                self.subscriber.connect(self.url)
            self.subscriber.setsockopt(zmq.SUBSCRIBE, topic)
            logger.info("subscriber initialized")
        except Exception as e:
            logger.error(e)

    def publish_message(self, topic, message):
        try:
            self.publisher.send_string("%s %s" % (topic, message))
        except Exception as e:
            logger.error(e)

    def receive_message(self):
        try:
            logger.debug("try receiving msg")
            messagedata = self.subscriber.recv_string()
            topic, message = messagedata.split(" ",1)
            logger.debug(topic + " " + message)
            return True, topic, message
        except zmq.Again as e:
            logger.debug("No messages received yet. Error = "+str(e))
            return False, None, None
        except Exception as e:
            logger.error(e)
            return False, None, None

    def recreq_server(self, callback_function):
        self.recreq = self.context.socket(zmq.REP)
        self.recreq.bind(self.url)

        while True:
            #  Wait for next request from client
            message = self.recreq.recv()
            logger.info("Received request: %s" % message)

            result = callback_function()
            #  Do some 'work'
            time.sleep(1)

            #  Send reply back to client
            self.recreq.send(bytes(result))