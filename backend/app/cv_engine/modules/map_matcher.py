"""
Map matcher — snap noisy GPS tracks to known roads/paths.
Uses rasterized road probability + Viterbi decoding.
"""
import numpy as np
from typing import Dict, List, Tuple
from ..ops import conv2d, relu, softmax


class MapMatcher:
    def __init__(self, road_probability_threshold: float = 0.5):
        self.threshold = road_probability_threshold
        self.conv1_w = np.random.randn(16, 2, 3, 3) * np.sqrt(2.0 / 18)
        self.conv1_b = np.zeros(16)
        self.conv2_w = np.random.randn(8, 16, 3, 3) * np.sqrt(2.0 / (16 * 9))
        self.conv2_b = np.zeros(8)
        self.road_w = np.random.randn(1, 8, 3, 3) * np.sqrt(2.0 / (8 * 9))
        self.road_b = np.zeros(1)

    def match(self, gps_points: np.ndarray, road_network: np.ndarray = None,
              extent: Tuple[float, float, float, float] = None) -> Dict:
        n_points = len(gps_points)
        if road_network is not None and extent is not None:
            road_prob = self._compute_road_probability(gps_points, road_network, extent)
        else:
            road_prob = self._estimate_road_probability(gps_points)
        matched = self._viterbi_decode(gps_points, road_prob)
        total_dist = 0.0
        for i in range(1, len(matched)):
            dx = matched[i][0] - matched[i - 1][0]
            dy = matched[i][1] - matched[i - 1][1]
            total_dist += np.sqrt(dx ** 2 + dy ** 2)
        snap_distances = []
        for orig, snapped in zip(gps_points, matched):
            snap_distances.append(float(np.sqrt((orig[0] - snapped[0]) ** 2 + (orig[1] - snapped[1]) ** 2)))
        return {
            'matched_points': matched,
            'total_distance': total_dist,
            'snap_distances': snap_distances,
            'max_snap_distance': max(snap_distances) if snap_distances else 0,
            'avg_snap_distance': float(np.mean(snap_distances)) if snap_distances else 0,
            'num_points': n_points,
        }

    def _compute_road_probability(self, gps_points: np.ndarray, road_network: np.ndarray,
                                   extent: Tuple[float, float, float, float]) -> np.ndarray:
        xmin, ymin, xmax, ymax = extent
        h, w = road_network.shape[:2] if road_network.ndim == 3 else (256, 256)
        probs = np.zeros(len(gps_points))
        for idx, (lon, lat) in enumerate(gps_points):
            col = int((lon - xmin) / (xmax - xmin) * (w - 1))
            row = int((lat - ymin) / (ymax - ymin) * (h - 1))
            col = max(0, min(col, w - 1))
            row = max(0, min(row, h - 1))
            if road_network.ndim == 3:
                probs[idx] = float(np.max(road_network[row, col]))
            else:
                probs[idx] = float(road_network[row, col])
        return probs

    def _estimate_road_probability(self, gps_points: np.ndarray) -> np.ndarray:
        n = len(gps_points)
        probs = np.ones(n) * 0.5
        if n < 3:
            return probs
        for i in range(1, n - 1):
            dx1 = gps_points[i][0] - gps_points[i - 1][0]
            dy1 = gps_points[i][1] - gps_points[i - 1][1]
            dx2 = gps_points[i + 1][0] - gps_points[i][0]
            dy2 = gps_points[i + 1][1] - gps_points[i][1]
            angle_change = abs(np.arctan2(dy2, dx2) - np.arctan2(dy1, dx1))
            angle_change = min(angle_change, 2 * np.pi - angle_change)
            probs[i] = max(0.1, 1.0 - angle_change / np.pi)
        return probs

    def _viterbi_decode(self, gps_points: np.ndarray, road_prob: np.ndarray,
                        snap_range: float = 0.001, n_states: int = 5) -> list:
        n = len(gps_points)
        snap_offsets = np.linspace(-snap_range, snap_range, n_states)
        V = np.zeros((n, n_states))
        path_back = np.zeros((n, n_states), dtype=int)
        for s in range(n_states):
            offset = snap_offsets[s]
            V[0, s] = -offset ** 2
        for t in range(1, n):
            for s in range(n_states):
                offset = snap_offsets[s]
                best_val = -np.inf
                best_prev = 0
                for ps in range(n_states):
                    prev_offset = snap_offsets[ps]
                    transition_cost = -((offset - prev_offset) ** 2)
                    observation_cost = road_prob[t] * (-offset ** 2) - (1 - road_prob[t]) * (offset ** 2)
                    val = V[t - 1, ps] + transition_cost + observation_cost
                    if val > best_val:
                        best_val = val
                        best_prev = ps
                V[t, s] = best_val
                path_back[t, s] = best_prev
        best_last = np.argmax(V[n - 1])
        best_path = [0] * n
        best_path[n - 1] = best_last
        for t in range(n - 2, -1, -1):
            best_path[t] = path_back[t + 1, best_path[t + 1]]
        matched = []
        for t in range(n):
            offset = snap_offsets[best_path[t]]
            matched.append((gps_points[t][0] + offset, gps_points[t][1] + offset))
        return matched

    def parameters(self):
        return [self.conv1_w, self.conv1_b, self.conv2_w, self.conv2_b, self.road_w, self.road_b]

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g

    def save_weights(self, path: str):
        np.savez_compressed(path, **{f'p_{i}': p for i, p in enumerate(self.parameters())})

    def load_weights(self, path: str):
        data = np.load(path)
        for i, p in enumerate(self.parameters()):
            p[:] = data[f'p_{i}']
