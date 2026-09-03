import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  Polyline,
  Marker,
  Popup,
  Polygon,
  CircleMarker,
  ScaleControl,
  ZoomControl,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Box,
  Typography,
  IconButton,
  Tooltip,
  Paper,
  Stack,
  Fade,
} from '@mui/material';
import {
  MyLocation as MyLocationIcon,
  FilterCenterFocus as FocusIcon,
  Fullscreen as FullscreenIcon,
  GpsFixed as GpsIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { MapLayers } from './BaseMapOverlay';
import { calculateDistance } from '../services/gisUtils';
import { useAppConfig } from '../services/gisUtils';

// Fix for Leaflet default icons
delete L.Icon.Default.prototype._getIconUrl;

const createSvgIcon = (color) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 21C16 17.5 19 14.4087 19 10.5C19 6.63401 15.866 3.5 12 3.5C8.13401 3.5 5 6.63401 5 10.5C5 14.4087 8 17.5 12 21Z" fill="${color}" stroke="white" stroke-width="2"/>
            <circle cx="12" cy="10.5" r="2.5" fill="white"/>
          </svg>`,
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24],
  });
};

const startIcon = createSvgIcon('#4caf50');
const endIcon = createSvgIcon('#f44336');
const waypointIcon = createSvgIcon('#2196f3');

const MapViewer = ({
  trackData,
  elevationData,
  watershedData,
  marineData,
  pourPoint,
  onPointSelect,
  showControls = true,
  height = '500px',
}) => {
  const [map, setMap] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const mapRef = useRef();
  const { config } = useAppConfig();

  const calculateDataBounds = () => {
    const bounds = { north: -90, south: 90, east: -180, west: 180 };
    let hasData = false;

    if (trackData?.points?.length > 0) {
      trackData.points.forEach(point => {
        bounds.north = Math.max(bounds.north, point.latitude);
        bounds.south = Math.min(bounds.south, point.latitude);
        bounds.east = Math.max(bounds.east, point.longitude);
        bounds.west = Math.min(bounds.west, point.longitude);
      });
      hasData = true;
    }

    if (watershedData?.bounds) {
        bounds.north = Math.max(bounds.north, watershedData.bounds.north);
        bounds.south = Math.min(bounds.south, watershedData.bounds.south);
        bounds.east = Math.max(bounds.east, watershedData.bounds.east);
        bounds.west = Math.min(bounds.west, watershedData.bounds.west);
        hasData = true;
    }

    return hasData ? bounds : null;
  };

  useEffect(() => {
    if (map) {
      const bounds = calculateDataBounds();
      if (bounds) {
        map.fitBounds([[bounds.south, bounds.west], [bounds.north, bounds.east]], { padding: [50, 50] });
      }
    }
  }, [map, trackData, watershedData]);

  const renderTrack = () => {
    if (!trackData?.points || trackData.points.length === 0) return null;
    return (
      <Polyline
        positions={trackData.points.map(p => [p.latitude, p.longitude])}
        pathOptions={{ color: '#0a84ff', weight: 4, opacity: 0.8 }}
      />
    );
  };

  const renderMarkers = () => {
    if (!trackData?.points || trackData.points.length === 0) return null;
    const points = trackData.points;
    const markers = [];

    if (points[0]) {
      markers.push(
        <Marker key="start" position={[points[0].latitude, points[0].longitude]} icon={startIcon}>
          <Popup><Typography variant="subtitle2">Start Point</Typography></Popup>
        </Marker>
      );
    }

    if (points.length > 1) {
      const last = points[points.length - 1];
      markers.push(
        <Marker key="end" position={[last.latitude, last.longitude]} icon={endIcon}>
          <Popup><Typography variant="subtitle2">End Point</Typography></Popup>
        </Marker>
      );
    }
    return markers;
  };

  const zoomToBounds = () => {
    const bounds = calculateDataBounds();
    if (map && bounds) map.fitBounds([[bounds.south, bounds.west], [bounds.north, bounds.east]]);
  };

  const toggleFullscreen = () => {
    const elem = mapRef.current;
    if (!document.fullscreenElement) elem.requestFullscreen?.();
    else document.exitFullscreen?.();
  };

  return (
    <Box sx={{ position: 'relative', height, borderRadius: '16px', overflow: 'hidden' }} ref={mapRef}>
      {/* Map Content */}
      <MapContainer
        center={[0, 0]}
        zoom={2}
        style={{ height: '100%', width: '100%' }}
        whenCreated={setMap}
        zoomControl={false}
      >
        <MapLayers layers={config?.mapLayers} />
        <ScaleControl position="bottomleft" imperial={false} />
        <ZoomControl position="bottomright" />
        
        {renderTrack()}
        {renderMarkers()}
        
        {watershedData?.boundary && (
            <GeoJSON data={watershedData.boundary} style={{ color: '#ff4b2b', weight: 3, opacity: 0.6, fillOpacity: 0.1 }} />
        )}
      </MapContainer>

      {/* Modern Control Overlays */}
      {showControls && (
        <>
          <Box className="glass-panel" sx={{ position: 'absolute', top: 20, left: 20, zIndex: 1000, p: 0.5 }}>
            <Stack direction="row" spacing={0.5}>
              <Tooltip title="Data Focus">
                <IconButton size="small" onClick={zoomToBounds} sx={{ color: '#fff' }}><FocusIcon fontSize="small" /></IconButton>
              </Tooltip>
              <Tooltip title="Fullscreen">
                <IconButton size="small" onClick={toggleFullscreen} sx={{ color: '#fff' }}><FullscreenIcon fontSize="small" /></IconButton>
              </Tooltip>
            </Stack>
          </Box>

          <Box className="glass-panel" sx={{ position: 'absolute', top: 20, right: 20, zIndex: 1000, py: 1.5, px: 2, minWidth: 160 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, color: 'primary.light', display: 'block', mb: 1.5, letterSpacing: 1 }}>VISUAL LAYERS</Typography>
            <Stack spacing={1}>
                 <LayerToggle label="Track Data" active={!!trackData} />
                 <LayerToggle label="Watershed" active={!!watershedData} />
                 <LayerToggle label="Elev Mesh" active={!!elevationData} />
            </Stack>
          </Box>
        </>
      )}

      {/* Selected Metadata Popup */}
      {selectedFeature && (
         <Fade in>
           <Box className="glass-panel" sx={{ position: 'absolute', bottom: 30, left: 30, zIndex: 1000, p: 2, minWidth: 200 }}>
             <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
               <Typography variant="subtitle2" sx={{ fontFamily: 'Outfit' }}>FEATURE DATA</Typography>
               <IconButton size="small" onClick={() => setSelectedFeature(null)}><CloseIcon fontSize="inherit" /></IconButton>
             </Box>
             <Typography variant="body2" color="text.secondary">
               Lat: {selectedFeature.position[0].toFixed(6)}<br/>
               Lon: {selectedFeature.position[1].toFixed(6)}
             </Typography>
           </Box>
         </Fade>
      )}

      {/* Premium Empty State */}
      {!trackData && !watershedData && !marineData && (
        <Box
          sx={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(12px)',
            zIndex: 999,
          }}
        >
          <GpsIcon sx={{ fontSize: 60, color: 'primary.main', mb: 3, opacity: 0.8 }} />
          <Typography variant="h5" sx={{ fontFamily: 'Outfit', fontWeight: 600, mb: 1 }}>Analysis Workspace Ready</Typography>
          <Typography variant="body2" sx={{ opacity: 0.7, maxWidth: 320, textAlign: 'center' }}>
            Upload a geospatial file in the sidebar to begin high-performance processing.
          </Typography>
        </Box>
      )}
    </Box>
  );
};

const LayerToggle = ({ label, active }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', opacity: active ? 1 : 0.4 }}>
        <Typography variant="caption" sx={{ fontWeight: 500 }}>{label}</Typography>
        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: active ? 'primary.main' : 'rgba(255,255,255,0.2)' }} />
    </Box>
);

export default MapViewer;