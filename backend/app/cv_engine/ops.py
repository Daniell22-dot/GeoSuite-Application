"""
Low-level operations — pure NumPy matrix math.
No PyTorch, no TensorFlow, no external dependencies.
"""
import numpy as np
from typing import Tuple


def im2col(input: np.ndarray, kH: int, kW: int, stride: int = 1) -> np.ndarray:
    N, C, H, W = input.shape
    H_out = (H - kH) // stride + 1
    W_out = (W - kW) // stride + 1
    as_strided = np.lib.stride_tricks.as_strided
    strides = (input.strides[0], input.strides[1], input.strides[2] * stride, input.strides[3] * stride,
               input.strides[2], input.strides[3])
    shape = (N, C, H_out, W_out, kH, kW)
    patches = as_strided(input, shape=shape, strides=strides)
    return patches.reshape(N, C * kH * kW, H_out * W_out)


def col2im(cols: np.ndarray, shape: tuple, kH: int, kW: int, stride: int = 1) -> np.ndarray:
    N, C, H, W = shape
    H_out = (H - kH) // stride + 1
    W_out = (W - kW) // stride + 1
    cols = cols.reshape(N, C, kH, kW, H_out, W_out)
    output = np.zeros(shape, dtype=cols.dtype)
    for ki in range(kH):
        ki_max = ki + stride * H_out
        for kj in range(kW):
            kj_max = kj + stride * W_out
            output[:, :, ki:ki_max:stride, kj:kj_max:stride] += cols[:, :, ki, kj, :, :]
    return output


def conv2d(input: np.ndarray, weight: np.ndarray, bias: np.ndarray,
           stride: int = 1, padding: int = 0) -> np.ndarray:
    if padding > 0:
        if input.ndim == 4:
            input = np.pad(input, ((0, 0), (0, 0), (padding, padding), (padding, padding)), mode='constant')
        else:
            input = np.pad(input, ((padding, padding), (padding, padding)), mode='constant')
    N, C_in, H, W = input.shape
    C_out, _, kH, kW = weight.shape
    H_out = (H - kH) // stride + 1
    W_out = (W - kW) // stride + 1
    cols = im2col(input, kH, kW, stride)
    W_mat = weight.reshape(C_out, -1)
    out = W_mat @ cols + bias.reshape(-1, 1)
    out = out.reshape(N, C_out, H_out, W_out)
    return out


def relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0, x)


def sigmoid(x: np.ndarray) -> np.ndarray:
    x_clipped = np.clip(x, -500, 500)
    return 1.0 / (1.0 + np.exp(-x_clipped))


def tanh(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x_shifted = x - np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x_shifted)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


def softmax_2d(x: np.ndarray) -> np.ndarray:
    return softmax(x, axis=1)


def batch_norm(x: np.ndarray, gamma: np.ndarray, beta: np.ndarray,
               running_mean: np.ndarray, running_var: np.ndarray,
               training: bool = True, eps: float = 1e-5, momentum: float = 0.1) -> np.ndarray:
    if x.ndim == 4:
        axes = (0, 2, 3)
        if training:
            mean = x.mean(axis=axes, keepdims=True)
            var = x.var(axis=axes, keepdims=True)
            running_mean[:] = (1 - momentum) * running_mean + momentum * mean.ravel()
            running_var[:] = (1 - momentum) * running_var + momentum * var.ravel()
        else:
            mean = running_mean.reshape(1, -1, 1, 1)
            var = running_var.reshape(1, -1, 1, 1)
        x_norm = (x - mean) / np.sqrt(var + eps)
        return gamma.reshape(1, -1, 1, 1) * x_norm + beta.reshape(1, -1, 1, 1)
    else:
        if training:
            mean = x.mean(axis=0, keepdims=True)
            var = x.var(axis=0, keepdims=True)
        else:
            mean = running_mean.reshape(1, -1)
            var = running_var.reshape(1, -1)
        x_norm = (x - mean) / np.sqrt(var + eps)
        return gamma * x_norm + beta


def max_pool(x: np.ndarray, kernel_size: int = 2, stride: int = 2, padding: int = 0) -> np.ndarray:
    if padding > 0:
        x = np.pad(x, ((0, 0), (0, 0), (padding, padding), (padding, padding)), mode='constant')
    N, C, H, W = x.shape
    H_out = (H - kernel_size) // stride + 1
    W_out = (W - kernel_size) // stride + 1
    output = np.zeros((N, C, H_out, W_out), dtype=x.dtype)
    for i in range(H_out):
        for j in range(W_out):
            h_start = i * stride
            w_start = j * stride
            output[:, :, i, j] = np.max(x[:, :, h_start:h_start + kernel_size, w_start:w_start + kernel_size], axis=(2, 3))
    return output


