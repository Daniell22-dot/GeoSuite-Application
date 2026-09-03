"""
Computer Vision API routes — all CV operations exposed as REST endpoints.
"""
import os
import io
import json
import uuid
import numpy as np
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from PIL import Image

router = APIRouter(prefix="/api/v1/cv", tags=["computer-vision"])

_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from app.cv_engine.pipeline import CVPipeline
        model_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cv_models')
        _pipeline = CVPipeline(model_dir=model_dir if os.path.exists(model_dir) else None)
    return _pipeline


def load_image_from_upload(file_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    arr = np.array(img, dtype=np.float64)
    return arr


class TransformRequest(BaseModel):
    easting: float
    northing: float
    direction: str = "cassini_to_utm"
    zone: str = "zone_3"
    method: str = "geodetic"


class BulkTransformRequest(BaseModel):
    coordinates: List[List[float]]
    direction: str = "cassini_to_utm"
    zone: str = "zone_3"
    method: str = "geodetic"


class GPSMatchRequest(BaseModel):
    points: List[List[float]]
    road_network_id: Optional[str] = None
    extent: Optional[List[float]] = None


@router.post("/digitize")
async def digitize_survey_plan(
    file: UploadFile = File(...),
    coordinate_system: str = Form("cassini"),
    zone: str = Form("zone_ii"),
    confidence_threshold: float = Form(0.7),
):
    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")
    pipeline = get_pipeline()
    result = pipeline.digitize_survey_plan(image)
    result['filename'] = file.filename
    result['coordinate_system'] = coordinate_system
    result['zone'] = zone
    return JSONResponse(content=result)


@router.post("/features")
async def extract_features(
    file: UploadFile = File(...),
):
    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")
    pipeline = get_pipeline()
    result = pipeline.extract_features(image)
    result['filename'] = file.filename
    return JSONResponse(content=result)


@router.post("/changes")
async def detect_changes(
    file_before: UploadFile = File(...),
    file_after: UploadFile = File(...),
    threshold: float = Form(0.3),
):
    contents_before = await file_before.read()
    contents_after = await file_after.read()
    try:
        img_before = load_image_from_upload(contents_before)
        img_after = load_image_from_upload(contents_after)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load images: {e}")
    pipeline = get_pipeline()
    result = pipeline.detect_changes(img_before, img_after)
    result['filename_before'] = file_before.filename
    result['filename_after'] = file_after.filename
    return JSONResponse(content=result)


@router.post("/gps-match")
async def match_gps_track(request: GPSMatchRequest):
    gps_array = np.array(request.points)
    pipeline = get_pipeline()
    extent = tuple(request.extent) if request.extent else None
    result = pipeline.match_gps_track(gps_array, extent=extent)
    return JSONResponse(content=result)


@router.post("/symbols")
async def recognize_symbols(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")
    pipeline = get_pipeline()
    result = pipeline.recognize_symbols(image)
    return JSONResponse(content={"symbols": result, "total": len(result), "filename": file.filename})


@router.post("/soundings")
async def extract_soundings(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")
    pipeline = get_pipeline()
    result = pipeline.extract_depth_soundings(image)
    result['filename'] = file.filename
    return JSONResponse(content=result)


@router.post("/land-use")
async def classify_land_use(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")
    pipeline = get_pipeline()
    result = pipeline.classify_land_use(image)
    result['filename'] = file.filename
    return JSONResponse(content=result)


@router.post("/text")
async def extract_text(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")
    pipeline = get_pipeline()
    result = pipeline.extract_text(image)
    return JSONResponse(content={"text_regions": result, "total": len(result), "filename": file.filename})


@router.post("/fast-digitize")
async def fast_digitize(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")
    pipeline = get_pipeline()
    result = pipeline.fast_digitize(image)
    return JSONResponse(content={
        "beacons": result['beacons'],
        "boundaries": result['boundaries'],
        "text_regions": result['text_regions'],
        "total_beacons": result['total_beacons'],
        "total_boundaries": result['total_boundaries'],
        "total_text_regions": result['total_text_regions'],
        "filename": file.filename,
    })


@router.get("/models")
async def get_model_info():
    pipeline = get_pipeline()
    return JSONResponse(content=pipeline.get_model_info())


@router.get("/capabilities")
async def get_capabilities():
    return {
        "engine": "KLISS CV Engine v0.1.0",
        "dependencies": "NumPy only",
        "modules": {
            "digitize": {
                "endpoint": "/api/v1/cv/digitize",
                "method": "POST",
                "description": "Auto-extract beacons, boundaries and labels from scanned survey plans",
                "input": "Image file (PDF, JPG, TIFF, PNG)",
                "output": "Beacon coordinates, boundary polylines, extracted text labels",
            },
            "features": {
                "endpoint": "/api/v1/cv/features",
                "method": "POST",
                "description": "Classify pixels in drone/satellite imagery (buildings, roads, vegetation, water)",
                "input": "Image file (GeoTIFF, JPG, PNG)",
                "output": "Semantic segmentation map with class areas",
            },
            "changes": {
                "endpoint": "/api/v1/cv/changes",
                "method": "POST",
                "description": "Detect changes between two images of the same area",
                "input": "Two image files (before/after)",
                "output": "Change map, changed regions, statistics",
            },
            "gps_match": {
                "endpoint": "/api/v1/cv/gps-match",
                "method": "POST",
                "description": "Snap noisy GPS track to nearest road using Viterbi decoding",
                "input": "GPS coordinate list",
                "output": "Matched track, snap distances",
            },
            "symbols": {
                "endpoint": "/api/v1/cv/symbols",
                "method": "POST",
                "description": "Detect map symbols (benchmarks, beacons, arrows, scale bars)",
                "input": "Image file",
                "output": "Symbol locations, types, confidence scores",
            },
            "soundings": {
                "endpoint": "/api/v1/cv/soundings",
                "method": "POST",
                "description": "Extract depth values from nautical chart rasters",
                "input": "Nautical chart image",
                "output": "Sounding positions and depths",
            },
            "land_use": {
                "endpoint": "/api/v1/cv/land-use",
                "method": "POST",
                "description": "Classify satellite imagery into land use categories",
                "input": "Satellite image (multi-band)",
                "output": "Land use class probabilities and pixel map",
            },
            "text": {
                "endpoint": "/api/v1/cv/text",
                "method": "POST",
                "description": "Extract text labels, annotations, bearings from map images",
                "input": "Map image",
                "output": "Text regions with bounding boxes and content",
            },
            "fast_digitize": {
                "endpoint": "/api/v1/cv/fast-digitize",
                "method": "POST",
                "description": "Traditional CV digitization — instant results, no training needed",
                "input": "Survey plan image",
                "output": "Beacons, boundaries, text regions",
            },
        },
    }
