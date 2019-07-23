from math import sqrt

from keras.layers import Dropout

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class TrainModel:

    def __init__(self, callback_stop_request):
        self.callback_stop_request = callback_stop_request

    def train(self, Xtrain, Ytrain, num_epochs, batch_size, hidden_size, num_timesteps, output_size, model_weights_path):
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
        from keras import backend as K
        import tensorflow as tf
        K.clear_session()

        session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=2)
        sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
        K.set_session(sess)

        model = Sequential()
        model.add(LSTM(hidden_size, stateful=True,
                       batch_input_shape=(batch_size, num_timesteps, 1),
                       return_sequences=True))
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

    def train_and_evaluate(self, Xtrain, Ytrain, num_epochs, batch_size, hidden_size, num_timesteps, output_size, model_weights_path,
                            Xtest, Ytest):
        """
                Creates a new model, compiles it and then trains it
                """
        import os
        # os.environ['THEANO_FLAGS'] = 'device=cpu,openmp=True'
        # os.environ['OMP_NUM_THREAD'] = '8'
        # os.environ['KERAS_BACKEND'] = 'theano'
        from keras.callbacks import EarlyStopping
        from keras.callbacks import ReduceLROnPlateau
        from keras.callbacks import ModelCheckpoint
        import keras as k
        from keras.models import Sequential
        from keras.layers import Dense
        from keras.layers import LSTM
        from keras import backend as K
        import tensorflow as tf
        K.clear_session()

        session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=2)
        sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
        K.set_session(sess)

        model = Sequential()
        model.add(LSTM(hidden_size, stateful=True,
                       batch_input_shape=(batch_size, num_timesteps, 1),
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

        # Saving the model with checkpoint callback
        checkpoint = ModelCheckpoint(model_weights_path, monitor='loss', verbose=1, save_best_only=True, mode='min')
        callbacks_list = [reduce_lr, earlystop, checkpoint]

        # Training a stateful LSTM
        for i in range(num_epochs):
            if self.callback_stop_request():
                break
            logger.info("Epoch " + str(i + 1) + "/" + str(num_epochs))
            logger.info("training size = " + str(len(Xtrain)))
            model.fit(Xtrain, Ytrain, batch_size=batch_size, epochs=1, verbose=1, callbacks=callbacks_list,
                      shuffle=False)
            logger.info("fit")
            model.reset_states()
        logger.info("Training completed, now evaluating")
        score, _ = model.evaluate(Xtest, Ytest, batch_size=batch_size, verbose=1)
        rmse = sqrt(score)
        logger.info("\nMSE: {:.3f}, RMSE: {:.3f}".format(score, rmse))
        K.clear_session()
        return model