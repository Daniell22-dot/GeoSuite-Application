"""
Land use classifier — multi-spectral satellite imagery classification.
Classifies: urban, agriculture, forest, water, wetland, barren, grassland.
"""
import numpy as np
from typing import Dict
from ..ops import conv2d, relu, softmax_2d
from ..backbone import CNNBackbone
from ..preprocessing import Preprocessor


class LandUseClassifier:
    CLASSES = ['urban', 'agriculture', 'forest', 'water', 'wetland', 'barren', 'grassland']
    NUM_CLASSES = len(CLASSES)

    def __init__(self, num_bands: int = 3, num_classes: int = 7):
        self.num_classes = num_classes
        self.backbone = CNNBackbone(in_channels=num_bands, base_channels=32)
        self.pool = lambda x: np.mean(x, axis=(2, 3))
        self.fc1_w = np.random.randn(128, 64) * np.sqrt(2.0 / 128)
        self.fc1_b = np.zeros(64)
        self.fc2_w = np.random.randn(64, num_classes) * np.sqrt(2.0 / 64)
        self.fc2_b = np.zeros(num_classes)
        self.preprocessor = Preprocessor(target_size=(256, 256))

    def classify(self, image: np.ndarray) -> Dict:
        processed, meta = self.preprocessor.process(image)
        if processed.ndim == 2:
            processed = np.stack([processed] * 3, axis=-1)
        x = processed[np.newaxis].transpose(0, 3, 1, 2)
        features = self.backbone.forward(x, training=False)
        pooled = self.pool(features)
        h = relu(pooled @ self.fc1_w + self.fc1_b)
        logits = h @ self.fc2_w + self.fc2_b
        probs = 1.0 / (1.0 + np.exp(-logits))
        probs = probs / probs.sum(axis=1, keepdims=True)
        class_idx = int(np.argmax(probs))
        pixel_map = self._generate_pixel_map(features, image.shape[:2])
        return {
            'dominant_class': self.CLASSES[class_idx],
            'class_probabilities': {self.CLASSES[i]: round(float(probs[0, i]), 4) for i in range(self.num_classes)},
            'pixel_classification_map': pixel_map,
            'class_names': self.CLASSES,
        }

    def _generate_pixel_map(self, features: np.ndarray, target_shape: tuple) -> np.ndarray:
        C, H, W = features.shape[1], features.shape[2], features.shape[3]
        simplified = features[0, :self.num_classes, :, :self.num_classes]
        if simplified.shape[0] < self.num_classes:
            pad = np.zeros((self.num_classes - simplified.shape[0], simplified.shape[1], simplified.shape[2]))
            simplified = np.concatenate([simplified, pad], axis=0)
        class_map = np.argmax(simplified, axis=0).astype(np.uint8)
        th, tw = class_map.shape
        h, w = target_shape
        row_idx = (np.arange(h) * th / h).astype(int)
        col_idx = (np.arange(w) * tw / w).astype(int)
        return class_map[np.ix_(row_idx, col_idx)]

    def parameters(self):
        return self.backbone.parameters() + [self.fc1_w, self.fc1_b, self.fc2_w, self.fc2_b]

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g

    def save_weights(self, path: str):
        self.backbone.save_weights(path + '_backbone.npz')
        np.savez_compressed(path + '_fc.npz',
                            fc1_w=self.fc1_w, fc1_b=self.fc1_b,
                            fc2_w=self.fc2_w, fc2_b=self.fc2_b)

    def load_weights(self, path: str):
        self.backbone.load_weights(path + '_backbone.npz')
        data = np.load(path + '_fc.npz')
        self.fc1_w[:] = data['fc1_w']
        self.fc1_b[:] = data['fc1_b']
        self.fc2_w[:] = data['fc2_w']
        self.fc2_b[:] = data['fc2_b']
