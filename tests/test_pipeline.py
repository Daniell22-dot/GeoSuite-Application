import sys
sys.path.insert(0, r'D:\Geospatial_suite\backend')
from app.cv_engine.pipeline import CVPipeline
import numpy as np

p = CVPipeline()
img = np.random.randint(0, 255, (128, 128, 3)).astype(np.float64)

print("Testing digitize_survey_plan...")
r = p.digitize_survey_plan(img)
print(f"  beacons={r['total_beacons']}, boundaries={r['total_boundaries']}, labels={r['total_labels']}, time={r['processing_time_ms']}ms")

print("Testing extract_features...")
r = p.extract_features(img)
print(f"  classes={len(r['class_areas_percent'])}")

print("ALL TESTS PASSED (mock mode)")