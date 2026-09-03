"""
Drone image processing service.
Handles EXIF extraction, image validation, and ODM orchestration.
"""
import os
import uuid
import json
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np

try:
    import exifread
    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class DroneEXIFExtractor:
    """Extract GPS and camera metadata from drone images."""

    def extract(self, image_path: str) -> Dict:
        """
        Extract EXIF data from an image file.
        Returns dict with lat, lon, altitude, focal_length, etc.
        """
        if PIL_AVAILABLE:
            return self._extract_pillow(image_path)
        elif EXIFREAD_AVAILABLE:
            return self._extract_exifread(image_path)
        else:
            return {"error": "No EXIF library available (install Pillow or exifread)"}

    # ── Pillow-based extraction ──────────────────────────────────────

    def _extract_pillow(self, image_path: str) -> Dict:
        try:
            img = Image.open(image_path)
            exif_data = img._getexif()
            if not exif_data:
                return {"error": "No EXIF data found"}

            result = {
                "image_width": img.width,
                "image_height": img.height,
                "file_size": os.path.getsize(image_path),
            }

            tag_map = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                tag_map[tag_name] = value

            # Camera info
            result["camera_make"] = str(tag_map.get("Make", ""))
            result["camera_model"] = str(tag_map.get("Model", ""))
            result["focal_length"] = self._to_float(tag_map.get("FocalLength"))
            result["focal_length_35mm"] = self._to_float(tag_map.get("FocalLengthIn35mmFilm"))

            # Image dimensions
            result["image_width"] = tag_map.get("PixelXDimension", img.width)
            result["image_height"] = tag_map.get("PixelYDimension", img.height)

            # GPS info
            gps_info = tag_map.get("GPSInfo")
            if gps_info:
                gps = {}
                for key, val in gps_info.items():
                    decode = GPSTAGS.get(key, key)
                    gps[decode] = val

                lat = self._gps_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
                lon = self._gps_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
                alt = gps.get("GPSAltitude")
                if alt is not None:
                    ref = gps.get("GPSAltitudeRef", b'\x00')
                    alt = self._to_float(alt)
                    if ref == b'\x01':  # below sea level
                        alt = -alt

                result["latitude"] = lat
                result["longitude"] = lon
                result["altitude"] = alt

            # DJI-specific tags (XMP embedded in EXIF)
            # These are in IFD-0 MakerNotes or XMP
            dji_tags = self._extract_dji_tags(exif_data)
            result.update(dji_tags)

            return result

        except Exception as e:
            return {"error": f"Pillow extraction failed: {str(e)}"}

    def _extract_dji_tags(self, exif_data: dict) -> Dict:
        """Extract DJI-specific gimbal and flight data from EXIF."""
        result = {}
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if "gimbal" in str(tag_name).lower() or "flight" in str(tag_name).lower():
                result[tag_name] = str(value)
        return result

    # ── exifread-based extraction (fallback) ─────────────────────────

    def _extract_exifread(self, image_path: str) -> Dict:
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)

            result = {
                "camera_make": str(tags.get("Image Make", "")),
                "camera_model": str(tags.get("Image Model", "")),
                "focal_length": self._parse_ratio(str(tags.get("EXIF FocalLength", ""))),
                "image_width": self._to_int(tags.get("EXIF ExifImageWidth")),
                "image_height": self._to_int(tags.get("EXIF ExifImageLength")),
                "file_size": os.path.getsize(image_path),
            }

            # GPS
            lat = self._exifread_gps_coord(tags, "GPS GPSLatitude", "GPS GPSLatitudeRef")
            lon = self._exifread_gps_coord(tags, "GPS GPSLongitude", "GPS GPSLongitudeRef")
            alt_tag = tags.get("GPS GPSAltitude")
            alt = self._parse_ratio(str(alt_tag)) if alt_tag else None
            alt_ref = str(tags.get("GPS GPSAltitudeRef", "0"))
            if alt is not None and alt_ref.strip() == "1":
                alt = -alt

            result["latitude"] = lat
            result["longitude"] = lon
            result["altitude"] = alt

            return result

        except Exception as e:
            return {"error": f"exifread extraction failed: {str(e)}"}

    def _exifread_gps_coord(self, tags, coord_tag, ref_tag):
        raw = tags.get(coord_tag)
        ref = str(tags.get(ref_tag, "N")).strip()
        if not raw:
            return None
        try:
            vals = [self._parse_ratio(str(v)) for v in raw.values]
            if len(vals) == 3:
                decimal = vals[0] + vals[1] / 60.0 + vals[2] / 3600.0
                if ref in ("S", "W"):
                    decimal = -decimal
                return decimal
        except Exception:
            return None
        return None

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _to_float(val) -> Optional[float]:
        if val is None:
            return None
        try:
            if hasattr(val, 'numerator'):
                return float(val.numerator) / float(val.denominator) if val.denominator else float(val)
            return float(val)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    @staticmethod
    def _to_int(val) -> Optional[int]:
        if val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_ratio(s: str) -> Optional[float]:
        """Parse '123/1' or '123' into a float."""
        s = s.strip()
        if not s:
            return None
        try:
            if '/' in s:
                num, den = s.split('/')
                return float(num.strip()) / float(den.strip())
            return float(s)
        except (ValueError, ZeroDivisionError):
            return None

    @staticmethod
    def _gps_to_decimal(coords, ref):
        if coords is None:
            return None
        try:
            if hasattr(coords[0], 'numerator'):
                d = float(coords[0].numerator) / float(coords[0].denominator)
                m = float(coords[1].numerator) / float(coords[1].denominator)
                s = float(coords[2].numerator) / float(coords[2].denominator)
            else:
                d, m, s = float(coords[0]), float(coords[1]), float(coords[2])
            decimal = d + m / 60.0 + s / 3600.0
            if ref and ref in ("S", "W"):
                decimal = -decimal
            return decimal
        except Exception:
            return None


