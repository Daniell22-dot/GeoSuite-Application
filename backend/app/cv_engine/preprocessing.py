"""
Image preprocessing — pure NumPy, zero dependencies.
Handles grayscale conversion, thresholding, deskewing, noise removal.
"""
import numpy as np
from typing import Tuple, Optional


def rgb_to_grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image.astype(np.float64)
    if image.shape[2] == 4:
        image = image[:, :, :3]
    return 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]


def normalize(image: np.ndarray) -> np.ndarray:
    mn, mx = image.min(), image.max()
    if mx - mn < 1e-8:
        return np.zeros_like(image, dtype=np.float64)
    return (image - mn) / (mx - mn)


def adaptive_threshold_niblack(image: np.ndarray, window_size: int = 15, k: float = -0.2) -> np.ndarray:
    h, w = image.shape
    pad = window_size // 2
    padded = np.pad(image.astype(np.float64), pad, mode='reflect')
    ph, pw = padded.shape
    integral = np.zeros((ph + 1, pw + 1), dtype=np.float64)
    integral[1:, 1:] = np.cumsum(np.cumsum(padded, axis=0), axis=1)
    integral_sq = np.zeros((ph + 1, pw + 1), dtype=np.float64)
    integral_sq[1:, 1:] = np.cumsum(np.cumsum(padded ** 2, axis=0), axis=1)
    y1 = np.arange(h).reshape(-1, 1)
    x1 = np.arange(w).reshape(1, -1)
    y2 = y1 + window_size
    x2 = x1 + window_size
    area = window_size * window_size
    s = integral[y2, x2] - integral[y1, x2] - integral[y2, x1] + integral[y1, x1]
    s_sq = integral_sq[y2, x2] - integral_sq[y1, x2] - integral_sq[y2, x1] + integral_sq[y1, x1]
    mean = s / area
    variance = s_sq / area - mean ** 2
    std = np.sqrt(np.maximum(variance, 0))
    threshold = mean + k * std
    return (image > threshold).astype(np.uint8) * 255


def otsu_threshold(image: np.ndarray) -> np.ndarray:
    hist, _ = np.histogram(image.ravel(), bins=256, range=(0, 256))
    total = image.size
    sum_total = np.dot(np.arange(256), hist)
    sum_bg = 0.0
    weight_bg = 0
    max_var = 0.0
    best_thresh = 0
    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        var_between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if var_between > max_var:
            max_var = var_between
            best_thresh = t
    return (image > best_thresh).astype(np.uint8) * 255


def canny_edges(image: np.ndarray, low: float = 50, high: float = 150) -> np.ndarray:
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float64)
    gx = conv2d_3x3(image.astype(np.float64), sobel_x)
    gy = conv2d_3x3(image.astype(np.float64), sobel_y)
    magnitude = np.sqrt(gx ** 2 + gy ** 2)
    direction = np.arctan2(gy, gx) * 180.0 / np.pi
    direction = direction % 180
    h, w = magnitude.shape
    nms = np.zeros_like(magnitude)
    a = direction[1:-1, 1:-1]
    m = magnitude[1:-1, 1:-1]
    mask0 = ((a < 22.5) | (a >= 157.5))
    mask1 = ((a >= 22.5) & (a < 67.5))
    mask2 = ((a >= 67.5) & (a < 112.5))
    mask3 = ((a >= 112.5) & (a < 157.5))
    n1 = np.zeros_like(m)
    n2 = np.zeros_like(m)
    n1[mask0] = magnitude[1:-1, 0:-2][mask0]; n2[mask0] = magnitude[1:-1, 2:][mask0]
    n1[mask1] = magnitude[0:-2, 2:][mask1]; n2[mask1] = magnitude[2:, 0:-2][mask1]
    n1[mask2] = magnitude[0:-2, 1:-1][mask2]; n2[mask2] = magnitude[2:, 1:-1][mask2]
    n1[mask3] = magnitude[0:-2, 0:-2][mask3]; n2[mask3] = magnitude[2:, 2:][mask3]
    winner = np.where(m >= np.maximum(n1, n2), m, 0)
    nms[1:-1, 1:-1] = winner
    strong = nms > high
    weak = (nms >= low) & (nms <= high)
    result = strong.astype(np.uint8) * 255
    for _ in range(3):
        dilated = np.zeros_like(result)
        for di in range(-1, 2):
            for dj in range(-1, 2):
                dilated = np.maximum(dilated, np.roll(np.roll(result, di, 0), dj, 1))
        weak_connected = weak & (dilated > 0)
        result = result | weak_connected.astype(np.uint8) * 255
    return result


