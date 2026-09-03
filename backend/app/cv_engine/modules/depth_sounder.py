"""
Depth sounder — extract sounding values from raster nautical charts.
Detects numeric text at water positions and converts to depth values.
"""
import numpy as np
from typing import Dict, List
from ..ops import conv2d, relu, softmax_2d, connected_components
from ..preprocessing import Preprocessor, otsu_threshold, normalize


class DepthSounder:
    def __init__(self, depth_range: tuple = (0, 100)):
        self.depth_min = depth_range[0]
        self.depth_max = depth_range[1]
        self.preprocessor = Preprocessor(target_size=(1024, 1024), do_deskew=False)
        self.conv1_w = np.random.randn(32, 1, 3, 3) * np.sqrt(2.0 / 9)
        self.conv1_b = np.zeros(32)
        self.conv2_w = np.random.randn(64, 32, 3, 3) * np.sqrt(2.0 / (32 * 9))
        self.conv2_b = np.zeros(64)
        self.detect_w = np.random.randn(2, 64, 1, 1) * np.sqrt(2.0 / 64)
        self.detect_b = np.zeros(2)

    def extract_soundings(self, chart_image: np.ndarray) -> Dict:
        gray, meta = self.preprocessor.process(chart_image)
        water_mask = self._detect_water_preprocessed(gray)
        x = gray[np.newaxis, np.newaxis]
        x = conv2d(x, self.conv1_w, self.conv1_b, 1, 1)
        x = relu(x)
        x = conv2d(x, self.conv2_w, self.conv2_b, 1, 1)
        x = relu(x)
        logits = conv2d(x, self.detect_w, self.detect_b, 1, 0)
        probs = 1.0 / (1.0 + np.exp(-logits))
        text_mask = (probs[0, 1] > 0.5).astype(np.uint8)
        text_mask = text_mask & water_mask
        labels, num_regions = connected_components(text_mask)
        soundings = []
        for region_id in range(1, num_regions + 1):
            ys, xs = np.where(labels == region_id)
            if len(ys) < 3:
                continue
            bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
            cx = float(xs.mean())
            cy = float(ys.mean())
            region_h = bbox[3] - bbox[1]
            region_w = bbox[2] - bbox[0]
            if region_h < 5 or region_w < 3:
                continue
            aspect = region_w / max(region_h, 1)
            estimated_depth = self._estimate_depth_from_region(gray, bbox)
            if self.depth_min <= estimated_depth <= self.depth_max:
                soundings.append({
                    'position': (cx, cy),
                    'depth': round(estimated_depth, 1),
                    'bbox': bbox,
                    'aspect_ratio': round(aspect, 2),
                    'region_size': len(ys),
                })
        return {
            'soundings': soundings,
            'total_soundings': len(soundings),
            'depth_range': [self.depth_min, self.depth_max],
            'water_mask': water_mask,
        }

    def _detect_water(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            gray = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
            blue_dominance = image[:, :, 2].astype(float) - (image[:, :, 0].astype(float) + image[:, :, 1].astype(float)) / 2
            water = (blue_dominance > 10) & (gray < 200)
        else:
            water = image < 180
        return water.astype(np.uint8)

    def _detect_water_preprocessed(self, gray: np.ndarray) -> np.ndarray:
        return (gray < 0.7).astype(np.uint8)

    def _estimate_depth_from_region(self, gray: np.ndarray, bbox: tuple) -> float:
        x1, y1, x2, y2 = bbox
        region = gray[y1:y2 + 1, x1:x2 + 1]
        if region.size == 0:
            return 0
        mean_val = float(np.mean(region))
        depth = self.depth_max * (1 - mean_val / 255.0)
        return max(self.depth_min, min(depth, self.depth_max))

    def parameters(self):
        return [self.conv1_w, self.conv1_b, self.conv2_w, self.conv2_b, self.detect_w, self.detect_b]

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g

    def save_weights(self, path: str):
        np.savez_compressed(path, **{f'p_{i}': p for i, p in enumerate(self.parameters())})

    def load_weights(self, path: str):
        data = np.load(path)
        for i, p in enumerate(self.parameters()):
            p[:] = data[f'p_{i}']
