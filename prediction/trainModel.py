from math import sqrt

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class TrainModel:

    def __init__(self, callback_stop_request):
        self.callback_stop_request = callback_stop_request

    def train_load(self, Xtrain, Ytrain, num_epochs, batch_size, hidden_size, input_size, output_size, model_weights_path, model):
        """
        Creates a new model, compiles it and then trains it
        """
        import os
        #os.environ['THEANO_FLAGS'] = 'device=cpu,openmp=True'
        #os.environ['OMP_NUM_THREAD'] = '8'
        #os.environ['KERAS_BACKEND'] = 'theano'
        from keras.callbacks import EarlyStopping
        from keras.callbacks import ReduceLROnPlateau
        from keras.callbacks import ModelCheckpoint
        import keras as k
        from keras.models import Sequential
        from keras.layers import Dense
        from keras.layers import LSTM
        from keras.layers import Dropout
        from keras import backend as K
        import tensorflow as tf

        if model is None:
            K.clear_session()
            session_conf = tf.compat.v1.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=2)

            sess = tf.compat.v1.Session(graph=tf.compat.v1.get_default_graph(), config=session_conf)
            K.set_session(sess)
            model = Sequential()
            model.add(LSTM(hidden_size, stateful=True,
                           batch_input_shape=(batch_size, input_size, 1),
                           return_sequences=True))
            model.add(Dropout(0.3))
            model.add(LSTM(hidden_size, stateful=True))
            model.add(Dense(output_size))
            adam = k.optimizers.Adam(lr=0.01)
            model.compile(loss="mean_squared_error", optimizer=adam,
                          metrics=["mean_squared_error"])

        logger.info(model.summary())
        # define reduceLROnPlateau and early stopping callback
        reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.2,
                                      patience=3, min_lr=0.001)
        earlystop = EarlyStopping(monitor='loss', min_delta=0.0001, patience=3, verbose=1, mode='auto')

        #Saving the model with checkpoint callback
        checkpoint = ModelCheckpoint(model_weights_path, monitor='loss', verbose=1, save_best_only=True, mode='min')
        callbacks_list = [reduce_lr, earlystop, checkpoint]

        # Training a stateful LSTM
        for i in range(num_epochs):
            if self.callback_stop_request():
                break
            logger.info("Epoch " + str(i + 1) + "/" + str(num_epochs))
            logger.info("training size = "+str(len(Xtrain)))
            model.fit(Xtrain, Ytrain, batch_size=batch_size, epochs=1, verbose=2, callbacks=callbacks_list,
                      shuffle=False)
            logger.info("fit")
            model.reset_states()
        logger.info("Training completed")
        K.clear_session()
        return model

    def train_pv(self, Xtrain, Ytrain, num_epochs, batch_size, hidden_size, input_size_real, input_size_hist,
                 output_size, model_weights_path, model):
        """
        Creates a new model, compiles it and then trains it
        """
        import os
        #os.environ['THEANO_FLAGS'] = 'device=cpu,openmp=True'
        #os.environ['OMP_NUM_THREAD'] = '8'
        #os.environ['KERAS_BACKEND'] = 'theano'
        from keras.callbacks import EarlyStopping
        from keras.callbacks import ReduceLROnPlateau
        from keras.callbacks import ModelCheckpoint
        import keras as k
        from keras import Input
        from keras.models import Sequential, Model
        from keras.layers import concatenate
        from keras.layers import Dense
        from keras.layers import LSTM
        from keras.layers import Dropout
        from keras.layers import Concatenate
        from keras import backend as K
        import tensorflow as tf

        if model is None:
            K.clear_session()
            session_conf = tf.compat.v1.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=2)

            sess = tf.compat.v1.Session(graph=tf.compat.v1.get_default_graph(), config=session_conf)
            K.set_session(sess)
            real_input = Input(batch_shape=(batch_size, input_size_real, 1), name="real")
            real_features = LSTM(hidden_size, stateful=True, return_sequences=True)(real_input)

            hist_input = Input(batch_shape=(batch_size, input_size_hist, 1), name="hist")
            hist_features = LSTM(hidden_size, stateful=True, return_sequences=True)(hist_input)

            x = concatenate([real_features, hist_features], axis=1)
            x = Dropout(0.3)(x)
            x = LSTM(hidden_size, stateful=True)(x)
            output_layer = Dense(output_size)(x)

            model = Model(inputs=[real_input, hist_input], outputs=output_layer)

            adam = k.optimizers.Adam(lr=0.01)
            model.compile(loss="mean_squared_error", optimizer=adam,
                          metrics=["mean_squared_error"])

        logger.info(model.summary())
        # define reduceLROnPlateau and early stopping callback
        reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.2,
                                      patience=3, min_lr=0.001)
        earlystop = EarlyStopping(monitor='loss', min_delta=0.0001, patience=3, verbose=1, mode='auto')

        #Saving the model with checkpoint callback
        checkpoint = ModelCheckpoint(model_weights_path, monitor='loss', verbose=1, save_best_only=True, mode='min')
        callbacks_list = [reduce_lr, earlystop, checkpoint]

        # Training a stateful LSTM
        for i in range(num_epochs):
            if self.callback_stop_request():
                break
            logger.info("Epoch " + str(i + 1) + "/" + str(num_epochs))
            logger.info("training size = "+str(len(Xtrain["real"])))
            model.fit(Xtrain, Ytrain, batch_size=batch_size, epochs=1, verbose=2, callbacks=callbacks_list,
                      shuffle=False)
            logger.info("fit")
            model.reset_states()
        logger.info("Training completed")
        K.clear_session()
        return model