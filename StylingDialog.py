#!/usr/bin/env python
"""
Styling Dialog for GeoSuite Desktop

Provides layer symbology configuration with various symbol types and color ramps.
Allows users to customize the appearance of raster and vector layers.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QComboBox, QPushButton, QLabel, QSlider, QCheckBox, QLineEdit,
    QButtonGroup, QButtonGroup, QApplication)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui = None  # QColor, QPixmap

# Import color ramps
from .color_ramps import COLOR_MAPS, get_color_ramp, get_default_style, is_dark_color, contrast_color


class StylingDialog(QDialog):
    """
    Dialog for configuring layer symbology and styling.
    
    Features:
    - Symbol type selection: Single Symbol, Categorized, Graduated, Rule-based, Palette
    - Color picker for single symbol
    - Color ramp selection for graduated symbology
    - Classification breaks control
    - Transparency slider for raster layers
    - Style preview thumbnail
    - Apply/Reset buttons
    """
    
    style_applied = pyqtSignal(dict)  # Emitted with style dict when applied
    
    def __init__(self, layer=None, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.setWindowTitle("Layer Styling")
        self.resize(450, 500)
        
        # Setup UI
        self.setup_ui()
        
        # Initialize with default style
        if layer:
            self.apply_default_style()
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Layer Styling")
        self.setMinimumSize(400, 500)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Style type group
        style_group = QGroupBox("Style Type")
        style_layout = QVBoxLayout(style_group)
        
        # Style type radio buttons
        self.style_group = QButtonGroup(self)
        
        self.rb_single_symbol = QRadioButton("Single Symbol")
        self.rb_single_symbol.toggled.connect(self.on_style_type_changed)
        self.style_group.addButton(self.rb_single_symbol)
        style_layout.addWidget(self.rb_single_symbol)
        
        self.rb_categorized = QRadioButton("Categorized (Unique Values)")
        self.rb_categorized.toggled.connect(self.on_style_type_changed)
        self.style_group.addButton(self.rb_categorized)
        style_layout.addWidget(self.rb_categorized)
        
        self.rb_graduated = QRadioButton("Graduated (Continuous)")
        self.rb_graduated.toggled.connect(self.on_style_type_changed)
        self.style_group.addButton(self.rb_graduated)
        style_layout.addWidget(self.rb_graduated)
        
        self.rb_rule_based = QRadioButton("Rule-based")
        self.rb_rule_based.toggled.connect(self.on_style_type_changed)
        self.style_group.addButton(self.rb_rule_based)
        style_layout.addWidget(self.rb_rule_based)
        
        self.rb_palette = QRadioButton("Palette")
        self.rb_palette.toggled.connect(self.on_style_type_changed)
        self.style_group.addButton(self.rb_palette)
        style_layout.addWidget(self.rb_palette)
        
        main_layout.addWidget(style_group)
        
        # Single Symbol controls
        self.single_symbol_group = QGroupBox("Single Symbol")
        single_layout = QFormLayout(self.single_symbol_group)
        
        self.rb_single_color = QPushButton("Choose Color...")
        self.rb_single_color.clicked.connect(self.choose_single_color)
        single_layout.addRow("Color:", self.rb_single_color)
        
        self.rb_single_stroke = QCheckBox("Stroke Outline")
        self.rb_single_stroke.setChecked(True)
        single_layout.addRow("Stroke Outline:", self.rb_single_stroke)
        
        self.rb_single_stroke_width = QSlider(Qt.Orientation.Horizontal)
        self.rb_single_stroke_width.setRange(1, 10)
        self.rb_single_stroke_width.setValue(1)
        single_layout.addRow("Stroke Width:", self.rb_single_stroke_width)
        
        self.rb_single_opacity = QSlider(Qt.Orientation.Horizontal)
        self.rb_single_opacity.setRange(0, 100)
        self.rb_single_opacity.setValue(100)
        single_layout.addRow("Opacity %:", self.rb_single_opacity)
        
        main_layout.addWidget(self.single_symbol_group)
        
        # Categorized controls
        self.categorized_group = QGroupBox("Categorized (Unique Values)")
        cat_layout = QVBoxLayout(self.categorized_group)
        
        self.cmb_category_column = QComboBox()
        cat_layout.addWidget(QLabel("Column:"))
        cat_layout.addWidget(self.cmb_category_column)
        
        self.cmb_color_ramp = QComboBox()
        self.cmb_color_ramp.addItems(["Viridis", "Plasma", "Inferno", "Magma", "Turbo"])
        cat_layout.addWidget(QLabel("Color Ramp:"))
        cat_layout.addWidget(self.cmb_color_ramp)
        
        self.cmb_breaks = QComboBox()
        self.cmb_breaks.addItems(["Equal Interval", "Quantiles", "Natural Breaks (Jenks)", "Standard Deviation"])
        cat_layout.addWidget(QLabel("Classification:"))
        cat_layout.addWidget(self.cmb_breaks)
        
        self.sb_breaks_count = QSlider(Qt.Orientation.Horizontal)
        self.sb_breaks_count.setRange(2, 30)
        self.sb_breaks_count.setValue(5)
        cat_layout.addWidget(QLabel("Classes:"))
        cat_layout.addWidget(self.sb_breaks_count)
        
        main_layout.addWidget(self.categorized_group)
        
        # Graduated controls
        self.graduated_group = QGroupBox("Graduated (Continuous)")
        grad_layout = QVBoxLayout(self.graduated_group)
        
        self.cmb_grad_column = QComboBox()
        grad_layout.addWidget(QLabel("Column:"))
        grad_layout.addWidget(self.cmb_grad_column)
        
        self.cmb_grad_ramp = QComboBox()
        self.cmb_grad_ramp.addItems(["Viridis", "Plasma", "Inferno", "Magma", "Turbo"])
        grad_layout.addWidget(QLabel("Color Ramp:"))
        grad_layout.addWidget(self.cmb_grad_ramp)
        
        self.sb_grad_breaks = QSlider(Qt.Orientation.Horizontal)
        self.sb_grad_breaks.setRange(2, 30)
        self.sb_grad_breaks.setValue(5)
        grad_layout.addWidget(QLabel("Classes:"))
        grad_layout.addWidget(self.sb_grad_breaks)
        
        main_layout.addWidget(self.graduated_group)
        
        # Rule-based controls (simplified)
        self.rule_based_group = QGroupBox("Rule-based")
        rule_layout = QVBoxLayout(self.rule_based_group)
        rule_layout.addWidget(QLabel("Expression (simplified):"))
        self.rule_edit = QLineEdit("\"value\" > 0")
        rule_layout.addWidget(self.rule_edit)
        
        main_layout.addWidget(self.rule_based_group)
        
        # Palette controls
        self.palette_group = QGroupBox("Palette")
        palette_layout = QVBoxLayout(self.palette_group)
        self.rb_palette_single = QRadioButton("Single Color")
        self.rb_palette_single.toggled.connect(self.on_style_type_changed)
        self.style_group.addButton(self.rb_palette_single)
        palette_layout.addWidget(self.rb_palette_single)
        
        self.rb_palette_range = QRadioButton("Color Ramp")
        self.rb_palette_range.toggled.connect(self.on_style_type_changed)
        self.style_group.addButton(self.rb_palette_range)
        palette_layout.addWidget(self.rb_palette_range)
        
        self.cmb_palette_ramp = QComboBox()
        self.cmb_palette_ramp.addItems(["Viridis", "Plasma", "Inferno", "Magma", "Turbo"])
        palette_layout.addWidget(QLabel("Ramp:"))
        palette_layout.addWidget(self.cmb_palette_ramp)
        
        main_layout.addWidget(self.palette_group)
        
        # Common controls for all types
        common_group = QGroupBox("Common Options")
        common_layout = QFormLayout(common_group)
        
        self.sb_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sb_opacity.setRange(0, 100)
        self.sb_opacity.setValue(100)
        common_layout.addRow("Opacity %:", self.sb_opacity)
        
        self.chk_transparent = QCheckBox("Transparency")
        common_layout.addRow("Transparent Background:", self.chk_transparent)
        
        main_layout.addWidget(common_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Reset | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_style)
        button_box.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.reset_style)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def on_style_type_changed(self):
        """Handle style type radio button change."""
        # Enable/disable controls based on selected type
        is_single = self.rb_single_symbol.isChecked()
        is_categorized = self.rb_categorized.isChecked()
        is_graduated = self.rb_graduated.isChecked()
        is_rule = self.rb_rule_based.isChecked()
        is_palette = self.rb_palette.isChecked()
        
        # Enable/disable widgets
        self.single_symbol_group.setEnabled(is_single)
        self.categorized_group.setEnabled(is_categorized)
        self.graduated_group.setEnabled(is_graduated)
        self.rule_based_group.setEnabled(is_rule)
        self.palette_group.setEnabled(is_palette)
    
    def choose_single_color(self):
        """Open color picker for single symbol color."""
        # In full implementation, would open QColorDialog
        # For now, just use a default blue
        pass
    
    def apply_default_style(self):
        """Apply a default style based on layer type."""
        if not self.layer:
            return
        
        # Determine layer type and apply appropriate default
        layer_type = 'unknown'
        
        # Emit default style
        style = {
            'type': 'single_symbol',
            'color': '#0a84ff',  # GeoSuite blue
            'opacity': 100,
            'symbol_type': 'circle',
        }
        self.style_applied.emit(style)
    
    def apply_style(self):
        """Apply the current styling configuration."""
        style = {}
        
        # Get style based on selected type
        if self.rb_single_symbol.isChecked():
            style = {
                'type': 'single_symbol',
                'color': '#0a84ff',  # GeoSuite blue
                'opacity': self.sb_opacity.value(),
                'symbol_type': 'circle',
            }
        elif self.rb_categorized.isChecked():
            style = {
                'type': 'categorized',
                'column': self.cmb_category_column.currentText(),
                'color_ramp': self.cmb_color_ramp.currentText(),
                'breaks': self.sb_breaks_count.value(),
            }
        elif self.rb_graduated.isChecked():
            style = {
                'type': 'graduated',
                'column': self.cmb_grad_column.currentText(),
                'color_ramp': self.cmb_grad_ramp.currentText(),
                'breaks': self.sb_grad_breaks.value(),
            }
        elif self.rb_rule_based.isChecked():
            style = {
                'type': 'rule-based',
                'expression': self.rule_edit.text(),
            }
        elif self.rb_palette.isChecked():
            style = {
                'type': 'palette',
                'palette_ramp': self.cmb_palette_ramp.currentText(),
            }
        
        # Emit style applied signal
        self.style_applied.emit(style)
        self.accept()
    
    def reset_style(self):
        """Reset all styling controls to defaults."""
        # Reset all controls to default values
        self.rb_single_symbol.setChecked(True)
        self.on_style_type_changed()
        self.sb_opacity.setValue(100)
        self.cmb_category_column.clear()
        self.cmb_color_ramp.clear()
        self.cmb_breaks.clear()
        self.sb_breaks_count.setValue(5)
        self.cmb_grad_column.clear()
        self.cmb_grad_ramp.clear()
        self.sb_grad_breaks.setValue(5)
        self.rule_edit.clear()
        self.rb_palette_single.setChecked(True)
        self.rb_palette_range.setChecked(False)
        self.cmb_palette_ramp.clear()
    
    def get_style(self):
        """Return the current style configuration."""
        style = {}
        
        if self.rb_single_symbol.isChecked():
            style = {
                'type': 'single_symbol',
                'color': '#0a84ff',
                'opacity': self.sb_opacity.value(),
                'symbol_type': 'circle',
            }
        elif self.rb_categorized.isChecked():
            style = {
                'type': 'categorized',
                'column': self.cmb_category_column.currentText() if self.cmb_category_column.count() > 0 else '',
                'color_ramp': self.cmb_color_ramp.currentText() if self.cmb_color_ramp.count() > 0 else 'Viridis',
                'breaks': self.sb_breaks_count.value(),
            }
        elif self.rb_graduated.isChecked():
            style = {
                'type': 'graduated',
                'column': self.cmb_grad_column.currentText() if self.cmb_grad_column.count() > 0 else '',
                'color_ramp': self.cmb_grad_ramp.currentText() if self.cmb_grad_ramp.count() > 0 else 'Viridis',
                'breaks': self.sb_grad_breaks.value(),
            }
        elif self.rb_rule_based.isChecked():
            style = {
                'type': 'rule-based',
                'expression': self.rule_edit.text() if self.rule_edit else '',
            }
        elif self.rb_palette.isChecked():
            style = {
                'type': 'palette',
                'palette_ramp': self.cmb_palette_ramp.currentText() if self.cmb_palette_ramp.count() > 0 else 'Viridis',
            }
        
        return style


# Helpful context manager
def show_styling_dialog(layer=None, parent=None):
    """Show the styling dialog and return the style dict if accepted."""
    dlg = StylingDialog(layer, parent)
    result = dlg.exec()
    if result == QDialog.Accepted:
        return dlg.get_style()
    return None