def avg_pool(x: np.ndarray, kernel_size: int = 2, stride: int = 2) -> np.ndarray:
    N, C, H, W = x.shape
    H_out = (H - kernel_size) // stride + 1
    W_out = (W - kernel_size) // stride + 1
    output = np.zeros((N, C, H_out, W_out), dtype=x.dtype)
    for i in range(H_out):
        for j in range(W_out):
            h_start = i * stride
            w_start = j * stride
            output[:, :, i, j] = np.mean(x[:, :, h_start:h_start + kernel_size, w_start:w_start + kernel_size], axis=(2, 3))
    return output


def upsample_2x(x: np.ndarray) -> np.ndarray:
    N, C, H, W = x.shape
    output = np.zeros((N, C, H * 2, W * 2), dtype=x.dtype)
    output[:, :, ::2, ::2] = x
    output[:, :, 1::2, ::2] = x
    output[:, :, ::2, 1::2] = x
    output[:, :, 1::2, 1::2] = x
    return output


def l2_normalize(x: np.ndarray, axis: int = -1, eps: float = 1e-8) -> np.ndarray:
    norm = np.sqrt(np.sum(x ** 2, axis=axis, keepdims=True) + eps)
    return x / norm


def cross_entropy_loss(logits: np.ndarray, targets: np.ndarray) -> float:
    probs = softmax(logits, axis=-1)
    N = targets.shape[0]
    log_probs = -np.log(np.clip(probs[np.arange(N), targets], 1e-8, 1.0))
    return np.mean(log_probs)


def sigmoid_cross_entropy(logits: np.ndarray, targets: np.ndarray) -> float:
    return np.mean(np.maximum(logits, 0) - logits * targets + np.log(1 + np.exp(-np.abs(logits))))


def mse_loss(pred: np.ndarray, target: np.ndarray) -> float:
    return np.mean((pred - target) ** 2)


def ctc_decode_best_path(logits: np.ndarray, blank_idx: int = 0) -> list:
    path = np.argmax(logits, axis=-1)
    decoded = []
    prev = None
    for idx in path:
        if idx != blank_idx and idx != prev:
            decoded.append(int(idx))
        prev = idx
    return decoded


def ctc_greedy_decode(logits: np.ndarray, idx_to_char: dict, blank_idx: int = 0) -> str:
    path = ctc_decode_best_path(logits, blank_idx)
    return ''.join(idx_to_char.get(idx, '') for idx in path)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.3) -> list:
    if len(boxes) == 0:
        return []
    order = np.argsort(scores)[::-1]
    keep = []
    while len(order) > 0:
        i = order[0]
        keep.append(int(i))
        if len(order) == 1:
            break
        ious = compute_iou(boxes[i], boxes[order[1:]])
        mask = ious < iou_threshold
        order = order[1:][mask]
    return keep


def compute_iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area_box = (box[2] - box[0]) * (box[3] - box[1])
    area_boxes = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    union = area_box + area_boxes - inter
    return inter / np.maximum(union, 1e-8)


def connected_components(binary: np.ndarray) -> Tuple[np.ndarray, int]:
    h, w = binary.shape
    labels = np.zeros_like(binary, dtype=np.int32)
    current_label = 0
    for i in range(h):
        for j in range(w):
            if binary[i, j] and labels[i, j] == 0:
                current_label += 1
                stack = [(i, j)]
                while stack:
                    ci, cj = stack.pop()
                    if 0 <= ci < h and 0 <= cj < w and binary[ci, cj] and labels[ci, cj] == 0:
                        labels[ci, cj] = current_label
                        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            stack.append((ci + di, cj + dj))
    return labels, current_label


def douglas_peucker(points: np.ndarray, epsilon: float) -> np.ndarray:
    if len(points) <= 2:
        return points
    dmax = 0
    index = 0
    for i in range(1, len(points) - 1):
        d = point_line_distance(points[i], points[0], points[-1])
        if d > dmax:
            index = i
            dmax = d
    if dmax > epsilon:
        left = douglas_peucker(points[:index + 1], epsilon)
        right = douglas_peucker(points[index:], epsilon)
        return np.vstack([left[:-1], right])
    else:
        return np.array([points[0], points[-1]])