def conv2d_3x3(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    padded = np.pad(image, 1, mode='reflect')
    h, w = image.shape
    output = np.zeros_like(image, dtype=np.float64)
    for ki in range(3):
        for kj in range(3):
            output += kernel[ki, kj] * padded[ki:ki+h, kj:kj+w]
    return output


def median_filter(image: np.ndarray, size: int = 3) -> np.ndarray:
    pad = size // 2
    padded = np.pad(image.astype(np.float64), pad, mode='reflect')
    h, w = image.shape
    as_strided = np.lib.stride_tricks.as_strided
    s = padded.strides
    windows = as_strided(padded, shape=(h, w, size, size),
                         strides=(s[0], s[1], s[0], s[1]))
    return np.median(windows.reshape(h, w, size * size), axis=2)


def gaussian_blur(image: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    k = int(np.ceil(3 * sigma)) * 2 + 1
    ax = np.arange(k) - k // 2
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2))
    kernel /= kernel.sum()
    return conv2d_general(image.astype(np.float64), kernel)


def conv2d_general(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    kh, kw = kernel.shape
    pad_h, pad_w = kh // 2, kw // 2
    padded = np.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), mode='reflect')
    h, w = image.shape
    output = np.zeros((h, w), dtype=np.float64)
    for ki in range(kh):
        for kj in range(kw):
            output += kernel[ki, kj] * padded[ki:ki+h, kj:kj+w]
    return output


