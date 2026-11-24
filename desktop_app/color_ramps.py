#!/usr/bin/env python
"""
Color Ramps for GeoSuite Desktop

Provides color map presets for common GIS uses, matching the style of
QGIS default color ramps and providing consistent visualization across
the application.

Ramps are color schemes that map data values to colors, useful for:
- Graduated symbology (graduated classes)
- Single symbol coloring
- Heat maps and thematic mapping
"""

# Color map presets matching QGIS default styles
# Each ramp maps data values to colors through a gradient

COLOR_MAPS = {
    'Viridis': {
        # A perceptually uniform color map from dark blue to bright yellow
        # Often used for continuous data visualization
        'colors': [
            '#440055',  # Dark purple
            '#481f6b',  # Purple
            '#3a4ca8',  # Purple-blue
            '#2a6db8',  # Blue
            '#21a5cf',  # Light blue
            '#18c7e8',  # Cyan
            '#1e98ff',  # Bright cyan
            '#20bf77',  # Green-cyan
            '#73d134',  # Light green
            '#fee26e',  # Yellow
            '#fdae61',  # Orange
            '#d7191c',  # Red
            '#a50026',  # Dark red
        ],
        'name': 'Viridis (Perceptually Uniform)',
        'description': 'A perceptually uniform color map ideal for sequential data'
    },
    'Plasma': {
        # A wide-range color map from blue to red through purple, yellow
        'colors': [
            '#0c2c88',  # Deep blue
            '#41a3e2',  # Bright blue
            '#3c78d8',  # Blue
            '#2c5aa0',  # Darker blue
            '#2180b0',  # Blue
            '#1f78c3',  # Bright blue
            '#1098d0',  # Cyan-blue
                '#00a6ca',  # Cyan
            '#66cc9a',  # Teal
            '#aad25d',  # Light green
            '#fde725',  # Yellow
            '#fdae61',  # Orange
            '#d73027',  # Red
            '#a50026',  # Dark red
            '#7f0000',  # Dark maroon
        ],
        'name': 'Plasma',
        'description': 'A wide-range color map useful for data with broad ranges'
    },
    'Inferno': {
        # A color map from black to red through orange and yellow
        'colors': [
            '#000004',  # Very dark nearly black
            '#262626',  # Very dark gray
            '#440154',  # Purple
            '#6e016e',  # Purple
            '#9e00b2',  # Purple
            '#c51b72',  # Purple-red
            '#de2d29',  # Red
            '#f03b25',  # Bright red
            '#fc8d59',  # Orange
            '#fdae61',  # Orange-yellow
            '#fef0d0',  # Light yellow
            '#ffffbf',  # Yellow-white
            '#ffffbf',  # Yellow
            '#f7fcb9',  # Light yellow-green
                '#a6dba0',  # Light green
                '#5ab4ac',  # Light teal
        ],
        'name': 'Inferno',
        'description': 'A color map from black to red, suitable for sequential data'
    },
    'Magma': {
        # A color map from black to red through orange and yellow (similar to Inferno)
        'colors': [
            '#000004',  # Very dark nearly black
            '#212121',  # Dark gray
            '#2f0a1e',  # Dark red-purple
            '#491d1f',  # Dark red-purple
            '#6b2e25',  # Red-purple
            '#954129',  # Red-brown
            '#a55e1e',  # Brown
            '#bea400',  # Yellow-brown
            '#e6c261',  # Light yellow-brown
            '#fff7bc',  # Very light yellow
            '#ffffd6',  # Very light yellow
                '#ffffd6',  # Light yellow
                '#ffffd6',  # Light yellow
                '#ffffd6',  # Light yellow
                '#ffffd6',  # Light yellow
        ],
        'name': 'Magma',
        'description': 'A color map from black to yellow/white, similar to Inferno'
    },
    'Greys': {
        # Grayscale ramp from black to white
        'colors': [
            '#000000',  # Black
            '#333333',  # Dark gray
            '#666666',  # Medium gray
            '#999999',  # Light gray
            '#cccccc',  # Light gray
            '#e5e5e5',  # Very light gray
            '#f7f7f7',  # Near white
            '#ffffff',  # White
        ],
        'name': 'Greys',
        'description': 'Grayscale ramp, ideal for single-band rasters'
    },
    'RdYlBu': {
        # Red-Yellow-Blue diverging color map
        'colors': [
            '#a50026',  # Dark red
            '#e41a1c',  # Red
            '#fdae61',  # Orange
            '#ffffbf',  # Yellow
            '#abdda8',  # Light green
            '#2c7bb6',  # Blue
            '#253494',  # Dark blue
        ],
        'name': 'RdYlBu (Diverging)',
        'description': 'Diverging color map with blue-white-red scheme'
    },
}


def get_ramp_colors(ramp_name):
    """Get the colors for a named color ramp."""
    ramp = COLOR_MAPS.get(ramp_name)
    if ramp:
        return ramp['colors']
    # Default to Viridis
    return COLOR_MAPS['Viridis']['colors']


def get_ramp_info(ramp_name):
    """Get information about a color ramp."""
    ramp = COLOR_MAPS.get(ramp_name)
    if ramp:
        return {
            'name': ramp['name'],
            'description': ramp['description'],
            'num_colors': len(ramp['colors']),
        }
    # Default info
    return {
        'name': 'Viridis',
        'description': 'Perceptually uniform color map',
        'num_colors': len(COLOR_MAPS['Viridis']['colors']),
    }


# Predefined style presets for common layer types
STYLE_PRESETS = {
    'point': {
        'name': 'Default Point',
        'symbol_type': 'circle',
        'default_color': '#0a84ff',  # GeoSuite blue
        'default_size': 5,
    },
    'line': {
        'name': 'Default Line',
        'symbol_type': 'line',
        'default_color': '#0a84ff',
        'default_width': 1,
    },
    'polygon': {
        'name': 'Default Polygon',
        'symbol_type': 'polygon',
        'default_brush': '#0a84ff',
        'default_stroke': '#0a84ff',
    },
    'raster_single': {
        'name': 'Single Symbol',
        'default_color': '#0a84ff',
        'default_opacity': 1.0,
    },
    'raster_graduated': {
        'name': 'Graduated (Depth)',
        'color_ramp': 'Plasma',
        'default_classes': 5,
    },
}


def get_style_preset(name):
    """Get a style preset by name."""
    return STYLE_PRESETS.get(name, STYLE_PRESETS['point'])


# Helper function to interpolate between two colors
def interpolate_color(color1, color2, t):
    """Interpolate between two QColor values."""
    # Strip # if present
    c1 = color1.lstrip('#')
    c2 = color2.lstrip('#')
    
    # Parse RGB
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    
    # Interpolate
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    
    return f"#{r:02x}{g:02x}{b:02x}"


# Example usage
if __name__ == "__main__":
    print("GeoSuite Color Ramps")
    print("=" * 40)
    for name, info in COLOR_MAPS.items():
        print(f"\n{name}:")
        print(f"  Description: {info['description']}")
        print(f"  Colors ({len(info['colors'])}):")
        for i, c in enumerate(info['colors']):
            print(f"  {i}: {c}")