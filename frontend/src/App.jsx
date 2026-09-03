import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';

// Components
import Dashboard from './components/Dashboard';
import Navigation from './components/Navigation';
import HomePage from './pages/HomePage';
import GpsPage from './pages/GpsPage';
import MarinePage from './pages/MarinePage';
import WatershedPage from './pages/WatershedPage';
import TerminalPage from './pages/TerminalPage';
import DroneProcessingPage from './pages/DroneProcessingPage';
import TransformPage from './pages/TransformPage';
import DigitizePage from './pages/DigitizePage';

// Services
import { ApiProvider, useApi } from './services/ApiContext';
import { useAppConfig } from './services/gisUtils';

// Icons
import { Terrain as TerrainIcon } from '@mui/icons-material';

const AppInner = () => {
  const [activeView, setActiveView] = useState('home');
  const { config } = useAppConfig();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', minHeight: '100vh', background: 'transparent' }}>
        <Navigation activeView={activeView} setActiveView={setActiveView} />
        
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            height: '100vh',
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
            zIndex: 1,
          }}
        >
          <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flex: 1 }}>
            <Routes>
              <Route path="/" element={<Navigate to="/home" replace />} />
              <Route path="/home" element={<HomePage />} />
              <Route path="/drone" element={<DroneProcessingPage />} />
              <Route path="/digitize" element={<DigitizePage />} />
              <Route path="/transform" element={<TransformPage />} />
              <Route path="/gps" element={<GpsPage />} />
              <Route path="/marine" element={<MarinePage />} />
              <Route path="/watershed" element={<WatershedPage />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/terminal" element={<TerminalPage />} />
            </Routes>
          </Container>
          
          <Box
            component="footer"
            sx={{
              py: 3,
              px: 4,
              mt: 'auto',
              borderTop: '1px solid rgba(255, 255, 255, 0.05)',
              background: 'rgba(15, 23, 42, 0.4)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <Container maxWidth="xl">
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TerrainIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                  <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'Outfit', color: 'text.secondary' }}>
                    {config?.appName || 'GeoSuite'} v{config?.appVersion || '2.0'}
                  </Typography>
                </Box>
                <Box sx={{ fontSize: '0.75rem', color: 'text.secondary', opacity: 0.7 }}>
                  SURVEY • DRONE • TRANSFORM • GPS • MARINE • WATERSHED • {new Date().getFullYear()}
                </Box>
              </Box>
            </Container>
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
};

function App() {
  return (
    <ApiProvider>
      <Router>
        <AppInner />
      </Router>
    </ApiProvider>
  );
}

export default App;