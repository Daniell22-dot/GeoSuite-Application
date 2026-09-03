"""
Beacon detection head — YOLO-style grid prediction.
Detects survey beacons (iron pins, concrete pillars, triangles) in plan images.
"""
import numpy as np
from typing import List, Dict, Tuple
from ..ops import conv2d, relu, sigmoid, softmax, nms, max_pool, conv2d_backward, relu_backward, sigmoid_backward
from ..backbone import CNNBackbone
from ..preprocessing import Preprocessor


class BeaconHead:
    def __init__(self, in_channels: int, num_beacon_types: int = 4, grid_size: int = 16):
        self.grid_size = grid_size
        self.num_types = num_beacon_types
        self.proj = self._init_conv(in_channels, 64, 1)
        self.head = self._init_conv(64, 5 + num_beacon_types, 3)

    def _init_conv(self, in_c, out_c, k):
        s = np.sqrt(2.0 / (in_c * k * k))
        return {'w': np.random.randn(out_c, in_c, k, k) * s, 'b': np.zeros(out_c)}

    def forward(self, features: np.ndarray) -> np.ndarray:
        self._proj_in = features.copy()
        x = conv2d(features, self.proj['w'], self.proj['b'], 1, 1)
        self._proj_out = x.copy()
        x = relu(x)
        self._head_in = x.copy()
        x = conv2d(x, self.head['w'], self.head['b'], 1, 1)
        self._head_out = x.copy()
        x = sigmoid(x)
        return x

    def parameters(self):
        return [self.proj['w'], self.proj['b'], self.head['w'], self.head['b']]

    def backward(self, dout: np.ndarray) -> np.ndarray:
        d = sigmoid_backward(dout, self._head_out)
        d, d_hw, d_hb = conv2d_backward(d, self._head_in, self.head['w'], self.head['b'], 1, 1)
        d = relu_backward(d, self._proj_out)
        d, d_pw, d_pb = conv2d_backward(d, self._proj_in, self.proj['w'], self.proj['b'], 1, 1)
        self.grad_pw = d_pw
        self.grad_pb = d_pb
        self.grad_hw = d_hw
        self.grad_hb = d_hb
        return d

    def gradients(self):
        return [self.grad_pw, self.grad_pb, self.grad_hw, self.grad_hb]

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g


class BeaconDetector:
    def __init__(self, grid_size: int = 16, confidence_threshold: float = 0.5,
                 iou_threshold: float = 0.3, num_beacon_types: int = 4):
        self.grid_size = grid_size
        self.conf_thresh = confidence_threshold
        self.iou_thresh = iou_threshold
        self.num_types = num_beacon_types
        self.backbone = CNNBackbone(in_channels=1, base_channels=32)
        self.head = BeaconHead(128, num_beacon_types, grid_size)
        self.preprocessor = Preprocessor(target_size=(512, 512))
        self.type_names = ['iron_pin', 'concrete', 'triangle', 'unknown']

    def predict(self, image: np.ndarray) -> List[Dict]:
        processed, meta = self.preprocessor.process(image)
        if processed.ndim == 2:
            processed = processed[np.newaxis, np.newaxis]
        else:
            processed = processed[np.newaxis].transpose(0, 3, 1, 2)
        features = self.backbone.forward(processed, training=False)
        return self.predict_from_features(features, meta)

    def predict_from_features(self, features: np.ndarray, meta: dict) -> List[Dict]:
        raw_pred = self.head.forward(features)
        S = raw_pred.shape[2]
        detections = self._decode_predictions(raw_pred[0], meta, S)
        keep = nms(
            np.array([[d['x1'], d['y1'], d['x2'], d['y2']] for d in detections]) if detections else np.empty((0, 4)),
            np.array([d['confidence'] for d in detections]) if detections else np.empty(0),
            self.iou_thresh
        )
        return [detections[i] for i in keep]

    def _decode_predictions(self, pred: np.ndarray, meta: dict, S: int = None) -> List[Dict]:
        if S is None:
            S = self.grid_size
        cell_h = meta['original_shape'][0] / S if 'original_shape' in meta else 512 / S
        cell_w = meta['original_shape'][1] / S if 'original_shape' in meta else 512 / S
        detections = []
        pred_reshaped = pred.reshape(S, S, 5 + self.num_types)
        for i in range(S):
            for j in range(S):
                obj_conf = pred_reshaped[i, j, 0]
                if obj_conf < self.conf_thresh:
                    continue
                cx = (j + pred_reshaped[i, j, 1]) * cell_w
                cy = (i + pred_reshaped[i, j, 2]) * cell_h
                w = pred_reshaped[i, j, 3] * cell_w * 2
                h = pred_reshaped[i, j, 4] * cell_h * 2
                type_scores = pred_reshaped[i, j, 5:]
                type_idx = int(np.argmax(type_scores))
                detections.append({
                    'x1': cx - w / 2, 'y1': cy - h / 2,
                    'x2': cx + w / 2, 'y2': cy + h / 2,
                    'center': (float(cx), float(cy)),
                    'confidence': float(obj_conf),
                    'type': self.type_names[type_idx],
                    'type_confidence': float(type_scores[type_idx]),
                })
        return detections

    def parameters(self):
        return self.backbone.parameters() + self.head.parameters()

    def update(self, lr: float):
        self.backbone.update(lr)
        self.head.update(lr, [np.zeros_like(p) for p in self.head.parameters()])

    def compute_loss(self, pred: np.ndarray, target: np.ndarray,
                     lambda_coord: float = 5.0, lambda_noobj: float = 0.5) -> float:
        S = self.grid_size
        pred_reshaped = pred.reshape(-1, S, S, 5 + self.num_types)
        obj_mask = target[..., 0] == 1
        noobj_mask = target[..., 0] == 0
        coord_loss = lambda_coord * np.sum((pred_reshaped[obj_mask, 1:3] - target[obj_mask, 1:3]) ** 2)
        size_loss = lambda_coord * np.sum(
            (np.sqrt(np.maximum(pred_reshaped[obj_mask, 3:5], 0)) -
             np.sqrt(np.maximum(target[obj_mask, 3:5], 0))) ** 2
        )
        class_loss = np.sum(-target[obj_mask, 5:] * np.log(np.clip(pred_reshaped[obj_mask, 5:], 1e-8, 1.0)))
        noobj_loss = lambda_noobj * np.sum(pred_reshaped[noobj_mask, 0] ** 2)
        return coord_loss + size_loss + class_loss + noobj_loss

    def save_weights(self, path: str):
        self.backbone.save_weights(path + '_backbone.npz')
        weights = {f'head_{i}': p for i, p in enumerate(self.head.parameters())}
        np.savez_compressed(path + '_head.npz', **weights)

    def load_weights(self, path: str):
        self.backbone.load_weights(path + '_backbone.npz')
        data = np.load(path + '_head.npz')
        for i, p in enumerate(self.head.parameters()):
            p[:] = data[f'head_{i}']
