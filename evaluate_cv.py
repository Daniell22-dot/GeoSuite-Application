"""
CV Engine Evaluation & Visualization
Evaluates all 3 trained heads on synthetic test data.
Generates accuracy metrics, confusion matrices, and prediction visualizations.
Outputs CSV + PNG files for documentation.
"""
import os
import sys
import time
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import ListedColormap

from app.cv_engine.ops import conv2d, relu, sigmoid, softmax_2d, max_pool, upsample_2x
from app.cv_engine.backbone import CNNBackbone
from app.cv_engine.heads.boundary_segmenter import DecoderBlock, BoundarySegmenter
from app.cv_engine.heads.beacon_detector import BeaconHead, BeaconDetector
from app.cv_engine.heads.feature_extractor import FeatureDecoder
from app.cv_engine.training.synthetic_generator import generate_parcel_batch
from app.cv_engine.preprocessing import resize_bilinear

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'cv_evaluation')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def preprocess_gray(images):
    gray = 0.299 * images[:, :, :, 0] + 0.587 * images[:, :, :, 1] + 0.114 * images[:, :, :, 2]
    return gray[:, np.newaxis, :, :] / 255.0


def load_boundary_segmenter():
    backbone = CNNBackbone(in_channels=1, base_channels=32)
    dec1 = DecoderBlock(128, 128, 64)
    dec2 = DecoderBlock(64, 64, 32)
    dec3 = DecoderBlock(32, 32, 16)
    final_w = np.random.randn(3, 16, 3, 3) * 0.01
    final_b = np.zeros(3)

    model_dir = os.path.join(os.path.dirname(__file__), 'backend', 'app', 'cv_models', 'boundary_segmenter')
    bb_path = os.path.join(model_dir, 'backbone.npz')
    dec_path = os.path.join(model_dir, 'decoder.npz')

    if os.path.exists(bb_path):
        bb_data = np.load(bb_path, allow_pickle=True)
        for i, p in enumerate(backbone.parameters()):
            if f'p_{i}' in bb_data:
                p[:] = bb_data[f'p_{i}']
    if os.path.exists(dec_path):
        dec_data = np.load(dec_path, allow_pickle=True)
        all_dec_params = dec1.parameters() + dec2.parameters() + dec3.parameters() + [final_w, final_b]
        for i, p in enumerate(all_dec_params):
            if f'p_{i}' in dec_data:
                p[:] = dec_data[f'p_{i}']

    return backbone, dec1, dec2, dec3, final_w, final_b


def load_beacon_detector():
    backbone = CNNBackbone(in_channels=1, base_channels=32)
    head = BeaconHead(128, 4, 16)

    model_dir = os.path.join(os.path.dirname(__file__), 'backend', 'app', 'cv_models', 'beacon_detector')
    bb_path = os.path.join(model_dir, 'backbone.npz')
    head_path = os.path.join(model_dir, 'head.npz')

    if os.path.exists(bb_path):
        bb_data = np.load(bb_path, allow_pickle=True)
        for i, p in enumerate(backbone.parameters()):
            if f'p_{i}' in bb_data:
                p[:] = bb_data[f'p_{i}']
    if os.path.exists(head_path):
        head_data = np.load(head_path, allow_pickle=True)
        for i, p in enumerate(head.parameters()):
            if f'p_{i}' in head_data:
                p[:] = head_data[f'p_{i}']

    return backbone, head


