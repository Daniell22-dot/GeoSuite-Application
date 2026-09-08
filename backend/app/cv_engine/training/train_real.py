"""
Train the KLISS CV engine heads on the real Kenya training dataset.

Loads the real 256x256 plan patches from DATASETS/kenya_training/train/,
derives beacon labels heuristically (junction/corner points of the drawn
boundary lines), splits the patches into a train/test partition (deterministic
seed), trains boundary_segmenter, beacon_detector and feature_extractor with a
compatible batch source, evaluates on the held-out test split, and saves the
trained weights into backend/app/cv_models/.

Pure NumPy + scipy (optional) — no external ML framework.
"""
import os
import sys
import time
import json
import random

import numpy as np

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.insert(0, os.path.join(REPO_ROOT, 'backend'))

try:
    from scipy import ndimage as scipy_ndimage
    HAS_SCIPY = True
except ImportError:
    scipy_ndimage = None
    HAS_SCIPY = False

from app.cv_engine.training.train import (
    train_boundary_segmenter,
    train_beacon_detector,
    train_feature_extractor,
)
from app.cv_engine.training.synthetic_generator import (
    _build_yolo_targets,
    GRID_SIZE,
    YOLO_CHANNELS,
)

DATASET_DIR = os.path.join(REPO_ROOT, 'DATASETS', 'kenya_training', 'train')
SAVE_DIR = os.path.join(REPO_ROOT, 'backend', 'app', 'cv_models')
GRID = GRID_SIZE
SEED = 42
TEST_SPLIT = 7


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def _load_npy_folder(folder: str) -> list[np.ndarray]:
    files = sorted(f for f in os.listdir(folder) if f.endswith('.npy'))
    return [np.load(os.path.join(folder, f)) for f in files]


def load_real_dataset() -> dict:
    """Load images + masks into a single dict of lists."""
    images = _load_npy_folder(os.path.join(DATASET_DIR, 'images'))
    boundary_masks = _load_npy_folder(os.path.join(DATASET_DIR, 'boundary_masks'))
    feature_masks = _load_npy_folder(os.path.join(DATASET_DIR, 'feature_masks'))

    n = len(images)
    assert len(boundary_masks) == n and len(feature_masks) == n, (
        f"Mismatched dataset sizes: images={n} bmask={len(boundary_masks)} fmask={len(feature_masks)}"
    )
    print(f"Loaded {n} real patches from {DATASET_DIR}")
    for i in range(n):
        assert images[i].shape[:2] == boundary_masks[i].shape == feature_masks[i].shape, (
            f"Patch {i} shape mismatch: {images[i].shape} vs {boundary_masks[i].shape}"
        )
    return {
        'images': images,
        'boundary_masks': boundary_masks,
        'feature_masks': feature_masks,
    }


# ---------------------------------------------------------------------------
# Beacon heuristic
# ---------------------------------------------------------------------------

def _junction_pixels(boundary: np.ndarray) -> np.ndarray:
    """Return bool mask of boundary pixels where >=3 boundary arms meet (junctions).

    Junction points of drawn parcel lines are used as a heuristic for survey
    beacons: in cadastral plans beacons are placed at parcel corners where the
    boundary lines change direction or meet.
    """
    b = (boundary > 0).astype(np.int32)
    from app.cv_engine.ops import conv2d
    kernel = np.ones((1, 1, 3, 3), dtype=np.float64)
    kernel[0, 0, 1, 1] = 0
    x = b[np.newaxis, np.newaxis].astype(np.float64)
    nbr = conv2d(x, kernel, np.zeros(1), stride=1, padding=1)[0, 0]
    return (nbr >= 3).astype(bool) & (b > 0)


