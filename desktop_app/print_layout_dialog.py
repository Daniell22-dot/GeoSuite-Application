#!/usr/bin/env python
"""
Print Layout Dialog for GeoSuite Desktop

Provides a dialog for configuring and generating print layouts
with map compositions, legends, scale bars, and export options.
"""

import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QPushButton, QLabel, QLineEdit, QCheckBox, QSlider,
    QButtonGroup, QButtonGroup, QDialogButtonBox, QFrame, QSlider,
    QSlider, QFrame)
from PyQt6.QtCore = None  # QSize, pyqtSignal
from PyQt6.QtGui = None  # QColor, QPixmap

from .print_layout_presets import PRESET_LAYOUTS, PrintLayoutConfig


class PrintLayoutDialog(QDialog):
    """
    Dialog for configuring and generating print layouts.
    
    Features:
    - Print layout presets (A4, A3, portrait, landscape)
    - Layout orientation (portrait/landscape)
    - Margin settings
    - Scale bar configuration
    - North arrow (north arrow) configuration
    - Legend configuration
    - Scale bar display
    - Title and metadata fields
    - Export options (PDF, PNG, SVG)
    - Preview of the layout
    """
    
    layout_applied = pyqtSignal(dict)  # Emitted with layout configuration
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Print Layout")
        self.resize(500, 450)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Print Layout")
        self.setMinimumSize(400, 400)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Layout preset group
        preset_group = QGroupBox("Layout Preset")
        preset_layout = QFormLayout(preset_group)
        
        self.cmb_preset = QComboBox()
        self.cmb_preset.addItems(["A4 Portrait", "A4 Landscape", "A3 Portrait", "A3 Landscape"])
        self.cmb_preset.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addRow("Layout Preset:", self.cmb_preset)
        
        # Orientation group
        orient_group = QGroupBox("Orientation")
        orient_layout = QVBoxLayout(orient_group)
        
        self.rb_portrait = QRadioButton("Portrait")
        self.rb_portrait.toggled.connect(self.on_orientation_changed)
        self.rb_portrait.setChecked(True)
        orient_layout.addWidget(self.rb_portrait)
        
        self.rb_landscape = QRadioButton("Landscape")
        self.rb_landscape.toggled.connect(self.on_orientation_changed)
        orient_layout.addWidget(self.rb_landscape)
        
        # Orientations group
        orient_group.setLayout(orient_layout)
        main_layout.addWidget(orient_group)
        
        # Margin settings
        margin_group = QGroupBox("Margins (mm)")
        margin_layout = QFormLayout(margin_group)
        
        self.sb_margin_left = QSlider(Qt.Orientation.Horizontal)
        self.sb_margin_left.setRange(0, 50)
        self.sb_margin_left.setValue(10)
        margin_layout.addRow("Left:", self.sb_margin_left)
        
        self.sb_margin_right = QSlider(Qt.Orientation.Horizontal)
        self.sb_margin_right.setRange(0, 50)
        self.sb_margin_right.setValue(10)
        margin_layout.addRow("Right:", self.sb_margin_right)
        
        self.sb_margin_top = QSlider(Qt.Orientation.Horizontal)
        self.sb_margin_top.setRange(0, 50)
        self.sb_margin_top.setValue(10)
        margin_layout.addRow("Top:", self.sb_margin_top)
        
        self.sb_margin_bottom = QSlider(Qt.Orientation.Horizontal)
        self.sb_margin_bottom.setRange(0, 50)
        self.sb_margin_bottom.setValue(10)
        margin_layout.addRow("Bottom:", self.sb_margin_bottom)
        
        main_layout.addWidget(margin_group)
        
        # Layout options
        options_group = QGroupBox("Layout Options")
        options_layout = QFormLayout(options_group)
        
        self.chk_scale_bar = QCheckBox("Show Scale Bar")
        self.chk_scale_bar.setChecked(True)
        options_layout.addRow("Scale Bar:", self.chk_scale_bar)
        
        self.chk_north_arrow = QCheckBox("Show North Arrow")
        self.chk_north_arrow.setChecked(True)
        options_layout.addRow("North Arrow:", self.chk_north_arrow)
        
        self.chk_legend = QCheckBox("Show Legend")
        self.chk_legend.setChecked(True)
        options_layout.addRow("Legend:", self.chk_legend)
        
        self.chk_scale_bar_num = QCheckBox("Show Scale Numerator")
        self.chk_scale_bar_num.setChecked(True)
        options_layout.addRow("Scale Numerator:", self.chk_scale_bar_num)
        
        self.sb_scale_denominator = QSlider(Qt.Orientation.Horizontal)
        self.sb_scale_denominator.setRange(100, 100000)
        self.sb_scale_denominator.setValue(50000)
        options_layout.addRow("Scale Denominator:", self.sb_scale_denominator)
        
        main_layout.addWidget(options_group)
        
        # Metadata group
        metadata_group = QGroupBox("Layout Metadata")
        metadata_layout = QFormLayout(metadata_group)
        
        self.le_title = QLineEdit("Layout")
        metadata_layout.addRow("Title:", self.le_title)
        
        self.le_author = QLineEdit("")
        metadata_layout.addRow("Author:", self.le_author)
        
        self.le_keywords = QLineEdit("")
        metadata_layout.addRow("Keywords:", self.le_keywords)
        
        self.le_comments = QLineEdit("")
        metadata_layout.addRow("Comments:", self.le_comments)
        
        main_layout.addWidget(metadata_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Reset | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_layout)
        button_box.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.reset_layout)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def on_preset_changed(self, preset_name):
        """Handle preset change."""
        layout = PRESET_LAYOUTS.get(preset_name)
        if layout:
            # Update margin sliders
            self.sb_margin_left.setValue(layout['margin'])
            self.sb_margin_right.setValue(layout['margin'])
            self.sb_margin_top.setValue(layout['margin'])
            self.sb_margin_bottom.setValue(layout['margin'])
    
    def on_orientation_changed(self, state):
        """Handle orientation change."""
        sender = self.sender()
        if sender.isChecked():
            if sender.text() == "Portrait":
                self.sb_margin_top.setValue(10)
                self.sb_margin_bottom.setValue(10)
            else:
                self.sb_margin_left.setValue(10)
                self.sb_margin_right.setValue(10)
    
    def apply_layout(self):
        """Apply the layout configuration."""
        layout = {
            'orientation': 'portrait' if self.rb_portrait.isChecked() else 'landscape',
            'margin': self.sb_margin_left.value(),
            'scale_bar': self.chk_scale_bar.isChecked(),
            'north_arrow': self.chk_north_arrow.isChecked(),
            'legend': self.chk_legend.isChecked(),
            'scale_denominator': self.sb_scale_denominator.value(),
            'title': self.le_title.text(),
            'author': self.le_author.text(),
            'keywords': self.le_keywords.text(),
            'comments': self.le_comments.text(),
        }
        self.layout_applied.emit(layout)
        self.accept()
    
    def reset_layout(self):
        """Reset all controls to defaults."""
        self.cmb_preset.setCurrentIndex(0)
        self.rb_portrait.setChecked(True)
        self.sb_margin_left.setValue(10)
        self.sb_margin_right.setValue(10)
        self.sb_margin_top.setValue(10)
        self.sb_margin_bottom.setValue(10)
        self.chk_scale_bar.setChecked(True)
        self.chk_north_arrow.setChecked(True)
        self.chk_legend.setChecked(True)
        self.chk_scale_bar_num.setChecked(True)
        self.sb_scale_denominator.setValue(50000)
        self.le_title.setText("Layout")
        self.le_author.setText("")
        self.le_keywords.setText("")
        self.le_comments.setText("")
    
    def get_layout(self):
        """Return the current layout configuration."""
        return {
            'orientation': 'portrait' if self.rb_portrait.isChecked() else 'landscape',
            'margin': self.sb_margin_left.value(),
            'scale_bar': self.chk_scale_bar.isChecked(),
            'north_arrow': self.chk_north_arrow.isChecked(),
            'legend': self.chk_legend.isChecked(),
            'scale_denominator': self.sb_scale_denominator.value(),
            'title': self.le_title.text(),
            'author': self.le_author.text(),
            'keywords': self.le_keywords.text(),
            'comments': self.le_comments.text(),
        }


# Helpful context manager
def show_print_layout_dialog(parent=None):
    """Show the print layout dialog and return the configuration."""
    dlg = PrintLayoutDialog(parent)
    result = dlg.exec()
    if result == QDialog.Accepted:
        return dlg.get_layout()
    return None