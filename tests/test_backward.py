import sys
sys.path.insert(0, r'D:\Geospatial_suite\backend')
import numpy as np
from app.cv_engine.ops import (
    conv2d, conv2d_backward, relu, relu_backward,
    max_pool, max_pool_backward, upsample_2x, upsample_2x_backward,
    softmax_2d, softmax_2d_backward
)

x = np.random.randn(1, 1, 32, 32)
w = np.random.randn(4, 1, 3, 3) * 0.1
b = np.zeros(4)

out = conv2d(x, w, b, 1, 1)
dout = np.random.randn(*out.shape)
dinp, dw, db = conv2d_backward(dout, x, w, b, 1, 1)
print('conv2d:', dinp.shape, dw.shape, db.shape)

pooled = max_pool(x, 2, 2)
dp = max_pool_backward(np.random.randn(*pooled.shape), x, 2, 2)
print('maxpool:', dp.shape)

up = upsample_2x(x)
dup = upsample_2x_backward(np.random.randn(*up.shape), x.shape[2], x.shape[3])
print('upsample:', dup.shape)

sm = softmax_2d(np.random.randn(1, 5, 8, 8))
dsm = softmax_2d_backward(np.random.randn(*sm.shape), sm)
print('softmax_2d:', dsm.shape)

from app.cv_engine.backbone import CNNBackbone
backbone = CNNBackbone(in_channels=1, base_channels=16)
img = np.random.randn(1, 1, 64, 64)
features = backbone.forward(img, training=True)
skips = backbone.get_skip_connections()
print('backbone features:', features.shape)
for i, s in enumerate(skips):
    print(f'  skip{i}: {s.shape}')

dout = np.random.randn(*features.shape)
backbone.backward(dout)

from app.cv_engine.training.train import collect_backbone_grads
all_params = backbone.parameters()
all_grads = collect_backbone_grads(backbone)
assert len(all_params) == len(all_grads), f"params={len(all_params)} grads={len(all_grads)}"
has_grad = sum(1 for g in all_grads if np.any(g != 0))
print(f'backbone grads: {has_grad}/{len(all_grads)} nonzero')
print('ALL BACKWARD TESTS PASSED')