def _beacon_targets_from_junctions(boundary: np.ndarray, image_size: int) -> np.ndarray:
    """Build a (GRID, GRID, YOLO_CHANNELS) YOLO target tensor from junction pixels.

    Every grid cell that contains a junction is assigned one beacon whose center
    is the mean of the junction pixels in that cell. Beacon type is 'unknown'
    (class index 3) since the real plans carry no labelled type info.
    """
    cells = _junction_pixels(boundary)
    targets = np.zeros((GRID, GRID, YOLO_CHANNELS), dtype=np.float64)
    junctions_y, junctions_x = np.where(cells)
    if junctions_y.size == 0:
        return targets

    cell = image_size / GRID
    cell_pixels = np.zeros((GRID, GRID), dtype=bool)
    gy = (junctions_y / cell).astype(int)
    gx = (junctions_x / cell).astype(int)
    gy = np.clip(gy, 0, GRID - 1)
    gx = np.clip(gx, 0, GRID - 1)
    cell_pixels[gy, gx] = True

    for r in range(GRID):
        for c in range(GRID):
            if not cell_pixels[r, c]:
                continue
            idx = np.where((gy == r) & (gx == c))[0]
            cy_px = float(np.mean(junctions_y[idx]))
            cx_px = float(np.mean(junctions_x[idx]))
            col = int(cx_px / cell)
            row = int(cy_px / cell)
            col = max(0, min(col, GRID - 1))
            row = max(0, min(row, GRID - 1))
            ox = (cx_px - col * cell) / cell
            oy = (cy_px - row * cell) / cell
            targets[row, col, 0] = 1.0
            targets[row, col, 1] = ox
            targets[row, col, 2] = oy
            targets[row, col, 3] = 12.0 / image_size
            targets[row, col, 4] = 12.0 / image_size
            targets[row, col, 5 + 3] = 1.0  # unknown type
    return targets


def apply_beacon_labels(dataset: dict) -> None:
    """In-place: mark beacon pixels (class 2) in masks + build YOLO targets."""
    beacon_targets = []
    for i in range(len(dataset['images'])):
        bmask = dataset['boundary_masks'][i]
        image_size = bmask.shape[0]
        yolo = _beacon_targets_from_junctions(bmask, image_size)
        beacon_targets.append(yolo)
        cells = _junction_pixels(bmask)
        dataset['boundary_masks'][i] = np.where(cells, 2, bmask).astype(np.int32)
        dataset['feature_masks'][i] = np.where(cells, 2, dataset['feature_masks'][i]).astype(np.int32)
    dataset['beacon_targets'] = beacon_targets


# ---------------------------------------------------------------------------
# Batch source (matches synthetic_generator.generate_parcel_batch's contract)
# ---------------------------------------------------------------------------

class RealBatchSource:
    def __init__(self, samples: list[int], images, bmasks, fmasks, targets,
                 image_size: int = 256, seed: int = SEED, strength: float = 1.0):
        self.samples = list(samples)
        self.images = images
        self.bmasks = bmasks
        self.fmasks = fmasks
        self.targets = targets
        self.image_size = image_size
        self.rng = random.Random(seed)
        self.order = list(samples)
        self.rng.shuffle(self.order)
        self.pos = 0

    def _next_epoch_order(self):
        self.rng.shuffle(self.order)
        self.pos = 0

    def __call__(self, batch_size: int, image_size: int = None):
        size = self.image_size if image_size is None else image_size
        out_images = []
        out_bmasks = []
        out_fmasks = []
        out_targets = []
        for _ in range(batch_size):
            if self.pos >= len(self.order):
                self._next_epoch_order()
            idx = self.order[self.pos]
            self.pos += 1

            img = self.images[idx]
            if img.ndim == 2:
                img = np.repeat(img[:, :, np.newaxis], 3, axis=2)
            img = np.asarray(img, dtype=np.float64)
            if img.shape[0] != size or img.shape[1] != size:
                from app.cv_engine.preprocessing import resize_bilinear
                img_r = np.zeros((size, size, img.shape[2]), dtype=np.float64)
                for ch in range(img.shape[2]):
                    img_r[:, :, ch] = resize_bilinear(img[:, :, ch], size, size)
                img = img_r

            bmask = np.asarray(self.bmasks[idx], dtype=np.int32)
            fmask = np.asarray(self.fmasks[idx], dtype=np.int32)
            if bmask.shape[0] != size or bmask.shape[1] != size:
                from app.cv_engine.preprocessing import resize_bilinear
                bmask = np.round(resize_bilinear(bmask.astype(np.float64), size, size)).astype(np.int32)
                fmask = np.round(resize_bilinear(fmask.astype(np.float64), size, size)).astype(np.int32)

            out_images.append(img)
            out_bmasks.append(bmask)
            out_fmasks.append(fmask)
            out_targets.append(self.targets[idx])

        return {
            'images': np.stack(out_images, axis=0),
            'beacon_targets': out_targets,
            'boundary_masks': np.stack(out_bmasks, axis=0),
            'feature_masks': np.stack(out_fmasks, axis=0),
        }


