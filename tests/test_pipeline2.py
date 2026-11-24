import sys
sys.path.insert(0, r'D:\Geospatial_suite\backend')
from app.cv_engine.pipeline import CVPipeline
import numpy as np

p = CVPipeline()
print('Pipeline model_dir:', p.model_dir)
print('Has real weights:', p.model_dir is not None)

img = np.random.randint(0, 255, (128, 128, 3)).astype(np.float64)

# Test digitize - this uses the pipeline which may fall back to mock
r = p.digitize_survey_plan(img)
print('Result note:', r.get('note', 'not specified'))
print('Beacons:', r['total_beacons'])