def point_line_distance(point: np.ndarray, line_start: np.ndarray, line_end: np.ndarray) -> float:
    if np.all(line_start == line_end):
        return np.sqrt(np.sum((point - line_start) ** 2))
    t = np.clip(np.dot(point - line_start, line_end - line_start) / np.sum((line_end - line_start) ** 2), 0, 1)
    projection = line_start + t * (line_end - line_start)
    return np.sqrt(np.sum((point - projection) ** 2))


# ---------------------------------------------------------------------------
# Backward pass operations for training
# ---------------------------------------------------------------------------

def conv2d_backward(dout, input, weight, bias, stride, padding):
    if padding > 0:
        input_padded = np.pad(input, ((0, 0), (0, 0), (padding, padding), (padding, padding)), mode='constant')
    else:
        input_padded = input
    N, C_in, H, W = input_padded.shape
    C_out, _, kH, kW = weight.shape
    H_out = (H - kH) // stride + 1
    W_out = (W - kW) // stride + 1
    cols = im2col(input_padded, kH, kW, stride)
    W_mat = weight.reshape(C_out, -1)
    cols_flat = cols.transpose(0, 2, 1).reshape(N * H_out * W_out, -1)
    dout_reshaped = dout.reshape(C_out, N * H_out * W_out)
    dweight = dout_reshaped @ cols_flat
    dweight = dweight.reshape(weight.shape)
    dbias = dout.reshape(C_out, -1).sum(axis=1)
    dcols = W_mat.T @ dout_reshaped
    dcols = dcols.reshape(N, H_out * W_out, C_in * kH * kW).transpose(0, 2, 1)
    dinput_padded = col2im(dcols, input_padded.shape, kH, kW, stride)
    if padding > 0:
        dinput = dinput_padded[:, :, padding:-padding, padding:-padding]
    else:
        dinput = dinput_padded
    return dinput, dweight, dbias


def relu_backward(dout, x):
    return dout * (x > 0).astype(x.dtype)


def sigmoid_backward(dout, output):
    return dout * output * (1.0 - output)


def max_pool_backward(dout, x, kernel_size=2, stride=2, padding=0):
    N, C, H, W = x.shape
    if padding > 0:
        x_padded = np.pad(x, ((0, 0), (0, 0), (padding, padding), (padding, padding)), mode='constant')
    else:
        x_padded = x
    H_p, W_p = x_padded.shape[2], x_padded.shape[3]
    H_out = (H_p - kernel_size) // stride + 1
    W_out = (W_p - kernel_size) // stride + 1
    dinput_padded = np.zeros_like(x_padded)
    as_strided = np.lib.stride_tricks.as_strided
    s = x_padded.strides
    patches = as_strided(x_padded,
                         shape=(N, C, H_out, W_out, kernel_size, kernel_size),
                         strides=(s[0], s[1], s[2] * stride, s[3] * stride, s[2], s[3]))
    patches_flat = patches.reshape(N, C, H_out * W_out, kernel_size * kernel_size)
    max_idx = np.argmax(patches_flat, axis=3)
    ki = max_idx // kernel_size
    kj = max_idx % kernel_size
    row_base = (np.arange(H_out) * stride).reshape(1, 1, H_out, 1).repeat(W_out, axis=3)
    col_base = (np.arange(W_out) * stride).reshape(1, 1, 1, W_out).repeat(H_out, axis=2)
    ki_reshaped = ki.reshape(N, C, H_out, W_out)
    kj_reshaped = kj.reshape(N, C, H_out, W_out)
    row_idx = (row_base + ki_reshaped).astype(np.intp)
    col_idx = (col_base + kj_reshaped).astype(np.intp)
    dout_reshaped = dout.reshape(N, C, H_out, W_out)
    np.add.at(dinput_padded, (slice(None), slice(None), row_idx, col_idx), dout_reshaped)
    if padding > 0:
        return dinput_padded[:, :, padding:padding + H, padding:padding + W]
    return dinput_padded


