# -*- coding: utf-8 -*-

import inspect

import numpy as np
import tensorflow as tf
from six.moves import xrange

from . import cost, files, iterate, ops, utils, visualize
from .core import *


class RNNLayer(Layer):
    """
    The :class:`RNNLayer` class is a RNN layer, you can implement vanilla RNN,
    LSTM and GRU with it.

    Parameters
    ----------
    layer : a :class:`Layer` instance
        The `Layer` class feeding into this layer.
    cell_fn : a TensorFlow's core RNN cell as follow (Note TF1.0+ and TF1.0- are different).
        - see `RNN Cells in TensorFlow <https://www.tensorflow.org/api_docs/python/>`_
    cell_init_args : a dictionary
        The arguments for the cell initializer.
    n_hidden : an int
        The number of hidden units in the layer.
    initializer : initializer
        The initializer for initializing the parameters.
    n_steps : an int
        The sequence length.
    initial_state : None or RNN State
        If None, initial_state is zero_state.
    return_last : boolean
        - If True, return the last output, "Sequence input and single output"
        - If False, return all outputs, "Synced sequence input and output"
        - In other word, if you want to apply one or more RNN(s) on this layer, set to False.
    return_seq_2d : boolean
        - When return_last = False
        - If True, return 2D Tensor [n_example, n_hidden], for stacking DenseLayer after it.
        - If False, return 3D Tensor [n_example/n_steps, n_steps, n_hidden], for stacking multiple RNN after it.
    name : a string or None
        An optional name to attach to this layer.

    Attributes
    --------------
    outputs : a tensor
        The output of this RNN.
        return_last = False, outputs = all cell_output, which is the hidden state.
            cell_output.get_shape() = (?, n_hidden)

    final_state : a tensor or StateTuple
        When state_is_tuple = False,
        it is the final hidden and cell states, states.get_shape() = [?, 2 * n_hidden].\n
        When state_is_tuple = True, it stores two elements: (c, h), in that order.
        You can get the final state after each iteration during training, then
        feed it to the initial state of next iteration.

    initial_state : a tensor or StateTuple
        It is the initial state of this RNN layer, you can use it to initialize
        your state at the begining of each epoch or iteration according to your
        training procedure.

    batch_size : int or tensor
        Is int, if able to compute the batch_size, otherwise, tensor for ``?``.

    Examples
    --------
    - For words
    >>> input_data = tf.placeholder(tf.int32, [batch_size, num_steps])
    >>> net = tl.layers.EmbeddingInputlayer(
    ...                 inputs = input_data,
    ...                 vocabulary_size = vocab_size,
    ...                 embedding_size = hidden_size,
    ...                 E_init = tf.random_uniform_initializer(-init_scale, init_scale),
    ...                 name ='embedding_layer')
    >>> net = tl.layers.DropoutLayer(net, keep=keep_prob, is_fix=True, is_train=is_train, name='drop1')
    >>> net = tl.layers.RNNLayer(net,
    ...             cell_fn=tf.contrib.rnn.BasicLSTMCell,
    ...             cell_init_args={'forget_bias': 0.0},# 'state_is_tuple': True},
    ...             n_hidden=hidden_size,
    ...             initializer=tf.random_uniform_initializer(-init_scale, init_scale),
    ...             n_steps=num_steps,
    ...             return_last=False,
    ...             name='basic_lstm_layer1')
    >>> lstm1 = net
    >>> net = tl.layers.DropoutLayer(net, keep=keep_prob, is_fix=True, is_train=is_train, name='drop2')
    >>> net = tl.layers.RNNLayer(net,
    ...             cell_fn=tf.contrib.rnn.BasicLSTMCell,
    ...             cell_init_args={'forget_bias': 0.0}, # 'state_is_tuple': True},
    ...             n_hidden=hidden_size,
    ...             initializer=tf.random_uniform_initializer(-init_scale, init_scale),
    ...             n_steps=num_steps,
    ...             return_last=False,
    ...             return_seq_2d=True,
    ...             name='basic_lstm_layer2')
    >>> lstm2 = net
    >>> net = tl.layers.DropoutLayer(net, keep=keep_prob, is_fix=True, is_train=is_train, name='drop3')
    >>> net = tl.layers.DenseLayer(net,
    ...             n_units=vocab_size,
    ...             W_init=tf.random_uniform_initializer(-init_scale, init_scale),
    ...             b_init=tf.random_uniform_initializer(-init_scale, init_scale),
    ...             act = tl.activation.identity, name='output_layer')

    - For CNN+LSTM
    >>> x = tf.placeholder(tf.float32, shape=[batch_size, image_size, image_size, 1])
    >>> net = tl.layers.InputLayer(x, name='input_layer')
    >>> net = tl.layers.Conv2dLayer(net,
    ...                         act = tf.nn.relu,
    ...                         shape = [5, 5, 1, 32],  # 32 features for each 5x5 patch
    ...                         strides=[1, 2, 2, 1],
    ...                         padding='SAME',
    ...                         name ='cnn_layer1')
    >>> net = tl.layers.PoolLayer(net,
    ...                         ksize=[1, 2, 2, 1],
    ...                         strides=[1, 2, 2, 1],
    ...                         padding='SAME',
    ...                         pool = tf.nn.max_pool,
    ...                         name ='pool_layer1')
    >>> net = tl.layers.Conv2dLayer(net,
    ...                         act = tf.nn.relu,
    ...                         shape = [5, 5, 32, 10], # 10 features for each 5x5 patch
    ...                         strides=[1, 2, 2, 1],
    ...                         padding='SAME',
    ...                         name ='cnn_layer2')
    >>> net = tl.layers.PoolLayer(net,
    ...                         ksize=[1, 2, 2, 1],
    ...                         strides=[1, 2, 2, 1],
    ...                         padding='SAME',
    ...                         pool = tf.nn.max_pool,
    ...                         name ='pool_layer2')
    >>> net = tl.layers.FlattenLayer(net, name='flatten_layer')
    >>> net = tl.layers.ReshapeLayer(net, shape=[-1, num_steps, int(net.outputs._shape[-1])])
    >>> rnn1 = tl.layers.RNNLayer(net,
    ...                         cell_fn=tf.nn.rnn_cell.LSTMCell,
    ...                         cell_init_args={},
    ...                         n_hidden=200,
    ...                         initializer=tf.random_uniform_initializer(-0.1, 0.1),
    ...                         n_steps=num_steps,
    ...                         return_last=False,
    ...                         return_seq_2d=True,
    ...                         name='rnn_layer')
    >>> net = tl.layers.DenseLayer(rnn1, n_units=3,
    ...                         act = tl.activation.identity, name='output_layer')

    Notes
    -----
    Input dimension should be rank 3 : [batch_size, n_steps, n_features], if no, please see :class:`ReshapeLayer`.

    References
    ----------
    - `Neural Network RNN Cells in TensorFlow <https://www.tensorflow.org/api_docs/python/rnn_cell/>`_
    - `tensorflow/python/ops/rnn.py <https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/ops/rnn.py>`_
    - `tensorflow/python/ops/rnn_cell.py <https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/ops/rnn_cell.py>`_
    - see TensorFlow tutorial ``ptb_word_lm.py``, TensorLayer tutorials ``tutorial_ptb_lstm*.py`` and ``tutorial_generate_text.py``
    """

    def __init__(
            self,
            layer=None,
            cell_fn=None,  #tf.nn.rnn_cell.BasicRNNCell,
            cell_init_args={},
            n_hidden=100,
            initializer=tf.random_uniform_initializer(-0.1, 0.1),
            n_steps=5,
            initial_state=None,
            return_last=False,
            # is_reshape = True,
            return_seq_2d=False,
            name='rnn_layer',
    ):
        Layer.__init__(self, name=name)
        if cell_fn is None:
            raise Exception("Please put in cell_fn")
        if 'GRU' in cell_fn.__name__:
            try:
                cell_init_args.pop('state_is_tuple')
            except:
                pass

        self.inputs = layer.outputs

        logging.info("RNNLayer %s: n_hidden:%d n_steps:%d in_dim:%d in_shape:%s cell_fn:%s " % (self.name, n_hidden, n_steps, self.inputs.get_shape().ndims,
                                                                                                self.inputs.get_shape(), cell_fn.__name__))
        # You can get the dimension by .get_shape() or ._shape, and check the
        # dimension by .with_rank() as follow.
        # self.inputs.get_shape().with_rank(2)
        # self.inputs.get_shape().with_rank(3)

        # Input dimension should be rank 3 [batch_size, n_steps(max), n_features]
        try:
            self.inputs.get_shape().with_rank(3)
        except:
            raise Exception("RNN : Input dimension should be rank 3 : [batch_size, n_steps, n_features]")

        # is_reshape : boolean (deprecate)
        #     Reshape the inputs to 3 dimension tensor.\n
        #     If input is［batch_size, n_steps, n_features], we do not need to reshape it.\n
        #     If input is [batch_size * n_steps, n_features], we need to reshape it.
        # if is_reshape:
        #     self.inputs = tf.reshape(self.inputs, shape=[-1, n_steps, int(self.inputs._shape[-1])])

        fixed_batch_size = self.inputs.get_shape().with_rank_at_least(1)[0]

        if fixed_batch_size.value:
            batch_size = fixed_batch_size.value
            logging.info("       RNN batch_size (concurrent processes): %d" % batch_size)
        else:
            from tensorflow.python.ops import array_ops
            batch_size = array_ops.shape(self.inputs)[0]
            logging.info("       non specified batch_size, uses a tensor instead.")
        self.batch_size = batch_size

        # Simplified version of tensorflow.models.rnn.rnn.py's rnn().
        # This builds an unrolled LSTM for tutorial purposes only.
        # In general, use the rnn() or state_saving_rnn() from rnn.py.
        #
        # The alternative version of the code below is:
        #
        # from tensorflow.models.rnn import rnn
        # inputs = [tf.squeeze(input_, [1])
        #           for input_ in tf.split(1, num_steps, inputs)]
        # outputs, state = rnn.rnn(cell, inputs, initial_state=self._initial_state)
        outputs = []
        if 'reuse' in inspect.getargspec(cell_fn.__init__).args:
            self.cell = cell = cell_fn(num_units=n_hidden, reuse=tf.get_variable_scope().reuse, **cell_init_args)
        else:
            self.cell = cell = cell_fn(num_units=n_hidden, **cell_init_args)
        if initial_state is None:
            self.initial_state = cell.zero_state(batch_size, dtype=D_TYPE)  #dtype=tf.float32)  # 1.2.3
        state = self.initial_state
        # with tf.variable_scope("model", reuse=None, initializer=initializer):
        with tf.variable_scope(name, initializer=initializer) as vs:
            for time_step in range(n_steps):
                if time_step > 0: tf.get_variable_scope().reuse_variables()
                (cell_output, state) = cell(self.inputs[:, time_step, :], state)
                outputs.append(cell_output)

            # Retrieve just the RNN variables.
            # rnn_variables = [v for v in tf.all_variables() if v.name.startswith(vs.name)]
            rnn_variables = tf.get_collection(TF_GRAPHKEYS_VARIABLES, scope=vs.name)

        logging.info("     n_params : %d" % (len(rnn_variables)))

        if return_last:
            # 2D Tensor [batch_size, n_hidden]
            self.outputs = outputs[-1]
        else:
            if return_seq_2d:
                # PTB tutorial: stack dense layer after that, or compute the cost from the output
                # 2D Tensor [n_example, n_hidden]
                try:  # TF1.0
                    self.outputs = tf.reshape(tf.concat(outputs, 1), [-1, n_hidden])
                except:  # TF0.12
                    self.outputs = tf.reshape(tf.concat(1, outputs), [-1, n_hidden])

            else:
                # <akara>: stack more RNN layer after that
                # 3D Tensor [n_example/n_steps, n_steps, n_hidden]
                try:  # TF1.0
                    self.outputs = tf.reshape(tf.concat(outputs, 1), [-1, n_steps, n_hidden])
                except:  # TF0.12
                    self.outputs = tf.reshape(tf.concat(1, outputs), [-1, n_steps, n_hidden])

        self.final_state = state

        self.all_layers = list(layer.all_layers)
        self.all_params = list(layer.all_params)
        self.all_drop = dict(layer.all_drop)
        # logging.info(type(self.outputs))
        self.all_layers.extend([self.outputs])
        self.all_params.extend(rnn_variables)


