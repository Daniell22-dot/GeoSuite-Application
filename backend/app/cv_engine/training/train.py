"""
Training script for the KLISS CV Engine.
Trains all heads using synthetic parcel plan data.
No external dependencies — pure NumPy.
"""
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.cv_engine.ops import (
    conv2d, relu, sigmoid, max_pool, softmax_2d, upsample_2x,
    conv2d_backward, relu_backward, sigmoid_backward, max_pool_backward,
    upsample_2x_backward, softmax_2d_backward, batch_norm_backward,
    mse_loss, ctc_loss,
)
from app.cv_engine.backbone import CNNBackbone
from app.cv_engine.training.synthetic_generator import generate_parcel_batch


SAVE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'cv_models')


class AdamOptimizer:
    def __init__(self, lr=1e-3, beta1=0.9, beta2=0.999, eps=1e-8):
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.t = 0
        self.m = {}
        self.v = {}

    def step(self, params, grads):
        self.t += 1
        for p, g in zip(params, grads):
            g = np.clip(g, -1.0, 1.0)
            key = id(p)
            if key not in self.m:
                self.m[key] = np.zeros_like(p)
                self.v[key] = np.zeros_like(p)
            self.m[key] = self.beta1 * self.m[key] + (1 - self.beta1) * g
            self.v[key] = self.beta2 * self.v[key] + (1 - self.beta2) * g ** 2
            m_hat = self.m[key] / (1 - self.beta1 ** self.t)
            v_hat = self.v[key] / (1 - self.beta2 ** self.t)
            p -= self.lr * m_hat / (np.sqrt(v_hat) + self.eps)


def collect_backbone_grads(backbone):
    grads = []
    grads.extend(backbone.conv1.gradients())
    grads.extend(backbone.bn1.gradients())
    for res in [backbone.res1, backbone.res2, backbone.res3, backbone.res4]:
        grads.extend(res.conv1.gradients())
        grads.extend(res.bn1.gradients())
        grads.extend(res.conv2.gradients())
        grads.extend(res.bn2.gradients())
        if res.shortcut_conv is not None:
            grads.extend(res.shortcut_conv.gradients())
            grads.extend(res.shortcut_bn.gradients())
    return grads


def preprocess_batch(images):
    gray = 0.299 * images[:, :, :, 0] + 0.587 * images[:, :, :, 1] + 0.114 * images[:, :, :, 2]
    x = gray[:, np.newaxis, :, :]
    x = x / 255.0
    return x


def train_boundary_segmenter(num_epochs=20, batch_size=2, lr=1e-3, save_every=5):
    print("\n" + "=" * 60)
    print("TRAINING BOUNDARY SEGMENTER")
    print("=" * 60)

    backbone = CNNBackbone(in_channels=1, base_channels=32)

    from app.cv_engine.heads.boundary_segmenter import DecoderBlock
    dec1 = DecoderBlock(128, 128, 64)
    dec2 = DecoderBlock(64, 64, 32)
    dec3 = DecoderBlock(32, 32, 16)
    final_w = np.random.randn(3, 16, 3, 3) * np.sqrt(2.0 / (16 * 9))
    final_b = np.zeros(3)

    optimizer = AdamOptimizer(lr=lr)

    for epoch in range(num_epochs):
        batch = generate_parcel_batch(batch_size, 256)
        images = preprocess_batch(batch['images'])
        target_masks = batch['boundary_masks']

        N, C, H, W = images.shape
        features = backbone.forward(images, training=True)
        skips = backbone.get_skip_connections()
        d1 = dec1.forward(features, skips[2])
        d2 = dec2.forward(d1, skips[1])
        d3 = dec3.forward(d2, skips[0])
        logits = conv2d(d3, final_w, final_b, 1, 1)
        probs = softmax_2d(logits)

        target_onehot = np.zeros((N, 3, probs.shape[2], probs.shape[3]), dtype=np.float64)
        for c in range(3):
            for i in range(N):
                mask_2d = (target_masks[i] == c).astype(np.float64)
                if mask_2d.shape != (probs.shape[2], probs.shape[3]):
                    from app.cv_engine.preprocessing import resize_bilinear
                    mask_2d = resize_bilinear(mask_2d, probs.shape[2], probs.shape[3])
                target_onehot[i, c] = mask_2d

        loss = -np.mean(np.sum(target_onehot * np.log(np.clip(probs, 1e-8, 1.0)), axis=1))

        dlogits = (probs - target_onehot) / N

        d3_back, final_w_grad, final_b_grad = conv2d_backward(dlogits, d3, final_w, final_b, 1, 1)
        d2_back, _ = dec3.backward(d3_back, skips[0])
        d1_back, _ = dec2.backward(d2_back, skips[1])
        df_back, _ = dec1.backward(d1_back, skips[2])
        backbone.backward(df_back)

        all_params = backbone.parameters() + dec1.parameters() + dec2.parameters() + dec3.parameters() + [final_w, final_b]
        all_grads = collect_backbone_grads(backbone) + dec1.gradients() + dec2.gradients() + dec3.gradients() + [final_w_grad, final_b_grad]

        optimizer.step(all_params, all_grads)

        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1}/{num_epochs} — loss={loss:.4f}")

        if (epoch + 1) % save_every == 0:
            save_path = os.path.join(SAVE_DIR, 'boundary_segmenter')
            os.makedirs(save_path, exist_ok=True)
            np.savez_compressed(os.path.join(save_path, 'backbone.npz'),
                                **{f'p_{i}': p for i, p in enumerate(backbone.parameters())})
            np.savez_compressed(os.path.join(save_path, 'decoder.npz'),
                                **{f'p_{i}': p for i, p in enumerate(
                                    dec1.parameters() + dec2.parameters() + dec3.parameters() +
                                    [final_w, final_b])})
            print(f"  Saved to {save_path}")

    return backbone, dec1, dec2, dec3, final_w, final_b


