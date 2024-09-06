'''
This file is adapted from the opico-server project (formally known as Spaghetti Detective).
Link: https://github.com/TheSpaghettiDetective/obico-server/tree/release
'''

#!python3

# pylint: disable=R, W0401, W0614, W0703
from lib.meta import Meta
from os import path
from lib.onnx import OnnxNet

alt_names = None
onnx_ready = True

def load_net(config_path, meta_path, weights_path=None):
    def try_loading_net(net_config_priority):
        for net_config in net_config_priority:
            weights = net_config['weights_path']
            use_gpu = net_config['use_gpu']
            net_main = None
            try:
                print(f'----- Trying to load weights: {weights} - use_gpu = {use_gpu} -----')
                if weights.endswith(".onnx"):
                    if not onnx_ready:
                        raise Exception('Not loading ONNX net due to previous import failure. Check earlier log for errors.')
                    net_main = OnnxNet(weights, meta_path, use_gpu)
                else:
                    raise Exception(f'Can not recognize net from weights file surfix: {weights}')
                print('Succeeded!')
                return net_main
            except Exception as e:
                print(f'Failed! - {e}')

        raise Exception(f'Failed to load any net after trying: {net_config_priority}')

    global alt_names  # pylint: disable=W0603

    model_dir = path.join(path.dirname(path.realpath(__file__)), '..', 'model')
    net_config_priority = [
            dict(weights_path=path.join(model_dir, 'model-weights.onnx'), use_gpu=True),
            dict(weights_path=path.join(model_dir, 'model-weights.onnx'), use_gpu=False),
        ]
    if weights_path is not None:
        net_config_priority = [ dict(weights_path=weights_path, use_gpu=True), dict(weights_path=weights_path, use_gpu=False) ]

    net_main = try_loading_net(net_config_priority)

    if alt_names is None:
        # In Python 3, the metafile default access craps out on Windows (but not Linux)
        # Read the names file and create a list to feed to detect
        try:
            meta = Meta(meta_path)
            alt_names = meta.names
        except Exception:
            pass

    return net_main

def detect(net, image, thresh=.5, hier_thresh=.5, nms=.45, debug=False):
    return net.detect(net.meta, image, alt_names, thresh, hier_thresh, nms, debug)
