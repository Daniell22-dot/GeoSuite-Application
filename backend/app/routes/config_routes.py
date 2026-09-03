"""
Application configuration endpoint.
Returns non-sensitive runtime configuration for the frontend.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.config import settings


router = APIRouter()


class MapLayerConfig(BaseModel):
    name: str
    url: str
    attribution: str
    isBase: bool = True


class AppConfig(BaseModel):
    appName: str
    appVersion: str
    apiVersion: str
    maxUploadSizeMB: int
    supportedFileTypes: Dict[str, List[str]]
    defaultMapCenter: List[float]
    defaultMapZoom: int
    mapLayers: List[MapLayerConfig]
    transformZones: List[Dict]
    transformMethods: List[str]
    watershedThresholds: List[int]
    weatherDefaultCity: str
    droneMaxImages: int


@router.get("/")
async def get_config():
    """
    Return application configuration for the frontend.
    No authentication required — safe to call on app startup.
    """
    return {
        "appName": settings.APP_NAME,
        "appVersion": settings.APP_VERSION,
        "apiVersion": settings.API_V1_STR,
        "maxUploadSizeMB": settings.MAX_UPLOAD_SIZE // (1024 * 1024),
        "supportedFileTypes": {
            "gps": [".gpx", ".kml", ".geojson", ".csv"],
            "marine": [".kap", ".bsb", ".dwg", ".dxf"],
            "dem": [".tif", ".tiff", ".hgt", ".asc", ".dem"],
            "vector": [".shp", ".zip"],
            "drone": [".jpg", ".jpeg", ".tif", ".tiff", ".png"],
        },
        "defaultMapCenter": [0.0, 0.0],
        "defaultMapZoom": 2,
        "mapLayers": [
            {"name": "Dark Matter", "url": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", "attribution": "&copy; <a href=\"https://carto.com/attributions\">CARTO</a>", "isBase": True},
            {"name": "World Imagery", "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "attribution": "Tiles &copy; Esri", "isBase": True},
            {"name": "OpenTopoMap", "url": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", "attribution": "&copy; OpenTopoMap contributors", "isBase": True},
            {"name": "OpenStreetMap", "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", "attribution": "&copy; OpenStreetMap contributors", "isBase": True},
            {"name": "Hillshade", "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}", "attribution": "&copy; Esri", "isBase": False},
            {"name": "Terrain", "url": "https://stamen-tiles.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png", "attribution": "&copy; Stamen Design", "isBase": False},
            {"name": "Nautical", "url": "https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png", "attribution": "&copy; OpenSeaMap contributors", "isBase": True},
            {"name": "Satellite", "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "attribution": "Tiles &copy; Esri", "isBase": True},
        ],
        "watershedThresholds": [500, 1000, 5000],
        "weatherDefaultCity": "Nairobi,KE",
        "droneMaxImages": 500,
        "terminalWsPath": "/api/v1/terminal/ws",
    }
