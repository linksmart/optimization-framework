import logging

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s : %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class Threadfactory:
    """
    Manages Threads for OptController
    """

    def __init__(self):
        self.stack = ""

    def create_thread(self, name):
        """
        Creates a new Thread and put it on the internal stack
        :param name: String
        :return: void
        """
        logger.info("Create thread" + name)
        self.stack = ""

