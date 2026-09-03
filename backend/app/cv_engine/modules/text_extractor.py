"""
Generic text extractor — OCR for map text, labels, annotations.
CTC-based with character-level decoding.
"""
import numpy as np
from typing import List, Dict
from ..ops import conv2d, relu, max_pool, sigmoid, tanh, softmax, softmax_2d, ctc_greedy_decode, connected_components
from ..preprocessing import Preprocessor, adaptive_threshold_niblack


CHAR_SET = list('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz°\'".-/ ():,;#&@[]{}|\\+=<>?!%$~^*')
CHAR_TO_IDX = {c: i for i, c in enumerate(CHAR_SET)}
IDX_TO_CHAR = {i: c for i, c in enumerate(CHAR_SET)}
BLANK_IDX = len(CHAR_SET)


class TextExtractor:
    def __init__(self):
        self.num_chars = BLANK_IDX + 1
        self.hidden_size = 128
        self.cnn_w1 = np.random.randn(32, 1, 3, 3) * np.sqrt(2.0 / 9)
        self.cnn_b1 = np.zeros(32)
        self.cnn_w2 = np.random.randn(64, 32, 3, 3) * np.sqrt(2.0 / (32 * 9))
        self.cnn_b2 = np.zeros(64)
        self.cnn_w3 = np.random.randn(128, 64, 3, 3) * np.sqrt(2.0 / (64 * 9))
        self.cnn_b3 = np.zeros(128)
        self.preprocessor = Preprocessor(target_size=(64, 256), do_deskew=False)
        cnn_out_h = 64 // (2 ** 3)
        cnn_out_c = 128
        combined = cnn_out_c * cnn_out_h + self.hidden_size
        self.lstm_W_i = np.random.randn(self.hidden_size, combined) * np.sqrt(2.0 / combined)
        self.lstm_b_i = np.zeros(self.hidden_size)
        self.lstm_W_f = np.random.randn(self.hidden_size, combined) * np.sqrt(2.0 / combined)
        self.lstm_b_f = np.zeros(self.hidden_size)
        self.lstm_W_o = np.random.randn(self.hidden_size, combined) * np.sqrt(2.0 / combined)
        self.lstm_b_o = np.zeros(self.hidden_size)
        self.lstm_W_c = np.random.randn(self.hidden_size, combined) * np.sqrt(2.0 / combined)
        self.lstm_b_c = np.zeros(self.hidden_size)
        self.out_w = np.random.randn(self.num_chars, self.hidden_size) * np.sqrt(2.0 / self.hidden_size)
        self.out_b = np.zeros(self.num_chars)

    def extract_text_regions(self, image: np.ndarray) -> List[Dict]:
        if image.ndim == 3:
            gray = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
        else:
            gray = image.astype(np.float64)
        from ..preprocessing import gaussian_blur, morphological_open, morphological_close
        blurred = gaussian_blur(gray, sigma=0.8)
        binary = adaptive_threshold_niblack(blurred.astype(np.uint8), window_size=25, k=-0.3)
        binary = morphological_open(binary, 2)
        binary = morphological_close(binary, 3)
        labels, num = connected_components(255 - binary)
        h_img, w_img = gray.shape
        min_area = max(15, int(h_img * w_img * 0.0001))
        regions = []
        for rid in range(1, num + 1):
            ys, xs = np.where(labels == rid)
            if len(ys) < 8:
                continue
            x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            w = x2 - x1
            h = y2 - y1
            if w < 10 or h < 6:
                continue
            if w * h < min_area:
                continue
            aspect = w / max(h, 1)
            if aspect < 0.3 or aspect > 15:
                continue
            fill_ratio = len(ys) / max(w * h, 1)
            if fill_ratio < 0.08 or fill_ratio > 0.95:
                continue
            roi = gray[y1:y2 + 1, x1:x2 + 1]
            text = self._recognize_text(roi)
            if text.strip() and len(text.strip()) >= 2:
                regions.append({
                    'bbox': (x1, y1, x2, y2),
                    'text': text,
                    'confidence': self._estimate_confidence(roi),
                    'region_size': len(ys),
                })
        regions.sort(key=lambda r: r['confidence'], reverse=True)
        return regions[:50]

    def _recognize_text(self, roi: np.ndarray) -> str:
        processed, _ = self.preprocessor.process(roi)
        if processed.ndim == 2:
            x = processed[np.newaxis, np.newaxis]
        else:
            x = processed[np.newaxis].transpose(0, 3, 1, 2)
        x = conv2d(x, self.cnn_w1, self.cnn_b1, 1, 1)
        x = relu(x)
        x = max_pool(x, 2, 2)
        x = conv2d(x, self.cnn_w2, self.cnn_b2, 1, 1)
        x = relu(x)
        x = max_pool(x, 2, 2)
        x = conv2d(x, self.cnn_w3, self.cnn_b3, 1, 1)
        x = relu(x)
        x = max_pool(x, 2, 2)
        N, C, H, W = x.shape
        seq_len = W
        h = np.zeros((self.hidden_size, 1))
        c = np.zeros((self.hidden_size, 1))
        outputs = []
        for t in range(seq_len):
            feat_t = x[:, :, :, t].reshape(N, -1)
            combined = np.concatenate([h[:, 0], feat_t[0]])
            i_gate = 1.0 / (1.0 + np.exp(-np.clip(-(self.lstm_W_i @ combined + self.lstm_b_i), 500, 500)))
            f_gate = 1.0 / (1.0 + np.exp(-np.clip(-(self.lstm_W_f @ combined + self.lstm_b_f), 500, 500)))
            o_gate = 1.0 / (1.0 + np.exp(-np.clip(-(self.lstm_W_o @ combined + self.lstm_b_o), 500, 500)))
            c_hat = np.tanh(self.lstm_W_c @ combined + self.lstm_b_c)
            c = f_gate * c + i_gate * c_hat
            h = o_gate * np.tanh(c)
            logits = self.out_w @ h + self.out_b.reshape(-1, 1)
            outputs.append(logits[:, 0])
        logits_array = np.array(outputs)
        text = ctc_greedy_decode(logits_array, IDX_TO_CHAR, BLANK_IDX)
        return text

    def _estimate_confidence(self, roi: np.ndarray) -> float:
        mean_val = float(np.mean(roi))
        contrast = float(np.std(roi))
        return min(1.0, contrast / 100.0 * (1 - mean_val / 255.0))

    def parameters(self):
        return [self.cnn_w1, self.cnn_b1, self.cnn_w2, self.cnn_b2,
                self.cnn_w3, self.cnn_b3, self.lstm_W_i, self.lstm_b_i,
                self.lstm_W_f, self.lstm_b_f, self.lstm_W_o, self.lstm_b_o,
                self.lstm_W_c, self.lstm_b_c, self.out_w, self.out_b]

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g

    def save_weights(self, path: str):
        np.savez_compressed(path, **{f'p_{i}': p for i, p in enumerate(self.parameters())})

    def load_weights(self, path: str):
        data = np.load(path)
        for i, p in enumerate(self.parameters()):
            p[:] = data[f'p_{i}']
