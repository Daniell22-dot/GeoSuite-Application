"""
Traditional CV digitizer — works without neural network training.
Uses classical computer vision techniques:
  - Adaptive thresholding for text/beacon detection
  - Morphological operations for line/boundary detection
  - Connected components for region detection
  - Hough-like line detection for boundaries
  - Template matching for beacon markers
"""
import numpy as np
from typing import Dict, List, Tuple
from ..ops import connected_components, douglas_peucker, nms, compute_iou
from ..preprocessing import (
    rgb_to_grayscale, normalize, adaptive_threshold_niblack,
    otsu_threshold, canny_edges, gaussian_blur,
    morphological_erode, morphological_dilate, morphological_open, morphological_close,
    resize_bilinear
)


class TraditionalDigitizer:
    def __init__(self):
        self.min_beacon_area = 20
        self.max_beacon_area = 400
        self.min_beacon_fill = 0.35
        self.min_line_length = 30
        self.max_line_gap = 10
        self.text_min_chars = 2

    def digitize(self, image: np.ndarray) -> Dict:
        if image.ndim == 3:
            gray = rgb_to_grayscale(image)
        else:
            gray = image.astype(np.float64)

        beacons = self._detect_beacons(gray)
        boundaries = self._detect_boundaries(gray)
        text_regions = self._detect_text_regions(gray)

        return {
            'beacons': beacons,
            'boundaries': boundaries,
            'text_regions': text_regions,
            'total_beacons': len(beacons),
            'total_boundaries': len(boundaries),
            'total_text_regions': len(text_regions),
            'method': 'traditional_cv',
        }

    def _detect_beacons(self, gray: np.ndarray) -> List[Dict]:
        binary = adaptive_threshold_niblack(gray.astype(np.uint8), window_size=31, k=-0.4)
        binary = morphological_open(binary, 2)
        labels, num = connected_components(255 - binary)
        h, w = gray.shape
        border = max(5, int(min(h, w) * 0.02))
        beacons = []
        for rid in range(1, num + 1):
            ys, xs = np.where(labels == rid)
            area = len(ys)
            if area < self.min_beacon_area or area > self.max_beacon_area:
                continue
            x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            if x1 < border or y1 < border or x2 > w - border or y2 > h - border:
                continue
            bw, bh = x2 - x1, y2 - y1
            if bw < 4 or bh < 4:
                continue
            fill_ratio = area / max(bw * bh, 1)
            if fill_ratio < self.min_beacon_fill:
                continue
            aspect = bw / max(bh, 1)
            if aspect > 3.0 or aspect < 0.33:
                continue
            perimeter_est = 2 * (bw + bh)
            circularity = min(1.0, 4 * np.pi * area / max(perimeter_est ** 2, 1))
            cx, cy = float(xs.mean()), float(ys.mean())
            dist_to_center = np.sqrt(((cx - w/2) / (w/2))**2 + ((cy - h/2) / (h/2))**2)
            beacon_type = 'unknown'
            if circularity > 0.6:
                beacon_type = 'iron_pin'
            elif 0.5 < fill_ratio and 0.7 < aspect < 1.4:
                beacon_type = 'concrete'
            elif circularity < 0.4:
                beacon_type = 'triangle'
            score = fill_ratio * 0.4 + circularity * 0.4 + (1 - dist_to_center) * 0.2
            beacons.append({
                'center': (cx, cy),
                'bbox': (x1, y1, x2, y2),
                'type': beacon_type,
                'confidence': round(score, 3),
                'area': area,
                'circularity': round(float(circularity), 3),
                'aspect_ratio': round(float(aspect), 3),
                'method': 'traditional',
            })
        beacons.sort(key=lambda b: b['confidence'], reverse=True)
        return beacons

    def _detect_boundaries(self, gray: np.ndarray) -> List[Dict]:
        edges = canny_edges(gray, low=30, high=100)
        dilated = morphological_dilate(edges, 3)
        h, w = gray.shape
        lines = self._hough_lines(dilated, h, w, threshold=80)
        boundaries = []
        for rho, theta in lines:
            angle_deg = np.degrees(theta)
            cx = w / 2
            cy = h / 2
            x1 = int(cx + 1000 * np.cos(theta))
            y1 = int(cy + 1000 * np.sin(theta))
            x2 = int(cx - 1000 * np.cos(theta))
            y2 = int(cy - 1000 * np.sin(theta))
            if rho < 0:
                rho = -rho
                x1, y1, x2, y2 = x2, y2, x1, y1
            boundaries.append({
                'rho': float(rho),
                'theta_degrees': round(float(angle_deg), 2),
                'start': (x1, y1),
                'end': (x2, y2),
                'confidence': 0.5,
                'method': 'traditional',
            })
        return boundaries

    def _hough_lines(self, edges: np.ndarray, h: int, w: int,
                     rho_res: float = 1.0, theta_res: float = 1.0,
                     threshold: int = 50) -> List[Tuple[float, float]]:
        diag = int(np.sqrt(h ** 2 + w ** 2))
        thetas = np.deg2rad(np.arange(-90, 90, theta_res))
        cos_t = np.cos(thetas)
        sin_t = np.sin(thetas)
        ys, xs = np.where(edges > 0)
        if len(ys) == 0:
            return []
        rho_vals = np.outer(ys, sin_t) + np.outer(xs, cos_t)
        rho_bins = np.round((rho_vals + diag) / rho_res).astype(np.int32)
        n_rhos = int(2 * diag / rho_res) + 1
        accumulator = np.zeros((n_rhos, len(thetas)), dtype=np.int32)
        for t_idx in range(len(thetas)):
            bins, counts = np.unique(rho_bins[:, t_idx], return_counts=True)
            valid = (bins >= 0) & (bins < n_rhos)
            accumulator[bins[valid], t_idx] = counts[valid]
        peak_rhos, peak_thetas = np.where(accumulator >= threshold)
        lines = []
        for pi in range(len(peak_rhos)):
            lines.append((peak_rhos[pi] * rho_res - diag, thetas[peak_thetas[pi]]))
        return self._suppress_line_peaks(lines, accumulator, rho_res, n_rhos)

    def _suppress_line_peaks(self, lines, accumulator, rho_res, n_rhos,
                             nms_rho=5, nms_theta=3):
        if not lines:
            return []
        used = set()
        n_thetas = accumulator.shape[1]
        scored = []
        for rho, theta in lines:
            r_idx = int((rho + n_rhos * rho_res / 2) / rho_res)
            t_idx = int(np.clip(theta / np.deg2rad(1) + 90, 0, n_thetas - 1))
            if 0 <= r_idx < accumulator.shape[0] and 0 <= t_idx < n_thetas:
                scored.append((accumulator[r_idx, t_idx], rho, theta))
        scored.sort(key=lambda x: x[0], reverse=True)
        result = []
        for _, rho, theta in scored:
            r_idx = int((rho + n_rhos * rho_res / 2) / rho_res)
            t_idx = int(np.clip(theta / np.deg2rad(1) + 90, 0, n_thetas - 1))
            if (r_idx, t_idx) in used:
                continue
            result.append((rho, theta))
            for dr in range(-nms_rho, nms_rho + 1):
                for dt in range(-nms_theta, nms_theta + 1):
                    used.add((r_idx + dr, t_idx + dt))
        return result[:50]

    def _detect_text_regions(self, gray: np.ndarray) -> List[Dict]:
        blurred = gaussian_blur(gray, sigma=0.8)
        binary = adaptive_threshold_niblack(blurred.astype(np.uint8), window_size=25, k=-0.3)
        binary = morphological_open(binary, 2)
        binary = morphological_close(binary, 3)
        labels, num = connected_components(255 - binary)
        h_img, w_img = gray.shape
        border = max(5, int(min(h_img, w_img) * 0.02))
        min_area = max(20, int(h_img * w_img * 0.00015))
        regions = []
        for rid in range(1, num + 1):
            ys, xs = np.where(labels == rid)
            if len(ys) < 10:
                continue
            x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            bw, bh = x2 - x1, y2 - y1
            if bw < 12 or bh < 8:
                continue
            if bw * bh < min_area:
                continue
            if x1 < border or y1 < border or x2 > w_img - border or y2 > h_img - border:
                continue
            aspect = bw / max(bh, 1)
            if aspect < 0.3 or aspect > 15:
                continue
            fill_ratio = len(ys) / max(bw * bh, 1)
            if fill_ratio < 0.10 or fill_ratio > 0.90:
                continue
            regions.append({
                'bbox': (x1, y1, x2, y2),
                'width': bw,
                'height': bh,
                'area': len(ys),
                'fill_ratio': round(float(fill_ratio), 3),
                'aspect_ratio': round(float(aspect), 3),
                'method': 'traditional',
            })
        regions.sort(key=lambda r: r['area'], reverse=True)
        return regions[:30]

    def parameters(self):
        return []

    def update(self, lr, grads):
        pass
