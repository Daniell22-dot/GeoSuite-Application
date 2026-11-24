#!/usr/bin/env python
"""
Attribute Editing Module for GeoSuite Desktop

Manages edit sessions for vector layer attributes, including undo/redo,
dirty tracking, and save/cancel operations.
"""

from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore = None  # QDate, QSettings
from PyQt6.QtGui = None  # QUndoStack

# Field type to validator mapping
FIELD_VALIDATORS = {
    'Integer': {
        'type': int,
        'validator': lambda x: isinstance(x, int),
        'help': 'Must be a whole number',
    },
    'Real': {
        'type': float,
        'validator': lambda x: isinstance(x, (int, float)),
        'help': 'Must be a number',
    },
    'String': {
        'type': str,
        'validator': lambda x: isinstance(x, str),
        'help': 'Text value',
    },
    'Date': {
        'type': str,
        'validator': lambda x: True,  # Date validation delegated to UI
        'help': 'Date value (YYYY-MM-DD format)',
    },
}


class EditSession:
    """Manages an edit session for vector layer attributes."""
    
    def __init__(self, layer):
        self.layer = layer
        self.old_attributes = {}  # Old attribute values before edit
        self.new_attributes = {}  # New attribute values after edit
        self.dirty = False  # Has anything been changed?
        self.session_id = id(self)
    
    def start_edit(self, feature_id):
        """Start an edit session for a specific feature."""
        self.old_attributes[feature_id] = self.layer.dataProvider().attributeValues(feature_id)
        self.new_attributes[feature_id] = dict(self.old_attributes[feature_id])
        self.dirty = False
    
    def set_attribute(self, feature_id, field_name, value):
        """Set an attribute value and mark as dirty."""
        if feature_id in self.new_attributes:
            self.new_attributes[feature_id][field_name] = value
            self.dirty = True
    
    def commit(self):
        """Commit the edit session to the layer."""
        if not self.dirty:
            return False
        
        # Apply changes to the layer
        provider = self.layer.dataProvider()
        if provider:
            for feature_id, attrs in self.new_attributes.items():
                provider.changeAttributeValues({feature_id: attrs})
        
        self.dirty = False
        return True
    
    def rollback(self):
        """Rollback the edit session to original values."""
        if self.old_attributes:
            provider = self.layer.dataProvider()
            if provider:
                for feature_id, old_attrs in self.old_attributes.items():
                    provider.changeAttributeValues({feature_id: old_attrs})
            self.dirty = False
            return True
        return False


class AttributeEditingManager:
    """Manages edit sessions for multiple layers."""
    
    def __init__(self):
        self.sessions = {}  # layer_id -> EditSession
    
    def start_session(self, layer):
        """Start an edit session for a layer."""
        session_id = id(self)
        self.sessions[id(self)] = EditSession(layer)
        return id(self)
    
    def get_session(self, layer):
        """Get the edit session for a layer."""
        for sid, session in self.sessions.items():
            if session.layer == layer:
                return session
        return None
    
    def finish_session(self, layer):
        """Finish and cleanup an edit session."""
        session = self.get_session(layer)
        if session:
            # Commit any pending changes
            session.commit()
            self.sessions.pop(id(self), None)