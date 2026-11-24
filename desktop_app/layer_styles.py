#!/usr/bin/env python
"""
Layer Styles and Symbology Presets for GeoSuite Desktop

Provides default styling presets for common GIS layer types.
"""

from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtCore import Qt


# Color ramps for common GIS uses
COLOR_MAPS = {
    'bouguer': {
        'min': QColor(38, 139, 210),  # Blue
        'mid': QColor(255, 255, 0),   # Yellow
        'max': QColor(255, 0, 0),     # Red
        'name': 'Bouguer Anomaly'
    },
    'depth': {
        'min': QColor(0, 0, 180),     # Dark blue
        'mid': QColor(0, 191, 255),   # Deep sky blue
        'max': QColor(255, 255, 0),   # Yellow
        'name': 'Bathymetric Depth'
    },
    'temperature': {
        'min': QColor(0, 0, 139),     # Dark blue
        'mid': QColor(255, 255, 0),   # Yellow
        'max': QColor(255, 0, 0),     # Red
        'name': 'Temperature'
    },
    'elevation': {
        'min': QColor(0, 128, 0),     # Green
        'mid': QColor(255, 255, 0),   # Yellow
        'max': QColor(255, 0, 0),     # Red
        'name': 'Elevation'
    },
    'simple': {
        'color': QColor(0, 0, 205),   # Deep sky blue
        'name': 'Simple Color'
    }
}


# Default symbology presets
DEFAULT_STYLES = {
    'point': {
        'name': 'Default Point',
        'symbol_type': 'circle',
        'color': QColor(255, 0, 0),
        'size': 5,
        'stroke_color': QColor(0, 0, 0),
        'stroke_width': 1,
    },
    'line': {
        'name': 'Default Line',
        'symbol_type': 'line',
        'color': QColor(0, 0, 0),
        'width': 1,
        'stroke_color': QColor(255, 255, 255),
    },
    'polygon': {
        'name': 'Default Polygon',
        'symbol_type': 'polygon',
        'brush_color': QColor(0, 0, 255, 50),  # Semi-transparent blue
        'stroke_color': QColor(0, 0, 255),
        'stroke_width': 1,
        'fill': True,
    },
    'raster_single': {
        'name': 'Single Symbol',
        'color': QColor(0, 0, 255),
        'opacity': 1.0,
    },
    'raster_graduated': {
        'name': 'Graduated (Depth)',
        'color_ramp': 'depth',
        'classes': 5,
    },
}


def get_color_ramp(name):
    """Get a color ramp preset by name."""
    return COLOR_MAPS.get(name, COLOR_MAPS['depth'])


def get_default_style(style_name):
    """Get a default style preset by name."""
    return DEFAULT_STYLES.get(style_name, DEFAULT_STYLES['point'])


def is_dark_color(color):
    """Check if a QColor is dark (for text contrast)."""
    brightness = color.lightness()
    return brightness < 128


def contrast_color(background_color):
    """Return black or white text color for contrast."""
    if is_dark_color(background_color):
        return QColor(255, 255, 255)  # White
    else:
        return QColor(0, 0, 0)  # Black


# Predefined style sheets for common widgets
STYLE_SHEETS = {
    'dark_background': """
        QWidget { background-color: #2b2b2b; color: #f0f0f0; }
        QPushButton { background-color: #3d3d3d; color: #f0f0f0; }
        QLabel { background-color: #2b2b2b; color: #f0f0f0; }
    """,
    'light_background': """
        QWidget { background-color: #f0f0f0; color: #2b2b2b; }
        QPushButton { background-color: #e0e0e0; color: #2b2b2b; }
        QLabel { background-color: #f0f0f0; color: #2b2b2b; }
    """,
}