def train_beacon_detector(num_epochs=20, batch_size=2, lr=1e-3, save_every=5):
    print("\n" + "=" * 60)
    print("TRAINING BEACON DETECTOR")
    print("=" * 60)

    backbone = CNNBackbone(in_channels=1, base_channels=32)
    from app.cv_engine.heads.beacon_detector import BeaconHead
    head = BeaconHead(128, 4, 16)

    optimizer = AdamOptimizer(lr=lr)

    for epoch in range(num_epochs):
        batch = generate_parcel_batch(batch_size, 256)
        images = preprocess_batch(batch['images'])
        beacon_targets = np.array(batch['beacon_targets'])

        N, C, H, W = images.shape
        features = backbone.forward(images, training=True)
        raw_pred = head.forward(features)
        S = raw_pred.shape[2]

        pred_reshaped = raw_pred.transpose(0, 2, 3, 1)
        S = pred_reshaped.shape[1]
        gt = beacon_targets
        if gt.shape[1] != S or gt.shape[2] != S:
            from app.cv_engine.preprocessing import resize_bilinear
            gt_resized = np.zeros((N, S, S, gt.shape[3]), dtype=np.float64)
            for i in range(N):
                for c in range(gt.shape[3]):
                    gt_resized[i, :, :, c] = resize_bilinear(gt[i, :, :, c], S, S)
            gt = gt_resized
        obj_mask = gt[:, :, :, 0] > 0.5
        noobj_mask = ~obj_mask

        pred_obj = pred_reshaped[:, :, :, 0]
        pred_tx = pred_reshaped[:, :, :, 1]
        pred_ty = pred_reshaped[:, :, :, 2]
        pred_tw = pred_reshaped[:, :, :, 3]
        pred_tc = pred_reshaped[:, :, :, 5:]

        obj_loss = np.mean((pred_obj[obj_mask] - 1.0) ** 2) if obj_mask.any() else 0
        tx_loss = np.mean((pred_tx[obj_mask] - gt[:, :, :, 1][obj_mask]) ** 2) if obj_mask.any() else 0
        ty_loss = np.mean((pred_ty[obj_mask] - gt[:, :, :, 2][obj_mask]) ** 2) if obj_mask.any() else 0
        tw_loss = np.mean((pred_tw[obj_mask] - gt[:, :, :, 3][obj_mask]) ** 2) if obj_mask.any() else 0
        noobj_loss = np.mean(pred_obj[noobj_mask] ** 2) if noobj_mask.any() else 0

        target_classes = gt[:, :, :, 5:]
        class_loss = -np.mean(np.sum(target_classes * np.log(np.clip(pred_tc, 1e-8, 1.0)), axis=-1))

        total_loss = 5.0 * (tx_loss + ty_loss + tw_loss) + obj_loss + 0.5 * noobj_loss + class_loss

        dpred = np.zeros_like(pred_reshaped)
        scale = 5.0 / N
        dpred[:, :, :, 0] = 2 * (pred_obj - gt[:, :, :, 0]) * pred_obj * (1 - pred_obj) / N
        dpred[:, :, :, 0][noobj_mask] *= 0.5
        dpred[:, :, :, 1] = 2 * (pred_tx - gt[:, :, :, 1]) * pred_tx * (1 - pred_tx) * scale
        dpred[:, :, :, 2] = 2 * (pred_ty - gt[:, :, :, 2]) * pred_ty * (1 - pred_ty) * scale
        dpred[:, :, :, 3] = 2 * (pred_tw - gt[:, :, :, 3]) * scale
        class_grad = -target_classes / np.clip(pred_tc, 1e-8, 1.0) / N
        dpred[:, :, :, 5:] = class_grad

        dfeatures = head.backward(dpred.transpose(0, 3, 1, 2))
        backbone.backward(dfeatures)

        all_params = backbone.parameters() + head.parameters()
        all_grads = collect_backbone_grads(backbone) + head.gradients()
        optimizer.step(all_params, all_grads)

        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1}/{num_epochs} — loss={total_loss:.4f}")

        if (epoch + 1) % save_every == 0:
            save_path = os.path.join(SAVE_DIR, 'beacon_detector')
            os.makedirs(save_path, exist_ok=True)
            np.savez_compressed(os.path.join(save_path, 'backbone.npz'),
                                **{f'p_{i}': p for i, p in enumerate(backbone.parameters())})
            np.savez_compressed(os.path.join(save_path, 'head.npz'),
                                **{f'p_{i}': p for i, p in enumerate(head.parameters())})
            print(f"  Saved to {save_path}")

    return backbone, head


