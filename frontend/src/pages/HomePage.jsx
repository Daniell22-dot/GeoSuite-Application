import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Grid,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  CardMedia,
  Stack,
  useTheme,
} from '@mui/material';
import {
  Map as MapIcon,
  Terrain as TerrainIcon,
  Waves as WavesIcon,
  ArrowForward as ArrowForwardIcon,
  ChevronRight as ChevronRightIcon,
  Flight as DroneIcon,
  Transform as TransformIcon,
  Scanner as DigitizeIcon,
} from '@mui/icons-material';

const HomePage = () => {
  const navigate = useNavigate();
  const theme = useTheme();

  const features = [
    {
      title: 'Survey Plan Digitizer',
      description: 'Auto-extract beacons, boundaries & labels from scanned survey plans using computer vision.',
      icon: <DigitizeIcon sx={{ fontSize: 40 }} />,
      path: '/digitize',
      color: '#0a84ff',
    },
    {
      title: 'Drone Surveys',
      description: 'Upload drone imagery, process with OpenDroneMap, generate COGs and PMTiles.',
      icon: <DroneIcon sx={{ fontSize: 40 }} />,
      path: '/drone',
      color: '#5e5ce6',
    },
    {
      title: 'Coordinate Transform',
      description: 'Cassini-Soldner ↔ UTM transformations with geodetic, polynomial & Helmert methods.',
      icon: <TransformIcon sx={{ fontSize: 40 }} />,
      path: '/transform',
      color: '#4caf50',
    },
    {
      title: 'GPS Analysis',
      description: 'Advanced track processing with elevation correction and performance metrics.',
      icon: <MapIcon sx={{ fontSize: 40 }} />,
      path: '/gps',
      color: '#ed6c02',
    },
    {
      title: 'Marine Charts',
      description: 'Visualize nautical data with depth soundings and bathymetry overlays.',
      icon: <WavesIcon sx={{ fontSize: 40 }} />,
      path: '/marine',
      color: '#00bcd4',
    },
    {
      title: 'Watershed Modeling',
      description: 'Delineate basins and extract stream networks with high-precision DEM analysis.',
      icon: <TerrainIcon sx={{ fontSize: 40 }} />,
      path: '/watershed',
      color: '#ff5722',
    },
  ];

  return (
    <Box className="animate-fade-in">
      {/* Hero Section */}
      <Box sx={{ pt: 10, pb: 14, position: 'relative', overflow: 'hidden' }}>
        <Container maxWidth="lg">
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={8}>
              <Typography
                variant="h1"
                sx={{
                  fontSize: { xs: '2.5rem', md: '4.5rem' },
                  lineHeight: 1.1,
                  mb: 3,
                  background: 'linear-gradient(to right, #fff, #94a3b8)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                Professional<br />
                <Box component="span" sx={{ color: 'primary.main', WebkitTextFillColor: 'initial' }}>
                  Geospatial
                </Box> Intelligence
              </Typography>
              <Typography
                variant="h6"
                sx={{ color: 'text.secondary', mb: 6, maxWidth: '600px', fontWeight: 400, fontSize: '1.15rem' }}
              >
                Survey plan digitization, drone processing, coordinate transformations,
                and field analysis — built for Kenyan surveyors.
              </Typography>
              <Stack direction="row" spacing={3}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => navigate('/digitize')}
                  sx={{ px: 6, py: 2, fontSize: '1.1rem', borderRadius: '100px' }}
                >
                  Get Started
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => navigate('/dashboard')}
                  sx={{
                    px: 6, py: 2, fontSize: '1.1rem', borderRadius: '100px',
                    borderColor: 'rgba(255,255,255,0.1)', color: '#fff',
                    '&:hover': { borderColor: 'rgba(255,255,255,0.3)', bgcolor: 'rgba(255,255,255,0.05)' }
                  }}
                >
                  Dashboard
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </Container>
        <Box sx={{
          position: 'absolute', top: '20%', right: '-10%',
          width: '600px', height: '600px',
          background: 'radial-gradient(circle, rgba(10, 132, 255, 0.15) 0%, transparent 70%)',
          zIndex: -1, filter: 'blur(60px)'
        }} />
      </Box>

      {/* Feature Cards */}
      <Container maxWidth="lg" sx={{ pb: 12 }}>
        <Typography variant="h4" sx={{ mb: 6, textAlign: 'center', fontFamily: 'Outfit' }}>
          Capabilities
        </Typography>
        <Grid container spacing={3}>
          {features.map((feature, index) => (
            <Grid item xs={12} sm={6} md={4} key={index}>
              <Card
                className="glass-card"
                sx={{ height: '100%', display: 'flex', flexDirection: 'column', cursor: 'pointer' }}
                onClick={() => navigate(feature.path)}
              >
                <CardContent sx={{ flexGrow: 1, pt: 4 }}>
                  <Box sx={{ color: feature.color, mb: 2 }}>{feature.icon}</Box>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3, lineHeight: 1.6 }}>
                    {feature.description}
                  </Typography>
                  <Box sx={{ mt: 'auto', display: 'flex', alignItems: 'center', color: 'primary.light', fontWeight: 600, fontSize: '0.9rem' }}>
                    Open <ChevronRightIcon sx={{ ml: 0.5, fontSize: 18 }} />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
};

export default HomePage;