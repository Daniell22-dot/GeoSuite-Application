import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
  Divider,
  Avatar,
  IconButton,
  useTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Map as MapIcon,
  Terrain as TerrainIcon,
  Waves as WavesIcon,
  Settings as SettingsIcon,
  Home as HomeIcon,
  Terminal as TerminalIcon,
  Flight as DroneIcon,
  Transform as TransformIcon,
  Scanner as DigitizeIcon,
  SatelliteAlt as SatelliteIcon,
  Timeline as AnalysisIcon,
  Architecture as ToolIcon,
} from '@mui/icons-material';
import WeatherWidget from './WeatherWidget';
import { useAppConfig } from '../services/gisUtils';

const drawerWidth = 260;

const Navigation = ({ activeView, setActiveView }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const { config } = useAppConfig();

  const menuItems = [
    { text: 'Overview', icon: <HomeIcon />, path: '/home' },
    { divider: true, label: 'FIELD' },
    { text: 'Drone Surveys', icon: <DroneIcon />, path: '/drone' },
    { text: 'Digitize Plans', icon: <DigitizeIcon />, path: '/digitize' },
    { divider: true, label: 'ANALYSIS' },
    { text: 'GPS Analysis', icon: <MapIcon />, path: '/gps' },
    { text: 'Coordinate Transform', icon: <TransformIcon />, path: '/transform' },
    { text: 'Marine Charts', icon: <WavesIcon />, path: '/marine' },
    { text: 'Watershed', icon: <TerrainIcon />, path: '/watershed' },
    { divider: true, label: 'SYSTEM' },
    { text: 'Terminal', icon: <TerminalIcon />, path: '/terminal' },
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  ];

  const handleNavigation = (path) => {
    navigate(path);
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          background: 'rgba(15, 23, 42, 0.8)',
          backdropFilter: 'blur(16px)',
          borderRight: '1px solid rgba(255, 255, 255, 0.1)',
          color: '#fff',
        },
      }}
    >
      <Box sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar 
          variant="rounded" 
          sx={{ 
            bgcolor: 'primary.main', 
            width: 32, 
            height: 32,
            boxShadow: '0 0 12px rgba(10, 132, 255, 0.4)'
          }}
        >
          <TerrainIcon sx={{ fontSize: 18 }} />
        </Avatar>
        <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.3 }}>
          {config?.appName || 'GeoSuite'}
        </Typography>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.05)' }} />

      <List dense sx={{ px: 1.5, py: 1.5 }}>
        {menuItems.map((item, index) => (
          item.divider ? (
            <Box key={index} sx={{ mt: 1.5, mb: 0.5, px: 1.5 }}>
              {item.label && (
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.35)', fontWeight: 600, letterSpacing: 1.5, fontSize: '0.62rem' }}>
                  {item.label}
                </Typography>
              )}
            </Box>
          ) : (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                onClick={() => handleNavigation(item.path)}
                selected={location.pathname === item.path}
                sx={{
                  minHeight: 30,
                  py: 0.7,
                  transition: 'all 0.15s',
                  '&.Mui-selected': {
                    bgcolor: 'rgba(10, 132, 255, 0.15)',
                    color: 'primary.light',
                    '&:hover': { bgcolor: 'rgba(10, 132, 255, 0.2)' },
                    '& .MuiListItemIcon-root': { color: 'primary.light' },
                  },
                  '&:hover': {
                    bgcolor: 'rgba(255, 255, 255, 0.05)',
                  },
                }}
              >
                <ListItemIcon 
                  sx={{ 
                    minWidth: 36, 
                    color: location.pathname === item.path ? 'primary.light' : 'rgba(255,255,255,0.5)' 
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText 
                  primary={item.text} 
                  primaryTypographyProps={{ 
                    fontSize: '0.82rem',
                    fontWeight: location.pathname === item.path ? 600 : 400
                  }} 
                />
              </ListItemButton>
            </ListItem>
          )
        ))}
      </List>

      <Box sx={{ mt: 'auto', p: 1.5 }}>
        <WeatherWidget city="Nairobi,KE" />
        <Box sx={{ mt: 1.5 }}>
          <ListItem disablePadding>
            <ListItemButton
              sx={{
                minHeight: 30,
                borderRadius: 3,
                bgcolor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.08)' }
              }}
            >
              <ListItemIcon sx={{ minWidth: 36, color: 'rgba(255,255,255,0.7)' }}>
                <SettingsIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText 
                primary="Settings" 
                primaryTypographyProps={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.7)' }} 
              />
            </ListItemButton>
          </ListItem>
        </Box>
      </Box>
    </Drawer>
  );
};

export default Navigation;
