"""
Unified CV pipeline — orchestrates all heads and modules.
Single entry point for all computer vision operations.
"""
import numpy as np
import json
import time
from typing import Dict, List, Optional
from .preprocessing import Preprocessor, rgb_to_grayscale
from .backbone import CNNBackbone
from .heads.beacon_detector import BeaconDetector
from .heads.boundary_segmenter import BoundarySegmenter
from .heads.text_reader import TextReader
from .heads.feature_extractor import FeatureExtractor
from .modules.change_detector import ChangeDetector
from .modules.map_matcher import MapMatcher
from .modules.symbol_recognizer import SymbolRecognizer
from .modules.depth_sounder import DepthSounder
from .modules.land_use_classifier import LandUseClassifier
from .modules.text_extractor import TextExtractor
from .modules.traditional_digitizer import TraditionalDigitizer


class CVPipeline:
    def __init__(self, model_dir: str = None):
        self.model_dir = model_dir
        self.beacon_detector = BeaconDetector()
        self.boundary_segmenter = BoundarySegmenter()
        self.text_reader = TextReader()
        self.feature_extractor = FeatureExtractor()
        self.change_detector = ChangeDetector()
        self.map_matcher = MapMatcher()
        self.symbol_recognizer = SymbolRecognizer()
        self.depth_sounder = DepthSounder()
        self.land_use_classifier = LandUseClassifier()
        self.text_extractor = TextExtractor()
        self.traditional = TraditionalDigitizer()
        if model_dir:
            self._load_all_weights(model_dir)

    def digitize_survey_plan(self, image: np.ndarray) -> Dict:
        t0 = time.time()
        backbone = self.beacon_detector.backbone
        processed, meta = self.beacon_detector.preprocessor.process(image)
        if processed.ndim == 2:
            x = processed[np.newaxis, np.newaxis]
        else:
            x = processed[np.newaxis].transpose(0, 3, 1, 2)
        features = backbone.forward(x, training=False)
        skips = backbone.get_skip_connections()
        beacons = self.beacon_detector.predict_from_features(features, meta)
        boundaries = self.boundary_segmenter.predict_from_features(features, skips, meta)
        text_regions = self.text_extractor.extract_text_regions(image)
        labels = []
        for region in text_regions:
            recognized = self.text_reader.predict(
                image[region['bbox'][1]:region['bbox'][3], region['bbox'][0]:region['bbox'][2]]
            )
            labels.append({
                'text': recognized['text'],
                'bbox': region['bbox'],
                'confidence': region['confidence'],
                'type': self._classify_label(recognized['text']),
            })
        elapsed = time.time() - t0
        return {
            'beacons': beacons,
            'boundaries': boundaries,
            'labels': labels,
            'text_regions': text_regions,
            'processing_time_ms': round(elapsed * 1000, 1),
            'total_beacons': len(beacons),
            'total_boundaries': len(boundaries),
            'total_labels': len(labels),
        }

    def extract_features(self, image: np.ndarray) -> Dict:
        return self.feature_extractor.predict(image)

    def detect_changes(self, image_t1: np.ndarray, image_t2: np.ndarray) -> Dict:
        return self.change_detector.detect(image_t1, image_t2)

    def match_gps_track(self, gps_points: np.ndarray, road_network: np.ndarray = None,
                        extent: tuple = None) -> Dict:
        return self.map_matcher.match(gps_points, road_network, extent)

    def recognize_symbols(self, image: np.ndarray) -> List[Dict]:
        return self.symbol_recognizer.recognize(image)

    def extract_depth_soundings(self, chart_image: np.ndarray) -> Dict:
        return self.depth_sounder.extract_soundings(chart_image)

    def classify_land_use(self, image: np.ndarray) -> Dict:
        return self.land_use_classifier.classify(image)

    def extract_text(self, image: np.ndarray) -> List[Dict]:
        return self.text_extractor.extract_text_regions(image)

    def fast_digitize(self, image: np.ndarray) -> Dict:
        return self.traditional.digitize(image)

    def _classify_label(self, text: str) -> str:
        text_upper = text.upper().strip()
        if any(c.isdigit() for c in text_upper) and len(text_upper) <= 10:
            if 'B' in text_upper or 'BM' in text_upper:
                return 'benchmark'
            return 'beacon_id'
        if '°' in text or "'" in text or '"' in text:
            return 'bearing'
        if any(c.isdigit() for c in text_upper) and ('.' in text_upper or ',' in text_upper):
            return 'distance'
        if 'L.R' in text_upper or 'LR' in text_upper:
            return 'title_reference'
        if 'P/' in text_upper or 'REF' in text_upper or 'S/' in text_upper:
            return 'plan_number'
        if 'SCALE' in text_upper:
            return 'scale'
        if text_upper in ('N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW'):
            return 'direction'
        return 'annotation'

    def _load_all_weights(self, model_dir: str):
        import os
        try:
            self.beacon_detector.load_weights(os.path.join(model_dir, 'beacon_detector'))
            self.boundary_segmenter.load_weights(os.path.join(model_dir, 'boundary_segmenter'))
            self.text_reader.load_weights(os.path.join(model_dir, 'text_reader'))
            self.feature_extractor.load_weights(os.path.join(model_dir, 'feature_extractor'))
            self.change_detector.load_weights(os.path.join(model_dir, 'change_detector'))
            self.map_matcher.load_weights(os.path.join(model_dir, 'map_matcher'))
            self.symbol_recognizer.load_weights(os.path.join(model_dir, 'symbol_recognizer'))
            self.depth_sounder.load_weights(os.path.join(model_dir, 'depth_sounder'))
            self.land_use_classifier.load_weights(os.path.join(model_dir, 'land_use_classifier'))
            self.text_extractor.load_weights(os.path.join(model_dir, 'text_extractor'))
        except Exception as e:
            print(f"Warning: Could not load model weights: {e}")

    def save_all_weights(self, model_dir: str):
        import os
        os.makedirs(model_dir, exist_ok=True)
        self.beacon_detector.save_weights(os.path.join(model_dir, 'beacon_detector'))
        self.boundary_segmenter.save_weights(os.path.join(model_dir, 'boundary_segmenter'))
        self.text_reader.save_weights(os.path.join(model_dir, 'text_reader'))
        self.feature_extractor.save_weights(os.path.join(model_dir, 'feature_extractor'))
        self.change_detector.save_weights(os.path.join(model_dir, 'change_detector'))
        self.map_matcher.save_weights(os.path.join(model_dir, 'map_matcher'))
        self.symbol_recognizer.save_weights(os.path.join(model_dir, 'symbol_recognizer'))
        self.depth_sounder.save_weights(os.path.join(model_dir, 'depth_sounder'))
        self.land_use_classifier.save_weights(os.path.join(model_dir, 'land_use_classifier'))
        self.text_extractor.save_weights(os.path.join(model_dir, 'text_extractor'))

    def get_model_info(self) -> Dict:
        models = {}
        for name, module in [
            ('beacon_detector', self.beacon_detector),
            ('boundary_segmenter', self.boundary_segmenter),
            ('text_reader', self.text_reader),
            ('feature_extractor', self.feature_extractor),
            ('change_detector', self.change_detector),
            ('map_matcher', self.map_matcher),
            ('symbol_recognizer', self.symbol_recognizer),
            ('depth_sounder', self.depth_sounder),
            ('land_use_classifier', self.land_use_classifier),
            ('text_extractor', self.text_extractor),
        ]:
            params = module.parameters()
            total_params = sum(p.size for p in params)
            models[name] = {
                'parameters': total_params,
                'size_mb': round(total_params * 8 / 1024 / 1024, 2),
            }
        total_params = sum(m['parameters'] for m in models.values())
        total_size = sum(m['size_mb'] for m in models.values())
        return {
            'models': models,
            'total_parameters': total_params,
            'total_size_mb': round(total_size, 2),
            'engine': 'KLISS CV Engine v0.1.0',
            'dependencies': 'NumPy only',
        }