def load_feature_extractor():
    backbone = CNNBackbone(in_channels=3, base_channels=32)
    dec1 = FeatureDecoder(128, 128, 64)
    dec2 = FeatureDecoder(64, 64, 32)
    dec3 = FeatureDecoder(32, 32, 16)
    final_w = np.random.randn(9, 16, 3, 3) * 0.01
    final_b = np.zeros(9)

    model_dir = os.path.join(os.path.dirname(__file__), 'backend', 'app', 'cv_models', 'feature_extractor')
    bb_path = os.path.join(model_dir, 'backbone.npz')
    dec_path = os.path.join(model_dir, 'decoder.npz')

    if os.path.exists(bb_path):
        bb_data = np.load(bb_path, allow_pickle=True)
        for i, p in enumerate(backbone.parameters()):
            if f'p_{i}' in bb_data:
                p[:] = bb_data[f'p_{i}']
    if os.path.exists(dec_path):
        dec_data = np.load(dec_path, allow_pickle=True)
        all_dec_params = dec1.parameters() + dec2.parameters() + dec3.parameters() + [final_w, final_b]
        for i, p in enumerate(all_dec_params):
            if f'p_{i}' in dec_data:
                p[:] = dec_data[f'p_{i}']

    return backbone, dec1, dec2, dec3, final_w, final_b


def boundary_segmenter_predict(backbone, dec1, dec2, dec3, final_w, final_b, images_gray):
    N, C, H, W = images_gray.shape
    features = backbone.forward(images_gray, training=False)
    skips = backbone.get_skip_connections()
    d1 = dec1.forward(features, skips[2])
    d2 = dec2.forward(d1, skips[1])
    d3 = dec2.forward(d2, skips[0]) if False else dec3.forward(d2, skips[0])
    logits = conv2d(d3, final_w, final_b, 1, 1)
    probs = softmax_2d(logits)
    return np.argmax(probs, axis=1)


def beacon_detector_predict(backbone, head, images_gray):
    features = backbone.forward(images_gray, training=False)
    raw = head.forward(features)
    return raw


def feature_extractor_predict(backbone, dec1, dec2, dec3, final_w, final_b, images_rgb):
    N, C, H, W = images_rgb.shape
    features = backbone.forward(images_rgb, training=False)
    skips = backbone.get_skip_connections()
    d1 = dec1.forward(features, skips[2])
    d2 = dec2.forward(d1, skips[1])
    d3 = dec3.forward(d2, skips[0])
    logits = conv2d(d3, final_w, final_b, 1, 1)
    probs = softmax_2d(logits)
    return np.argmax(probs, axis=1)


