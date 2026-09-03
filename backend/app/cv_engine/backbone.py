"""
Custom CNN backbone — zero external dependencies.
ResNet-style with residual connections, batch norm, and skip connections.
"""
import numpy as np
from typing import List, Tuple, Optional
from .ops import conv2d, relu, batch_norm, max_pool, avg_pool, softmax_2d
from .ops import conv2d_backward, relu_backward, batch_norm_backward, max_pool_backward


class ConvLayer:
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3,
                 stride: int = 1, padding: int = 1):
        self.stride = stride
        self.padding = padding
        scale = np.sqrt(2.0 / (in_channels * kernel_size * kernel_size))
        self.weight = np.random.randn(out_channels, in_channels, kernel_size, kernel_size) * scale
        self.bias = np.zeros(out_channels)
        self.grad_w = np.zeros_like(self.weight)
        self.grad_b = np.zeros_like(self.bias)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.input = x
        return conv2d(x, self.weight, self.bias, self.stride, self.padding)

    def backward(self, dout: np.ndarray):
        dinput, self.grad_w, self.grad_b = conv2d_backward(
            dout, self.input, self.weight, self.bias, self.stride, self.padding)
        return dinput

    def parameters(self):
        return [self.weight, self.bias]

    def gradients(self):
        return [self.grad_w, self.grad_b]


class BatchNormLayer:
    def __init__(self, num_features: int, eps: float = 1e-5, momentum: float = 0.1):
        self.eps = eps
        self.momentum = momentum
        self.gamma = np.ones(num_features)
        self.beta = np.zeros(num_features)
        self.running_mean = np.zeros(num_features)
        self.running_var = np.ones(num_features)
        self.grad_gamma = np.zeros_like(self.gamma)
        self.grad_beta = np.zeros_like(self.beta)

    def forward(self, x: np.ndarray, training: bool = True) -> np.ndarray:
        self.input = x
        if x.ndim == 4:
            if training:
                axes = (0, 2, 3)
                self.batch_mean = x.mean(axis=axes, keepdims=True)
                self.batch_var = x.var(axis=axes, keepdims=True)
                self.running_mean = (1 - self.momentum) * self.running_mean + self.momentum * self.batch_mean.ravel()
                self.running_var = (1 - self.momentum) * self.running_var + self.momentum * self.batch_var.ravel()
            else:
                self.batch_mean = self.running_mean.reshape(1, -1, 1, 1)
                self.batch_var = self.running_var.reshape(1, -1, 1, 1)
            x_norm = (x - self.batch_mean) / np.sqrt(self.batch_var + self.eps)
            out = self.gamma.reshape(1, -1, 1, 1) * x_norm + self.beta.reshape(1, -1, 1, 1)
        else:
            if training:
                self.batch_mean = x.mean(axis=0, keepdims=True)
                self.batch_var = x.var(axis=0, keepdims=True)
            else:
                self.batch_mean = self.running_mean.reshape(1, -1)
                self.batch_var = self.running_var.reshape(1, -1)
            x_norm = (x - self.batch_mean) / np.sqrt(self.batch_var + self.eps)
            out = self.gamma * x_norm + self.beta
        self.x_norm = x_norm
        return out

    def backward(self, dout: np.ndarray):
        if dout.ndim == 4:
            C = dout.shape[1]
            dx_hat = dout * self.gamma.reshape(1, C, 1, 1)
            x_hat = self.x_norm
            dgamma = np.sum(dout * x_hat, axis=(0, 2, 3))
            dbeta = np.sum(dout, axis=(0, 2, 3))
            mean = self.batch_mean
            var = self.batch_var
            N_H_W = dout.size / C
            dx = (1.0 / np.sqrt(var + self.eps)) * (
                dx_hat - np.sum(dx_hat, axis=(0, 2, 3), keepdims=True) / N_H_W -
                x_hat * np.sum(dx_hat * x_hat, axis=(0, 2, 3), keepdims=True) / N_H_W
            )
            self.grad_gamma = dgamma
            self.grad_beta = dbeta
            return dx
        else:
            x_hat = self.x_norm
            dgamma = np.sum(dout * x_hat, axis=0)
            dbeta = np.sum(dout, axis=0)
            var = self.batch_var
            dx = self.gamma / np.sqrt(var + self.eps) * (dout - np.mean(dout * x_hat, axis=0) * x_hat - np.mean(dout, axis=0))
            self.grad_gamma = dgamma
            self.grad_beta = dbeta
            return dx

    def parameters(self):
        return [self.gamma, self.beta]

    def gradients(self):
        return [self.grad_gamma, self.grad_beta]

    def update(self, lr: float):
        self.gamma -= lr * self.grad_gamma
        self.beta -= lr * self.grad_beta


