import React, { useState } from 'react';
import { TileLayer, LayersControl } from 'react-leaflet';
import { Box, Typography, Switch, FormControlLabel, Slider, Chip } from '@mui/material';

const { BaseLayer, Overlay } = LayersControl;

const BaseMapOverlay = ({ onLayerChange }) => {
  const [overlays, setOverlays] = useState({
    terrain: false,
    hillshade: true,
    contours: false,
    satellite: false,
  });
  const [opacity, setOpacity] = useState(0.7);

  const handleOverlayToggle = (layer) => {
    const newOverlays = { ...overlays, [layer]: !overlays[layer] };
    setOverlays(newOverlays);
    if (onLayerChange) onLayerChange(newOverlays);
  };

  const handleOpacityChange = (event, newValue) => {
    setOpacity(newValue / 100);
    if (onLayerChange) onLayerChange({ ...overlays, opacity: newValue / 100 });
  };

  const baseLayers = [
    { name: 'Carto Dark', url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png' },
    { name: 'Topo', url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png' },
    { name: 'Satellite', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}' },
    { name: 'Street', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png' },
  ];

  return (
    <Box className="glass-panel" sx={{ p: 2 }}>
      <Typography variant="subtitle2" sx={{ mb: 2, fontFamily: 'Outfit', color: 'primary.light' }}>
        MAP CONFIGURATION
      </Typography>
      
      <Box sx={{ mb: 2.5 }}>
        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>Base Layer</Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {baseLayers.map((layer) => (
            <Chip
              key={layer.name}
              label={layer.name}
              size="small"
              onClick={() => console.log(`Switch to ${layer.name}`)}
              variant="outlined"
              sx={{ borderColor: 'rgba(255,255,255,0.1)', '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' } }}
            />
          ))}
        </Box>
      </Box>

      <Box sx={{ mb: 2.5 }}>
        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>Overlays</Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
          {['Terrain', 'Hillshade', 'Satellite'].map((name) => (
            <FormControlLabel
              key={name}
              control={
                <Switch
                  checked={overlays[name.toLowerCase()]}
                  onChange={() => handleOverlayToggle(name.toLowerCase())}
                  size="small"
                />
              }
              label={<Typography variant="body2">{name}</Typography>}
            />
          ))}
        </Box>
      </Box>

      <Box>
        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
          Overlap Opacity: {Math.round(opacity * 100)}%
        </Typography>
        <Slider
          value={opacity * 100}
          onChange={handleOpacityChange}
          min={0}
          max={100}
          size="small"
        />
      </Box>
    </Box>
  );
};

export const MapLayers = ({ overlays = {}, opacity = 0.5 }) => {
  return (
    <LayersControl position="topright">
      <BaseLayer checked name="Dark Matter">
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
      </BaseLayer>

      <BaseLayer name="World Imagery">
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution='&copy; Esri'
        />
      </BaseLayer>

      <BaseLayer name="OpenTopoMap">
        <TileLayer
          url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenTopoMap contributors'
        />
      </BaseLayer>

      {overlays.hillshade && (
        <Overlay checked name="Hillshade">
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}"
            attribution='&copy; Esri'
            opacity={opacity}
          />
        </Overlay>
      )}

      {overlays.terrain && (
        <Overlay name="Terrain">
          <TileLayer
            url="https://stamen-tiles.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png"
            attribution='&copy; Stamen Design'
            opacity={opacity}
          />
        </Overlay>
      )}
    </LayersControl>
  );
};

export default BaseMapOverlay;