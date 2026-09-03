"""
Feature extraction head — semantic segmentation for drone/satellite imagery.
Classifies: building, road, vegetation, bare_soil, water, roof_type.
"""
import numpy as np
from typing import Dict
from ..ops import conv2d, relu, upsample_2x, softmax_2d
from ..ops import conv2d_backward, relu_backward, upsample_2x_backward
from ..backbone import CNNBackbone
from ..preprocessing import Preprocessor


class FeatureDecoder:
    def __init__(self, in_ch: int, skip_ch: int, out_ch: int):
        s = np.sqrt(2.0 / (in_ch * 9))
        self.up_w = np.random.randn(in_ch, in_ch, 3, 3) * s
        self.up_b = np.zeros(in_ch)
        self.concat_w = np.random.randn(out_ch, in_ch + skip_ch, 3, 3) * s * 0.5
        self.concat_b = np.zeros(out_ch)

    def forward(self, x: np.ndarray, skip: np.ndarray) -> np.ndarray:
        self._input_shape = x.shape
        self._skip_shape = skip.shape
        x = upsample_2x(x)
        self._upsampled = x.copy()
        x = conv2d(x, self.up_w, self.up_b, 1, 1)
        self._conv1_out_pre_relu = x.copy()
        x = relu(x)
        self._conv1_out = x.copy()
        x = x[:, :, :skip.shape[2], :skip.shape[3]]
        self._concat_in = x.copy()
        x = np.concatenate([x, skip], axis=1)
        self._concat_out = x.copy()
        x = conv2d(x, self.concat_w, self.concat_b, 1, 1)
        self._conv2_out_pre_relu = x.copy()
        x = relu(x)
        return x

    def backward(self, dout: np.ndarray, skip: np.ndarray) -> np.ndarray:
        dout = relu_backward(dout, self._conv2_out_pre_relu)
        dconcat, d_w2, d_b2 = conv2d_backward(dout, self._concat_out, self.concat_w, self.concat_b, 1, 1)
        self.grad_w2 = d_w2
        self.grad_b2 = d_b2
        d_in_concat = dconcat[:, :self._concat_in.shape[1], :, :]
        d_skip = dconcat[:, self._concat_in.shape[1]:, :, :]
        if d_in_concat.shape[2:] != self._conv1_out.shape[2:]:
            pad_h = self._conv1_out.shape[2] - d_in_concat.shape[2]
            pad_w = self._conv1_out.shape[3] - d_in_concat.shape[3]
            d_in_concat = np.pad(d_in_concat, ((0,0),(0,0),(0,pad_h),(0,pad_w)), mode='constant')
        dout = relu_backward(d_in_concat, self._conv1_out_pre_relu)
        d_up, d_w1, d_b1 = conv2d_backward(dout, self._upsampled, self.up_w, self.up_b, 1, 1)
        self.grad_w1 = d_w1
        self.grad_b1 = d_b1
        d_upsampled = upsample_2x_backward(d_up, self._input_shape[2], self._input_shape[3])
        return d_upsampled, d_skip

    def parameters(self):
        return [self.up_w, self.up_b, self.concat_w, self.concat_b]

    def gradients(self):
        return [self.grad_w1, self.grad_b1, self.grad_w2, self.grad_b2]


class FeatureExtractor:
    CLASSES = ['background', 'building', 'road', 'vegetation', 'bare_soil', 'water', 'roof_iron', 'roof_mud', 'roof_tile']
    NUM_CLASSES = len(CLASSES)

    def __init__(self, num_classes: int = 9):
        self.num_classes = num_classes
        self.backbone = CNNBackbone(in_channels=3, base_channels=32)
        self.dec1 = FeatureDecoder(128, 128, 64)
        self.dec2 = FeatureDecoder(64, 64, 32)
        self.dec3 = FeatureDecoder(32, 32, 16)
        self.final_w = np.random.randn(num_classes, 16, 3, 3) * np.sqrt(2.0 / (16 * 9))
        self.final_b = np.zeros(num_classes)
        self.preprocessor = Preprocessor(target_size=(512, 512))

    def predict(self, image: np.ndarray) -> Dict:
        processed, meta = self.preprocessor.process(image)
        if processed.ndim == 2:
            processed = np.stack([processed] * 3, axis=-1)
        x = processed[np.newaxis].transpose(0, 3, 1, 2)
        features = self.backbone.forward(x, training=False)
        skips = self.backbone.get_skip_connections()
        d1 = self.dec1.forward(features, skips[2])
        d2 = self.dec2.forward(d1, skips[1])
        d3 = self.dec3.forward(d2, skips[0])
        logits = conv2d(d3, self.final_w, self.final_b, 1, 1)
        probs = softmax_2d(logits)[0]
        seg_map = np.argmax(probs, axis=0).astype(np.uint8)
        class_areas = {}
        total_pixels = seg_map.size
        for c in range(self.num_classes):
            class_areas[self.CLASSES[c]] = float(np.sum(seg_map == c) / total_pixels * 100)
        return {
            'segmentation_map': seg_map,
            'probabilities': probs,
            'class_areas_percent': class_areas,
            'num_classes': self.num_classes,
            'class_names': self.CLASSES,
            'original_shape': meta.get('original_shape', image.shape),
        }

    def parameters(self):
        params = self.backbone.parameters()
        params += self.dec1.parameters() + self.dec2.parameters() + self.dec3.parameters()
        params += [self.final_w, self.final_b]
        return params

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g

    def save_weights(self, path: str):
        self.backbone.save_weights(path + '_backbone.npz')
        weights = {}
        for i, p in enumerate(self.dec1.parameters() + self.dec2.parameters() + self.dec3.parameters()):
            weights[f'dec_{i}'] = p
        weights['final_w'] = self.final_w
        weights['final_b'] = self.final_b
        np.savez_compressed(path + '_decoder.npz', **weights)

    def load_weights(self, path: str):
        self.backbone.load_weights(path + '_backbone.npz')
        data = np.load(path + '_decoder.npz')
        dec_params = self.dec1.parameters() + self.dec2.parameters() + self.dec3.parameters()
        for i, p in enumerate(dec_params):
            p[:] = data[f'dec_{i}']
        self.final_w[:] = data['final_w']
        self.final_b[:] = data['final_b']
