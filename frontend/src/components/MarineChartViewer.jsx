import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, LayersControl, GeoJSON, Polygon, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import * as turf from '@turf/turf';
import {
  Box,
  Paper,
  Typography,
  Button,
  Slider,
  Switch,
  FormControlLabel,
  Chip,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Layers,
  Visibility,
  VisibilityOff,
  ZoomIn,
  ZoomOut,
  MyLocation,
  Download,
  Settings,
} from '@mui/icons-material';
import { useMarine } from '../services/ApiContext';
import { useAppConfig } from '../services/gisUtils';

const createSvgIcon = (color, size = 30) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="2"/>
            <circle cx="12" cy="12" r="4" fill="white"/>
          </svg>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
};

const harborIcon = createSvgIcon('#ff9800', 28);
const buoyIcon = createSvgIcon('#2196f3', 24);

const MarineChartViewer = ({ chartData, onChartLoad }) => {
  const [map, setMap] = useState(null);
  const [layers, setLayers] = useState({
    chart: true,
    soundings: true,
    contours: true,
    navigation: true,
    depth: true,
  });
  const [depthRange, setDepthRange] = useState([0, 100]);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [viewState, setViewState] = useState({
    center: [0, 0],
    zoom: 10,
  });
  const mapRef = useRef();
  const { processMarineFile } = useMarine();
  const { config } = useAppConfig();
  const apiLayers = config?.mapLayers || [];
  const baseLayers = apiLayers.filter(l => l.isBase);
  const overlayLayers = apiLayers.filter(l => !l.isBase);

  // Initialize map
  useEffect(() => {
    if (chartData && map) {
      const bounds = chartData.bounds;
      if (bounds && bounds.north && bounds.south && bounds.east && bounds.west) {
        const mapBounds = [
          [bounds.south, bounds.west],
          [bounds.north, bounds.east],
        ];
        map.fitBounds(mapBounds);
      }
    }
  }, [chartData, map]);

  // Handle layer toggles
  const handleLayerToggle = (layer) => {
    setLayers(prev => ({
      ...prev,
      [layer]: !prev[layer]
    }));
  };

  // Render chart layers
  const renderChartLayers = () => {
    if (!chartData) return null;

    const elements = [];
    const chartId = chartData.chart_id || chartData.id;

    // Render chart image as tile layer
    if (layers.chart && chartData.tiles && chartId) {
      chartData.tiles.tile_urls.forEach(tile => {
        const url = tile.url_template
          .replace('{chart_id}', chartId)
          .replace('{z}', '{z}')
          .replace('{x}', '{x}')
          .replace('{y}', '{y}');
        elements.push(
          <TileLayer
            key={`chart-tile-${tile.zoom}-${chartId}`}
            url={url}
            minZoom={tile.zoom}
            maxZoom={tile.zoom}
            bounds={[
              [chartData.bounds.south, chartData.bounds.west],
              [chartData.bounds.north, chartData.bounds.east]
            ]}
          />
        );
      });
    }

    // Render soundings
    if (layers.soundings && chartData.soundings) {
      chartData.soundings.forEach((sounding, index) => {
        if (sounding.depth >= depthRange[0] && sounding.depth <= depthRange[1]) {
          const popupContent = `
            <div>
              <strong>Depth:</strong> ${sounding.depth} ${sounding.unit || 'm'}<br/>
              <strong>Position:</strong> ${(sounding.latitude || 0).toFixed(6)}, ${(sounding.longitude || 0).toFixed(6)}<br/>
              <strong>Quality:</strong> ${sounding.quality || 'N/A'}
            </div>
          `;

          elements.push(
            <Marker
              key={`sounding-${index}`}
              position={[sounding.latitude, sounding.longitude]}
              icon={buoyIcon}
              eventHandlers={{
                click: () => setSelectedFeature({
                  type: 'sounding',
                  data: sounding,
                  position: [sounding.latitude, sounding.longitude]
                })
              }}
            >
              <Popup>{popupContent}</Popup>
            </Marker>
          );
        }
      });
    }

    // Render depth contours
    if (layers.contours && chartData.contours) {
      chartData.contours.forEach((contour, index) => {
        const points = contour.points || [];
        const coords = points
          .filter(p => p.latitude != null && p.longitude != null)
          .map(p => [p.latitude, p.longitude]);
        
        if (coords.length > 2) {
          const depth = contour.depth || 0;
          let color = '#0000FF';
          if (depth < 10) color = '#FF0000';
          else if (depth < 20) color = '#FFFF00';
          else if (depth < 50) color = '#00FF00';

          elements.push(
            <Polygon
              key={`contour-${index}`}
              positions={coords}
              pathOptions={{
                color: color,
                weight: depth < 10 ? 3 : 2,
                opacity: 0.7,
                fillOpacity: 0.1,
              }}
              eventHandlers={{
                click: () => setSelectedFeature({
                  type: 'contour',
                  data: contour,
                })
              }}
            />
          );
        }
      });
    }

    return elements;
  };

  // Calculate depth statistics
  const calculateDepthStats = () => {
    if (!chartData?.soundings) return null;

    const depths = chartData.soundings.map(s => s.depth);
    return {
      min: Math.min(...depths),
      max: Math.max(...depths),
      avg: depths.reduce((a, b) => a + b, 0) / depths.length,
      count: depths.length,
    };
  };

  const depthStats = calculateDepthStats();

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Control Panel */}
      <Paper 
        elevation={3} 
        sx={{ 
          p: 2, 
          mb: 2, 
          display: 'flex', 
          flexWrap: 'wrap', 
          gap: 2,
          alignItems: 'center'
        }}
      >
        <Typography variant="h6" sx={{ mr: 2 }}>
          Marine Chart Controls
        </Typography>
        
        {Object.keys(layers).map(layer => (
          <FormControlLabel
            key={layer}
            control={
              <Switch
                checked={layers[layer]}
                onChange={() => handleLayerToggle(layer)}
                size="small"
              />
            }
            label={layer.charAt(0).toUpperCase() + layer.slice(1)}
          />
        ))}

        <Box sx={{ ml: 'auto', display: 'flex', gap: 1 }}>
          <Tooltip title="Zoom to chart">
            <IconButton onClick={() => {
              if (chartData?.bounds && map) {
                const bounds = [
                  [chartData.bounds.south, chartData.bounds.west],
                  [chartData.bounds.north, chartData.bounds.east]
                ];
                map.fitBounds(bounds);
              }
            }}>
              <ZoomIn />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Reset view">
            <IconButton onClick={() => map?.setView([0, 0], 2)}>
              <MyLocation />
            </IconButton>
          </Tooltip>
        </Box>
      </Paper>

      {/* Depth Controls */}
      {depthStats && (
        <Paper elevation={2} sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Depth Filter: {depthRange[0]}m - {depthRange[1]}m
          </Typography>
          <Slider
            value={depthRange}
            onChange={(e, newValue) => setDepthRange(newValue)}
            min={Math.floor(depthStats.min)}
            max={Math.ceil(depthStats.max)}
            valueLabelDisplay="auto"
            sx={{ maxWidth: 400 }}
          />
          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
            <Chip label={`Min: ${depthStats.min.toFixed(1)}m`} size="small" />
            <Chip label={`Max: ${depthStats.max.toFixed(1)}m`} size="small" />
            <Chip label={`Avg: ${depthStats.avg.toFixed(1)}m`} size="small" />
            <Chip label={`Points: ${depthStats.count}`} size="small" />
          </Box>
        </Paper>
      )}

      {/* Map Container */}
      <Paper elevation={3} sx={{ flex: 1, position: 'relative' }}>
        <MapContainer
          center={viewState.center}
          zoom={viewState.zoom}
          style={{ height: '100%', width: '100%' }}
          whenCreated={setMap}
          ref={mapRef}
        >
          {/* Base Map Options */}
          <LayersControl position="topright">
            {baseLayers.length > 0 ? (
              baseLayers.map((layer, idx) => (
                <LayersControl.BaseLayer checked={idx === 0} key={layer.name} name={layer.name}>
                  <TileLayer
                    url={layer.url}
                    attribution={layer.attribution}
                  />
                </LayersControl.BaseLayer>
              ))
            ) : (
              <>
                <LayersControl.BaseLayer checked name="OpenStreetMap">
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  />
                </LayersControl.BaseLayer>
                
                <LayersControl.BaseLayer name="Satellite">
                  <TileLayer
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    attribution='Tiles &copy; Esri'
                  />
                </LayersControl.BaseLayer>
                
                <LayersControl.BaseLayer name="Nautical">
                  <TileLayer
                    url="https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png"
                    attribution='&copy; OpenSeaMap contributors'
                  />
                </LayersControl.BaseLayer>
              </>
            )}
          </LayersControl>

          {/* Chart Layers */}
          {renderChartLayers()}
        </MapContainer>

        {/* Feature Info Panel */}
        {selectedFeature && (
          <Paper
            elevation={3}
            sx={{
              position: 'absolute',
              top: 10,
              right: 10,
              width: 300,
              p: 2,
              zIndex: 1000,
              bgcolor: 'background.paper'
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle1">
                {selectedFeature.type.toUpperCase()}
              </Typography>
              <IconButton size="small" onClick={() => setSelectedFeature(null)}>
                <VisibilityOff fontSize="small" />
              </IconButton>
            </Box>
            
            {selectedFeature.type === 'sounding' && (
              <div>
                <Typography variant="body2">
                  <strong>Depth:</strong> {selectedFeature.data.depth} {selectedFeature.data.unit}
                </Typography>
                <Typography variant="body2">
                  <strong>Position:</strong> {selectedFeature.data.latitude.toFixed(6)}, {selectedFeature.data.longitude.toFixed(6)}
                </Typography>
                <Typography variant="body2">
                  <strong>Quality:</strong> {selectedFeature.data.quality}
                </Typography>
              </div>
            )}
            
            {selectedFeature.type === 'contour' && (
              <div>
                <Typography variant="body2">
                  <strong>Depth Contour:</strong> {selectedFeature.data.depth} {selectedFeature.data.unit}
                </Typography>
                <Typography variant="body2">
                  <strong>Points:</strong> {selectedFeature.data.points?.length || 0}
                </Typography>
              </div>
            )}
            
            {selectedFeature.type === 'navigation' && (
              <div>
                <Typography variant="body2">
                  <strong>Name:</strong> {selectedFeature.data.name}
                </Typography>
                <Typography variant="body2">
                  <strong>Type:</strong> {selectedFeature.data.type}
                </Typography>
                {selectedFeature.data.light && (
                  <Typography variant="body2">
                    <strong>Light:</strong> {selectedFeature.data.light}
                  </Typography>
                )}
              </div>
            )}
          </Paper>
        )}
      </Paper>

      {/* Chart Metadata */}
      {chartData?.metadata && (
        <Paper elevation={2} sx={{ p: 2, mt: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Chart Information
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            <Chip label={`Name: ${chartData.metadata.name}`} size="small" />
            <Chip label={`Scale: 1:${chartData.metadata.scale}`} size="small" />
            <Chip label={`Projection: ${chartData.metadata.projection}`} size="small" />
            <Chip label={`Units: ${chartData.metadata.sounding_units}`} size="small" />
            {chartData.metadata.created && (
              <Chip label={`Created: ${chartData.metadata.created}`} size="small" />
            )}
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default MarineChartViewer;