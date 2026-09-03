import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Box,
  Typography,
  Button,
  Switch,
  FormControlLabel,
  CircularProgress,
  IconButton,
  Tooltip,
  MenuItem,
  Select,
  FormControl,
  Stack,
  Fade,
  Grid,
} from '@mui/material';
import {
  Terrain,
  Download,
  Timeline,
  Water,
  MyLocation,
  ZoomIn,
  ZoomOut,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { useWatershed } from '../services/ApiContext';
import { useAppConfig } from '../services/gisUtils';

const WatershedTools = ({ demData, onAnalysisComplete }) => {
  const [map, setMap] = useState(null);
  const [layers, setLayers] = useState({ flow: true, streams: true, watershed: true });
  const [analysisState, setAnalysisState] = useState({ loading: false, error: null, results: null });
  const [pourPoint, setPourPoint] = useState(null);
  const [threshold, setThreshold] = useState(1000);
  const [mapZoom, setMapZoom] = useState(2);
  const { delineateWatershed, extractStreams, calculateFlowPath } = useWatershed();
  const { config } = useAppConfig();
  const baseTile = (config?.mapLayers || []).find(l => l.name === 'Dark Matter')?.url || 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png';
  const thresholds = config?.watershedThresholds || [500, 1000, 5000];

  useEffect(() => {
    if (map) {
      const handleClick = (e) => setPourPoint({ lat: e.latlng.lat, lng: e.latlng.lng });
      map.on('click', handleClick);
      return () => map.off('click', handleClick);
    }
  }, [map]);

  const runAnalysis = async () => {
    if (!pourPoint || !demData) return;
    setAnalysisState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const watershed = await delineateWatershed(demData.id, { latitude: pourPoint.lat, longitude: pourPoint.lng });
      const streams = await extractStreams(demData.id, threshold);
      const flowPath = await calculateFlowPath(demData.id, { latitude: pourPoint.lat, longitude: pourPoint.lng });
      const results = { watershed, streams, flowPath, timestamp: new Date().toISOString() };
      setAnalysisState({ loading: false, error: null, results });
      if (onAnalysisComplete) onAnalysisComplete(results);
    } catch (error) {
      setAnalysisState({ loading: false, error: error.message || 'Analysis failed', results: null });
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 3 }}>
      {/* Header & Global Controls */}
      <Box className="glass-panel" sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Stack direction="row" spacing={3} alignItems="center">
          <Typography variant="subtitle2" sx={{ fontFamily: 'Outfit', fontWeight: 600, letterSpacing: 1, color: 'primary.light' }}>
            WATERSHED ENGINE
          </Typography>
          <Stack direction="row" spacing={1}>
            {Object.keys(layers).map(k => (
              <FormControlLabel
                key={k}
                control={<Switch size="small" checked={layers[k]} onChange={() => setLayers(p => ({ ...p, [k]: !p[k] }))} />}
                label={<Typography variant="caption" sx={{ textTransform: 'capitalize' }}>{k}</Typography>}
              />
            ))}
          </Stack>
        </Stack>
        
        <Stack direction="row" spacing={2}>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <Select value={threshold} onChange={(e) => setThreshold(e.target.value)} sx={{ fontSize: '0.8rem', bgcolor: 'rgba(255,255,255,0.02)' }}>
              {thresholds.map(t => (
                <MenuItem key={t} value={t}>{t} cells</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="contained"
            size="small"
            startIcon={analysisState.loading ? <CircularProgress size={16} color="inherit"/> : <Terrain />}
            onClick={runAnalysis}
            disabled={!pourPoint || analysisState.loading}
            sx={{ px: 3, fontWeight: 600 }}
          >
            PROCESS
          </Button>
        </Stack>
      </Box>

      {/* Main Workspace */}
      <Box sx={{ display: 'flex', flex: 1, gap: 3, minHeight: 0 }}>
        {/* Map Workspace */}
        <Box sx={{ flex: 2, position: 'relative', borderRadius: '16px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)' }}>
          <MapContainer center={[0, 0]} zoom={mapZoom} style={{ height: '100%', width: '100%' }} whenCreated={setMap} zoomControl={false}>
            <TileLayer url={baseTile} attribution="&copy; CARTO" />
            {analysisState.results && (
              <>
                {layers.watershed && analysisState.results.watershed?.boundary && (
                  <GeoJSON data={analysisState.results.watershed.boundary} style={{ color: '#f44336', weight: 2, fillOpacity: 0.1 }} />
                )}
                {layers.streams && analysisState.results.streams?.network && (
                  <GeoJSON data={analysisState.results.streams.network} style={(f) => ({ color: '#0a84ff', weight: f?.properties?.order || 1, opacity: 0.8 })} />
                )}
              </>
            )}
            {pourPoint && <CircleMarker center={[pourPoint.lat, pourPoint.lng]} radius={6} pathOptions={{ color: '#fff', fillColor: '#f44336', fillOpacity: 1, weight: 2 }} />}
          </MapContainer>

          {/* Map Nav Overlay */}
          <Box className="glass-panel" sx={{ position: 'absolute', top: 15, left: 15, zIndex: 1000, p: 0.5 }}>
             <Stack direction="row" spacing={0.5}>
                <IconButton size="small" onClick={() => map?.zoomIn()}><ZoomIn fontSize="small"/></IconButton>
                <IconButton size="small" onClick={() => map?.zoomOut()}><ZoomOut fontSize="small"/></IconButton>
             </Stack>
          </Box>

          {!pourPoint && (
            <Fade in>
              <Box sx={{ position: 'absolute', inset: 0, zIndex: 999, bgcolor: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
                 <Box sx={{ textAlign: 'center', p: 3, borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)', bgcolor: 'rgba(15,23,42,0.8)' }}>
                    <Water sx={{ fontSize: 40, color: 'primary.main', mb: 2, opacity: 0.8 }} />
                    <Typography variant="h6" sx={{ fontFamily: 'Outfit' }}>Set Pour Point</Typography>
                    <Typography variant="caption" color="text.secondary">Select the outlet location on the map to begin delineation.</Typography>
                 </Box>
              </Box>
            </Fade>
          )}
        </Box>

        {/* Results Insight */}
        <Box sx={{ flex: 1, overflowY: 'auto', pr: 1 }}>
          {!analysisState.results ? (
             <Box className="glass-panel" sx={{ p: 4, height: '100%', textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <Timeline sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.3 }} />
                <Typography variant="body2" color="text.secondary">Insights will appear here after analysis.</Typography>
             </Box>
          ) : (
            <Stack spacing={2}>
              <Box className="glass-panel" sx={{ p: 2 }}>
                <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', mb: 2, display: 'block' }}>MORPHOMETRIC STATS</Typography>
                <Grid container spacing={2}>
                  <AnalysisStat label="AREA" value={`${analysisState.results.watershed.area_km2?.toFixed(2)} km²`} />
                  <AnalysisStat label="RELIEF" value={`${analysisState.results.watershed.elevation_stats?.relief?.toFixed(0)} m`} />
                </Grid>
              </Box>

              <Box className="glass-panel" sx={{ p: 2 }}>
                 <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', mb: 2, display: 'block' }}>FLOW TOPOLOGY</Typography>
                 <Box sx={{ height: 180 }}>
                    <ResponsiveContainer width="100%" height="100%">
                       <AreaChart data={analysisState.results.flowPath?.elevation_profile?.map((e, i) => ({ d: i, e }))}>
                          <Area type="monotone" dataKey="e" stroke="#0a84ff" fill="rgba(10, 132, 255, 0.1)" strokeWidth={2} dot={false} />
                          <RechartsTooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: 'none', borderRadius: '8px' }} />
                       </AreaChart>
                    </ResponsiveContainer>
                 </Box>
              </Box>

              <Button variant="outlined" startIcon={<Download />} fullWidth onClick={() => {
                const blob = new Blob([JSON.stringify(analysisState.results)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = url; a.download = 'watershed_meta.json'; a.click();
              }}>
                EXPORT GeoJSON
              </Button>
            </Stack>
          )}
        </Box>
      </Box>
    </Box>
  );
};

const AnalysisStat = ({ label, value }) => (
  <Grid item xs={6}>
    <Box sx={{ p: 1.5, borderRadius: '8px', bgcolor: 'rgba(255,255,255,0.02)' }}>
      <Typography variant="h6" sx={{ fontFamily: 'Outfit', fontWeight: 600, fontSize: '1rem' }}>{value}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', letterSpacing: 0.5 }}>{label}</Typography>
    </Box>
  </Grid>
);

export default WatershedTools;