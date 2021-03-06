# -*- coding: utf-8 -*-

import numpy as np
import tensorflow as tf
from six.moves import xrange

from . import cost, files, iterate, ops, utils, visualize
from .core import *


class ROIPoolingLayer(Layer):
    """
    The :class:`ROIPoolingLayer` class is Region of interest pooling layer.

    Parameters
    -----------
    layer : a :class:`Layer` instance
        The `Layer` class feeding into this layer, the feature maps on which to perform the pooling operation
    rois : list of regions of interest in the format (feature map index, upper left, bottom right)
    pool_width : int, size of the pooling sections.
    pool_width : int, size of the pooling sections.

    Notes
    -----------
    - This implementation is from `Deepsense-AI <https://github.com/deepsense-ai/roi-pooling>`_ .
    - Please install it by the instruction `HERE <https://github.com/zsdonghao/tensorlayer/blob/master/tensorlayer/third_party/roi_pooling/README.md>`_.
    """

    def __init__(
            self,
            #inputs = None,
            layer=None,
            rois=None,
            pool_height=2,
            pool_width=2,
            name='roipooling_layer',
    ):
        Layer.__init__(self, name=name)
        self.inputs = layer.outputs
        logging.info("ROIPoolingLayer %s: (%d, %d)" % (self.name, pool_height, pool_width))
        try:
            from tensorlayer.third_party.roi_pooling.roi_pooling.roi_pooling_ops import roi_pooling
        except Exception as e:
            logging.info(e)
            logging.info("\nHINT: \n1. https://github.com/deepsense-ai/roi-pooling  \n2. tensorlayer/third_party/roi_pooling\n")
        self.outputs = roi_pooling(self.inputs, rois, pool_height, pool_width)

        self.all_layers = list(layer.all_layers)
        self.all_params = list(layer.all_params)
        self.all_drop = dict(layer.all_drop)
        self.all_layers.extend([self.outputs])
