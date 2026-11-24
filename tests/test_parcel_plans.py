"""
Test parcel plan digitization — compares traditional CV vs deep learning approach.
"""
import sys
import os
import time
import numpy as np
from PIL import Image

sys.path.insert(0, r'D:\Geospatial_suite\backend')
from app.cv_engine.pipeline import CVPipeline

IMAGES = [
    r'D:\Geospatial_suite\WhatsApp Image 2026-07-14 at 11.57.38.jpeg',
    r'D:\Geospatial_suite\WhatsApp Image 2026-07-14 at 11.57.38 (1).jpeg',
    r'D:\Geospatial_suite\WhatsApp Image 2026-07-14 at 11.57.38 (2).jpeg',
    r'D:\Geospatial_suite\WhatsApp Image 2026-07-14 at 11.57.38 (3).jpeg',
]


def load_image(path: str) -> np.ndarray:
    img = Image.open(path)
    img = img.convert('RGB')
    return np.array(img, dtype=np.float64)


def main():
    pipeline = CVPipeline()

    for img_path in IMAGES:
        if not os.path.exists(img_path):
            print(f"  SKIP: {img_path}")
            continue

        name = os.path.basename(img_path)
        img = load_image(img_path)
        print(f"\n{'='*60}")
        print(f"IMAGE: {name} ({img.shape[0]}x{img.shape[1]})")

        t0 = time.time()
        r = pipeline.fast_digitize(img)
        dt = time.time() - t0
        print(f"\n  TRADITIONAL CV ({dt:.2f}s):")
        print(f"    Beacons: {r['total_beacons']}")
        for b in r['beacons'][:8]:
            print(f"      {b['type']} @ ({b['center'][0]:.0f},{b['center'][1]:.0f}) "
                  f"conf={b['confidence']:.3f} area={b['area']} circ={b['circularity']:.3f}")
        print(f"    Boundaries: {r['total_boundaries']}")
        for bd in r['boundaries'][:5]:
            print(f"      rho={bd['rho']:.1f} theta={bd['theta_degrees']:.1f}°")
        print(f"    Text regions: {r['total_text_regions']}")
        for tr in r['text_regions'][:5]:
            print(f"      bbox={tr['bbox']} size={tr['width']}x{tr['height']} "
                  f"fill={tr['fill_ratio']:.3f} aspect={tr['aspect_ratio']:.3f}")

        print()


if __name__ == '__main__':
    main()
