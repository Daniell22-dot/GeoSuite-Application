#!/usr/bin/env python
"""
Navigation Tools for GeoSuite Desktop

Provides zoom, pan, and extent control functionality for the MapCanvas.
"""

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui = None  # Would be QCursor, QMouseEvent
from PyQt6.QtWidgets = None  # Would be QWidget, QApplication


class NavigationTools:
    """Navigation tools for map canvas interaction."""
    
    # Signals
    zoom_changed = pyqtSignal(float)  # New zoom level
    pan_changed = pyqtSignal(tuple)  # (dx, dy) pan delta
    extent_changed = pyqtSignal(tuple)  # (minx, miny, maxx, maxy)
    
    def __init__(self, canvas):
        self.canvas = canvas
        self._zoom = canvas.get_zoom() if canvas else 1.0
        self._pan_dx = 0.0
        self._pan_dy = 0.0
        self._pan_mode = False
        self._last_pos = None
        
        # Connect canvas signals
        if canvas:
            canvas.zoom_changed.connect(self._on_zoom_changed)
            canvas.mouse_position_changed.connect(self._on_mouse_position)
    
    def _on_zoom_changed(self, zoom):
        """Handle zoom change from canvas."""
        self._zoom = zoom
        self.zoom_changed.emit(zoom)
    
    def _on_mouse_position(self, pos):
        """Handle mouse position changes."""
        pass  # Could track mouse position for pan calculations
    
    def wheel_zoom(self, event):
        """Handle mouse wheel for zooming."""
        # Determine zoom direction
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def zoom_in(self):
        """Zoom in by 25%."""
        new_zoom = self._zoom * 1.25
        self._zoom = new_zoom
        self.zoom_changed.emit(new_zoom)
        # Would call canvas.set_zoom(new_zoom) in full implementation
    
    def zoom_out(self):
        """Zoom out by 25%."""
        new_zoom = self._zoom * 0.8
        self._zoom = new_zoom
        self.zoom_changed.emit(new_zoom)
        # Would call canvas.set_zoom(new_zoom) in full implementation
    
    def pan(self, dx, dy):
        """Pan the map by the given deltas."""
        self._pan_dx = dx
        self._pan_dy = dy
        self._pan_mode = True
        self.pan_changed.emit((dx, dy))
        # Would update canvas pan position in full implementation
    
    def pan_by_pixel(self, dx_px, dy_px):
        """Pan by pixel deltas."""
        # Convert pixels to map units based on current zoom and CRS
        # Simplified: just emit the pixel deltas
        self.pan(dx_px, dy_px)
    
    def reset_extent(self):
        """Reset map extent to show all layers."""
        self._zoom = 1.0
        self.zoom_changed.emit(1.0)
        self.extent_changed.emit(None)  # Would emit actual extent
    
    def get_zoom(self):
        """Return current zoom level."""
        return self._zoom
    
    def set_zoom(self, zoom):
        """Set zoom level."""
        self._zoom = max(0.1, min(10.0, zoom))
        self.zoom_changed.emit(self._zoom)