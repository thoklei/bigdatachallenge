import sys
import numpy as np 
import tensorflow as tf 
from preprocessing import *

def model_fn(features, labels, mode, params):

    config = params['config']

    inp = tf.unstack(tf.cast(features,tf.float32), axis=1)

    cell = tf.contrib.rnn.BasicLSTMCell(config.layer_dim, dtype=tf.float32)
    outputs, _ = tf.nn.static_rnn(cell, inp, dtype=tf.float32)
    middle_layer = tf.layers.dense(outputs[-1], config.middle_size, activation=tf.nn.tanh)
    logits = tf.layers.dense(middle_layer, config.output_dim, activation=None)

    # Compute predictions.
    predicted_classes = tf.argmax(logits, 1)
    if mode == tf.estimator.ModeKeys.PREDICT:
        predictions = {
            'class_ids': predicted_classes[:, tf.newaxis],
            'probabilities': tf.nn.softmax(logits),
            'logits': logits,
        }
        return tf.estimator.EstimatorSpec(mode, predictions=predictions)
        
    # Compute loss.
    loss = tf.losses.sparse_softmax_cross_entropy(labels=labels, logits=logits)

    # Compute evaluation metrics.
    accuracy = tf.metrics.accuracy(labels=labels,
                                   predictions=predicted_classes,
                                   name='acc_op')
    metrics = {'accuracy': accuracy}
    tf.summary.scalar('accuracy', accuracy[1])
    summary_op = tf.summary.merge_all()

    if mode == tf.estimator.ModeKeys.EVAL:
        return tf.estimator.EstimatorSpec(
            mode, loss=loss, eval_metric_ops=metrics)

    # Create training op.
    assert mode == tf.estimator.ModeKeys.TRAIN

    optimizer = config.optimizer
    
    train_op = optimizer.minimize(loss, global_step=tf.train.get_global_step())
    
    return tf.estimator.EstimatorSpec(mode, loss=loss, train_op=train_op)

def input_fn(x, y, config):
    return tf.estimator.inputs.numpy_input_fn(
        x=x,#{"x": x},
        y=y,
        num_epochs=1,
        batch_size=config.batchsize,
        shuffle=True
)

def main(data_path, save_path):

    class Config(object):

        def __init__(self):
            self.optimizer = tf.train.AdamOptimizer()
            self.layer_dim = 80
            self.output_dim = 22
            self.num_epochs = 10
            self.middle_size = 50
            self.batchsize = 32

    config = Config()

    print("Generating Data")
    (x_train, y_train), (x_test, y_test) = create_median_filtered_dataset(data_path+"train.csv", 100)

    classifier = tf.estimator.Estimator(
        model_fn=model_fn,
        model_dir=save_path,
        params={
            'config': config
        })

    for epoch in range(config.num_epochs):

        # Train the Model.
        classifier.train(
            input_fn=input_fn(x_train, y_train, config)) #500*128 = 64000 = number of training samples

        #Evaluate the model.
        eval_result = classifier.evaluate(
            input_fn=input_fn(x_test, y_test, config),
            name="validation")

        print('\nValidation set accuracy after epoch {}: {accuracy:0.3f}\n'.format(epoch+1,**eval_result))

if __name__ == "__main__":
    main(data_path="/Users/thomasklein/Projects/BremenBigDataChallenge2019/bbdc_2019_Bewegungsdaten/",
         save_path="/Users/thomasklein/Projects/BremenBigDataChallenge2019/networks/bigger_LSTM/")