class BiRNNLayer(Layer):
    """
    The :class:`BiRNNLayer` class is a Bidirectional RNN layer.

    Parameters
    ----------
    layer : a :class:`Layer` instance
        The `Layer` class feeding into this layer.
    cell_fn : a TensorFlow's core RNN cell as follow (Note TF1.0+ and TF1.0- are different).
        - see `RNN Cells in TensorFlow <https://www.tensorflow.org/api_docs/python/>`_
    cell_init_args : a dictionary
        The arguments for the cell initializer.
    n_hidden : an int
        The number of hidden units in the layer.
    initializer : initializer
        The initializer for initializing the parameters.
    n_steps : an int
        The sequence length.
    fw_initial_state : None or forward RNN State
        If None, initial_state is zero_state.
    bw_initial_state : None or backward RNN State
        If None, initial_state is zero_state.
    dropout : `tuple` of `float`: (input_keep_prob, output_keep_prob).
        The input and output keep probability.
    n_layer : an int, default is 1.
        The number of RNN layers.
    return_last : boolean
        - If True, return the last output, "Sequence input and single output"
        - If False, return all outputs, "Synced sequence input and output"
        - In other word, if you want to apply one or more RNN(s) on this layer, set to False.
    return_seq_2d : boolean
        - When return_last = False
        - If True, return 2D Tensor [n_example, n_hidden], for stacking DenseLayer after it.
        - If False, return 3D Tensor [n_example/n_steps, n_steps, n_hidden], for stacking multiple RNN after it.
    name : a string or None
        An optional name to attach to this layer.

    Attributes
    --------------
    outputs : a tensor
        The output of this RNN.
        return_last = False, outputs = all cell_output, which is the hidden state.
            cell_output.get_shape() = (?, n_hidden)

    fw(bw)_final_state : a tensor or StateTuple
        When state_is_tuple = False,
        it is the final hidden and cell states, states.get_shape() = [?, 2 * n_hidden].\n
        When state_is_tuple = True, it stores two elements: (c, h), in that order.
        You can get the final state after each iteration during training, then
        feed it to the initial state of next iteration.

    fw(bw)_initial_state : a tensor or StateTuple
        It is the initial state of this RNN layer, you can use it to initialize
        your state at the begining of each epoch or iteration according to your
        training procedure.

    batch_size : int or tensor
        Is int, if able to compute the batch_size, otherwise, tensor for ``?``.

    Notes
    -----
    - Input dimension should be rank 3 : [batch_size, n_steps, n_features], if no, please see :class:`ReshapeLayer`.
    - For predicting, the sequence length has to be the same with the sequence length of training, while, for normal
    RNN, we can use sequence length of 1 for predicting.

    References
    ----------
    - `Source <https://github.com/akaraspt/deepsleep/blob/master/deepsleep/model.py>`_
    """

    def __init__(
            self,
            layer=None,
            cell_fn=None,  #tf.nn.rnn_cell.LSTMCell,
            cell_init_args={'use_peepholes': True,
                            'state_is_tuple': True},
            n_hidden=100,
            initializer=tf.random_uniform_initializer(-0.1, 0.1),
            n_steps=5,
            fw_initial_state=None,
            bw_initial_state=None,
            dropout=None,
            n_layer=1,
            return_last=False,
            return_seq_2d=False,
            name='birnn_layer',
    ):
        Layer.__init__(self, name=name)
        if cell_fn is None:
            raise Exception("Please put in cell_fn")
        if 'GRU' in cell_fn.__name__:
            try:
                cell_init_args.pop('state_is_tuple')
            except:
                pass

        self.inputs = layer.outputs

        logging.info("BiRNNLayer %s: n_hidden:%d n_steps:%d in_dim:%d in_shape:%s cell_fn:%s dropout:%s n_layer:%d " % (self.name, n_hidden, n_steps,
                                                                                                                        self.inputs.get_shape().ndims,
                                                                                                                        self.inputs.get_shape(),
                                                                                                                        cell_fn.__name__, dropout, n_layer))

        fixed_batch_size = self.inputs.get_shape().with_rank_at_least(1)[0]

        if fixed_batch_size.value:
            self.batch_size = fixed_batch_size.value
            logging.info("       RNN batch_size (concurrent processes): %d" % self.batch_size)
        else:
            from tensorflow.python.ops import array_ops
            self.batch_size = array_ops.shape(self.inputs)[0]
            logging.info("       non specified batch_size, uses a tensor instead.")

        # Input dimension should be rank 3 [batch_size, n_steps(max), n_features]
        try:
            self.inputs.get_shape().with_rank(3)
        except:
            raise Exception("RNN : Input dimension should be rank 3 : [batch_size, n_steps, n_features]")

        with tf.variable_scope(name, initializer=initializer) as vs:
            rnn_creator = lambda: cell_fn(num_units=n_hidden, **cell_init_args)
            # Apply dropout
            if dropout:
                if type(dropout) in [tuple, list]:
                    in_keep_prob = dropout[0]
                    out_keep_prob = dropout[1]
                elif isinstance(dropout, float):
                    in_keep_prob, out_keep_prob = dropout, dropout
                else:
                    raise Exception("Invalid dropout type (must be a 2-D tuple of " "float)")
                try:  # TF 1.0
                    DropoutWrapper_fn = tf.contrib.rnn.DropoutWrapper
                except:
                    DropoutWrapper_fn = tf.nn.rnn_cell.DropoutWrapper
                cell_creator = lambda: DropoutWrapper_fn(rnn_creator(), input_keep_prob=in_keep_prob, output_keep_prob=1.0)  # out_keep_prob)
            else:
                cell_creator = rnn_creator
            self.fw_cell = cell_creator()
            self.bw_cell = cell_creator()

            # Apply multiple layers
            if n_layer > 1:
                try:  # TF1.0
                    MultiRNNCell_fn = tf.contrib.rnn.MultiRNNCell
                except:
                    MultiRNNCell_fn = tf.nn.rnn_cell.MultiRNNCell

                try:
                    self.fw_cell = MultiRNNCell_fn([cell_creator() for _ in range(n_layer)], state_is_tuple=True)
                    self.bw_cell = MultiRNNCell_fn([cell_creator() for _ in range(n_layer)], state_is_tuple=True)
                except:
                    self.fw_cell = MultiRNNCell_fn([cell_creator() for _ in range(n_layer)])
                    self.bw_cell = MultiRNNCell_fn([cell_creator() for _ in range(n_layer)])

            # Initial state of RNN
            if fw_initial_state is None:
                self.fw_initial_state = self.fw_cell.zero_state(self.batch_size, dtype=D_TYPE)  # dtype=tf.float32)
            else:
                self.fw_initial_state = fw_initial_state
            if bw_initial_state is None:
                self.bw_initial_state = self.bw_cell.zero_state(self.batch_size, dtype=D_TYPE)  # dtype=tf.float32)
            else:
                self.bw_initial_state = bw_initial_state
            # exit()
            # Feedforward to MultiRNNCell
            try:  # TF1.0
                list_rnn_inputs = tf.unstack(self.inputs, axis=1)
            except:  # TF0.12
                list_rnn_inputs = tf.unpack(self.inputs, axis=1)

            try:  # TF1.0
                bidirectional_rnn_fn = tf.contrib.rnn.static_bidirectional_rnn
            except:
                bidirectional_rnn_fn = tf.nn.bidirectional_rnn
            outputs, fw_state, bw_state = bidirectional_rnn_fn(  # outputs, fw_state, bw_state = tf.contrib.rnn.static_bidirectional_rnn(
                cell_fw=self.fw_cell,
                cell_bw=self.bw_cell,
                inputs=list_rnn_inputs,
                initial_state_fw=self.fw_initial_state,
                initial_state_bw=self.bw_initial_state)

            if return_last:
                raise Exception("Do not support return_last at the moment.")
                self.outputs = outputs[-1]
            else:
                self.outputs = outputs
                if return_seq_2d:
                    # 2D Tensor [n_example, n_hidden]
                    try:  # TF1.0
                        self.outputs = tf.reshape(tf.concat(outputs, 1), [-1, n_hidden * 2])
                    except:  # TF0.12
                        self.outputs = tf.reshape(tf.concat(1, outputs), [-1, n_hidden * 2])
                else:
                    # <akara>: stack more RNN layer after that
                    # 3D Tensor [n_example/n_steps, n_steps, n_hidden]

                    try:  # TF1.0
                        self.outputs = tf.reshape(tf.concat(outputs, 1), [-1, n_steps, n_hidden * 2])
                    except:  # TF0.12
                        self.outputs = tf.reshape(tf.concat(1, outputs), [-1, n_steps, n_hidden * 2])
            self.fw_final_state = fw_state
            self.bw_final_state = bw_state

            # Retrieve just the RNN variables.
            rnn_variables = tf.get_collection(TF_GRAPHKEYS_VARIABLES, scope=vs.name)

        logging.info("     n_params : %d" % (len(rnn_variables)))

        self.all_layers = list(layer.all_layers)
        self.all_params = list(layer.all_params)
        self.all_drop = dict(layer.all_drop)
        self.all_layers.extend([self.outputs])
        self.all_params.extend(rnn_variables)