def compute_pixel_metrics(pred, target, num_classes):
    results = {}
    total_correct = (pred == target).sum()
    total_pixels = pred.size
    results['pixel_accuracy'] = float(total_correct / total_pixels)

    per_class = {}
    ious = []
    f1s = []
    for c in range(num_classes):
        tp = ((pred == c) & (target == c)).sum()
        fp = ((pred == c) & (target != c)).sum()
        fn = ((pred != c) & (target == c)).sum()
        tn = ((pred != c) & (target != c)).sum()
        iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        cls_acc = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        per_class[c] = {
            'iou': round(iou, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1': round(f1, 4),
            'pixel_acc': round(cls_acc, 4),
            'support': int(tp + fn),
        }
        ious.append(iou)
        f1s.append(f1)
    results['mean_iou'] = round(float(np.mean(ious)), 4)
    results['mean_f1'] = round(float(np.mean(f1s)), 4)
    results['per_class'] = per_class
    return results


def compute_confusion_matrix(pred, target, num_classes):
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for i in range(num_classes):
        for j in range(num_classes):
            cm[i, j] = ((pred == i) & (target == j)).sum()
    return cm


def plot_confusion_matrix(cm, class_names, title, save_path):
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    ax.set(xticks=np.arange(cm.shape[1]), yticks=np.arange(cm.shape[0]),
           xticklabels=class_names, yticklabels=class_names,
           title=title, ylabel='True', xlabel='Predicted')
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'), ha='center', va='center',
                    color='white' if cm[i, j] > thresh else 'black', fontsize=8)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_prediction_comparison(images, gt_masks, pred_masks, class_names, cmap_colors, title, save_path, max_samples=4):
    n = min(max_samples, len(images))
    fig, axes = plt.subplots(n, 3, figsize=(15, 5 * n))
    if n == 1:
        axes = axes.reshape(1, -1)
    cmap = ListedColormap(cmap_colors)

    for i in range(n):
        img = images[i]
        if img.ndim == 3 and img.shape[0] in [1, 3]:
            img = img.transpose(1, 2, 0)
        if img.ndim == 3 and img.shape[2] == 1:
            img = img[:, :, 0]
        if img.max() <= 1.0:
            img = (img * 255).astype(np.uint8)
        else:
            img = img.astype(np.uint8)

        axes[i, 0].imshow(img, cmap='gray' if img.ndim == 2 else None)
        axes[i, 0].set_title('Input')
        axes[i, 0].axis('off')

        axes[i, 1].imshow(gt_masks[i], cmap=cmap, vmin=0, vmax=len(class_names)-1, interpolation='nearest')
        axes[i, 1].set_title('Ground Truth')
        axes[i, 1].axis('off')

        axes[i, 2].imshow(pred_masks[i], cmap=cmap, vmin=0, vmax=len(class_names)-1, interpolation='nearest')
        axes[i, 2].set_title('Prediction')
        axes[i, 2].axis('off')

    patches = [plt.Rectangle((0, 0), 1, 1, fc=cmap_colors[j]) for j in range(len(class_names))]
    fig.legend(patches, class_names, loc='lower center', ncol=min(len(class_names), 5), fontsize=8, frameon=True)
    fig.suptitle(title, fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_beacon_predictions(images, gt_targets, raw_preds, save_path, max_samples=4):
    n = min(max_samples, len(images))
    fig, axes = plt.subplots(n, 2, figsize=(12, 5 * n))
    if n == 1:
        axes = axes.reshape(1, -1)

    type_names = ['iron_pin', 'concrete', 'triangle', 'unknown']

    for i in range(n):
        img = images[i]
        if img.ndim == 3 and img.shape[0] in [1, 3]:
            img = img.transpose(1, 2, 0)
        if img.ndim == 3 and img.shape[2] == 1:
            img = img[:, :, 0]
        if img.max() <= 1.0:
            img = (img * 255).astype(np.uint8)
        else:
            img = img.astype(np.uint8)

        axes[i, 0].imshow(img, cmap='gray' if img.ndim == 2 else None)
        gt = gt_targets[i]
        S_gt = gt.shape[0]
        for r in range(S_gt):
            for c in range(S_gt):
                if gt[r, c, 0] > 0.5:
                    cx = (c + gt[r, c, 1]) / S_gt
                    cy = (r + gt[r, c, 2]) / S_gt
                    cls = int(np.argmax(gt[r, c, 5:]))
                    color = ['red', 'blue', 'green', 'gray'][cls]
                    axes[i, 0].plot(cx, img.shape[0] * (1 - cy), 'o', color=color, markersize=6)
        axes[i, 0].set_title(f'Ground Truth ({sum(1 for r in range(S_gt) for c in range(S_gt) if gt[r,c,0]>0.5)} beacons)')
        axes[i, 0].axis('off')

        axes[i, 1].imshow(img, cmap='gray' if img.ndim == 2 else None)
        pred = raw_preds[i].transpose(1, 2, 0)
        S = pred.shape[0]
        for r in range(S):
            for c in range(S):
                obj_conf = 1.0 / (1.0 + np.exp(-pred[r, c, 0]))
                if obj_conf > 0.3:
                    cx = (c + 1.0 / (1.0 + np.exp(-pred[r, c, 1]))) / S
                    cy = (r + 1.0 / (1.0 + np.exp(-pred[r, c, 2]))) / S
                    cls = int(np.argmax(pred[r, c, 5:]))
                    color = ['red', 'blue', 'green', 'gray'][cls]
                    size = obj_conf * 8
                    axes[i, 1].plot(cx, img.shape[0] * (1 - cy), 'o', color=color, markersize=size)
        axes[i, 1].set_title(f'Prediction (conf>0.3)')
        axes[i, 1].axis('off')

    type_colors = ['red', 'blue', 'green', 'gray']
    patches = [plt.Rectangle((0, 0), 1, 1, fc=type_colors[j]) for j in range(len(type_names))]
    fig.legend(patches, type_names, loc='lower center', ncol=4, fontsize=9, frameon=True)
    fig.suptitle('Beacon Detection — Ground Truth vs Prediction', fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0.06, 1, 0.95])
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_bar_chart(names, values, title, ylabel, save_path, color='steelblue'):
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(names, values, color=color, edgecolor='white', linewidth=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f'{val:.1%}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, max(values) * 1.15 if max(values) > 0 else 1.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_metric_radar(class_names, metric_values, title, save_path):
    n = len(class_names)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    metric_values = metric_values + [metric_values[0]]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.plot(angles, metric_values, 'o-', linewidth=2, color='steelblue')
    ax.fill(angles, metric_values, alpha=0.25, color='steelblue')
    ax.set_thetagrids(np.degrees(angles[:-1]), class_names, fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=20)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def main():
    results = {}
    NUM_EVAL = 8
    IMG_SIZE = 256

    print("=" * 60)
    print("CV ENGINE EVALUATION")
    print("=" * 60)

    batch = generate_parcel_batch(NUM_EVAL, IMG_SIZE)
    images_nhwc = batch['images']
    boundary_masks = batch['boundary_masks']
    feature_masks = batch['feature_masks']
    beacon_targets_list = batch['beacon_targets']
    beacon_targets = np.array(beacon_targets_list)

    print(f"\nGenerated {NUM_EVAL} test images at {IMG_SIZE}x{IMG_SIZE}")

    boundary_class_names = ['Background', 'Boundary', 'Beacon']
    feature_class_names = ['Background', 'Boundary', 'Beacon', 'Road', 'Residential',
                           'Agricultural', 'Commercial', 'Water', 'Vegetation']
    boundary_cmap = ['#f5f0e1', '#1a1a1a', '#ff3333']
    feature_cmap = ['#f5f0e1', '#1a1a1a', '#ff3333', '#808080', '#c8b8d8',
                    '#228B22', '#d4a017', '#4488ff', '#006400']

    t0 = time.time()

    print("\n--- Boundary Segmenter ---")
    backbone_b, dec1_b, dec2_b, dec3_b, fw_b, fb_b = load_boundary_segmenter()
    images_gray = preprocess_gray(images_nhwc)
    t1 = time.time()
    pred_boundary = boundary_segmenter_predict(backbone_b, dec1_b, dec2_b, dec3_b, fw_b, fb_b, images_gray)
    t_bench = time.time() - t1
    print(f"  Inference: {t_bench*1000:.0f}ms total ({t_bench/NUM_EVAL*1000:.0f}ms/image)")

    if pred_boundary.shape[1:] != boundary_masks.shape[1:]:
        pred_boundary_resized = np.zeros((NUM_EVAL, boundary_masks.shape[1], boundary_masks.shape[2]), dtype=np.int64)
        for i in range(NUM_EVAL):
            pred_boundary_resized[i] = np.round(
                resize_bilinear(pred_boundary[i].astype(np.float64),
                                boundary_masks.shape[1], boundary_masks.shape[2])
            ).astype(np.int64)
            pred_boundary_resized[i] = np.clip(pred_boundary_resized[i], 0, 2)
        pred_boundary = pred_boundary_resized

    boundary_metrics = compute_pixel_metrics(pred_boundary, boundary_masks, 3)
    boundary_cm = compute_confusion_matrix(pred_boundary.flatten(), boundary_masks.flatten(), 3)
    results['boundary_segmenter'] = boundary_metrics
    print(f"  Pixel Accuracy: {boundary_metrics['pixel_accuracy']:.1%}")
    print(f"  Mean IoU: {boundary_metrics['mean_iou']:.1%}")
    print(f"  Mean F1: {boundary_metrics['mean_f1']:.1%}")
    for c, info in boundary_metrics['per_class'].items():
        print(f"    {boundary_class_names[c]}: IoU={info['iou']:.1%} F1={info['f1']:.1%} support={info['support']}")

    plot_confusion_matrix(boundary_cm, boundary_class_names,
                          'Boundary Segmenter — Confusion Matrix',
                          os.path.join(OUTPUT_DIR, 'boundary_confusion_matrix.png'))
    plot_prediction_comparison(images_nhwc, boundary_masks, pred_boundary, boundary_class_names, boundary_cmap,
                               'Boundary Segmenter — Predictions vs Ground Truth',
                               os.path.join(OUTPUT_DIR, 'boundary_predictions.png'))
    plot_bar_chart(boundary_class_names,
                   [boundary_metrics['per_class'][c]['f1'] for c in range(3)],
                   'Boundary Segmenter — F1 Score per Class', 'F1 Score',
                   os.path.join(OUTPUT_DIR, 'boundary_f1_scores.png'))

    print("\n--- Beacon Detector ---")
    backbone_bd, head_bd = load_beacon_detector()
    t1 = time.time()
    raw_preds = beacon_detector_predict(backbone_bd, head_bd, images_gray)
    t_bench = time.time() - t1
    print(f"  Inference: {t_bench*1000:.0f}ms total ({t_bench/NUM_EVAL*1000:.0f}ms/image)")

    beacon_type_names = ['iron_pin', 'concrete', 'triangle', 'unknown']
    pred_conf = 1.0 / (1.0 + np.exp(-raw_preds[:, 0, :, :]))
    S_pred = pred_conf.shape[1]
    S_gt = beacon_targets.shape[1]
    if S_pred != S_gt:
        pred_conf_resized = np.zeros((NUM_EVAL, S_gt, S_gt), dtype=np.float64)
        for i in range(NUM_EVAL):
            pred_conf_resized[i] = resize_bilinear(pred_conf[i], S_gt, S_gt)
        pred_conf = pred_conf_resized
        pred_probs = np.zeros((NUM_EVAL, S_gt, S_gt, raw_preds.shape[1]), dtype=np.float64)
        for i in range(NUM_EVAL):
            for c in range(raw_preds.shape[1]):
                pred_probs[i, :, :, c] = resize_bilinear(raw_preds[i, c], S_gt, S_gt)
        pred_conf = 1.0 / (1.0 + np.exp(-pred_probs[:, :, :, 0]))
        pred_probs[:, :, :, 0] = pred_conf
    gt_has_beacon = beacon_targets[:, :, :, 0] > 0.5
    pred_has_beacon = pred_conf > 0.3

    tp = ((pred_has_beacon) & (gt_has_beacon)).sum()
    fp = ((pred_has_beacon) & (~gt_has_beacon)).sum()
    fn = ((~pred_has_beacon) & (gt_has_beacon)).sum()
    tn = ((~pred_has_beacon) & (~gt_has_beacon)).sum()
    det_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    det_recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    det_f1 = 2 * det_precision * det_recall / (det_precision + det_recall) if (det_precision + det_recall) > 0 else 0

    beacon_metrics = {
        'precision': round(float(det_precision), 4),
        'recall': round(float(det_recall), 4),
        'f1': round(float(det_f1), 4),
        'tp': int(tp), 'fp': int(fp), 'fn': int(fn), 'tn': int(tn),
    }
    results['beacon_detector'] = beacon_metrics
    print(f"  Precision: {det_precision:.1%}")
    print(f"  Recall: {det_recall:.1%}")
    print(f"  F1: {det_f1:.1%}")
    print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")

    plot_beacon_predictions(images_nhwc, beacon_targets, raw_preds,
                            os.path.join(OUTPUT_DIR, 'beacon_predictions.png'))
    plot_bar_chart(['Precision', 'Recall', 'F1'],
                   [det_precision, det_recall, det_f1],
                   'Beacon Detector — Detection Metrics', 'Score',
                   os.path.join(OUTPUT_DIR, 'beacon_metrics.png'), color='#d4a017')

    print("\n--- Feature Extractor ---")
    backbone_f, dec1_f, dec2_f, dec3_f, fw_f, fb_f = load_feature_extractor()
    images_rgb = images_nhwc.transpose(0, 3, 1, 2) / 255.0
    t1 = time.time()
    pred_features = feature_extractor_predict(backbone_f, dec1_f, dec2_f, dec3_f, fw_f, fb_f, images_rgb)
    t_bench = time.time() - t1
    print(f"  Inference: {t_bench*1000:.0f}ms total ({t_bench/NUM_EVAL*1000:.0f}ms/image)")

    if pred_features.shape[2:] != feature_masks.shape[1:]:
        pred_features_resized = np.zeros((NUM_EVAL, feature_masks.shape[1], feature_masks.shape[2]), dtype=np.int64)
        for i in range(NUM_EVAL):
            pred_features_resized[i] = np.round(
                resize_bilinear(pred_features[i].astype(np.float64),
                                feature_masks.shape[1], feature_masks.shape[2])
            ).astype(np.int64)
            pred_features_resized[i] = np.clip(pred_features_resized[i], 0, 8)
        pred_features = pred_features_resized

    feature_metrics = compute_pixel_metrics(pred_features, feature_masks, 9)
    feature_cm = compute_confusion_matrix(pred_features.flatten(), feature_masks.flatten(), 9)
    results['feature_extractor'] = feature_metrics
    print(f"  Pixel Accuracy: {feature_metrics['pixel_accuracy']:.1%}")
    print(f"  Mean IoU: {feature_metrics['mean_iou']:.1%}")
    print(f"  Mean F1: {feature_metrics['mean_f1']:.1%}")
    for c, info in feature_metrics['per_class'].items():
        print(f"    {feature_class_names[c]}: IoU={info['iou']:.1%} F1={info['f1']:.1%} support={info['support']}")

    plot_confusion_matrix(feature_cm, feature_class_names,
                          'Feature Extractor — Confusion Matrix',
                          os.path.join(OUTPUT_DIR, 'feature_confusion_matrix.png'))
    plot_prediction_comparison(images_nhwc, feature_masks, pred_features, feature_class_names, feature_cmap,
                               'Feature Extractor — Predictions vs Ground Truth',
                               os.path.join(OUTPUT_DIR, 'feature_predictions.png'))

    valid_f1 = [feature_metrics['per_class'][c]['f1'] for c in range(9) if feature_metrics['per_class'][c]['support'] > 0]
    valid_names = [feature_class_names[c] for c in range(9) if feature_metrics['per_class'][c]['support'] > 0]
    plot_bar_chart(valid_names, valid_f1,
                   'Feature Extractor — F1 Score per Class', 'F1 Score',
                   os.path.join(OUTPUT_DIR, 'feature_f1_scores.png'), color='#228B22')
    plot_metric_radar(valid_names, valid_f1,
                      'Feature Extractor — Per-Class F1 Radar',
                      os.path.join(OUTPUT_DIR, 'feature_radar.png'))

    total_time = time.time() - t0

    results['evaluation_meta'] = {
        'num_test_images': NUM_EVAL,
        'image_size': IMG_SIZE,
        'total_time_seconds': round(total_time, 1),
    }

    json_path = os.path.join(OUTPUT_DIR, 'evaluation_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"EVALUATION COMPLETE — {total_time:.1f}s")
    print(f"Results saved to: {OUTPUT_DIR}")
    print(f"  evaluation_results.json")
    print(f"  boundary_confusion_matrix.png")
    print(f"  boundary_predictions.png")
    print(f"  boundary_f1_scores.png")
    print(f"  beacon_predictions.png")
    print(f"  beacon_metrics.png")
    print(f"  feature_confusion_matrix.png")
    print(f"  feature_predictions.png")
    print(f"  feature_f1_scores.png")
    print(f"  feature_radar.png")


if __name__ == '__main__':
    main()
