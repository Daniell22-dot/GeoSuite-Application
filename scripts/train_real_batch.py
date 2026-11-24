import os
import sys
os.environ['SECRET_KEY'] = 'geosuite-dev-secret-key-change-in-production'
os.environ['JWT_SECRET'] = 'geosuite-dev-jwt-secret-change-in-production'

sys_path = r'D:\Geospatial_suite\backend'
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from app.cv_engine.training.train_real import (
    load_real_dataset, apply_beacon_labels, RealBatchSource,
    train_boundary_segmenter, save_pipeline_format, _verify_pipeline_format
)
from app.cv_engine.pipeline import CVPipeline
import numpy as np

# Load and prepare dataset
dataset = load_real_dataset()
images = dataset['images']
bmasks = dataset['boundary_masks']
fmasks = dataset['feature_masks']
n = len(images)

print(f'Loaded {n} images')

# Apply beacon labels
apply_beacon_labels(dataset)
n_beacons = [int((t[:, :, 0] > 0.5).sum()) for t in dataset['beacon_targets']]
print(f'Beacons derived: total={sum(n_beacons)}, per-patch={n_beacons}')

# Split: 20 train / 7 test
SEED = 42
TEST_SPLIT = 7
rng = np.random.RandomState(SEED)
perm = rng.permutation(n)
train_idx = sorted(perm[:-TEST_SPLIT].tolist())
test_idx = sorted(perm[-TEST_SPLIT:].tolist())
print(f'Split: {len(train_idx)} train / {len(test_idx)} test')

# Create batch source for training
train_source = RealBatchSource(train_idx, dataset['images'], dataset['boundary_masks'],
                               dataset['feature_masks'], dataset['beacon_targets'])

# Test one batch
b = train_source.__call__(min(4, len(train_idx)))
img_shape = b['images'].shape
bmask_shape = b['boundary_masks'].shape
fmask_shape = b['feature_masks'].shape
beacon_count = sum(int((t[:, :, 0] > 0.5).sum()) for t in b['beacon_targets'])
print(f'Batch - images: {img_shape}, bmask: {bmask_shape}, fmask: {fmask_shape}, beacons: {beacon_count}')

# Train boundary segmenter with reasonable params
print('\nTraining boundary segmenter...')
boundary_models = train_boundary_segmenter(
    num_epochs=20,
    batch_size=4,
    lr=1e-3,
    save_every=5,
    batch_source=train_source
)

print('\nBoundary training complete!')

# Save the models
products = {
    'boundary': boundary_models,
}
save_pipeline_format(products)
print('\nModels saved!')

# Verify pipeline format
if _verify_pipeline_format(products):
    print('Pipeline format verification: PASSED')
else:
    print('Pipeline format verification: FAILED')

# Quick inference test
p = CVPipeline(model_dir=r'D:\Geospatial_suite\backend\cv_models')
test_img = np.random.randint(0, 255, (128, 128, 3)).astype(np.float64)
r = p.digitize_survey_plan(test_img)
print(f'\nInference test: beacons={r["total_beacons"]}, boundaries={r["total_boundaries"]}, labels={r["total_labels"]}')