class ConvRNNCell(object):
    """Abstract object representing an Convolutional RNN Cell.
    """

    def __call__(self, inputs, state, scope=None):
        """Run this RNN cell on inputs, starting from the given state.
        """
        raise NotImplementedError("Abstract method")

    @property
    def state_size(self):
        """size(s) of state(s) used by this cell.
        """
        raise NotImplementedError("Abstract method")

    @property
    def output_size(self):
        """Integer or TensorShape: size of outputs produced by this cell."""
        raise NotImplementedError("Abstract method")

    def zero_state(self, batch_size, dtype):
        """Return zero-filled state tensor(s).
        Args:
          batch_size: int, float, or unit Tensor representing the batch size.
          dtype: the data type to use for the state.
        Returns:
          tensor of shape '[batch_size x shape[0] x shape[1] x num_features]
          filled with zeros
        """

        shape = self.shape
        num_features = self.num_features
        zeros = tf.zeros([batch_size, shape[0], shape[1], num_features * 2])
        return zeros


class BasicConvLSTMCell(ConvRNNCell):
    """Basic Conv LSTM recurrent network cell.

    Parameters
    -----------
    shape : int tuple thats the height and width of the cell
    filter_size : int tuple thats the height and width of the filter
    num_features : int thats the depth of the cell
    forget_bias : float, The bias added to forget gates (see above).
    input_size : Deprecated and unused.
    state_is_tuple : If True, accepted and returned states are 2-tuples of
        the `c_state` and `m_state`.  If False, they are concatenated
        along the column axis.  The latter behavior will soon be deprecated.
    activation : Activation function of the inner states.
    """

    def __init__(self, shape, filter_size, num_features, forget_bias=1.0, input_size=None, state_is_tuple=False, activation=tf.nn.tanh):
        """Initialize the basic Conv LSTM cell."""
        # if not state_is_tuple:
        # logging.warn("%s: Using a concatenated state is slower and will soon be "
        #             "deprecated.  Use state_is_tuple=True.", self)
        if input_size is not None:
            logging.warn("%s: The input_size parameter is deprecated.", self)
        self.shape = shape
        self.filter_size = filter_size
        self.num_features = num_features
        self._forget_bias = forget_bias
        self._state_is_tuple = state_is_tuple
        self._activation = activation

    @property
    def state_size(self):
        """State size of the LSTMStateTuple."""
        return (LSTMStateTuple(self._num_units, self._num_units) if self._state_is_tuple else 2 * self._num_units)

    @property
    def output_size(self):
        """Number of units in outputs."""
        return self._num_units

    def __call__(self, inputs, state, scope=None):
        """Long short-term memory cell (LSTM)."""
        with tf.variable_scope(scope or type(self).__name__):  # "BasicLSTMCell"
            # Parameters of gates are concatenated into one multiply for efficiency.
            if self._state_is_tuple:
                c, h = state
            else:
                # print state
                # c, h = tf.split(3, 2, state)
                c, h = tf.split(state, 2, 3)
            concat = _conv_linear([inputs, h], self.filter_size, self.num_features * 4, True)

            # i = input_gate, j = new_input, f = forget_gate, o = output_gate
            # i, j, f, o = tf.split(3, 4, concat)
            i, j, f, o = tf.split(concat, 4, 3)

            new_c = (c * tf.nn.sigmoid(f + self._forget_bias) + tf.nn.sigmoid(i) * self._activation(j))
            new_h = self._activation(new_c) * tf.nn.sigmoid(o)

            if self._state_is_tuple:
                new_state = LSTMStateTuple(new_c, new_h)
            else:
                new_state = tf.concat([new_c, new_h], 3)
            return new_h, new_state


def _conv_linear(args, filter_size, num_features, bias, bias_start=0.0, scope=None):
    """convolution:

    Parameters
    ----------
      args: a 4D Tensor or a list of 4D, batch x n, Tensors.
      filter_size: int tuple of filter height and width.
      num_features: int, number of features.
      bias_start: starting value to initialize the bias; 0 by default.
      scope: VariableScope for the created subgraph; defaults to "Linear".

    Returns
    --------
    - A 4D Tensor with shape [batch h w num_features]

    Raises
    -------
    - ValueError : if some of the arguments has unspecified or wrong shape.
    """

    # Calculate the total size of arguments on dimension 1.
    total_arg_size_depth = 0
    shapes = [a.get_shape().as_list() for a in args]
    for shape in shapes:
        if len(shape) != 4:
            raise ValueError("Linear is expecting 4D arguments: %s" % str(shapes))
        if not shape[3]:
            raise ValueError("Linear expects shape[4] of arguments: %s" % str(shapes))
        else:
            total_arg_size_depth += shape[3]

    dtype = [a.dtype for a in args][0]

    # Now the computation.
    with tf.variable_scope(scope or "Conv"):
        matrix = tf.get_variable("Matrix", [filter_size[0], filter_size[1], total_arg_size_depth, num_features], dtype=dtype)
        if len(args) == 1:
            res = tf.nn.conv2d(args[0], matrix, strides=[1, 1, 1, 1], padding='SAME')
        else:
            res = tf.nn.conv2d(tf.concat(args, 3), matrix, strides=[1, 1, 1, 1], padding='SAME')
        if not bias:
            return res
        bias_term = tf.get_variable("Bias", [num_features], dtype=dtype, initializer=tf.constant_initializer(bias_start, dtype=dtype))
    return res + bias_term


