#!/usr/bin/env python
"""
Analysis Results Dock Widget for GeoSuite Desktop

Displays analysis results from spatial analysis tools and provides
save/load functionality for results.
"""

from PyQt6.QtWidgets import (QDockWidget, QVBoxLayout, QWidget, QLabel,
    QPushButton, QFrame, QGroupBox, QFormLayout, QComboBox, QComboBox,
    QListWidget, QListWidgetItem, QLineEdit)
from PyQt6.QtCore = None  # QSize, Qt
from PyQt6.QtGui = None  # QColor, QPixmap

# In-memory storage for analysis results
analysis_results_storage = []


class AnalysisResultsDock(QDockWidget):
    """Dock widget displaying analysis results and providing save/load functionality."""
    
    def __init__(self, parent=None):
        super().__init__(self)
        self.setWindowTitle("Analysis Results")
        self.resize(300, 400)
        
        self.setup_ui()
        self.load_results()
    
    def setup_ui(self):
        """Set up the user interface."""
        widget = QWidget()
        self.setWidget(widget)
        layout = QVBoxLayout(widget)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.on_result_selected)
        layout.addWidget(self.results_list)
        
        # Buttons frame
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        
        self.btn_save = QPushButton("Save Results")
        self.btn_save.clicked.connect(self.save_results)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_clear = QPushButton("Clear Results")
        self.btn_clear.clicked.connect(self.clear_results)
        btn_layout.addWidget(self.btn_clear)
        
        self.btn_export = QPushButton("Export...")
        self.btn_export.clicked.connect(self.export_results)
        btn_layout.addWidget(self.btn_export)
        
        layout.addWidget(btn_frame)
        
        # Info label
        self.info_label = QLabel("No results yet. Run analysis tools to display results.")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
    
    def load_results(self):
        """Load stored analysis results."""
        global analysis_results_storage
        self.results_list.clear()
        
        if not analysis_results_storage:
            self.info_label.setVisible(True)
            self.info_label.setText("No results yet. Run analysis tools to display results.")
            return
        
        self.info_label.setVisible(False)
        for i, result in enumerate(analysis_results_storage):
            item = QListWidgetItem(f"Result {i+1}: {result.get('name', 'Unknown')[:50]}")
            item.setData(1000, result)  # Store result data in item user role
            self.results_list.addItem(item)
        
        self.info_label.setVisible(False)
    
    def add_result(self, result_dict):
        """Add a new analysis result."""
        global analysis_results_storage
        analysis_results_storage.append(result_dict)
        index = self.results_list.count()
        item = QListWidgetItem(f"Result {index + 1}: {result_dict.get('name', 'Unknown')[:50]}")
        item.setData(1000, result_dict)
        self.results_list.addItem(item)
        self.info_label.setVisible(False)
    
    def on_result_selected(self, item):
        """Handle result selection."""
        result = item.data(1000)
        # Could emit signal or open details view
        pass
    
    def save_results(self):
        """Save analysis results to file."""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "",
            "GeoJSON (*.geojson);;CSV (*.csv);;All Files (*)"
        )
        
        if file_path:
            result_data = self.results_list.currentItem().data(1000) if self.results_list.currentItem() else {}
            if save_analysis_result(result_data, file_path):
                self.statusBar.showMessage(f"Results saved to {file_path}", 2000)
            else:
                QMessageBox.warning(self, "Error", "Failed to save results")
    
    def clear_results(self):
        """Clear all analysis results."""
        global analysis_results_storage
        analysis_results_storage = []
        self.results_list.clear()
        self.info_label.setVisible(True)
        self.info_label.setText("No results yet. Run analysis tools to display results.")
    
    def export_results(self):
        """Export results with format selection."""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "",
            "GeoJSON (*.geojson);;CSV (*.csv);;All Files (*)"
        )
        
        if file_path:
            # Get current result
            current_item = self.results_list.currentItem()
            if current_item:
                result_data = current_item.data(1000)
                if save_analysis_result(result_data, file_path):
                    QMessageBox.information(self, "Success", "Results exported successfully")
                else:
                    QMessageBox.warning(self, "Error", "Failed to export results")
    
    def set_status_bar(self, status_bar):
        """Set the status bar for messages."""
        self.status_bar = status_bar