# ---------------------------------------------------------------------------
# Evaluation on held-out split
# ---------------------------------------------------------------------------

def evaluate_test_split(train_fn_products, dataset, test_idx):
    print("\n" + "=" * 60)
    print("EVALUATING ON HELD-OUT TEST SPLIT")
    print("=" * 60)
    results = {}
    image_size = dataset['images'][0].shape[0]
    test_images = [dataset['images'][i] for i in test_idx]
    test_bmasks = [dataset['boundary_masks'][i] for i in test_idx]
    test_fmasks = [dataset['feature_masks'][i] for i in test_idx]
    test_targets = [dataset['beacon_targets'][i] for i in test_idx]

    batch_source = RealBatchSource(test_idx, dataset['images'], dataset['boundary_masks'],
                                   dataset['feature_masks'], dataset['beacon_targets'],
                                   image_size=image_size)
    batch = batch_source.__call__(len(test_idx))

    # ---- boundary segmenter ----
    bb, dec1, dec2, dec3, fw, fb = train_fn_products['boundary']
    from app.cv_engine.ops import conv2d, softmax_2d
    gray = 0.299 * batch['images'][:, :, :, 0] + 0.587 * batch['images'][:, :, :, 1] + 0.114 * batch['images'][:, :, :, 2]
    x = gray[:, np.newaxis, :, :] / 255.0
    feats = bb.forward(x, training=False)
    skips = bb.get_skip_connections()
    d1 = dec1.forward(feats, skips[2])
    d2 = dec2.forward(d1, skips[1])
    d3 = dec3.forward(d2, skips[0])
    logits = conv2d(d3, fw, fb, 1, 1)
    probs = softmax_2d(logits)
    pred_b = np.argmax(probs, axis=1)
    gt_b = batch['boundary_masks']
    if pred_b.shape[1:] != gt_b.shape[1:]:
        from app.cv_engine.preprocessing import resize_bilinear
        resized = np.zeros((pred_b.shape[0], gt_b.shape[1], gt_b.shape[2]), dtype=np.int64)
        for i in range(pred_b.shape[0]):
            resized[i] = np.clip(np.round(resize_bilinear(pred_b[i].astype(np.float64), gt_b.shape[1], gt_b.shape[2])), 0, 2)
        pred_b = resized
    results['boundary_segmenter'] = _pixel_metrics(pred_b, gt_b, 3)

    # ---- beacon detector ----
    bb_bd, head = train_fn_products['beacon']
    raw = head.forward(bb_bd.forward(x, training=False))
    S = raw.shape[2]
    pred_conf = 1.0 / (1.0 + np.exp(-raw[:, 0, :, :]))
    gt_targets = np.array([t for t in test_targets])
    if S != gt_targets.shape[1] or S != gt_targets.shape[2]:
        from app.cv_engine.preprocessing import resize_bilinear
        resized_conf = np.zeros((pred_conf.shape[0], gt_targets.shape[1], gt_targets.shape[2]), dtype=np.float64)
        for i in range(pred_conf.shape[0]):
            resized_conf[i] = resize_bilinear(pred_conf[i], gt_targets.shape[1], gt_targets.shape[2])
        pred_conf = resized_conf
    matched = _beacon_det_metrics(pred_conf, gt_targets[:, :, :, 0] > 0.5, thresh=0.3, window=1)
    results['beacon_detector'] = matched

    # ---- feature extractor ----
    bbf, fdec1, fdec2, fdec3, ffw, ffb = train_fn_products['feature']
    xrgb = batch['images'].transpose(0, 3, 1, 2) / 255.0
    feats = bbf.forward(xrgb, training=False)
    skips = bbf.get_skip_connections()
    d1 = fdec1.forward(feats, skips[2])
    d2 = fdec2.forward(d1, skips[1])
    d3 = fdec3.forward(d2, skips[0])
    logits = conv2d(d3, ffw, ffb, 1, 1)
    probs = softmax_2d(logits)
    pred_f = np.argmax(probs, axis=1)
    gt_f = batch['feature_masks']
    if pred_f.shape[1:] != gt_f.shape[1:]:
        from app.cv_engine.preprocessing import resize_bilinear
        resized = np.zeros((pred_f.shape[0], gt_f.shape[1], gt_f.shape[2]), dtype=np.int64)
        for i in range(pred_f.shape[0]):
            resized[i] = np.clip(np.round(resize_bilinear(pred_f[i].astype(np.float64), gt_f.shape[1], gt_f.shape[2])), 0, 8)
        pred_f = resized
    results['feature_extractor'] = _pixel_metrics(pred_f, gt_f, 9)

    return results


