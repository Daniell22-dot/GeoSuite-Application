import React, { useState, useEffect } from 'react';
import {
  Typography,
  Box,
  Grid,
  IconButton,
  Tooltip,
  Slider,
  FormControl,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Stack,
  Fade,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Height as HeightIcon,
  Timeline as TimelineIcon,
  Straighten as StraightenIcon,
  Download as DownloadIcon,
  FilterAlt as FilterIcon,
} from '@mui/icons-material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { calculateElevationStats, formatDistance } from '../services/gisUtils';

const ElevationProfile = ({ elevationData, trackData }) => {
  const [chartData, setChartData] = useState([]);
  const [stats, setStats] = useState(null);
  const [smoothing, setSmoothing] = useState(5);
  const [showSmoothed, setShowSmoothed] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState('elevation');

  useEffect(() => {
    if (elevationData?.points || trackData?.points) {
      const points = elevationData?.points || trackData?.points || [];
      processElevationData(points);
    }
  }, [elevationData, trackData, smoothing]);

  const processElevationData = (points) => {
    if (!points || points.length === 0) {
      setChartData([]);
      setStats(null);
      return;
    }

    let cumulativeDistance = 0;
    const rawData = [];
    
    for (let i = 0; i < points.length; i++) {
      const point = points[i];
      if (i > 0) {
        const prev = points[i - 1];
        const d = Math.sqrt(Math.pow(point.longitude - prev.longitude, 2) + Math.pow(point.latitude - prev.latitude, 2)) * 111000;
        cumulativeDistance += d;
      }
      rawData.push({
        distance: cumulativeDistance,
        elevation: point.elevation || point.elevation_corrected || 0,
      });
    }

    const smoothed = applySmoothing(rawData, smoothing);
    setChartData(smoothed);

    const elevations = smoothed.map(d => d.elevation);
    const s = calculateElevationStats(elevations);
    s.totalDistance = cumulativeDistance;
    setStats(s);
  };

  const applySmoothing = (data, windowSize) => {
    if (windowSize <= 1) return data;
    return data.map((point, index) => {
      const start = Math.max(0, index - Math.floor(windowSize / 2));
      const end = Math.min(data.length, index + Math.floor(windowSize / 2));
      const windowData = data.slice(start, end);
      const avgElevation = windowData.reduce((sum, p) => sum + p.elevation, 0) / windowData.length;
      return { ...point, smoothedElevation: avgElevation };
    });
  };

  if (!chartData.length || !stats) {
    return (
      <Box className="glass-panel" sx={{ p: 4, textAlign: 'center', minHeight: 300, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <TimelineIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2, opacity: 0.5 }} />
        <Typography variant="h6" sx={{ fontFamily: 'Outfit' }}>Profile Pending</Typography>
        <Typography variant="body2" color="text.secondary">Upload data to visualize vertical topology.</Typography>
      </Box>
    );
  }

  return (
    <Box className="glass-panel" sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="subtitle1" sx={{ fontFamily: 'Outfit', fontWeight: 600, letterSpacing: 1 }}>
          ELEVATION PROFILE
        </Typography>
        <Stack direction="row" spacing={1}>
           <Tooltip title="Export Data"><IconButton size="small"><DownloadIcon fontSize="small" /></IconButton></Tooltip>
        </Stack>
      </Box>

      <Grid container spacing={2} sx={{ mb: 4 }}>
        <StatCard icon={<HeightIcon sx={{ color: 'primary.light' }}/>} label="Peak" value={`${stats.max?.toFixed(0)}m`} />
        <StatCard icon={<TrendingUpIcon sx={{ color: '#4caf50' }}/>} label="Ascent" value={`${stats.totalAscent?.toFixed(0)}m`} />
        <StatCard icon={<TrendingDownIcon sx={{ color: '#f44336' }}/>} label="Descent" value={`${stats.totalDescent?.toFixed(0)}m`} />
        <StatCard icon={<StraightenIcon sx={{ color: '#00bcd4' }}/>} label="Distance" value={formatDistance(stats.totalDistance)} />
      </Grid>

      <Box sx={{ height: 260, mb: 3 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorElev" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0a84ff" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#0a84ff" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="distance" tickFormatter={formatDistance} hide />
            <YAxis hide domain={['dataMin - 20', 'dataMax + 20']} />
            <RechartsTooltip 
              contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
              labelStyle={{ color: '#0a84ff', fontWeight: 600 }}
              formatter={(val) => [`${val.toFixed(1)} m`, 'Elev']}
            />
            <Area type="monotone" dataKey={showSmoothed ? "smoothedElevation" : "elevation"} stroke="#0a84ff" fillOpacity={1} fill="url(#colorElev)" strokeWidth={2} isAnimationActive={false} />
            <ReferenceLine y={stats.avg} stroke="rgba(255,255,255,0.2)" strokeDasharray="5 5" label={{ value: `AVG: ${stats.avg.toFixed(0)}m`, fill: 'rgba(255,255,255,0.4)', fontSize: 10, position: 'right' }} />
          </AreaChart>
        </ResponsiveContainer>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, alignItems: 'center', opacity: 0.8 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>Smoothing Intensity</Typography>
            <Slider value={smoothing} onChange={(e, v) => setSmoothing(v)} min={1} max={20} size="small" />
          </Box>
          <FormControlLabel
            control={<Switch size="small" checked={showSmoothed} onChange={(e) => setShowSmoothed(e.target.checked)} />}
            label={<Typography variant="caption">Filter Noise</Typography>}
          />
      </Box>
    </Box>
  );
};

const StatCard = ({ icon, label, value }) => (
  <Grid item xs={6} sm={3}>
    <Box sx={{ bgcolor: 'rgba(255,255,255,0.02)', p: 2, borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', textAlign: 'center' }}>
      <Box sx={{ mb: 1, opacity: 0.8 }}>{icon}</Box>
      <Typography variant="h6" sx={{ fontFamily: 'Outfit', fontWeight: 600, fontSize: '1.1rem' }}>{value}</Typography>
      <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</Typography>
    </Box>
  </Grid>
);

export default ElevationProfile;