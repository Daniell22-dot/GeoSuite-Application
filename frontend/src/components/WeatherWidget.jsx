import React, { useState, useEffect } from 'react';
import { Box, Typography, Skeleton, Tooltip } from '@mui/material';
import { 
  WbSunny as SunIcon, 
  Cloud as CloudIcon, 
  Opacity as RainIcon, 
  Thunderstorm as BoltIcon,
  Air as WindIcon,
  WaterDrop as DropIcon,
  LocationOn as LocationIcon
} from '@mui/icons-material';
import axios from 'axios';

const WeatherWidget = ({ city = 'Nairobi,KE' }) => {
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchWeather = async () => {
      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        const response = await axios.get(`${apiUrl}/api/v1/weather/current?q=${city}`);
        setWeather(response.data);
        setError(false);
      } catch (err) {
        console.error('Weather fetch error:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchWeather();
    // Refresh every 10 minutes
    const interval = setInterval(fetchWeather, 600000);
    return () => clearInterval(interval);
  }, [city]);

  const getWeatherIcon = (id) => {
    if (id >= 200 && id < 300) return <BoltIcon sx={{ color: '#bf5af2' }} />;
    if (id >= 300 && id < 600) return <RainIcon sx={{ color: '#0a84ff' }} />;
    if (id >= 800) return <SunIcon sx={{ color: '#ffd60a' }} />;
    return <CloudIcon sx={{ color: '#94a3b8' }} />;
  };

  if (loading) {
    return (
      <Box sx={{ p: 2, borderRadius: '16px', bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
        <Skeleton variant="text" width="60%" height={24} sx={{ mb: 1 }} />
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Skeleton variant="circular" width={40} height={40} />
          <Skeleton variant="text" width="30%" height={40} />
        </Box>
      </Box>
    );
  }

  if (error || !weather) return null;

  return (
    <Tooltip title={`Humidity: ${weather.humidity}% | Wind: ${weather.wind_speed} m/s`} arrow placement="right">
      <Box 
        sx={{ 
          p: 2.5, 
          borderRadius: '16px', 
          background: 'linear-gradient(135deg, rgba(10, 132, 255, 0.05) 0%, rgba(94, 92, 230, 0.05) 100%)',
          border: '1px solid rgba(255,255,255,0.08)',
          backdropFilter: 'blur(10px)',
          transition: 'all 0.3s ease',
          '&:hover': {
            background: 'rgba(255,255,255,0.08)',
            transform: 'translateY(-2px)'
          }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
          <LocationIcon sx={{ fontSize: 14, color: 'primary.main' }} />
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', letterSpacing: 0.5, textTransform: 'uppercase' }}>
            {weather.city}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700, fontFamily: 'Outfit', color: 'text.primary', lineHeight: 1 }}>
              {Math.round(weather.temp)}°
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 0.5 }}>
              {weather.description}
            </Typography>
          </Box>
          <Box sx={{ fontSize: '2.5rem', display: 'flex' }}>
            {getWeatherIcon(weather.id)}
          </Box>
        </Box>

        <Box sx={{ display: 'flex', gap: 2, mt: 1.5, pt: 1.5, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <DropIcon sx={{ fontSize: 12, color: 'primary.light' }} />
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>{weather.humidity}%</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <WindIcon sx={{ fontSize: 12, color: 'secondary.light' }} />
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>{weather.wind_speed} m/s</Typography>
          </Box>
        </Box>
      </Box>
    </Tooltip>
  );
};

export default WeatherWidget;