def _pixel_metrics(pred, target, num_classes):
    results = {}
    results['pixel_accuracy'] = float((pred == target).sum() / pred.size)
    per_class = {}
    ious = []
    f1s = []
    for c in range(num_classes):
        tp = ((pred == c) & (target == c)).sum()
        fp = ((pred == c) & (target != c)).sum()
        fn = ((pred != c) & (target == c)).sum()
        iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_class[c] = {
            'iou': round(float(iou), 4),
            'precision': round(float(precision), 4),
            'recall': round(float(recall), 4),
            'f1': round(float(f1), 4),
            'support': int(tp + fn),
        }
        ious.append(iou)
        f1s.append(f1)
    results['mean_iou'] = round(float(np.mean(ious)), 4)
    results['mean_f1'] = round(float(np.mean(f1s)), 4)
    results['per_class'] = per_class
    return results


def _beacon_det_metrics(pred_conf, gt_mask, thresh=0.3, window=1):
    pred = pred_conf > thresh
    gt = gt_mask
    if pred.shape[1:] != gt.shape[1:]:
        from app.cv_engine.preprocessing import resize_bilinear
        resized = np.zeros((pred.shape[0], gt.shape[1], gt.shape[2]), dtype=np.float64)
        for i in range(pred.shape[0]):
            resized[i] = resize_bilinear(pred[i].astype(np.float64), gt.shape[1], gt.shape[2])
        pred = resized > thresh

    tp = fp = fn = 0
    for i in range(pred.shape[0]):
        gcells = np.argwhere(gt[i])
        pcells = np.argwhere(pred[i])
        for (py, px) in pcells:
            matched_any = any(max(abs(py - gy), abs(px - gx)) <= window for (gy, gx) in gcells)
            if matched_any:
                tp += 1
            else:
                fp += 1
        for (gy, gx) in gcells:
            matched_any = any(max(abs(py - gy), abs(px - gx)) <= window for (py, px) in pcells)
            if not matched_any:
                fn += 1
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        'precision': round(float(precision), 4),
        'recall': round(float(recall), 4),
        'f1': round(float(f1), 4),
        'tp': int(tp), 'fp': int(fp), 'fn': int(fn),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    os.makedirs(SAVE_DIR, exist_ok=True)

    print("=" * 60)
    print("REAL-DATA TRAINING (KENYA TRAINING SET)")
    print("=" * 60)

    dataset = load_real_dataset()
    images = dataset['images']
    bmasks = dataset['boundary_masks']
    fmasks = dataset['feature_masks']
    n = len(images)

    n_train = n - TEST_SPLIT
    rng = np.random.RandomState(SEED)
    perm = rng.permutation(n)
    train_idx = sorted(perm[:n_train].tolist())
    test_idx = sorted(perm[n_train:].tolist())
    print(f"Split: {n_train} train / {TEST_SPLIT} test (seed={SEED})")
    print(f"  train indices: {train_idx}")
    print(f"  test  indices: {test_idx}")

    apply_beacon_labels(dataset)
    n_beacons = [int((t[:, :, 0] > 0.5).sum()) for t in dataset['beacon_targets']]
    print(f"Beacons derived heuristically: total={sum(n_beacons)}, per-patch={n_beacons}")

    for split, idx in [('train', train_idx), ('test', test_idx)]:
        fb = RealBatchSource(idx, dataset['images'], dataset['boundary_masks'],
                             dataset['feature_masks'], dataset['beacon_targets'])
        b = fb.__call__(len(idx))
        got = sum(int((t[:, :, 0] > 0.5).sum()) for t in b['beacon_targets'])
        print(f"  {split} split preview: {len(idx)} patches, images {b['images'].shape}, " +
              f"bmask {b['boundary_masks'].shape}, fmask {b['feature_masks'].shape}, beacons={got}")

    train_source = RealBatchSource(train_idx, dataset['images'], dataset['boundary_masks'],
                                   dataset['feature_masks'], dataset['beacon_targets'])

    boundary_models = train_boundary_segmenter(
        num_epochs=40, batch_size=4, lr=1e-4, save_every=10, batch_source=train_source)
    beacon_models = train_beacon_detector(
        num_epochs=40, batch_size=4, lr=1e-4, save_every=10, batch_source=train_source)
    feature_models = train_feature_extractor(
        num_epochs=40, batch_size=3, lr=1e-4, save_every=10, batch_source=train_source)

    products = {
        'boundary': boundary_models,
        'beacon': beacon_models,
        'feature': feature_models,
    }

    results = evaluate_test_split(products, dataset, test_idx)

    results['meta'] = {
        'dataset': DATASET_DIR,
        'num_train': len(train_idx),
        'num_test': len(test_idx),
        'seed': SEED,
        'train_indices': train_idx,
        'test_indices': test_idx,
        'beacons_derived_total': sum(n_beacons),
        'grid_size': GRID,
        'yolo_channels': YOLO_CHANNELS,
        'total_time_seconds': round(time.time() - t0, 1),
    }

    out_json = os.path.join(SAVE_DIR, '..', '..', '..', '..', 'cv_evaluation',
                            'evaluation_real_test.json')
    out_json = os.path.normpath(out_json)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, 'w') as f:
        json.dump(results, f, indent=2)

    print("\n--- Test split metrics ---")
    for name, metrics in results.items():
        if name == 'meta':
            continue
        print(f"  {name}:")
        for k, v in metrics.items():
            if k in ('pixel_accuracy', 'mean_iou', 'mean_f1'):
                print(f"    {k}: {v:.4f}")
            elif k in ('precision', 'recall', 'f1', 'tp', 'fp', 'fn'):
                print(f"    {k}: {v}")
    print(f"\nResults: {out_json}")

    print("\n" + "=" * 60)
    print(f"TRAINING + EVAL COMPLETE — {time.time() - t0:.1f}s")
    print(f"Weights saved to: {SAVE_DIR}")


if __name__ == '__main__':
    main()