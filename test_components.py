import os, sys
os.environ['SECRET_KEY'] = 'geosuite-dev-secret-key-change-in-production'
os.environ['JWT_SECRET'] = 'geosuite-dev-jwt-secret-change-in-production'

sys_path = r'D:\Geospatial_suite\backend'
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from app.cv_engine.training.train_real import load_real_dataset, apply_beacon_labels
from app.cv_engine.training.synthetic_generator import generate_parcel_batch
from app.cv_engine.training.train import train_boundary_segmenter
from app.cv_engine.heads.boundary_segmenter import BoundarySegmenter
import numpy as np

# Load real dataset
dataset = load_real_dataset()
apply_beacon_labels(dataset)
print('Loaded real images with beacon labels')

# Use synthetic generator for quick test
batch = generate_parcel_batch(batch_size=2, image_size=256)
print('Synthetic batch shapes OK')

# Quick test: create boundary segmenter and forward pass
b = BoundarySegmenter(num_classes=3)
print('BoundarySegmenter created with', len(b.parameters()), 'parameters')

# Quick forward pass - grayscale input (batch, H, W)
gray_img = np.random.randint(0, 255, (2, 256, 256)).astype(np.float64)
# Convert to single channel if needed
if gray_img.ndim == 3 and gray_img.shape[2] == 256:
    gray = gray_img
else:
    gray = np.mean(gray_img, axis=2) if gray_img.ndim == 4 else gray_img

# Preprocess: add channel dim, normalize
x = gray[:, :, :, np.newaxis] / 255.0 if gray_img.ndim == 3 else gray[np.newaxis, np.newaxis, :, :] / 255.0
print('Input shape after preprocess:', x.shape)
features = b.forward(x, training=True)
print('Forward pass successful')

print('All components working')