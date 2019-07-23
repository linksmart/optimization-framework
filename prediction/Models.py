"""
Created on Sep 19 16:19 2018

@author: nishit
"""

import os

import sys

import time

"""
os.environ['PYTHONHASHSEED'] = '0'
np.random.seed(42)
rn.seed(12345)

tf.set_random_seed(1234)
"""
from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class Models:

    def __init__(self, num_timesteps, hidden_size, batch_size, save_path, save_path_temp):
        self.num_timesteps = num_timesteps
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.model = None
        self.model_temp = None
        self.graph = None
        self.model_weights_path = save_path
        self.model_weights_path_temp = save_path_temp
        self.last_loaded = None
        logger.info("paths = " + str(self.model_weights_path))

    def get_model(self, id_topic):
        """
        manages which model to load
        If model.h5 present in disk
	    then present then use model.h5
	    else load model_temp.h5 from disk (temp pre-trained model)
	    """
        logger.debug("get model method")
        temp = False
        if os.path.exists(self.model_weights_path):
            last_updated = os.path.getmtime(self.model_weights_path)
            logger.debug(self.model_weights_path + " file exists")
        else:
            last_updated = None
            logger.debug(self.model_weights_path + " file does not exist")
        if self.model and (
                self.last_loaded is not None and last_updated is not None and last_updated <= self.last_loaded):
            logger.info(str(id_topic) + "model present in memory ")
            return self.model, self.model_temp, temp, self.graph
        model, graph = self.load_saved_model(self.model_weights_path)
        if model:
            self.model = model
            self.graph = graph
            return model, self.model_temp, temp, graph
        else:
            """try temp model"""
            if self.model_temp:
                logger.info(str(id_topic) + "temp model present in memory")
                temp = True
                return model, self.model_temp, temp, self.graph
            model_temp, graph = self.load_saved_model(self.model_weights_path_temp)
            if model_temp:
                temp = True
                self.model_temp = model_temp
                self.graph = graph
                return self.model, model_temp, temp, graph
            else:
                return self.model, self.model_temp, temp, self.graph

    def load_saved_model(self, path):
        try:
            # os.environ['THEANO_FLAGS'] = 'device=cpu,openmp=True'
            # os.environ['OMP_NUM_THREAD'] = '8'
            # os.environ['KERAS_BACKEND'] = 'theano'
            from keras.models import load_model
            from keras import backend as K
            import tensorflow as tf
            model, graph = None, None
            if os.path.exists(path):
                logger.info("Loading model from disk from path = " + str(path))
                K.clear_session()
                session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=2)
                sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
                K.set_session(sess)
                model = load_model(path)
                model._make_predict_function()
                graph = tf.get_default_graph()
                self.last_loaded = time.time()
                logger.info("Loaded model from disk")
            return model, graph
        except Exception as e:
            logger.error("Exception loading model " + str(e))
            return None, None
