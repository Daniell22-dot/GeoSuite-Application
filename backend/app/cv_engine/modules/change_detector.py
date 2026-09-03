"""
Change detection — compare two images of the same area over time.
Detects new buildings, demolitions, vegetation loss, boundary shifts.
"""
import numpy as np
from typing import Dict, List
from ..ops import conv2d, relu, sigmoid, connected_components
from ..preprocessing import Preprocessor


class ChangeDetector:
    CHANGE_TYPES = [
        'new_building', 'demolished', 'vegetation_loss', 'vegetation_gain',
        'road_new', 'road_removed', 'water_new', 'water_lost', 'boundary_shift', 'none'
    ]

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        self.preprocessor = Preprocessor(target_size=(256, 256))
        self.diff_w1 = np.random.randn(32, 6, 3, 3) * np.sqrt(2.0 / (6 * 9))
        self.diff_b1 = np.zeros(32)
        self.diff_w2 = np.random.randn(16, 32, 3, 3) * np.sqrt(2.0 / (32 * 9))
        self.diff_b2 = np.zeros(16)
        self.class_w = np.random.randn(10, 16, 3, 3) * np.sqrt(2.0 / (16 * 9))
        self.class_b = np.zeros(10)

    def detect(self, image_t1: np.ndarray, image_t2: np.ndarray) -> Dict:
        proc1, meta1 = self.preprocessor.process(image_t1)
        proc2, meta2 = self.preprocessor.process(image_t2)
        if proc1.ndim == 2:
            proc1 = np.stack([proc1] * 3, axis=-1)
        if proc2.ndim == 2:
            proc2 = np.stack([proc2] * 3, axis=-1)
        x1 = proc1[np.newaxis].transpose(0, 3, 1, 2)
        x2 = proc2[np.newaxis].transpose(0, 3, 1, 2)
        diff_input = np.concatenate([x1, x2], axis=1)
        x = conv2d(diff_input, self.diff_w1, self.diff_b1, 1, 1)
        x = relu(x)
        x = conv2d(x, self.diff_w2, self.diff_b2, 1, 1)
        x = relu(x)
        logits = conv2d(x, self.class_w, self.class_b, 1, 1)
        probs = 1.0 / (1.0 + np.exp(-logits))
        change_map = np.argmax(probs[0], axis=0).astype(np.uint8)
        h, w = change_map.shape
        change_map_resized = self._resize_nearest(change_map, image_t1.shape[0], image_t1.shape[1])
        change_regions = self._extract_regions(change_map_resized, probs[0])
        stats = self._compute_statistics(change_map, image_t1.shape[0] * image_t1.shape[1])
        return {
            'change_map': change_map_resized,
            'change_regions': change_regions,
            'statistics': stats,
            'num_classes': 10,
            'class_names': self.CHANGE_TYPES,
        }

    def _resize_nearest(self, arr: np.ndarray, new_h: int, new_w: int) -> np.ndarray:
        h, w = arr.shape
        row_idx = (np.arange(new_h) * h / new_h).astype(int)
        col_idx = (np.arange(new_w) * w / new_w).astype(int)
        return arr[np.ix_(row_idx, col_idx)]

    def _extract_regions(self, change_map: np.ndarray, probs: np.ndarray) -> List[Dict]:
        regions = []
        for c in range(1, probs.shape[0]):
            binary = (change_map == c).astype(np.uint8)
            labels, num = connected_components(binary)
            for region_id in range(1, num + 1):
                ys, xs = np.where(labels == region_id)
                if len(ys) < 10:
                    continue
                areas = len(ys)
                bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
                cx, cy = float(xs.mean()), float(ys.mean())
                regions.append({
                    'class': self.CHANGE_TYPES[c],
                    'class_id': c,
                    'area_pixels': areas,
                    'bbox': bbox,
                    'centroid': (cx, cy),
                    'confidence': float(probs[c, ys[0], xs[0]]),
                })
        return regions

    def _compute_statistics(self, change_map: np.ndarray, total_pixels: int) -> Dict:
        stats = {}
        for c in range(10):
            count = int(np.sum(change_map == c))
            stats[self.CHANGE_TYPES[c]] = {
                'pixels': count,
                'percent': round(count / total_pixels * 100, 2),
            }
        return stats

    def parameters(self):
        return [self.diff_w1, self.diff_b1, self.diff_w2, self.diff_b2, self.class_w, self.class_b]

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g

    def save_weights(self, path: str):
        np.savez_compressed(path, **{f'p_{i}': p for i, p in enumerate(self.parameters())})

    def load_weights(self, path: str):
        data = np.load(path)
        for i, p in enumerate(self.parameters()):
            p[:] = data[f'p_{i}']