class ConvLSTMLayer(Layer):
    """
    The :class:`ConvLSTMLayer` class is a Convolutional LSTM layer,
    see `Convolutional LSTM Layer <https://arxiv.org/abs/1506.04214>`_ .

    Parameters
    ----------
    layer : a :class:`Layer` instance
        The `Layer` class feeding into this layer.
    cell_shape : tuple, the shape of each cell width*height
    filter_size : tuple, the size of filter width*height
    cell_fn : a Convolutional RNN cell as follow.
    feature_map : a int
        The number of feature map in the layer.
    initializer : initializer
        The initializer for initializing the parameters.
    n_steps : a int
        The sequence length.
    initial_state : None or ConvLSTM State
        If None, initial_state is zero_state.
    return_last : boolen
        - If True, return the last output, "Sequence input and single output"
        - If False, return all outputs, "Synced sequence input and output"
        - In other word, if you want to apply one or more ConvLSTM(s) on this layer, set to False.
    return_seq_2d : boolen
        - When return_last = False
        - If True, return 4D Tensor [n_example, h, w, c], for stacking DenseLayer after it.
        - If False, return 5D Tensor [n_example/n_steps, h, w, c], for stacking multiple ConvLSTM after it.
    name : a string or None
        An optional name to attach to this layer.

    Attributes
    --------------
    outputs : a tensor
        The output of this RNN.
        return_last = False, outputs = all cell_output, which is the hidden state.
            cell_output.get_shape() = (?, h, w, c])

    final_state : a tensor or StateTuple
        When state_is_tuple = False,
        it is the final hidden and cell states,
        When state_is_tuple = True,
        You can get the final state after each iteration during training, then
        feed it to the initial state of next iteration.

    initial_state : a tensor or StateTuple
        It is the initial state of this ConvLSTM layer, you can use it to initialize
        your state at the begining of each epoch or iteration according to your
        training procedure.

    batch_size : int or tensor
        Is int, if able to compute the batch_size, otherwise, tensor for ``?``.
    """

    def __init__(
            self,
            layer=None,
            cell_shape=None,
            feature_map=1,
            filter_size=(3, 3),
            cell_fn=BasicConvLSTMCell,
            initializer=tf.random_uniform_initializer(-0.1, 0.1),
            n_steps=5,
            initial_state=None,
            return_last=False,
            return_seq_2d=False,
            name='convlstm_layer',
    ):
        Layer.__init__(self, name=name)
        self.inputs = layer.outputs
        logging.info("ConvLSTMLayer %s: feature_map:%d, n_steps:%d, "
                     "in_dim:%d %s, cell_fn:%s " % (self.name, feature_map, n_steps, self.inputs.get_shape().ndims, self.inputs.get_shape(), cell_fn.__name__))
        # You can get the dimension by .get_shape() or ._shape, and check the
        # dimension by .with_rank() as follow.
        # self.inputs.get_shape().with_rank(2)
        # self.inputs.get_shape().with_rank(3)

        # Input dimension should be rank 5 [batch_size, n_steps(max), h, w, c]
        try:
            self.inputs.get_shape().with_rank(5)
        except:
            raise Exception("RNN : Input dimension should be rank 5 : [batch_size, n_steps, input_x, " "input_y, feature_map]")

        fixed_batch_size = self.inputs.get_shape().with_rank_at_least(1)[0]

        if fixed_batch_size.value:
            batch_size = fixed_batch_size.value
            logging.info("     RNN batch_size (concurrent processes): %d" % batch_size)
        else:
            from tensorflow.python.ops import array_ops
            batch_size = array_ops.shape(self.inputs)[0]
            logging.info("     non specified batch_size, uses a tensor instead.")
        self.batch_size = batch_size

        outputs = []
        self.cell = cell = cell_fn(shape=cell_shape, filter_size=filter_size, num_features=feature_map)
        if initial_state is None:
            self.initial_state = cell.zero_state(batch_size, dtype=D_TYPE)  # dtype=tf.float32)  # 1.2.3
        state = self.initial_state
        # with tf.variable_scope("model", reuse=None, initializer=initializer):
        with tf.variable_scope(name, initializer=initializer) as vs:
            for time_step in range(n_steps):
                if time_step > 0: tf.get_variable_scope().reuse_variables()
                (cell_output, state) = cell(self.inputs[:, time_step, :, :, :], state)
                outputs.append(cell_output)

            # Retrieve just the RNN variables.
            # rnn_variables = [v for v in tf.all_variables() if v.name.startswith(vs.name)]
            rnn_variables = tf.get_collection(tf.GraphKeys.VARIABLES, scope=vs.name)

        logging.info(" n_params : %d" % (len(rnn_variables)))

        if return_last:
            # 2D Tensor [batch_size, n_hidden]
            self.outputs = outputs[-1]
        else:
            if return_seq_2d:
                # PTB tutorial: stack dense layer after that, or compute the cost from the output
                # 4D Tensor [n_example, h, w, c]
                self.outputs = tf.reshape(tf.concat(outputs, 1), [-1, cell_shape[0] * cell_shape[1] * feature_map])
            else:
                # <akara>: stack more RNN layer after that
                # 5D Tensor [n_example/n_steps, n_steps, h, w, c]
                self.outputs = tf.reshape(tf.concat(outputs, 1), [-1, n_steps, cell_shape[0], cell_shape[1], feature_map])

        self.final_state = state

        self.all_layers = list(layer.all_layers)
        self.all_params = list(layer.all_params)
        self.all_drop = dict(layer.all_drop)
        self.all_layers.extend([self.outputs])
        self.all_params.extend(rnn_variables)


# Advanced Ops for Dynamic RNN
def advanced_indexing_op(input, index):
    """Advanced Indexing for Sequences, returns the outputs by given sequence lengths.
    When return the last output :class:`DynamicRNNLayer` uses it to get the last outputs with the sequence lengths.

    Parameters
    -----------
    input : tensor for data
        [batch_size, n_step(max), n_features]
    index : tensor for indexing, i.e. sequence_length in Dynamic RNN.
        [batch_size]

    Examples
    ---------
    >>> batch_size, max_length, n_features = 3, 5, 2
    >>> z = np.random.uniform(low=-1, high=1, size=[batch_size, max_length, n_features]).astype(np.float32)
    >>> b_z = tf.constant(z)
    >>> sl = tf.placeholder(dtype=tf.int32, shape=[batch_size])
    >>> o = advanced_indexing_op(b_z, sl)
    >>>
    >>> sess = tf.InteractiveSession()
    >>> tl.layers.initialize_global_variables(sess)
    >>>
    >>> order = np.asarray([1,1,2])
    >>> print("real",z[0][order[0]-1], z[1][order[1]-1], z[2][order[2]-1])
    >>> y = sess.run([o], feed_dict={sl:order})
    >>> print("given",order)
    >>> print("out", y)
    ... real [-0.93021595  0.53820813] [-0.92548317 -0.77135968] [ 0.89952248  0.19149846]
    ... given [1 1 2]
    ... out [array([[-0.93021595,  0.53820813],
    ...             [-0.92548317, -0.77135968],
    ...             [ 0.89952248,  0.19149846]], dtype=float32)]

    References
    -----------
    - Modified from TFlearn (the original code is used for fixed length rnn), `references <https://github.com/tflearn/tflearn/blob/master/tflearn/layers/recurrent.py>`_.
    """
    batch_size = tf.shape(input)[0]
    # max_length = int(input.get_shape()[1])    # for fixed length rnn, length is given
    max_length = tf.shape(input)[1]  # for dynamic_rnn, length is unknown
    dim_size = int(input.get_shape()[2])
    index = tf.range(0, batch_size) * max_length + (index - 1)
    flat = tf.reshape(input, [-1, dim_size])
    relevant = tf.gather(flat, index)
    return relevant


def retrieve_seq_length_op(data):
    """An op to compute the length of a sequence from input shape of [batch_size, n_step(max), n_features],
    it can be used when the features of padding (on right hand side) are all zeros.

    Parameters
    -----------
    data : tensor
        [batch_size, n_step(max), n_features] with zero padding on right hand side.

    Examples
    ---------
    >>> data = [[[1],[2],[0],[0],[0]],
    ...         [[1],[2],[3],[0],[0]],
    ...         [[1],[2],[6],[1],[0]]]
    >>> data = np.asarray(data)
    >>> print(data.shape)
    ... (3, 5, 1)
    >>> data = tf.constant(data)
    >>> sl = retrieve_seq_length_op(data)
    >>> sess = tf.InteractiveSession()
    >>> tl.layers.initialize_global_variables(sess)
    >>> y = sl.eval()
    ... [2 3 4]

    - Multiple features
    >>> data = [[[1,2],[2,2],[1,2],[1,2],[0,0]],
    ...         [[2,3],[2,4],[3,2],[0,0],[0,0]],
    ...         [[3,3],[2,2],[5,3],[1,2],[0,0]]]
    >>> print(sl)
    ... [4 3 4]

    References
    ------------
    - Borrow from `TFlearn <https://github.com/tflearn/tflearn/blob/master/tflearn/layers/recurrent.py>`_.
    """
    with tf.name_scope('GetLength'):
        # TF 1.0 change reduction_indices to axis
        used = tf.sign(tf.reduce_max(tf.abs(data), 2))
        length = tf.reduce_sum(used, 1)
        # TF < 1.0
        # used = tf.sign(tf.reduce_max(tf.abs(data), reduction_indices=2))
        # length = tf.reduce_sum(used, reduction_indices=1)
        length = tf.cast(length, tf.int32)
    return length


