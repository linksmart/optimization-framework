"""
Created on Okt 19 12:05 2018

@author: nishit
"""
import logging
from abc import abstractmethod
from queue import Queue

from IO.dataPublisher import DataPublisher
from IO.dataReceiver import DataReceiver

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class RecPub:

    def Stop(self):
        self.rec.exit()
        self.pub.exit()

    @abstractmethod
    def data_formater(self, data):
        pass

    def __init__(self, receiver_params, publisher_params, config, section):
        self.q = Queue(maxsize=0)
        self.pub = Publisher(False, publisher_params, config, self.q, 0.1)
        self.pub.start()
        self.rec = Receiver(False, receiver_params, config, self.q, self.data_formater, section)

class Receiver(DataReceiver):

    def __init__(self, internal, topic_params, config, q, data_formater, section):
        super().__init__(internal, topic_params, config, section=section)
        self.q = q
        self.data_formater = data_formater

    def on_msg_received(self, payload):
        try:
            logger.info("msg rec : "+str(payload))
            data = self.data_formater(payload)
            for topic, value in data.items():
                self.q.put({"topic": topic, "data": value})
        except Exception as e:
            logger.error(e)

class Publisher(DataPublisher):

    def __init__(self, internal, topic_params, config, q, publish_frequency):
        super().__init__(internal, topic_params, config, publish_frequency)
        self.q = q

    def get_data(self):
        if not self.q.empty():
            try:
                new_data = self.q.get_nowait()
                self.q.task_done()
                logger.debug("Queue size: "+str(self.q.qsize()))
                topic = new_data["topic"]
                data = new_data["data"]
                return data, topic
            except Exception:
                logger.debug("Queue empty")
        return None, None

    def exit(self):
        self.Stop()