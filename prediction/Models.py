"""
Created on Sep 19 16:19 2018

@author: nishit
"""

import os

import sys

import time

from stopit import threading_timeoutable as timeoutable  # doctest: +SKIP

"""
os.environ['PYTHONHASHSEED'] = '0'
np.random.seed(42)
rn.seed(12345)

tf.set_random_seed(1234)
"""
from utils_intern.messageLogger import MessageLogger

logger = MessageLogger.get_logger_parent()


class Models:

    def __init__(self, model_weights_path, model_weights_path_temp, model_weights_path_base):
        self.model = None
        self.model_temp = None
        self.model_base = None
        self.graph = None
        self.model_weights_path = model_weights_path
        self.model_weights_path_temp = model_weights_path_temp
        self.model_weights_path_base = model_weights_path_base
        self.last_loaded = None
        self.last_loaded_path = None
        logger.info("paths = " + str(self.model_weights_path))

    def get_model(self, id_topic, predict):
        """
            manages which model to load
            If model_base.h5 present in disk
            then present then use model_base.h5
            else load model_temp.h5 from disk (temp pre-trained model)
        """
        logger.debug("get model for "+str(id_topic))
        model_updated = False
        # get saved model last modified time
        if os.path.exists(self.model_weights_path):
            last_updated = os.path.getmtime(self.model_weights_path)
            if self.last_loaded is not None and last_updated > self.last_loaded:
                model_updated = True

        self.model, self.graph, loaded = self.check_and_get_model(self.model, self.graph, self.model_weights_path,
                                                                  predict, force_load=model_updated)
        if loaded:
            return self.model, self.graph

        self.model_temp, self.graph, loaded = self.check_and_get_model(self.model_temp, self.graph,
                                                                       self.model_weights_path_temp, predict)
        if loaded:
            return self.model_temp, self.graph

        logger.debug("try pre trained model for "+str(id_topic)+" "+str(self.model_base is None))
        self.model_base, self.graph, loaded = self.check_and_get_model(self.model_base, self.graph,
                                                                       self.model_weights_path_base, predict)
        if loaded:
            return self.model_base, self.graph
        return None, None

    def check_and_get_model(self, model, graph, model_weights_path, predict, force_load=False):
        if model is not None and graph is not None and not force_load:
            return model, graph, True
        else:
            """Load model"""
            model, graph = self.load_saved_model(model_weights_path, predict, load_timeout=60)
            if model is not None:
                return model, graph, True
            else:
                return model, graph, False

    @timeoutable((None, None), timeout_param='load_timeout')
    def load_saved_model(self, path, predict):
        try:
            model, graph = None, None
            logger.debug("trying to load model from path " + str(path))
            if os.path.exists(path):
                # os.environ['THEANO_FLAGS'] = 'device=cpu,openmp=True'
                # os.environ['OMP_NUM_THREAD'] = '8'
                # os.environ['KERAS_BACKEND'] = 'theano'
                from keras.models import load_model
                from keras import backend as K
                import tensorflow as tf
                logger.info("Loading model from disk from path = " + str(path))
                K.clear_session()
                session_conf = tf.compat.v1.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=2)
                sess = tf.compat.v1.Session(graph=tf.compat.v1.get_default_graph(), config=session_conf)
                K.set_session(sess)
                model = load_model(path)
                if predict:
                    model._make_predict_function()
                graph = tf.compat.v1.get_default_graph()
                self.last_loaded = time.time()
                self.last_loaded_path = path
                logger.info("Loaded model from disk")
            else:
                logger.info(str(path) + " file does not exist")
            return model, graph
        except Exception as e:
            logger.error("Exception loading model " + str(e))
            return None, None

    def remove_saved_model(self):
        if self.last_loaded_path != self.model_weights_path_base:
            if os.path.exists(self.last_loaded_path):
                os.remove(self.last_loaded_path)
                self.model = None
                self.graph = None
                self.model_temp = None
                self.last_loaded = None
                self.last_loaded_path = None
                logger.info("deleted model " + str(self.last_loaded_path) + " due to exception")