def retrieve_seq_length_op2(data):
    """An op to compute the length of a sequence, from input shape of [batch_size, n_step(max)],
    it can be used when the features of padding (on right hand side) are all zeros.

    Parameters
    -----------
    data : tensor
        [batch_size, n_step(max)] with zero padding on right hand side.

    Examples
    --------
    >>> data = [[1,2,0,0,0],
    ...         [1,2,3,0,0],
    ...         [1,2,6,1,0]]
    >>> o = retrieve_seq_length_op2(data)
    >>> sess = tf.InteractiveSession()
    >>> tl.layers.initialize_global_variables(sess)
    >>> print(o.eval())
    ... [2 3 4]
    """
    return tf.reduce_sum(tf.cast(tf.greater(data, tf.zeros_like(data)), tf.int32), 1)


def retrieve_seq_length_op3(data, pad_val=0):  # HangSheng: return tensor for sequence length, if input is tf.string
    data_shape_size = data.get_shape().ndims
    if data_shape_size == 3:
        return tf.reduce_sum(tf.cast(tf.reduce_any(tf.not_equal(data, pad_val), axis=2), dtype=tf.int32), 1)
    elif data_shape_size == 2:
        return tf.reduce_sum(tf.cast(tf.not_equal(data, pad_val), dtype=tf.int32), 1)
    elif data_shape_size == 1:
        raise ValueError("retrieve_seq_length_op3: data has wrong shape!")
    else:
        raise ValueError("retrieve_seq_length_op3: handling data_shape_size %s hasn't been implemented!" % (data_shape_size))


def target_mask_op(data, pad_val=0):  # HangSheng: return tensor for mask,if input is tf.string
    data_shape_size = data.get_shape().ndims
    if data_shape_size == 3:
        return tf.cast(tf.reduce_any(tf.not_equal(data, pad_val), axis=2), dtype=tf.int32)
    elif data_shape_size == 2:
        return tf.cast(tf.not_equal(data, pad_val), dtype=tf.int32)
    elif data_shape_size == 1:
        raise ValueError("target_mask_op: data has wrong shape!")
    else:
        raise ValueError("target_mask_op: handling data_shape_size %s hasn't been implemented!" % (data_shape_size))


# Dynamic RNN
class DynamicRNNLayer(Layer):
    """
    The :class:`DynamicRNNLayer` class is a Dynamic RNN layer, see ``tf.nn.dynamic_rnn``.

    Parameters
    ----------
    layer : a :class:`Layer` instance
        The `Layer` class feeding into this layer.
    cell_fn : a TensorFlow's core RNN cell as follow (Note TF1.0+ and TF1.0- are different).
        - see `RNN Cells in TensorFlow <https://www.tensorflow.org/api_docs/python/>`_
    cell_init_args : a dictionary
        The arguments for the cell initializer.
    n_hidden : an int
        The number of hidden units in the layer.
    initializer : initializer
        The initializer for initializing the parameters.
    sequence_length : a tensor, array or None. The sequence length of each row of input data, see ``Advanced Ops for Dynamic RNN``.
        - If None, it uses ``retrieve_seq_length_op`` to compute the sequence_length, i.e. when the features of padding (on right hand side) are all zeros.
        - If using word embedding, you may need to compute the sequence_length from the ID array (the integer features before word embedding) by using ``retrieve_seq_length_op2`` or ``retrieve_seq_length_op``.
        - You can also input an numpy array.
        - More details about TensorFlow dynamic_rnn in `Wild-ML Blog <http://www.wildml.com/2016/08/rnns-in-tensorflow-a-practical-guide-and-undocumented-features/>`_.
    initial_state : None or RNN State
        If None, initial_state is zero_state.
    dropout : `tuple` of `float`: (input_keep_prob, output_keep_prob).
        The input and output keep probability.
    n_layer : an int, default is 1.
        The number of RNN layers.
    return_last : boolean
        - If True, return the last output, "Sequence input and single output"
        - If False, return all outputs, "Synced sequence input and output"
        - In other word, if you want to apply one or more RNN(s) on this layer, set to False.
    return_seq_2d : boolean
        - When return_last = False
        - If True, return 2D Tensor [n_example, n_hidden], for stacking DenseLayer or computing cost after it.
        - If False, return 3D Tensor [n_example/n_steps(max), n_steps(max), n_hidden], for stacking multiple RNN after it.
    name : a string or None
        An optional name to attach to this layer.

    Attributes
    ------------
    outputs : a tensor
        The output of this RNN.
        return_last = False, outputs = all cell_output, which is the hidden state.
            cell_output.get_shape() = (?, n_hidden)

    final_state : a tensor or StateTuple
        When state_is_tuple = False,
        it is the final hidden and cell states, states.get_shape() = [?, 2 * n_hidden].\n
        When state_is_tuple = True, it stores two elements: (c, h), in that order.
        You can get the final state after each iteration during training, then
        feed it to the initial state of next iteration.

    initial_state : a tensor or StateTuple
        It is the initial state of this RNN layer, you can use it to initialize
        your state at the begining of each epoch or iteration according to your
        training procedure.

    sequence_length : a tensor or array, shape = [batch_size]
        The sequence lengths computed by Advanced Opt or the given sequence lengths.

    Notes
    -----
    Input dimension should be rank 3 : [batch_size, n_steps(max), n_features], if no, please see :class:`ReshapeLayer`.

    Examples
    --------
    >>> input_seqs = tf.placeholder(dtype=tf.int64, shape=[batch_size, None], name="input_seqs")
    >>> net = tl.layers.EmbeddingInputlayer(
    ...             inputs = input_seqs,
    ...             vocabulary_size = vocab_size,
    ...             embedding_size = embedding_size,
    ...             name = 'seq_embedding')
    >>> net = tl.layers.DynamicRNNLayer(net,
    ...             cell_fn = tf.contrib.rnn.BasicLSTMCell, # for TF0.2 tf.nn.rnn_cell.BasicLSTMCell,
    ...             n_hidden = embedding_size,
    ...             dropout = 0.7,
    ...             sequence_length = tl.layers.retrieve_seq_length_op2(input_seqs),
    ...             return_seq_2d = True,     # stack denselayer or compute cost after it
    ...             name = 'dynamic_rnn')
    ... net = tl.layers.DenseLayer(net, n_units=vocab_size,
    ...             act=tf.identity, name="output")

    References
    ----------
    - `Wild-ML Blog <http://www.wildml.com/2016/08/rnns-in-tensorflow-a-practical-guide-and-undocumented-features/>`_
    - `dynamic_rnn.ipynb <https://github.com/dennybritz/tf-rnn/blob/master/dynamic_rnn.ipynb>`_
    - `tf.nn.dynamic_rnn <https://github.com/tensorflow/tensorflow/blob/master/tensorflow/g3doc/api_docs/python/functions_and_classes/shard8/tf.nn.dynamic_rnn.md>`_
    - `tflearn rnn <https://github.com/tflearn/tflearn/blob/master/tflearn/layers/recurrent.py>`_
    - ``tutorial_dynamic_rnn.py``
    """

    def __init__(
            self,
            layer=None,
            cell_fn=None,  #tf.nn.rnn_cell.LSTMCell,
            cell_init_args={'state_is_tuple': True},
            n_hidden=256,
            initializer=tf.random_uniform_initializer(-0.1, 0.1),
            sequence_length=None,
            initial_state=None,
            dropout=None,
            n_layer=1,
            return_last=False,
            return_seq_2d=False,
            dynamic_rnn_init_args={},
            name='dyrnn_layer',
    ):
        Layer.__init__(self, name=name)
        if cell_fn is None:
            raise Exception("Please put in cell_fn")
        if 'GRU' in cell_fn.__name__:
            try:
                cell_init_args.pop('state_is_tuple')
            except:
                pass
        self.inputs = layer.outputs

        logging.info("DynamicRNNLayer %s: n_hidden:%d, in_dim:%d in_shape:%s cell_fn:%s dropout:%s n_layer:%d" %
                     (self.name, n_hidden, self.inputs.get_shape().ndims, self.inputs.get_shape(), cell_fn.__name__, dropout, n_layer))

        # Input dimension should be rank 3 [batch_size, n_steps(max), n_features]
        try:
            self.inputs.get_shape().with_rank(3)
        except:
            raise Exception("RNN : Input dimension should be rank 3 : [batch_size, n_steps(max), n_features]")

        # Get the batch_size
        fixed_batch_size = self.inputs.get_shape().with_rank_at_least(1)[0]
        if fixed_batch_size.value:
            batch_size = fixed_batch_size.value
            logging.info("       batch_size (concurrent processes): %d" % batch_size)
        else:
            from tensorflow.python.ops import array_ops
            batch_size = array_ops.shape(self.inputs)[0]
            logging.info("       non specified batch_size, uses a tensor instead.")
        self.batch_size = batch_size

        # Creats the cell function
        # cell_instance_fn=lambda: cell_fn(num_units=n_hidden, **cell_init_args) # HanSheng
        rnn_creator = lambda: cell_fn(num_units=n_hidden, **cell_init_args)

        # Apply dropout
        if dropout:
            if type(dropout) in [tuple, list]:
                in_keep_prob = dropout[0]
                out_keep_prob = dropout[1]
            elif isinstance(dropout, float):
                in_keep_prob, out_keep_prob = dropout, dropout
            else:
                raise Exception("Invalid dropout type (must be a 2-D tuple of " "float)")
            try:  # TF1.0
                DropoutWrapper_fn = tf.contrib.rnn.DropoutWrapper
            except:
                DropoutWrapper_fn = tf.nn.rnn_cell.DropoutWrapper

            # cell_instance_fn1=cell_instance_fn        # HanSheng
            # cell_instance_fn=DropoutWrapper_fn(
            #                     cell_instance_fn1(),
            #                     input_keep_prob=in_keep_prob,
            #                     output_keep_prob=out_keep_prob)
            cell_creator = lambda: DropoutWrapper_fn(rnn_creator(), input_keep_prob=in_keep_prob, output_keep_prob=1.0)  #out_keep_prob)
        else:
            cell_creator = rnn_creator
        self.cell = cell_creator()
        # Apply multiple layers
        if n_layer > 1:
            try:
                MultiRNNCell_fn = tf.contrib.rnn.MultiRNNCell
            except:
                MultiRNNCell_fn = tf.nn.rnn_cell.MultiRNNCell

            # cell_instance_fn2=cell_instance_fn # HanSheng
            try:
                # cell_instance_fn=lambda: MultiRNNCell_fn([cell_instance_fn2() for _ in range(n_layer)], state_is_tuple=True) # HanSheng
                self.cell = MultiRNNCell_fn([cell_creator() for _ in range(n_layer)], state_is_tuple=True)
            except:  # when GRU
                # cell_instance_fn=lambda: MultiRNNCell_fn([cell_instance_fn2() for _ in range(n_layer)]) # HanSheng
                self.cell = MultiRNNCell_fn([cell_creator() for _ in range(n_layer)])

        # self.cell=cell_instance_fn() # HanSheng

        # Initialize initial_state
        if initial_state is None:
            self.initial_state = self.cell.zero_state(batch_size, dtype=D_TYPE)  # dtype=tf.float32)
        else:
            self.initial_state = initial_state

        # Computes sequence_length
        if sequence_length is None:
            try:  # TF1.0
                sequence_length = retrieve_seq_length_op(self.inputs if isinstance(self.inputs, tf.Tensor) else tf.stack(self.inputs))
            except:  # TF0.12
                sequence_length = retrieve_seq_length_op(self.inputs if isinstance(self.inputs, tf.Tensor) else tf.pack(self.inputs))

        # Main - Computes outputs and last_states
        with tf.variable_scope(name, initializer=initializer) as vs:
            outputs, last_states = tf.nn.dynamic_rnn(
                cell=self.cell,
                # inputs=X
                inputs=self.inputs,
                # dtype=tf.float64,
                sequence_length=sequence_length,
                initial_state=self.initial_state,
                **dynamic_rnn_init_args)
            rnn_variables = tf.get_collection(TF_GRAPHKEYS_VARIABLES, scope=vs.name)

            # logging.info("     n_params : %d" % (len(rnn_variables)))
            # Manage the outputs
            if return_last:
                # [batch_size, n_hidden]
                # outputs = tf.transpose(tf.pack(outputs), [1, 0, 2]) # TF1.0 tf.pack --> tf.stack
                self.outputs = advanced_indexing_op(outputs, sequence_length)
            else:
                # [batch_size, n_step(max), n_hidden]
                # self.outputs = result[0]["outputs"]
                # self.outputs = outputs    # it is 3d, but it is a list
                if return_seq_2d:
                    # PTB tutorial:
                    # 2D Tensor [n_example, n_hidden]
                    try:  # TF1.0
                        self.outputs = tf.reshape(tf.concat(outputs, 1), [-1, n_hidden])
                    except:  # TF0.12
                        self.outputs = tf.reshape(tf.concat(1, outputs), [-1, n_hidden])
                else:
                    # <akara>:
                    # 3D Tensor [batch_size, n_steps(max), n_hidden]
                    max_length = tf.shape(outputs)[1]
                    batch_size = tf.shape(outputs)[0]

                    try:  # TF1.0
                        self.outputs = tf.reshape(tf.concat(outputs, 1), [batch_size, max_length, n_hidden])
                    except:  # TF0.12
                        self.outputs = tf.reshape(tf.concat(1, outputs), [batch_size, max_length, n_hidden])
                    # self.outputs = tf.reshape(tf.concat(1, outputs), [-1, max_length, n_hidden])

        # Final state
        self.final_state = last_states

        self.sequence_length = sequence_length

        self.all_layers = list(layer.all_layers)
        self.all_params = list(layer.all_params)
        self.all_drop = dict(layer.all_drop)

        self.all_layers.extend([self.outputs])
        self.all_params.extend(rnn_variables)


