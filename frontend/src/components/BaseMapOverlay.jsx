import React, { useState } from 'react';
import { TileLayer, LayersControl } from 'react-leaflet';
import { Box, Typography, Switch, FormControlLabel, Slider, Chip } from '@mui/material';
import { useAppConfig } from '../services/gisUtils';

const { BaseLayer, Overlay } = LayersControl;

const BaseMapOverlay = ({ onLayerChange }) => {
  const [overlays, setOverlays] = useState({
    terrain: false,
    hillshade: true,
    contours: false,
    satellite: false,
  });
  const [opacity, setOpacity] = useState(0.7);
  const { config } = useAppConfig();

  const apiLayers = config?.mapLayers || [];
  const baseLayers = apiLayers.filter(l => l.isBase);
  const overlayLayers = apiLayers.filter(l => !l.isBase);

  const handleOverlayToggle = (layer) => {
    const newOverlays = { ...overlays, [layer]: !overlays[layer] };
    setOverlays(newOverlays);
    if (onLayerChange) onLayerChange(newOverlays);
  };

  const handleOpacityChange = (event, newValue) => {
    setOpacity(newValue / 100);
    if (onLayerChange) onLayerChange({ ...overlays, opacity: newValue / 100 });
  };

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
              onClick={() => {}}
              variant="outlined"
              sx={{ borderColor: 'rgba(255,255,255,0.1)', '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' } }}
            />
          ))}
        </Box>
      </Box>

      <Box sx={{ mb: 2.5 }}>
        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>Overlays</Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
          {overlayLayers.map((name) => (
            <FormControlLabel
              key={name.name}
              control={
                <Switch
                  checked={overlays[name.name.toLowerCase()] || false}
                  onChange={() => handleOverlayToggle(name.name.toLowerCase())}
                  size="small"
                />
              }
              label={<Typography variant="body2">{name.name}</Typography>}
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

export const MapLayers = ({ overlays = {}, opacity = 0.5, layers: propLayers }) => {
  const { config } = useAppConfig();
  const apiLayers = propLayers || config?.mapLayers || [];
  const baseLayers = apiLayers.filter(l => l.isBase);
  const overlayLayers = apiLayers.filter(l => !l.isBase);

  return (
    <LayersControl position="topright">
      {baseLayers.map((layer, idx) => (
        <BaseLayer key={layer.name} checked={idx === 0} name={layer.name}>
          <TileLayer
            url={layer.url}
            attribution={layer.attribution}
          />
        </BaseLayer>
      ))}

      {overlayLayers.map((layer) => (
        <Overlay key={layer.name} checked={overlays[layer.name.toLowerCase()]} name={layer.name}>
          <TileLayer
            url={layer.url}
            attribution={layer.attribution}
            opacity={opacity}
          />
        </Overlay>
      ))}
    </LayersControl>
  );
};

export default BaseMapOverlay;