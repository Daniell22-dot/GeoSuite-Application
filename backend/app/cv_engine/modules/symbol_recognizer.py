"""
Symbol recognizer — detect map symbols (benchmarks, beacons, arrows, scale bars).
YOLO-style detection with small anchor boxes.
"""
import numpy as np
from typing import List, Dict
from ..ops import conv2d, relu, sigmoid, nms
from ..backbone import CNNBackbone
from ..preprocessing import Preprocessor


class SymbolRecognizer:
    SYMBOL_CLASSES = [
        'benchmark', 'beacon', 'north_arrow', 'scale_bar', 'grid_reference',
        'contour_label', 'title_block', 'boundary_stone', 'cement_marker', 'iron_pin'
    ]

    def __init__(self, confidence_threshold: float = 0.4):
        self.conf_thresh = confidence_threshold
        self.num_classes = len(self.SYMBOL_CLASSES)
        self.backbone = CNNBackbone(in_channels=1, base_channels=32)
        self.head_w = np.random.randn(self.num_classes + 5, 128, 1, 1) * np.sqrt(2.0 / 128)
        self.head_b = np.zeros(self.num_classes + 5)
        self.preprocessor = Preprocessor(target_size=(256, 256))

    def recognize(self, image: np.ndarray) -> List[Dict]:
        processed, meta = self.preprocessor.process(image)
        if processed.ndim == 2:
            x = processed[np.newaxis, np.newaxis]
        else:
            x = processed[np.newaxis].transpose(0, 3, 1, 2)
        features = self.backbone.forward(x, training=False)
        N, C, H, W = features.shape
        pred = conv2d(features, self.head_w, self.head_b, 1, 0)
        obj_logits = pred[:, 0:1, :, :]
        bbox_logits = pred[:, 1:5, :, :]
        cls_logits = pred[:, 5:, :, :]
        obj = 1.0 / (1.0 + np.exp(-obj_logits))
        bbox = 1.0 / (1.0 + np.exp(-bbox_logits))
        cls = self._softmax_2d(cls_logits)
        pred_activated = np.concatenate([obj, bbox, cls], axis=1)
        detections = self._decode(pred_activated[0], meta)
        if detections:
            boxes = np.array([[d['x1'], d['y1'], d['x2'], d['y2']] for d in detections])
            scores = np.array([d['confidence'] for d in detections])
            keep = nms(boxes, scores, 0.3)
            return [detections[i] for i in keep]
        return []

    @staticmethod
    def _softmax_2d(x: np.ndarray) -> np.ndarray:
        x = x - np.max(x, axis=1, keepdims=True)
        e = np.exp(x)
        return e / (np.sum(e, axis=1, keepdims=True) + 1e-8)

    def _decode(self, pred: np.ndarray, meta: dict) -> List[Dict]:
        C, H, W = pred.shape
        detections = []
        cell_h = meta['original_shape'][0] / H if 'original_shape' in meta else 256 / H
        cell_w = meta['original_shape'][1] / W if 'original_shape' in meta else 256 / W
        for i in range(H):
            for j in range(W):
                obj_conf = pred[0, i, j]
                if obj_conf < self.conf_thresh:
                    continue
                cx = (j + pred[1, i, j]) * cell_w
                cy = (i + pred[2, i, j]) * cell_h
                w = pred[3, i, j] * cell_w * 2
                h = pred[4, i, j] * cell_h * 2
                class_scores = pred[5:, i, j]
                class_idx = int(np.argmax(class_scores))
                detections.append({
                    'x1': cx - w / 2, 'y1': cy - h / 2,
                    'x2': cx + w / 2, 'y2': cy + h / 2,
                    'center': (float(cx), float(cy)),
                    'confidence': float(obj_conf * class_scores[class_idx]),
                    'symbol_type': self.SYMBOL_CLASSES[class_idx],
                    'class_scores': {self.SYMBOL_CLASSES[k]: float(v) for k, v in enumerate(class_scores)},
                })
        return detections

    def parameters(self):
        return [self.head_w, self.head_b]

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g

    def save_weights(self, path: str):
        self.backbone.save_weights(path + '_backbone.npz')
        np.savez_compressed(path + '_head.npz', head_w=self.head_w, head_b=self.head_b)

    def load_weights(self, path: str):
        self.backbone.load_weights(path + '_backbone.npz')
        data = np.load(path + '_head.npz')
        self.head_w[:] = data['head_w']
        self.head_b[:] = data['head_b']