# Bidirectional Dynamic RNN
class BiDynamicRNNLayer(Layer):
    """
    The :class:`BiDynamicRNNLayer` class is a RNN layer, you can implement vanilla RNN,
    LSTM and GRU with it.

    Parameters
    ----------
    layer : a :class:`Layer` instance
        The `Layer` class feeding into this layer.
    cell_fn : a TensorFlow's core RNN cell as follow (Note TF1.0+ and TF1.0- are different).
        - see `RNN Cells in TensorFlow <https://www.tensorflow.org/api_docs/python/>`_
    cell_init_args : a dictionary
        The arguments for the cell initializer.
    n_hidden : an int
        The number of hidden units in the layer.
    initializer : initializer
        The initializer for initializing the parameters.
    sequence_length : a tensor, array or None.
        The sequence length of each row of input data, see ``Advanced Ops for Dynamic RNN``.
            - If None, it uses ``retrieve_seq_length_op`` to compute the sequence_length, i.e. when the features of padding (on right hand side) are all zeros.
            - If using word embedding, you may need to compute the sequence_length from the ID array (the integer features before word embedding) by using ``retrieve_seq_length_op2`` or ``retrieve_seq_length_op``.
            - You can also input an numpy array.
            - More details about TensorFlow dynamic_rnn in `Wild-ML Blog <http://www.wildml.com/2016/08/rnns-in-tensorflow-a-practical-guide-and-undocumented-features/>`_.
    fw_initial_state : None or forward RNN State
        If None, initial_state is zero_state.
    bw_initial_state : None or backward RNN State
        If None, initial_state is zero_state.
    dropout : `tuple` of `float`: (input_keep_prob, output_keep_prob).
        The input and output keep probability.
    n_layer : an int, default is 1.
        The number of RNN layers.
    return_last : boolean
        If True, return the last output, "Sequence input and single output"\n
        If False, return all outputs, "Synced sequence input and output"\n
        In other word, if you want to apply one or more RNN(s) on this layer, set to False.
    return_seq_2d : boolean
        - When return_last = False
        - If True, return 2D Tensor [n_example, 2 * n_hidden], for stacking DenseLayer or computing cost after it.
        - If False, return 3D Tensor [n_example/n_steps(max), n_steps(max), 2 * n_hidden], for stacking multiple RNN after it.
    name : a string or None
        An optional name to attach to this layer.

    Attributes
    -----------------------
    outputs : a tensor
        The output of this RNN.
        return_last = False, outputs = all cell_output, which is the hidden state.
            cell_output.get_shape() = (?, 2 * n_hidden)

    fw(bw)_final_state : a tensor or StateTuple
        When state_is_tuple = False,
        it is the final hidden and cell states, states.get_shape() = [?, 2 * n_hidden].\n
        When state_is_tuple = True, it stores two elements: (c, h), in that order.
        You can get the final state after each iteration during training, then
        feed it to the initial state of next iteration.

    fw(bw)_initial_state : a tensor or StateTuple
        It is the initial state of this RNN layer, you can use it to initialize
        your state at the begining of each epoch or iteration according to your
        training procedure.

    sequence_length : a tensor or array, shape = [batch_size]
        The sequence lengths computed by Advanced Opt or the given sequence lengths.

    Notes
    -----
    Input dimension should be rank 3 : [batch_size, n_steps(max), n_features], if no, please see :class:`ReshapeLayer`.


    References
    ----------
    - `Wild-ML Blog <http://www.wildml.com/2016/08/rnns-in-tensorflow-a-practical-guide-and-undocumented-features/>`_
    - `bidirectional_rnn.ipynb <https://github.com/dennybritz/tf-rnn/blob/master/bidirectional_rnn.ipynb>`_
    """

    def __init__(
            self,
            layer=None,
            cell_fn=None,  #tf.nn.rnn_cell.LSTMCell,
            cell_init_args={'state_is_tuple': True},
            n_hidden=256,
            initializer=tf.random_uniform_initializer(-0.1, 0.1),
            sequence_length=None,
            fw_initial_state=None,
            bw_initial_state=None,
            dropout=None,
            n_layer=1,
            return_last=False,
            return_seq_2d=False,
            dynamic_rnn_init_args={},
            name='bi_dyrnn_layer',
    ):
        Layer.__init__(self, name=name)
        if cell_fn is None:
            raise Exception("Please put in cell_fn")
        if 'GRU' in cell_fn.__name__:
            try:
                cell_init_args.pop('state_is_tuple')
            except:
                pass
        self.inputs = layer.outputs

        logging.info("BiDynamicRNNLayer %s: n_hidden:%d in_dim:%d in_shape:%s cell_fn:%s dropout:%s n_layer:%d" %
                     (self.name, n_hidden, self.inputs.get_shape().ndims, self.inputs.get_shape(), cell_fn.__name__, dropout, n_layer))

        # Input dimension should be rank 3 [batch_size, n_steps(max), n_features]
        try:
            self.inputs.get_shape().with_rank(3)
        except:
            raise Exception("RNN : Input dimension should be rank 3 : [batch_size, n_steps(max), n_features]")

        # Get the batch_size
        fixed_batch_size = self.inputs.get_shape().with_rank_at_least(1)[0]
        if fixed_batch_size.value:
            batch_size = fixed_batch_size.value
            logging.info("       batch_size (concurrent processes): %d" % batch_size)
        else:
            from tensorflow.python.ops import array_ops
            batch_size = array_ops.shape(self.inputs)[0]
            logging.info("       non specified batch_size, uses a tensor instead.")
        self.batch_size = batch_size

        with tf.variable_scope(name, initializer=initializer) as vs:
            # Creats the cell function
            # cell_instance_fn=lambda: cell_fn(num_units=n_hidden, **cell_init_args) # HanSheng
            rnn_creator = lambda: cell_fn(num_units=n_hidden, **cell_init_args)

            # Apply dropout
            if dropout:
                if type(dropout) in [tuple, list]:
                    in_keep_prob = dropout[0]
                    out_keep_prob = dropout[1]
                elif isinstance(dropout, float):
                    in_keep_prob, out_keep_prob = dropout, dropout
                else:
                    raise Exception("Invalid dropout type (must be a 2-D tuple of " "float)")
                try:
                    DropoutWrapper_fn = tf.contrib.rnn.DropoutWrapper
                except:
                    DropoutWrapper_fn = tf.nn.rnn_cell.DropoutWrapper

                    # cell_instance_fn1=cell_instance_fn            # HanSheng
                    # cell_instance_fn=lambda: DropoutWrapper_fn(
                    #                     cell_instance_fn1(),
                    #                     input_keep_prob=in_keep_prob,
                    #                     output_keep_prob=out_keep_prob)
                cell_creator = lambda is_last=True: \
                    DropoutWrapper_fn(rnn_creator(),
                                      input_keep_prob=in_keep_prob,
                                      output_keep_prob=out_keep_prob if is_last else 1.0)  # out_keep_prob)
            else:
                cell_creator = lambda: rnn_creator()

            # if dropout:
            #     self.fw_cell = DropoutWrapper_fn(self.fw_cell, input_keep_prob=1.0, output_keep_prob=out_keep_prob)
            #     self.bw_cell = DropoutWrapper_fn(self.bw_cell, input_keep_prob=1.0, output_keep_prob=out_keep_prob)

            # self.fw_cell=cell_instance_fn()
            # self.bw_cell=cell_instance_fn()
            # Initial state of RNN

            self.fw_initial_state = fw_initial_state
            self.bw_initial_state = bw_initial_state
            # Computes sequence_length
            if sequence_length is None:
                try:  # TF1.0
                    sequence_length = retrieve_seq_length_op(self.inputs if isinstance(self.inputs, tf.Tensor) else tf.stack(self.inputs))
                except:  # TF0.12
                    sequence_length = retrieve_seq_length_op(self.inputs if isinstance(self.inputs, tf.Tensor) else tf.pack(self.inputs))

            if n_layer > 1:
                self.fw_cell = [cell_creator(is_last=i == n_layer - 1) for i in range(n_layer)]
                self.bw_cell = [cell_creator(is_last=i == n_layer - 1) for i in range(n_layer)]
                from tensorflow.contrib.rnn import stack_bidirectional_dynamic_rnn
                outputs, states_fw, states_bw = stack_bidirectional_dynamic_rnn(
                    cells_fw=self.fw_cell,
                    cells_bw=self.bw_cell,
                    inputs=self.inputs,
                    sequence_length=sequence_length,
                    initial_states_fw=self.fw_initial_state,
                    initial_states_bw=self.bw_initial_state,
                    dtype=D_TYPE,
                    **dynamic_rnn_init_args)

            else:
                self.fw_cell = cell_creator()
                self.bw_cell = cell_creator()
                outputs, (states_fw, states_bw) = tf.nn.bidirectional_dynamic_rnn(
                    cell_fw=self.fw_cell,
                    cell_bw=self.bw_cell,
                    inputs=self.inputs,
                    sequence_length=sequence_length,
                    initial_state_fw=self.fw_initial_state,
                    initial_state_bw=self.bw_initial_state,
                    dtype=D_TYPE,
                    **dynamic_rnn_init_args)

            rnn_variables = tf.get_collection(TF_GRAPHKEYS_VARIABLES, scope=vs.name)

            logging.info("     n_params : %d" % (len(rnn_variables)))
            # Manage the outputs
            try:  # TF1.0
                outputs = tf.concat(outputs, 2)
            except:  # TF0.12
                outputs = tf.concat(2, outputs)
            if return_last:
                # [batch_size, 2 * n_hidden]
                raise Exception("Do not support return_last at the moment")
                self.outputs = advanced_indexing_op(outputs, sequence_length)
            else:
                # [batch_size, n_step(max), 2 * n_hidden]
                if return_seq_2d:
                    # PTB tutorial:
                    # 2D Tensor [n_example, 2 * n_hidden]
                    try:  # TF1.0
                        self.outputs = tf.reshape(tf.concat(outputs, 1), [-1, 2 * n_hidden])
                    except:  # TF0.12
                        self.outputs = tf.reshape(tf.concat(1, outputs), [-1, 2 * n_hidden])
                else:
                    # <akara>:
                    # 3D Tensor [batch_size, n_steps(max), 2 * n_hidden]
                    max_length = tf.shape(outputs)[1]
                    batch_size = tf.shape(outputs)[0]
                    try:  # TF1.0
                        self.outputs = tf.reshape(tf.concat(outputs, 1), [batch_size, max_length, 2 * n_hidden])
                    except:  # TF0.12
                        self.outputs = tf.reshape(tf.concat(1, outputs), [batch_size, max_length, 2 * n_hidden])
                    # self.outputs = tf.reshape(tf.concat(1, outputs), [-1, max_length, 2 * n_hidden])

        # Final state
        self.fw_final_states = states_fw
        self.bw_final_states = states_bw

        self.sequence_length = sequence_length

        self.all_layers = list(layer.all_layers)
        self.all_params = list(layer.all_params)
        self.all_drop = dict(layer.all_drop)

        self.all_layers.extend([self.outputs])
        self.all_params.extend(rnn_variables)