class ResidualBlock:
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        self.conv1 = ConvLayer(in_channels, out_channels, 3, stride, 1)
        self.bn1 = BatchNormLayer(out_channels)
        self.conv2 = ConvLayer(out_channels, out_channels, 3, 1, 1)
        self.bn2 = BatchNormLayer(out_channels)
        self.shortcut_stride = stride
        self.needs_projection = (in_channels != out_channels) or (stride != 1)
        if self.needs_projection:
            self.shortcut_conv = ConvLayer(in_channels, out_channels, 1, stride, 0)
            self.shortcut_bn = BatchNormLayer(out_channels)
        else:
            self.shortcut_conv = None
            self.shortcut_bn = None

    def forward(self, x: np.ndarray, training: bool = True) -> np.ndarray:
        self.input = x
        h1 = self.conv1.forward(x)
        h1 = self.bn1.forward(h1, training)
        h1_relu = relu(h1)
        h2 = self.conv2.forward(h1_relu)
        h2 = self.bn2.forward(h2, training)
        self._h1_relu = h1_relu
        if self.needs_projection:
            shortcut = self.shortcut_conv.forward(x)
            shortcut = self.shortcut_bn.forward(shortcut, training)
        else:
            shortcut = x
        out = relu(h2 + shortcut)
        self._shortcut = shortcut
        self._h2 = h2
        return out

    def backward(self, dout: np.ndarray):
        dout_pre_relu = relu_backward(dout, self._h2 + self._shortcut)
        d2 = self.bn2.backward(dout_pre_relu)
        d2 = self.conv2.backward(d2)
        d1_relu = relu_backward(d2, self._h1_relu)
        d1 = self.bn1.backward(d1_relu)
        d1 = self.conv1.backward(d1)
        if self.needs_projection:
            dsc = self.shortcut_bn.backward(dout_pre_relu)
            dsc = self.shortcut_conv.backward(dsc)
        else:
            dsc = dout_pre_relu
        return d1 + dsc

    def parameters(self):
        params = self.conv1.parameters() + self.bn1.parameters()
        params += self.conv2.parameters() + self.bn2.parameters()
        if self.shortcut_conv is not None:
            params += self.shortcut_conv.parameters() + self.shortcut_bn.parameters()
        return params

    def update(self, lr: float):
        self.conv1.update(lr)
        self.bn1.update(lr)
        self.conv2.update(lr)
        self.bn2.update(lr)
        if self.shortcut_conv is not None:
            self.shortcut_conv.update(lr)
            self.shortcut_bn.update(lr)


class CNNBackbone:
    def __init__(self, in_channels: int = 1, base_channels: int = 32):
        self.conv1 = ConvLayer(in_channels, base_channels, 7, 2, 3)
        self.bn1 = BatchNormLayer(base_channels)
        self.pool1 = lambda x: max_pool(x, 3, 2, 1)
        self.res1 = ResidualBlock(base_channels, base_channels, 1)
        self.res2 = ResidualBlock(base_channels, base_channels * 2, 2)
        self.res3 = ResidualBlock(base_channels * 2, base_channels * 4, 2)
        self.res4 = ResidualBlock(base_channels * 4, base_channels * 4, 1)

    def forward(self, x: np.ndarray, training: bool = True) -> np.ndarray:
        self.input = x
        x = self.conv1.forward(x)
        x = self.bn1.forward(x, training)
        self._bn1_out = x.copy()
        x = relu(x)
        self._pooled_input = x.copy()
        x = self.pool1(x)
        x = self.res1.forward(x, training)
        self.skip1 = x.copy()
        x = self.res2.forward(x, training)
        self.skip2 = x.copy()
        x = self.res3.forward(x, training)
        self.skip3 = x.copy()
        x = self.res4.forward(x, training)
        return x

    def get_skip_connections(self) -> List[np.ndarray]:
        return [self.skip1, self.skip2, self.skip3]

    def backward(self, dout: np.ndarray):
        dout = self.res4.backward(dout)
        dout = self.res3.backward(dout)
        dout = self.res2.backward(dout)
        dout = self.res1.backward(dout)
        dout = max_pool_backward(dout, self._pooled_input, 3, 2, 1)
        dout = relu_backward(dout, self._bn1_out)
        dout = self.bn1.backward(dout)
        dout = self.conv1.backward(dout)
        return dout

    def parameters(self):
        params = self.conv1.parameters() + self.bn1.parameters()
        params += self.res1.parameters() + self.res2.parameters()
        params += self.res3.parameters() + self.res4.parameters()
        return params

    def update(self, lr: float):
        self.conv1.update(lr)
        self.bn1.update(lr)
        self.res1.update(lr)
        self.res2.update(lr)
        self.res3.update(lr)
        self.res4.update(lr)

    def save_weights(self, path: str):
        weights = {}
        for i, p in enumerate(self.parameters()):
            weights[f'param_{i}'] = p
        np.savez_compressed(path, **weights)

    def load_weights(self, path: str):
        data = np.load(path)
        for i, p in enumerate(self.parameters()):
            p[:] = data[f'param_{i}']
