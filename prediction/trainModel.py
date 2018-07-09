import logging
from keras.callbacks import EarlyStopping
from keras.callbacks import ReduceLROnPlateau
from keras.callbacks import ModelCheckpoint

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class TrainModel:

    def __init__(self, save_path):
        self.model_weights_path = save_path

    def train(self, model, Xtrain, Ytrain, num_epochs, batch_size):
        # define reduceLROnPlateau and early stopping callback
        reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.2,
                                      patience=3, min_lr=0.001)
        earlystop = EarlyStopping(monitor='loss', min_delta=0, patience=4, verbose=1, mode='auto')

        #Saving the model with checkpoint callback
        checkpoint = ModelCheckpoint(self.model_weights_path, monitor='loss', verbose=1, save_best_only=True, mode='min')
        callbacks_list = [reduce_lr, earlystop, checkpoint]

        # Training a stateful LSTM
        for i in range(num_epochs):
            print("Epoch {:d}/{:d}".format(i + 1, num_epochs))
            model.fit(Xtrain, Ytrain, batch_size=batch_size, epochs=1, verbose=1, callbacks=callbacks_list,
                      shuffle=False)
            model.reset_states()
        return model