# Seq2seq
class Seq2Seq(Layer):
    """
    The :class:`Seq2Seq` class is a Simple :class:`DynamicRNNLayer` based Seq2seq layer without using `tl.contrib.seq2seq <https://www.tensorflow.org/api_guides/python/contrib.seq2seq>`_.
    See `Model <https://camo.githubusercontent.com/9e88497fcdec5a9c716e0de5bc4b6d1793c6e23f/687474703a2f2f73757269796164656570616e2e6769746875622e696f2f696d672f736571327365712f73657132736571322e706e67>`_
    and `Sequence to Sequence Learning with Neural Networks <https://arxiv.org/abs/1409.3215>`_.

    - Please check the example `Chatbot in 200 lines of code <https://github.com/zsdonghao/seq2seq-chatbot>`_.
    - The Author recommends users to read the source code of :class:`DynamicRNNLayer` and :class:`Seq2Seq`.

    Parameters
    ----------
    net_encode_in : a :class:`Layer` instance
        Encode sequences, [batch_size, None, n_features].
    net_decode_in : a :class:`Layer` instance
        Decode sequences, [batch_size, None, n_features].
    cell_fn : a TensorFlow's core RNN cell as follow (Note TF1.0+ and TF1.0- are different).
        - see `RNN Cells in TensorFlow <https://www.tensorflow.org/api_docs/python/>`_
    cell_init_args : a dictionary
        The arguments for the cell initializer.
    n_hidden : an int
        The number of hidden units in the layer.
    initializer : initializer
        The initializer for initializing the parameters.
    encode_sequence_length : tensor for encoder sequence length, see :class:`DynamicRNNLayer` .
    decode_sequence_length : tensor for decoder sequence length, see :class:`DynamicRNNLayer` .
    initial_state_encode : None or RNN state (from placeholder or other RNN).
        If None, initial_state_encode is of zero state.
    initial_state_decode : None or RNN state (from placeholder or other RNN).
        If None, initial_state_decode is of the final state of the RNN encoder.
    dropout : `tuple` of `float`: (input_keep_prob, output_keep_prob).
        The input and output keep probability.
    n_layer : an int, default is 1.
        The number of RNN layers.
    return_seq_2d : boolean
        - When return_last = False
        - If True, return 2D Tensor [n_example, n_hidden], for stacking DenseLayer or computing cost after it.
        - If False, return 3D Tensor [n_example/n_steps(max), n_steps(max), n_hidden], for stacking multiple RNN after it.
    name : a string or None
        An optional name to attach to this layer.

    Attributes
    ------------
    outputs : a tensor
        The output of RNN decoder.
    initial_state_encode : a tensor or StateTuple
        Initial state of RNN encoder.
    initial_state_decode : a tensor or StateTuple
        Initial state of RNN decoder.
    final_state_encode : a tensor or StateTuple
        Final state of RNN encoder.
    final_state_decode : a tensor or StateTuple
        Final state of RNN decoder.

    Notes
    --------
    - How to feed data: `Sequence to Sequence Learning with Neural Networks <https://arxiv.org/pdf/1409.3215v3.pdf>`_
    - input_seqs : ``['how', 'are', 'you', '<PAD_ID>']``
    - decode_seqs : ``['<START_ID>', 'I', 'am', 'fine', '<PAD_ID>']``
    - target_seqs : ``['I', 'am', 'fine', '<END_ID>', '<PAD_ID>']``
    - target_mask : ``[1, 1, 1, 1, 0]``
    - related functions : tl.prepro <pad_sequences, precess_sequences, sequences_add_start_id, sequences_get_mask>

    Examples
    ----------
    >>> from tensorlayer.layers import *
    >>> batch_size = 32
    >>> encode_seqs = tf.placeholder(dtype=tf.int64, shape=[batch_size, None], name="encode_seqs")
    >>> decode_seqs = tf.placeholder(dtype=tf.int64, shape=[batch_size, None], name="decode_seqs")
    >>> target_seqs = tf.placeholder(dtype=tf.int64, shape=[batch_size, None], name="target_seqs")
    >>> target_mask = tf.placeholder(dtype=tf.int64, shape=[batch_size, None], name="target_mask") # tl.prepro.sequences_get_mask()
    >>> with tf.variable_scope("model"):
    ...     # for chatbot, you can use the same embedding layer,
    ...     # for translation, you may want to use 2 seperated embedding layers
    >>>     with tf.variable_scope("embedding") as vs:
    >>>         net_encode = EmbeddingInputlayer(
    ...                 inputs = encode_seqs,
    ...                 vocabulary_size = 10000,
    ...                 embedding_size = 200,
    ...                 name = 'seq_embedding')
    >>>         vs.reuse_variables()
    >>>         tl.layers.set_name_reuse(True)
    >>>         net_decode = EmbeddingInputlayer(
    ...                 inputs = decode_seqs,
    ...                 vocabulary_size = 10000,
    ...                 embedding_size = 200,
    ...                 name = 'seq_embedding')
    >>>     net = Seq2Seq(net_encode, net_decode,
    ...             cell_fn = tf.contrib.rnn.BasicLSTMCell,
    ...             n_hidden = 200,
    ...             initializer = tf.random_uniform_initializer(-0.1, 0.1),
    ...             encode_sequence_length = retrieve_seq_length_op2(encode_seqs),
    ...             decode_sequence_length = retrieve_seq_length_op2(decode_seqs),
    ...             initial_state_encode = None,
    ...             dropout = None,
    ...             n_layer = 1,
    ...             return_seq_2d = True,
    ...             name = 'seq2seq')
    >>> net_out = DenseLayer(net, n_units=10000, act=tf.identity, name='output')
    >>> e_loss = tl.cost.cross_entropy_seq_with_mask(logits=net_out.outputs, target_seqs=target_seqs, input_mask=target_mask, return_details=False, name='cost')
    >>> y = tf.nn.softmax(net_out.outputs)
    >>> net_out.print_params(False)


    """

    def __init__(
            self,
            net_encode_in=None,
            net_decode_in=None,
            cell_fn=None,  #tf.nn.rnn_cell.LSTMCell,
            cell_init_args={'state_is_tuple': True},
            n_hidden=256,
            initializer=tf.random_uniform_initializer(-0.1, 0.1),
            encode_sequence_length=None,
            decode_sequence_length=None,
            initial_state_encode=None,
            initial_state_decode=None,
            dropout=None,
            n_layer=1,
            # return_last = False,
            return_seq_2d=False,
            name='seq2seq',
    ):
        Layer.__init__(self, name=name)
        if cell_fn is None:
            raise Exception("Please put in cell_fn")
        if 'GRU' in cell_fn.__name__:
            try:
                cell_init_args.pop('state_is_tuple')
            except:
                pass
        # self.inputs = layer.outputs
        logging.info("  [**] Seq2Seq %s: n_hidden:%d cell_fn:%s dropout:%s n_layer:%d" % (self.name, n_hidden, cell_fn.__name__, dropout, n_layer))

        with tf.variable_scope(name) as vs:  #, reuse=reuse):
            # tl.layers.set_name_reuse(reuse)
            # network = InputLayer(self.inputs, name=name+'/input')
            network_encode = DynamicRNNLayer(
                net_encode_in,
                cell_fn=cell_fn,
                cell_init_args=cell_init_args,
                n_hidden=n_hidden,
                initial_state=initial_state_encode,
                dropout=dropout,
                n_layer=n_layer,
                sequence_length=encode_sequence_length,
                return_last=False,
                return_seq_2d=True,
                name=name + '_encode')
            # vs.reuse_variables()
            # tl.layers.set_name_reuse(True)
            network_decode = DynamicRNNLayer(
                net_decode_in,
                cell_fn=cell_fn,
                cell_init_args=cell_init_args,
                n_hidden=n_hidden,
                initial_state=(network_encode.final_state if initial_state_decode is None else initial_state_decode),
                dropout=dropout,
                n_layer=n_layer,
                sequence_length=decode_sequence_length,
                return_last=False,
                return_seq_2d=return_seq_2d,
                name=name + '_decode')
            self.outputs = network_decode.outputs

            # rnn_variables = tf.get_collection(TF_GRAPHKEYS_VARIABLES, scope=vs.name)

        # Initial state
        self.initial_state_encode = network_encode.initial_state
        self.initial_state_decode = network_decode.initial_state

        # Final state
        self.final_state_encode = network_encode.final_state
        self.final_state_decode = network_decode.final_state

        # self.sequence_length = sequence_length
        self.all_layers = list(network_encode.all_layers)
        self.all_params = list(network_encode.all_params)
        self.all_drop = dict(network_encode.all_drop)

        self.all_layers.extend(list(network_decode.all_layers))
        self.all_params.extend(list(network_decode.all_params))
        self.all_drop.update(dict(network_decode.all_drop))

        self.all_layers.extend([self.outputs])
        # self.all_params.extend( rnn_variables )

        self.all_layers = list_remove_repeat(self.all_layers)
        self.all_params = list_remove_repeat(self.all_params)


