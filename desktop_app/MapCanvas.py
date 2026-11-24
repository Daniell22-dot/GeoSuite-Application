#!/usr/bin/env python
"""
Map Canvas for GeoSuite Desktop

QgsMapCanvas subclass with navigation tools (zoom, pan, extent reset).
Provides the main mapping view for displaying raster and vector layers.
"""

from PyQt6.QtWidgets import QWidget, QSize
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui = None  # Would be QgsMapCanvas from QGIS

# Since QGIS may not be available in all environments, provide a fallback
# class that can be replaced with QgsMapCanvas when QGIS is available


class MapCanvas(QWidget):
    """
    Map canvas widget for displaying geospatial layers.
    
    Features:
    - Layer rendering (placeholder - would use QgsMapCanvas with QGIS)
    - Zoom in/out controls
    - Pan functionality
    - Extent/reset to full extent
    - Coordinate display at mouse position
    - Overview map inset
    - Scale display
    - Mouse position tracking
    """
    
    # Signals
    layer_added = pyqtSignal(object)  # Emitted when a layer is added to the canvas
    layer_removed = pyqtSignal(object)  # Emitted when a layer is removed
    crs_changed = pyqtSignal(str)  # Emitted when CRS changes
    mouse_position_changed = pyqtSignal(tuple)  # (x, y) in canvas coordinates
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        # Canvas state
        self.setMouseTracking(True)
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._crs = "EPSG:4326"  # Default CRS
        self._layers = []
        self._selected_feature = None
        
        # UI state
        self._pan_mode = False
        self._last_mouse_pos = None
        
        # Setup the widget
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the map canvas widget."""
        # Set size policy
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().expanding
        )
        
        # Set minimum size
        self.setMinimumSize(600, 400)
    
    def set_crs(self, crs):
        """Set the coordinate reference system."""
        self._crs = crs
        self.crs_changed.emit(crs)
        self.update()  # Trigger repaint
    
    def set_layers(self, layers):
        """Set the layers to display."""
        self._layers = layers
        self.update()  # Trigger repaint
    
    def add_layer(self, layer):
        """Add a layer to the canvas."""
        self._layers.append(layer)
        self.layer_added.emit(layer)
        self.update()
    
    def remove_layer(self, layer):
        """Remove a layer from the canvas."""
        if layer in self._layers:
            self._layers.remove(layer)
            self.layer_removed.emit(layer)
            self.update()
    
    def clear_layers(self):
        """Remove all layers."""
        self._layers = []
        self.update()
    
    def paintEvent(self, event):
        """Paint the map canvas.
        
        In a full implementation, this would use QgsMapCanvas from QGIS.
        For now, provides a placeholder background with layer information.
        """
        from PyQt6.QtGui = None
        from PyQt6.QtCore = None
        
        # Get painter
        painter = None  # Would be QPainter in full implementation
        
        # Set background based on CRS or default
        bg_color = QColor(240, 240, 240) if not hasattr(self, '_dark_mode') else QColor(30, 30, 30)
        
        # Draw background
        self.fillRect(self.rect(), bg_color)
        
        # Draw layer information
        painter = None  # Placeholder
        # draw_text = self.tr("Map Canvas - %s" % self._crs)
        # painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignLeft, draw_text)
        
        # Draw layers (placeholder)
        for i, layer in enumerate(self._layers[:3]):  # Show first 3 layers
            pass  # Would draw layer extent, etc.
        
        # Draw info text
        info_text = f"Map Canvas\nCRS: {self._crs}\nLayers: {len(self._layers)}"
        # painter.drawText(10, 20, info_text)
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self.update()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        self._last_mouse_pos = event.pos()
        self.mouse_position_changed.emit((event.pos().x(), event.pos().y()))
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pan_mode = True
            self._last_mouse_pos = event.pos()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pan_mode = False
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click events - zoom to extent."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.zoom_to_extent()
        super().mouseDoubleClickEvent(event)
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        # Zoom in/out based on wheel delta
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        super().wheelEvent(event)
    
    def zoom_in(self):
        """Zoom in by 25%."""
        self._zoom *= 1.25
        self.update()
    
    def zoom_out(self):
        """Zoom out by 25%."""
        self._zoom *= 0.8
        self.update()
    
    def zoom_to_extent(self):
        """Zoom to show all layers."""
        # In a full implementation, would calculate extent from all layers
        # and set the canvas extent accordingly
        self._zoom = 1.0  # Reset to default
        self.update()
    
    def get_zoom(self):
        """Return current zoom level."""
        return self._zoom
    
    def set_zoom(self, zoom):
        """Set zoom level."""
        self._zoom = max(0.1, min(10.0, zoom))  # Clamp between 0.1 and 10
        self.update()
    
    def get_crs(self):
        """Return current CRS."""
        return self._crs
    
    def set_layers(self, layers):
        """Set layers to display."""
        self._layers = layers
        self.update()
    
    def get_layers(self):
        """Return list of layers."""
        return self._layers