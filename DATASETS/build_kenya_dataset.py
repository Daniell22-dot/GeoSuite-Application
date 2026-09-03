"""
Build training dataset from ANGOROM cadastral plans + WhatsApp photos.
Skips WorldCover (too large to load in memory).
"""
import os
import numpy as np
from PIL import Image
import json

BASE_DIR = r"D:\Geospatial_suite"
RAW_DIR = os.path.join(BASE_DIR, "RAW DATA")
DATASETS_DIR = os.path.join(BASE_DIR, "DATASETS")
OUTPUT_DIR = os.path.join(DATASETS_DIR, "kenya_training")

BOUNDARY_CLASSES = {0: "background", 1: "boundary", 2: "beacon"}
FEATURE_CLASSES = {
    0: "background", 1: "boundary", 2: "beacon", 3: "road",
    4: "residential", 5: "agricultural", 6: "commercial",
    7: "water", 8: "vegetation"
}


def ensure_dirs():
    for split in ["train", "val", "test"]:
        for subdir in ["images", "boundary_masks", "feature_masks"]:
            os.makedirs(os.path.join(OUTPUT_DIR, split, subdir), exist_ok=True)


def load_image(path, target_size=None):
    img = Image.open(path).convert("RGB")
    if target_size:
        img = img.resize(target_size, Image.BILINEAR)
    return np.array(img, dtype=np.float64)


def extract_patches(img_array, patch_size=256, stride=128):
    h, w = img_array.shape[:2]
    patches = []
    for y in range(0, h - patch_size + 1, stride):
        for x in range(0, w - patch_size + 1, stride):
            patch = img_array[y:y+patch_size, x:x+patch_size]
            gray = np.mean(patch, axis=2)
            if np.std(gray) > 15:
                patches.append(patch)
    return patches


def create_boundary_mask(img):
    gray = np.mean(img, axis=2)
    mask = np.zeros(img.shape[:2], dtype=np.int32)
    mask[gray < 128] = 1  # dark lines = boundary
    return mask


def create_feature_mask(img):
    gray = np.mean(img, axis=2)
    mask = np.zeros(img.shape[:2], dtype=np.int32)
    mask[gray < 128] = 1  # dark lines = boundary
    # Could add more heuristics here for text, numbers, etc.
    return mask


def process_angorom():
    print("--- ANGOROM Survey Plans ---")
    files = sorted([f for f in os.listdir(RAW_DIR) if f.startswith("ANGOROM") and f.endswith(".jpg")])
    all_patches = []
    all_boundary_masks = []
    all_feature_masks = []
    
    for fname in files:
        path = os.path.join(RAW_DIR, fname)
        img = load_image(path)
        h, w = img.shape[:2]
        patches = extract_patches(img)
        
        for p in patches:
            bm = create_boundary_mask(p)
            fm = create_feature_mask(p)
            all_patches.append(p)
            all_boundary_masks.append(bm)
            all_feature_masks.append(fm)
        
        print(f"  {fname}: {w}x{h} -> {len(patches)} patches")
    
    print(f"  Total: {len(all_patches)} patches")
    return all_patches, all_boundary_masks, all_feature_masks


def process_whatsapp():
    print("\n--- WhatsApp Parcel Plans ---")
    files = sorted([f for f in os.listdir(RAW_DIR) if f.startswith("WhatsApp") and f.endswith(".jpeg")])
    patches = []
    boundary_masks = []
    feature_masks = []
    
    for fname in files:
        path = os.path.join(RAW_DIR, fname)
        img = load_image(path, target_size=(256, 256))
        bm = create_boundary_mask(img)
        fm = create_feature_mask(img)
        patches.append(img)
        boundary_masks.append(bm)
        feature_masks.append(fm)
        print(f"  {fname}: OK")
    
    print(f"  Total: {len(patches)} patches")
    return patches, boundary_masks, feature_masks


def main():
    print("=" * 60)
    print("KENYA TRAINING DATASET BUILDER")
    print("=" * 60)
    ensure_dirs()
    
    # Process data
    ang_patches, ang_bm, fm = process_angorom()
    wp_patches, wp_bm, wp_fm = process_whatsapp()
    
    all_patches = ang_patches + wp_patches
    all_bm = ang_bm + wp_bm
    all_fm = fm + wp_fm
    
    print(f"\nTotal: {len(all_patches)} patches")
    
    # Shuffle
    indices = np.random.permutation(len(all_patches))
    
    # Split 70/15/15
    n = len(indices)
    n_train = int(n * 0.7)
    n_val = int(n * 0.15)
    
    splits = {
        "train": indices[:n_train],
        "val": indices[n_train:n_train+n_val],
        "test": indices[n_train+n_val:]
    }
    
    for split_name, split_idx in splits.items():
        print(f"  Saving {split_name}: {len(split_idx)} patches")
        for i, idx in enumerate(split_idx):
            np.save(os.path.join(OUTPUT_DIR, split_name, "images", f"{i:05d}.npy"), all_patches[idx].astype(np.float32))
            np.save(os.path.join(OUTPUT_DIR, split_name, "boundary_masks", f"{i:05d}.npy"), all_bm[idx].astype(np.int32))
            np.save(os.path.join(OUTPUT_DIR, split_name, "feature_masks", f"{i:05d}.npy"), all_fm[idx].astype(np.int32))
    
    meta = {
        "total": len(all_patches),
        "splits": {k: len(v) for k, v in splits.items()},
        "classes_boundary": BOUNDARY_CLASSES,
        "classes_feature": {str(k): v for k, v in FEATURE_CLASSES.items()},
        "patch_size": 256,
        "sources": ["angorom", "whatsapp"]
    }
    
    with open(os.path.join(OUTPUT_DIR, "dataset_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)
    
    # Report
    total_mb = 0
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for f in files:
            if f.endswith('.npy'):
                total_mb += os.path.getsize(os.path.join(root, f))
    
    print(f"\n{'='*60}")
    print(f"DATASET BUILT: {len(all_patches)} patches, {total_mb//1024//1024} MB")
    print(f"  Train: {len(splits['train'])} | Val: {len(splits['val'])} | Test: {len(splits['test'])}")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