class PeekySeq2Seq(Layer):
    """
    Waiting for contribution.
    The :class:`PeekySeq2Seq` class, see `Model <https://camo.githubusercontent.com/7f690d451036938a51e62feb77149c8bb4be6675/687474703a2f2f6936342e74696e797069632e636f6d2f333032617168692e706e67>`_
    and `Learning Phrase Representations using RNN Encoder-Decoder for Statistical Machine Translation <https://arxiv.org/abs/1406.1078>`_ .
    """

    def __init__(
            self,
            net_encode_in=None,
            net_decode_in=None,
            cell_fn=None,  #tf.nn.rnn_cell.LSTMCell,
            cell_init_args={'state_is_tuple': True},
            n_hidden=256,
            initializer=tf.random_uniform_initializer(-0.1, 0.1),
            in_sequence_length=None,
            out_sequence_length=None,
            initial_state=None,
            dropout=None,
            n_layer=1,
            # return_last = False,
            return_seq_2d=False,
            name='peeky_seq2seq',
    ):
        Layer.__init__(self, name=name)
        if cell_fn is None:
            raise Exception("Please put in cell_fn")
        # self.inputs = layer.outputs
        logging.info("PeekySeq2seq %s: n_hidden:%d cell_fn:%s dropout:%s n_layer:%d" % (self.name, n_hidden, cell_fn.__name__, dropout, n_layer))


class AttentionSeq2Seq(Layer):
    """
    Waiting for contribution.
    The :class:`AttentionSeq2Seq` class, see `Model <https://camo.githubusercontent.com/0e2e4e5fb2dd47846c2fe027737a5df5e711df1b/687474703a2f2f6936342e74696e797069632e636f6d2f6132727733642e706e67>`_
    and `Neural Machine Translation by Jointly Learning to Align and Translate <https://arxiv.org/pdf/1409.0473v6.pdf>`_ .
    """

    def __init__(
            self,
            net_encode_in=None,
            net_decode_in=None,
            cell_fn=None,  #tf.nn.rnn_cell.LSTMCell,
            cell_init_args={'state_is_tuple': True},
            n_hidden=256,
            initializer=tf.random_uniform_initializer(-0.1, 0.1),
            in_sequence_length=None,
            out_sequence_length=None,
            initial_state=None,
            dropout=None,
            n_layer=1,
            # return_last = False,
            return_seq_2d=False,
            name='attention_seq2seq',
    ):
        Layer.__init__(self, name=name)
        if cell_fn is None:
            raise Exception("Please put in cell_fn")
        # self.inputs = layer.outputs
        logging.info("PeekySeq2seq %s: n_hidden:%d cell_fn:%s dropout:%s n_layer:%d" % (self.name, n_hidden, cell_fn.__name__, dropout, n_layer))