class DroneSurveyService:
    """Manages drone surveys — image ingestion, EXIF parsing, survey lifecycle."""

    def __init__(self, upload_dir: str = "data/drone_surveys"):
        self.upload_dir = upload_dir
        self.extractor = DroneEXIFExtractor()
        os.makedirs(upload_dir, exist_ok=True)

    def create_survey(self, name: str, description: str = "", user_id: str = None) -> Dict:
        """Create a new drone survey container."""
        survey_id = str(uuid.uuid4())
        survey_dir = os.path.join(self.upload_dir, survey_id)
        images_dir = os.path.join(survey_dir, "images")
        output_dir = os.path.join(survey_dir, "output")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        return {
            "survey_id": survey_id,
            "name": name,
            "description": description,
            "status": "uploaded",
            "survey_dir": survey_dir,
            "images_dir": images_dir,
            "output_dir": output_dir,
            "user_id": user_id,
        }

    def add_image(self, survey_dir: str, file_name: str, file_content: bytes) -> Dict:
        """Save an image and extract its EXIF metadata."""
        images_dir = os.path.join(survey_dir, "images")
        file_path = os.path.join(images_dir, file_name)

        with open(file_path, "wb") as f:
            f.write(file_content)

        metadata = self.extractor.extract(file_path)
        metadata["file_name"] = file_name
        metadata["file_path"] = file_path
        metadata["file_size"] = os.path.getsize(file_path)

        return metadata

    def finalize_upload(self, survey_id: str) -> Dict:
        """
        After all images uploaded, compute survey bounds and stats.
        """
        survey_dir = os.path.join(self.upload_dir, survey_id)
        images_dir = os.path.join(survey_dir, "images")

        if not os.path.exists(images_dir):
            return {"error": "Survey directory not found"}

        images = [f for f in os.listdir(images_dir)
                  if f.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png'))]

        if not images:
            return {"error": "No images found in survey"}

        # Extract EXIF from all images
        lats, lons, alts = [], [], []
        camera_models = set()
        for img_name in images:
            img_path = os.path.join(images_dir, img_name)
            meta = self.extractor.extract(img_path)
            if "latitude" in meta and meta["latitude"] is not None:
                lats.append(meta["latitude"])
            if "longitude" in meta and meta["longitude"] is not None:
                lons.append(meta["longitude"])
            if "altitude" in meta and meta["altitude"] is not None:
                alts.append(meta["altitude"])
            if meta.get("camera_model"):
                camera_models.add(meta["camera_model"])

        bounds = {}
        if lats and lons:
            bounds = {
                "north": max(lats),
                "south": min(lats),
                "east": max(lons),
                "west": min(lons),
            }

        # Rough area estimation (Haversine)
        area_km2 = 0.0
        if lats and lons and len(lats) > 1:
            from math import radians, cos, sin, asin, sqrt
            lat_span = radians(max(lats) - min(lats))
            lon_span = radians(max(lons) - min(lons))
            avg_lat = radians(np.mean(lats))
            km_lat = 111.32 * lat_span
            km_lon = 111.32 * cos(avg_lat) * lon_span
            area_km2 = km_lat * km_lon

        return {
            "image_count": len(images),
            "bounds": bounds,
            "area_km2": round(area_km2, 4),
            "area_hectares": round(area_km2 * 100, 2),
            "camera_models": list(camera_models),
            "elevation_range": {
                "min": round(min(alts), 2) if alts else None,
                "max": round(max(alts), 2) if alts else None,
            } if alts else None,
        }

    def get_survey_images(self, survey_id: str) -> List[Dict]:
        """List all images in a survey with their EXIF metadata."""
        survey_dir = os.path.join(self.upload_dir, survey_id)
        images_dir = os.path.join(survey_dir, "images")

        if not os.path.exists(images_dir):
            return []

        results = []
        for img_name in sorted(os.listdir(images_dir)):
            if img_name.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png')):
                img_path = os.path.join(images_dir, img_name)
                meta = self.extractor.extract(img_path)
                meta["file_name"] = img_name
                results.append(meta)

        return results
