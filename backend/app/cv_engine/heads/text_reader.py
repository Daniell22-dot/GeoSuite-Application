"""
Text reader — CTC-based OCR for bearing/distance/label extraction.
CNN feature extractor + RNN sequence modeler + CTC decoding.
"""
import numpy as np
from typing import List, Dict
from ..ops import conv2d, relu, max_pool, sigmoid, tanh, softmax, softmax_2d, ctc_greedy_decode
from ..preprocessing import Preprocessor


CHAR_SET = list('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz°\'".-/ ')
CHAR_TO_IDX = {c: i for i, c in enumerate(CHAR_SET)}
IDX_TO_CHAR = {i: c for i, c in enumerate(CHAR_SET)}
BLANK_IDX = len(CHAR_SET)


class LSTMCell:
    def __init__(self, input_size: int, hidden_size: int):
        scale = np.sqrt(2.0 / (input_size + hidden_size))
        combined = input_size + hidden_size
        self.W_i = np.random.randn(hidden_size, combined) * scale
        self.b_i = np.zeros(hidden_size)
        self.W_f = np.random.randn(hidden_size, combined) * scale
        self.b_f = np.zeros(hidden_size)
        self.W_o = np.random.randn(hidden_size, combined) * scale
        self.b_o = np.zeros(hidden_size)
        self.W_c = np.random.randn(hidden_size, combined) * scale
        self.b_c = np.zeros(hidden_size)
        self.hidden_size = hidden_size

    def forward(self, x: np.ndarray, h_prev: np.ndarray, c_prev: np.ndarray):
        combined = np.concatenate([h_prev, x], axis=-1)
        i_gate = sigmoid(self.W_i @ combined.T + self.b_i.reshape(-1, 1))
        f_gate = sigmoid(self.W_f @ combined.T + self.b_f.reshape(-1, 1))
        o_gate = sigmoid(self.W_o @ combined.T + self.b_o.reshape(-1, 1))
        c_hat = tanh(self.W_c @ combined.T + self.b_c.reshape(-1, 1))
        c = f_gate * c_prev + i_gate * c_hat
        h = o_gate * tanh(c)
        return h, c

    def parameters(self):
        return [self.W_i, self.b_i, self.W_f, self.b_f, self.W_o, self.b_o, self.W_c, self.b_c]

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g


class TextReader:
    def __init__(self, num_chars: int = len(CHAR_SET) + 1, hidden_size: int = 128):
        self.num_chars = num_chars
        self.hidden_size = hidden_size
        self.cnn_conv1_w = np.random.randn(32, 1, 3, 3) * np.sqrt(2.0 / 9)
        self.cnn_conv1_b = np.zeros(32)
        self.cnn_conv2_w = np.random.randn(64, 32, 3, 3) * np.sqrt(2.0 / (32 * 9))
        self.cnn_conv2_b = np.zeros(64)
        self.cnn_conv3_w = np.random.randn(128, 64, 3, 3) * np.sqrt(2.0 / (64 * 9))
        self.cnn_conv3_b = np.zeros(128)
        self.lstm = LSTMCell(128 * 4, hidden_size)
        self.output_w = np.random.randn(num_chars, hidden_size) * np.sqrt(2.0 / hidden_size)
        self.output_b = np.zeros(num_chars)
        self.preprocessor = Preprocessor(target_size=(32, 128))

    def _extract_features(self, x: np.ndarray) -> np.ndarray:
        x = conv2d(x, self.cnn_conv1_w, self.cnn_conv1_b, 1, 1)
        x = relu(x)
        x = max_pool(x, 2, 2)
        x = conv2d(x, self.cnn_conv2_w, self.cnn_conv2_b, 1, 1)
        x = relu(x)
        x = max_pool(x, 2, 2)
        x = conv2d(x, self.cnn_conv3_w, self.cnn_conv3_b, 1, 1)
        x = relu(x)
        x = max_pool(x, 2, 2)
        return x

    def predict(self, image: np.ndarray) -> Dict:
        processed, meta = self.preprocessor.process(image)
        if processed.ndim == 2:
            x = processed[np.newaxis, np.newaxis]
        else:
            x = processed[np.newaxis].transpose(0, 3, 1, 2)
        features = self._extract_features(x)
        N, C, H, W = features.shape
        seq_len = W
        h = np.zeros((self.hidden_size, 1))
        c = np.zeros((self.hidden_size, 1))
        outputs = []
        for t in range(seq_len):
            feat_t = features[:, :, :, t].reshape(N, -1)
            h, c = self.lstm.forward(feat_t[0], h[:, 0], c[:, 0])
            logits = self.output_w @ h + self.output_b.reshape(-1, 1)
            outputs.append(logits[:, 0])
        logits_array = np.array(outputs)
        text = ctc_greedy_decode(logits_array, IDX_TO_CHAR, BLANK_IDX)
        return {
            'text': text,
            'logits': logits_array,
            'num_timesteps': seq_len,
        }

    def predict_batch(self, images: list) -> List[Dict]:
        return [self.predict(img) for img in images]

    def parameters(self):
        params = [self.cnn_conv1_w, self.cnn_conv1_b, self.cnn_conv2_w, self.cnn_conv2_b,
                   self.cnn_conv3_w, self.cnn_conv3_b]
        params += self.lstm.parameters()
        params += [self.output_w, self.output_b]
        return params

    def update(self, lr: float, grads: list):
        for p, g in zip(self.parameters(), grads):
            p -= lr * g

    def save_weights(self, path: str):
        weights = {f'param_{i}': p for i, p in enumerate(self.parameters())}
        np.savez_compressed(path, **weights)

    def load_weights(self, path: str):
        data = np.load(path)
        for i, p in enumerate(self.parameters()):
            p[:] = data[f'param_{i}']
