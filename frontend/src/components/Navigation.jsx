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

const drawerWidth = 260;

const Navigation = ({ activeView, setActiveView }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();

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
      <Box sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Avatar 
          variant="rounded" 
          sx={{ 
            bgcolor: 'primary.main', 
            width: 40, 
            height: 40,
            boxShadow: '0 0 20px rgba(10, 132, 255, 0.5)'
          }}
        >
          <TerrainIcon />
        </Avatar>
        <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.5, fontFamily: 'Outfit' }}>
          GeoSuite
        </Typography>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.05)' }} />

      <List sx={{ px: 2, py: 2 }}>
        {menuItems.map((item, index) => (
          item.divider ? (
            <Box key={index} sx={{ mt: 2, mb: 1, px: 2 }}>
              {item.label && (
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontWeight: 600, letterSpacing: 1.5, fontSize: '0.65rem' }}>
                  {item.label}
                </Typography>
              )}
            </Box>
          ) : (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                onClick={() => handleNavigation(item.path)}
                selected={location.pathname === item.path}
                sx={{
                  borderRadius: '12px',
                  py: 1.5,
                  transition: 'all 0.2s',
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
                    minWidth: 46, 
                    color: location.pathname === item.path ? 'primary.light' : 'rgba(255,255,255,0.5)' 
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText 
                  primary={item.text} 
                  primaryTypographyProps={{ 
                    fontSize: '0.95rem',
                    fontWeight: location.pathname === item.path ? 600 : 400
                  }} 
                />
              </ListItemButton>
            </ListItem>
          )
        ))}
      </List>

      <Box sx={{ mt: 'auto', p: 2 }}>
        <WeatherWidget city="Nairobi,KE" />
        <Box sx={{ mt: 2 }}>
          <ListItem disablePadding>
            <ListItemButton
              sx={{
                borderRadius: '12px',
                bgcolor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.08)' }
              }}
            >
              <ListItemIcon sx={{ minWidth: 46, color: 'rgba(255,255,255,0.7)' }}>
                <SettingsIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText 
                primary="Settings" 
                primaryTypographyProps={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.7)' }} 
              />
            </ListItemButton>
          </ListItem>
        </Box>
      </Box>
    </Drawer>
  );
};

export default Navigation;
