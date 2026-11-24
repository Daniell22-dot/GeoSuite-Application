#!/usr/bin/env python
"""
Layer Compatibility Checker for GeoSuite Desktop

Checks CRS compatibility across loaded layers and provides warnings
when mismatches are detected.
"""

def check_crs_compatibility(layers):
    """Check CRS compatibility across all layers.
    
    Args:
        layers: List of layer dicts with 'crs' key
        
    Returns:
        tuple: (is_compatible, mismatched_crss, warning_message)
    """
    if not layers:
        return True, [], ""
    
    # Extract CRS from each layer
    crss = []
    for layer in layers:
        crs = layer.get('crs', 'EPSG:4326')
        crss.append(crs)
    
    # Unique CRS values
    unique_crss = set(crss)
    
    # If only one unique CRS, all compatible
    if len(unique_crss) <= 1:
        return True, [], ""
    
    # Multiple different CRS values
    mismatched = ", ".join(sorted(unique_crss))
    warning = f"CRS Mismatch Detected: {len(layers)} layers use {len(unique_crss)} different CRS values"
    
    return False, list(unique_crss), warning


def format_crs_for_display(crs):
    """Format a CRS string for display purposes."""
    # Strip 'EPSG:' prefix for cleaner display, but keep it for compatibility
    if crs and crs.startswith("EPSG:"):
        return crs
    return crs or "Unknown CRS"


def compat_tooltip(crss):
    """Generate a tooltip text showing CRS compatibility status."""
    if not crss:
        return "No CRS information available"
    
    unique = set(crss)
    if len(unique) == 1:
        return f"All layers use {list(unique)[0]} CRS - Compatible"
    
    mismatched = ", ".join(sorted(unique))
    count = len(unique)
    total = len(crss)
    return f"{total} layers use {count} different CRS values: {mismatched}\nSome layer operations may produce unexpected results"


# Example usage
if __name__ == "__main__":
    # Test with sample layers
    test_layers = [
        {'name': 'Layer 1', 'crs': 'EPSG:4326'},
        {'name': 'Layer 2', 'crs': 'EPSG:4326'},
        {'name': 'Layer 3', 'crs': 'EPSG:3857'},
    ]
    
    compatible, mismatched, warning = check_crs_compatibility(test_layers)
    print(f"Compatible: {compatible}")
    print(f"Mismatched: {mismatched}")
    print(f"Warning: {warning}")
    
    # Test with compatible layers
    test_layers2 = [
        {'name': 'Layer 1', 'crs': 'EPSG:4326'},
        {'name': 'Layer 2', 'crs': 'EPSG:4326'},
    ]
    
    compatible2, mismatched2, warning2 = check_crs_compatibility(test_layers2)
    print(f"\nCompatible2: {compatible2}")
    print(f"Mismatched2: {mismatched2}")
    print(f"Warning2: {warning2}")