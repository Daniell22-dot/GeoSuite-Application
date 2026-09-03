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

// Custom icons
const harborIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const buoyIcon = new L.Icon({
  iconUrl: 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png',
  iconSize: [30, 30],
  iconAnchor: [15, 30],
});

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

    // Render chart image as tile layer
    if (layers.chart && chartData.tiles) {
      chartData.tiles.tile_urls.forEach(tile => {
        elements.push(
          <TileLayer
            key={`chart-tile-${tile.zoom}`}
            url={tile.url_template.replace('{z}', '{z}').replace('{x}', '{x}').replace('{y}', '{y}')}
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
              <strong>Depth:</strong> ${sounding.depth} ${sounding.unit}<br/>
              <strong>Lat:</strong> ${sounding.latitude.toFixed(6)}<br/>
              <strong>Lon:</strong> ${sounding.longitude.toFixed(6)}<br/>
              <strong>Quality:</strong> ${sounding.quality}
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
        if (contour.points && contour.points.length > 0) {
          const coordinates = contour.points.map(p => [p.latitude, p.longitude]);
          
          // Determine color based on depth
          const depth = contour.depth;
          let color = '#0000FF'; // Blue for deep
          if (depth < 10) color = '#FF0000'; // Red for shallow
          else if (depth < 20) color = '#FFFF00'; // Yellow
          else if (depth < 50) color = '#00FF00'; // Green

          elements.push(
            <Polygon
              key={`contour-${index}`}
              positions={coordinates}
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

    // Render navigation aids
    if (layers.navigation && chartData.navigation_aids) {
      chartData.navigation_aids.forEach((aid, index) => {
        elements.push(
          <Marker
            key={`nav-aid-${index}`}
            position={[aid.latitude, aid.longitude]}
            icon={harborIcon}
            eventHandlers={{
              click: () => setSelectedFeature({
                type: 'navigation',
                data: aid,
                position: [aid.latitude, aid.longitude]
              })
            }}
          >
            <Popup>
              <div>
                <strong>{aid.name}</strong><br/>
                Type: {aid.type}<br/>
                Light: {aid.light || 'None'}<br/>
                Fog Signal: {aid.fog_signal || 'None'}
              </div>
            </Popup>
          </Marker>
        );
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