def upsample_2x_backward(dout, H, W):
    N, C, H_d, W_d = dout.shape
    dinput = np.zeros((N, C, H, W), dtype=dout.dtype)
    dinput[:, :, ::2, ::2] = dout[:, :, :H // 2 + (H % 2), :W // 2 + (W % 2)]
    dinput[:, :, 1::2, ::2] = dout[:, :, H // 2:H, :W // 2 + (W % 2)]
    dinput[:, :, ::2, 1::2] = dout[:, :, :H // 2 + (H % 2), W // 2:W]
    dinput[:, :, 1::2, 1::2] = dout[:, :, H // 2:H, W // 2:W]
    return dinput[:, :, :H, :W]


def softmax_2d_backward(dout, probs):
    return probs * (dout - np.sum(dout * probs, axis=1, keepdims=True))


def batch_norm_backward(dout, x, gamma, running_mean, running_var, eps=1e-5):
    N, C, H, W = x.shape
    x_hat = (x - running_mean.reshape(1, C, 1, 1)) / np.sqrt(running_var.reshape(1, C, 1, 1) + eps)
    dgamma = np.sum(dout * x_hat, axis=(0, 2, 3))
    dbeta = np.sum(dout, axis=(0, 2, 3))
    dx_hat = dout * gamma.reshape(1, C, 1, 1)
    dvar = np.sum(dx_hat * (x - running_mean.reshape(1, C, 1, 1)) * -0.5 *
                  (running_var.reshape(1, C, 1, 1) + eps) ** (-1.5), axis=(0, 2, 3))
    dmean = np.sum(dx_hat * (-1.0 / np.sqrt(running_var.reshape(1, C, 1, 1) + eps)), axis=(0, 2, 3))
    dvar_term = 2.0 * (x - running_mean.reshape(1, C, 1, 1)) / (H * W)
    dx = dx_hat / np.sqrt(running_var.reshape(1, C, 1, 1) + eps) + \
         dvar.reshape(1, C, 1, 1) * dvar_term + \
         dmean.reshape(1, C, 1, 1) / (H * W)
    return dx, dgamma, dbeta


def ctc_loss(logits, targets, input_length, target_length):
    T = logits.shape[0]
    S = target_length
    L = 2 * S + 1
    blank = logits.shape[1] - 1
    log_alpha = np.full((T, L), -1e9, dtype=np.float64)
    log_alpha[0, 0] = logits[0, blank]
    if L > 1:
        log_alpha[0, 1] = logits[0, targets[0]] if S > 0 else -1e9
    for t in range(1, min(T, input_length)):
        for s in range(L):
            log_alpha[t, s] = log_sum_exp(
                log_alpha[t - 1, s],
                log_alpha[t - 1, s - 1] if s > 0 else -1e9,
                log_alpha[t - 1, s - 2] if s > 1 else -1e9,
            )
            if s % 2 == 1:
                char_idx = targets[s // 2]
                log_alpha[t, s] += logits[t, char_idx]
            else:
                log_alpha[t, s] += logits[t, blank]
    log_beta = np.full((T, L), -1e9, dtype=np.float64)
    log_beta[T - 1, 0] = 0.0
    if L > 1:
        log_beta[T - 1, 1] = 0.0 if S > 0 else -1e9
    for t in range(T - 2, -1, -1):
        for s in range(L):
            log_beta[t, s] = log_sum_exp(
                log_beta[t + 1, s] + logits[t + 1, blank if s % 2 == 0 else targets[s // 2]],
                log_beta[t + 1, s + 1] + (logits[t + 1, blank if (s + 1) % 2 == 0 else targets[(s + 1) // 2]] if s + 1 < L else -1e9),
                log_beta[t + 1, s + 2] + (logits[t + 1, blank if (s + 2) % 2 == 0 else targets[(s + 2) // 2]] if s + 2 < L else -1e9),
            )
    loss = -log_alpha[min(T - 1, input_length - 1), 0]
    log_probs = logits - log_sum_exp_single(logits)
    log_joint = np.full_like(log_probs, -1e9)
    for t in range(min(T, input_length)):
        for s in range(L):
            if s % 2 == 0:
                log_joint[t, blank] = np.logaddexp(log_joint[t, blank],
                                                     log_alpha[t, s] + log_beta[t, s] - log_probs[t, blank])
            else:
                c = targets[s // 2]
                log_joint[t, c] = np.logaddexp(log_joint[t, c],
                                                  log_alpha[t, s] + log_beta[t, s] - log_probs[t, c])
    dlogits = np.exp(log_joint) - np.exp(log_probs) * np.sum(np.exp(log_joint), axis=1, keepdims=True)
    return float(loss), dlogits


def log_sum_exp(*args):
    vals = [a for a in args if a > -1e8]
    if not vals:
        return -1e9
    max_val = max(vals)
    return max_val + np.log(sum(np.exp(v - max_val) for v in vals))


def log_sum_exp_single(x):
    max_val = np.max(x, axis=-1, keepdims=True)
    return max_val.squeeze() + np.log(np.sum(np.exp(x - max_val), axis=-1))
