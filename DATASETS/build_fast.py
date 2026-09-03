"""Fast Kenya dataset builder - saves as single .npz files."""
import os, sys, json, time
import numpy as np
from PIL import Image

BASE_DIR = r"D:\Geospatial_suite"
RAW_DIR = os.path.join(BASE_DIR, "RAW DATA")
OUTPUT_DIR = os.path.join(BASE_DIR, "DATASETS", "kenya_training")


def load_image(path):
    return np.array(Image.open(path).convert("RGB"), dtype=np.float32)


def extract_patches(img, ps=256, stride=128):
    h, w = img.shape[:2]
    patches = []
    for y in range(0, h - ps + 1, stride):
        for x in range(0, w - ps + 1, stride):
            p = img[y:y+ps, x:x+ps]
            if np.std(p) > 15:
                patches.append(p)
    return patches


def make_boundary_mask(img):
    gray = np.mean(img, axis=2)
    return (gray < 128).astype(np.int32)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    all_images = []
    all_masks = []
    
    # ANGOROM plans
    files = sorted([f for f in os.listdir(RAW_DIR) if f.startswith("ANGOROM") and f.endswith(".jpg")])
    print("Processing ANGOROM survey plans...")
    for fname in files:
        img = load_image(os.path.join(RAW_DIR, fname))
        patches = extract_patches(img)
        masks = [make_boundary_mask(p) for p in patches]
        all_images.extend(patches)
        all_masks.extend(masks)
        print(f"  {fname}: {len(patches)} patches")
    
    # WhatsApp photos
    print("\nProcessing WhatsApp parcel plans...")
    for fname in sorted(os.listdir(RAW_DIR)):
        if fname.startswith("WhatsApp") and fname.endswith(".jpeg"):
            img = load_image(os.path.join(RAW_DIR, fname))
            img = np.array(Image.fromarray(img.astype(np.uint8)).resize((256, 256), Image.BILINEAR), dtype=np.float32)
            all_images.append(img)
            all_masks.append(make_boundary_mask(img))
            print(f"  {fname}")
    
    # Convert to arrays
    images = np.stack(all_images)
    masks = np.stack(all_masks)
    print(f"\nTotal: {len(images)} patches, shape: {images.shape}")
    
    # Shuffle and split
    idx = np.random.permutation(len(images))
    n = len(idx)
    n_tr = int(n * 0.7)
    n_val = int(n * 0.15)
    
    splits = {
        "train": idx[:n_tr],
        "val": idx[n_tr:n_tr+n_val],
        "test": idx[n_tr+n_val:]
    }
    
    for name, s in splits.items():
        d = os.path.join(OUTPUT_DIR, name)
        os.makedirs(d, exist_ok=True)
        np.savez_compressed(os.path.join(d, "data.npz"),
                          images=images[s], masks=masks[s])
        sz = os.path.getsize(os.path.join(d, "data.npz")) // 1024 // 1024
        print(f"  {name}: {len(s)} patches, {sz}MB")
    
    meta = {"total": n, "splits": {k: len(v) for k, v in splits.items()}, "patch_size": 256}
    with open(os.path.join(OUTPUT_DIR, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"\nDone! Dataset saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