def train_feature_extractor(num_epochs=20, batch_size=2, lr=1e-3, save_every=5):
    print("\n" + "=" * 60)
    print("TRAINING FEATURE EXTRACTOR")
    print("=" * 60)

    backbone = CNNBackbone(in_channels=3, base_channels=32)
    from app.cv_engine.heads.feature_extractor import FeatureDecoder
    dec1 = FeatureDecoder(128, 128, 64)
    dec2 = FeatureDecoder(64, 64, 32)
    dec3 = FeatureDecoder(32, 32, 16)
    final_w = np.random.randn(9, 16, 3, 3) * np.sqrt(2.0 / (16 * 9))
    final_b = np.zeros(9)

    optimizer = AdamOptimizer(lr=lr)

    for epoch in range(num_epochs):
        batch = generate_parcel_batch(batch_size, 256)
        images = batch['images'].transpose(0, 3, 1, 2) / 255.0
        target_masks = batch['feature_masks']

        features = backbone.forward(images, training=True)
        skips = backbone.get_skip_connections()
        d1 = dec1.forward(features, skips[2])
        d2 = dec2.forward(d1, skips[1])
        d3 = dec3.forward(d2, skips[0])
        logits = conv2d(d3, final_w, final_b, 1, 1)
        probs = softmax_2d(logits)

        N = images.shape[0]
        target_onehot = np.zeros((N, 9, probs.shape[2], probs.shape[3]), dtype=np.float64)
        for c in range(9):
            for i in range(N):
                mask_2d = (target_masks[i] == c).astype(np.float64)
                if mask_2d.shape != (probs.shape[2], probs.shape[3]):
                    from app.cv_engine.preprocessing import resize_bilinear
                    mask_2d = resize_bilinear(mask_2d, probs.shape[2], probs.shape[3])
                target_onehot[i, c] = mask_2d

        loss = -np.mean(np.sum(target_onehot * np.log(np.clip(probs, 1e-8, 1.0)), axis=1))

        dlogits = (probs - target_onehot) / N
        d3_back, final_w_grad, final_b_grad = conv2d_backward(dlogits, d3, final_w, final_b, 1, 1)
        d2_back, _ = dec3.backward(d3_back, skips[0])
        d1_back, _ = dec2.backward(d2_back, skips[1])
        df_back, _ = dec1.backward(d1_back, skips[2])
        backbone.backward(df_back)

        all_params = backbone.parameters() + dec1.parameters() + dec2.parameters() + dec3.parameters() + [final_w, final_b]
        all_grads = collect_backbone_grads(backbone) + dec1.gradients() + dec2.gradients() + dec3.gradients() + [final_w_grad, final_b_grad]
        optimizer.step(all_params, all_grads)

        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1}/{num_epochs} — loss={loss:.4f}")

        if (epoch + 1) % save_every == 0:
            save_path = os.path.join(SAVE_DIR, 'feature_extractor')
            os.makedirs(save_path, exist_ok=True)
            np.savez_compressed(os.path.join(save_path, 'backbone.npz'),
                                **{f'p_{i}': p for i, p in enumerate(backbone.parameters())})
            np.savez_compressed(os.path.join(save_path, 'decoder.npz'),
                                **{f'p_{i}': p for i, p in enumerate(
                                    dec1.parameters() + dec2.parameters() + dec3.parameters() +
                                    [final_w, final_b])})
            print(f"  Saved to {save_path}")

    return backbone, dec1, dec2, dec3, final_w, final_b


def main():
    t0 = time.time()
    os.makedirs(SAVE_DIR, exist_ok=True)

    train_boundary_segmenter(num_epochs=30, batch_size=4, lr=1e-4)
    train_beacon_detector(num_epochs=30, batch_size=4, lr=1e-4)
    train_feature_extractor(num_epochs=20, batch_size=2, lr=1e-4)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"TRAINING COMPLETE — {elapsed:.1f}s total")
    print(f"Weights saved to: {SAVE_DIR}")


if __name__ == '__main__':
    main()