def morphological_erode(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    pad = kernel_size // 2
    padded = np.pad(image, pad, mode='constant')
    h, w = image.shape
    output = np.zeros_like(image)
    for ki in range(kernel_size):
        for kj in range(kernel_size):
            region = padded[ki:ki+h, kj:kj+w]
            output = np.where((ki == 0) & (kj == 0), region, np.minimum(output, region))
    return output


def morphological_dilate(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    pad = kernel_size // 2
    padded = np.pad(image, pad, mode='constant')
    h, w = image.shape
    output = np.zeros_like(image)
    for ki in range(kernel_size):
        for kj in range(kernel_size):
            region = padded[ki:ki+h, kj:kj+w]
            output = np.where((ki == 0) & (kj == 0), region, np.maximum(output, region))
    return output


def morphological_open(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    return morphological_dilate(morphological_erode(image, kernel_size), kernel_size)


def morphological_close(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    return morphological_erode(morphological_dilate(image, kernel_size), kernel_size)


def compute_skew_angle(binary: np.ndarray) -> float:
    edges = canny_edges(binary.astype(np.float64) * 255)
    h, w = edges.shape
    diag = int(np.sqrt(h ** 2 + w ** 2))
    theta_range = np.linspace(-np.pi / 4, np.pi / 4, 180)
    accumulator = np.zeros(len(theta_range))
    ys, xs = np.where(edges > 0)
    for idx, theta in enumerate(theta_range):
        rho_vals = xs * np.cos(theta) + ys * np.sin(theta)
        rho_idx = (rho_vals + diag).astype(int)
        valid = (rho_idx >= 0) & (rho_idx < 2 * diag)
        for ri in rho_idx[valid]:
            accumulator[idx] += 1
    best_idx = np.argmax(accumulator)
    return theta_range[best_idx] * 180.0 / np.pi


def rotate_image(image: np.ndarray, angle_deg: float) -> np.ndarray:
    h, w = image.shape[:2]
    cy, cx = h / 2, w / 2
    theta = np.radians(angle_deg)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    M = np.array([[cos_t, sin_t, (1 - cos_t) * cx - sin_t * cy],
                   [-sin_t, cos_t, sin_t * cx + (1 - cos_t) * cy]])
    inv_M = np.linalg.inv(np.vstack([M, [0, 0, 1]]))[:2]
    out = np.zeros_like(image, dtype=np.float64)
    for i in range(h):
        for j in range(w):
            src = inv_M @ np.array([j, i, 1])
            si, sj = src
            if 0 <= si < h - 1 and 0 <= sj < w - 1:
                i0, j0 = int(si), int(sj)
                di, dj = si - i0, sj - j0
                out[i, j] = ((1 - di) * (1 - dj) * image[i0, j0] +
                              di * (1 - dj) * image[min(i0 + 1, h - 1), j0] +
                              (1 - di) * dj * image[i0, min(j0 + 1, w - 1)] +
                              di * dj * image[min(i0 + 1, h - 1), min(j0 + 1, w - 1)])
    return out


def deskew(image: np.ndarray) -> np.ndarray:
    binary = otsu_threshold(image)
    angle = compute_skew_angle(binary)
    if abs(angle) < 0.1:
        return image
    return rotate_image(image, -angle)


def resize_bilinear(image: np.ndarray, new_h: int, new_w: int) -> np.ndarray:
    h, w = image.shape[:2]
    out = np.zeros((new_h, new_w), dtype=np.float64) if image.ndim == 2 else np.zeros((new_h, new_w, image.shape[2]), dtype=np.float64)
    sy, sx = h / new_h, w / new_w
    for i in range(new_h):
        for j in range(new_w):
            si, sj = min(i * sy, h - 1.001), min(j * sx, w - 1.001)
            i0, j0 = int(si), int(sj)
            di, dj = si - i0, sj - j0
            i1, j1 = min(i0 + 1, h - 1), min(j0 + 1, w - 1)
            if image.ndim == 2:
                out[i, j] = ((1 - di) * (1 - dj) * image[i0, j0] +
                              di * (1 - dj) * image[i1, j0] +
                              (1 - di) * dj * image[i0, j1] +
                              di * dj * image[i1, j1])
            else:
                out[i, j] = ((1 - di) * (1 - dj) * image[i0, j0] +
                              di * (1 - dj) * image[i1, j0] +
                              (1 - di) * dj * image[i0, j1] +
                              di * dj * image[i1, j1])
    return out


def pad_to_multiple(image: np.ndarray, multiple: int = 32) -> Tuple[np.ndarray, Tuple[int, int]]:
    h, w = image.shape[:2]
    new_h = ((h - 1) // multiple + 1) * multiple
    new_w = ((w - 1) // multiple + 1) * multiple
    pad_h, pad_w = new_h - h, new_w - w
    if image.ndim == 2:
        padded = np.pad(image, ((0, pad_h), (0, pad_w)), mode='constant')
    else:
        padded = np.pad(image, ((0, pad_h), (0, pad_w), (0, 0)), mode='constant')
    return padded, (pad_h, pad_w)


class Preprocessor:
    def __init__(self, target_size: Tuple[int, int] = (512, 512), do_deskew: bool = True):
        self.target_size = target_size
        self.do_deskew = do_deskew

    def process(self, image: np.ndarray) -> Tuple[np.ndarray, dict]:
        meta = {'original_shape': image.shape}
        gray = rgb_to_grayscale(image)
        meta['deskew_angle'] = 0.0
        if self.do_deskew:
            angle = compute_skew_angle(otsu_threshold(gray))
            meta['deskew_angle'] = angle
            if abs(angle) > 0.1:
                gray = rotate_image(gray, -angle)
        blurred = gaussian_blur(gray, sigma=0.8)
        normalized = normalize(blurred)
        resized = resize_bilinear(normalized, self.target_size[0], self.target_size[1])
        padded, pad_info = pad_to_multiple(resized, 32)
        meta['pad_info'] = pad_info
        meta['processed_shape'] = padded.shape
        return padded, meta

    def process_for_display(self, image: np.ndarray) -> np.ndarray:
        gray = rgb_to_grayscale(image)
        return normalize(gray)
