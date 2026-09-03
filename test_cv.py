import sys
import numpy as np
sys.path.insert(0, r'D:\Geospatial_suite\backend')
from app.cv_engine.pipeline import CVPipeline

p = CVPipeline()
img = np.random.randint(0, 255, (128, 128, 3)).astype(np.float64)

print("Testing digitize_survey_plan...")
r = p.digitize_survey_plan(img)
print(f"  beacons={r['total_beacons']}, boundaries={r['total_boundaries']}, labels={r['total_labels']}, time={r['processing_time_ms']}ms")

print("Testing extract_features...")
r = p.extract_features(img)
print(f"  classes={len(r['class_areas_percent'])}")

print("Testing detect_changes...")
r = p.detect_changes(img, img)
print(f"  change_types={len(r['statistics'])}")

print("Testing recognize_symbols...")
r = p.recognize_symbols(img)
print(f"  symbols_found={len(r)}")

print("Testing extract_depth_soundings...")
r = p.extract_depth_soundings(img)
print(f"  soundings={r['total_soundings']}")

print("Testing classify_land_use...")
r = p.classify_land_use(img)
print(f"  dominant={r['dominant_class']}")

print("Testing extract_text...")
r = p.extract_text(img)
print(f"  text_regions={len(r)}")

print("Testing match_gps_track...")
gps = np.array([[36.8, -1.3], [36.81, -1.31], [36.82, -1.32]])
r = p.match_gps_track(gps)
print(f"  matched={r['num_points']}, avg_snap={r['avg_snap_distance']:.6f}")

print("\nALL TESTS PASSED")
