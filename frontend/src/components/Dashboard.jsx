import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Chip,
  LinearProgress,
  IconButton,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  Storage as StorageIcon,
  Map as MapIcon,
  Terrain as TerrainIcon,
  Waves as WavesIcon,
  Timeline as TimelineIcon,
  CloudUpload as CloudUploadIcon,
  Notifications as NotificationsIcon,
  Settings as SettingsIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

import { useApi } from '../services/ApiContext';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalFiles: 0,
    totalAnalyses: 0,
    storageUsed: 0,
    activeUsers: 0,
  });
  const [recentActivities, setRecentActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const { monitoring, request } = useApi();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [health, statsData] = await Promise.all([
        monitoring.getHealth(),
        request('get', '/api/v1/monitoring/stats').catch(() => null),
      ]);
      
      const counts = statsData?.counts || {};
      setStats({
        totalFiles: counts.gps_tracks + counts.marine_charts + counts.drone_surveys || 0,
        totalAnalyses: counts.watershed_analyses || 0,
        storageUsed: 0,
        activeUsers: counts.users || 0,
        systemHealth: health.status,
      });
      
      setRecentActivities([
        { id: 1, user: 'System', action: 'Application started', time: 'Just now', type: 'system' },
        { id: 2, user: 'Health', action: `Status: ${health.status}`, time: 'Just now', type: 'system' },
      ]);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const uploadData = [
    { day: 'Mon', gps: 4, marine: 2, dem: 1 },
    { day: 'Tue', gps: 3, marine: 3, dem: 2 },
    { day: 'Wed', gps: 5, marine: 1, dem: 0 },
    { day: 'Thu', gps: 7, marine: 2, dem: 3 },
    { day: 'Fri', gps: 6, marine: 4, dem: 1 },
    { day: 'Sat', gps: 2, marine: 1, dem: 0 },
    { day: 'Sun', gps: 3, marine: 2, dem: 1 },
  ];

  const analysisData = [
    { name: 'GPS', value: 45 },
    { name: 'Watershed', value: 25 },
    { name: 'Marine', value: 20 },
    { name: 'HEC-RAS', value: 10 },
  ];

  const COLORS = ['#0a84ff', '#5e5ce6', '#ed6c02', '#2e7d32'];

  if (loading) {
    return (
      <Container maxWidth="xl">
        <LinearProgress sx={{ mt: 4 }} />
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" className="animate-fade-in">
      {/* Welcome Header */}
      <Box sx={{ mb: 5 }}>
        <Typography variant="h3" sx={{ fontWeight: 700, fontFamily: 'Outfit', mb: 1 }}>
          Reporting & Insights
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ fontWeight: 400 }}>
          System metrics and geospatial activity overview.
        </Typography>
      </Box>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
           <DashboardStatCard 
             title="Total Records" 
             value={stats.totalFiles} 
             subtitle="+12% this week" 
             icon={<CloudUploadIcon />} 
             color="#0a84ff"
           />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
           <DashboardStatCard 
             title="Analyses" 
             value={stats.totalAnalyses} 
             subtitle="Steady processing" 
             icon={<TimelineIcon />} 
             color="#5e5ce6"
           />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
           <DashboardStatCard 
             title="Storage" 
             value={`${stats.storageUsed} GB`} 
             subtitle="24% Capacity" 
             icon={<StorageIcon />} 
             color="#ed6c02"
             progress={(stats.storageUsed / 10) * 100}
           />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
           <DashboardStatCard 
             title="Sync Status" 
             value={stats.systemHealth.toUpperCase()} 
             subtitle="C++ Engine Active" 
             icon={<PersonIcon />} 
             color="#2e7d32"
           />
        </Grid>
      </Grid>

      {/* Main Content */}
      <Grid container spacing={4}>
        <Grid item xs={12} lg={8}>
          <Box className="glass-panel" sx={{ p: 4, mb: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
              <Typography variant="h6" sx={{ fontFamily: 'Outfit' }}>Processing Activity</Typography>
              <Button size="small" variant="text">Details</Button>
            </Box>
            <Box sx={{ height: 350 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={uploadData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '12px', background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                  />
                  <Bar dataKey="gps" name="GPS" fill="#0a84ff" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="marine" name="Marine" fill="#5e5ce6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="dem" name="Watershed" fill="#ed6c02" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </Box>
        </Grid>

        <Grid item xs={12} lg={4}>
          <Box className="glass-panel" sx={{ p: 4, mb: 4 }}>
            <Typography variant="h6" sx={{ mb: 4, fontFamily: 'Outfit' }}>Analysis Mix</Typography>
            <Box sx={{ height: 250, position: 'relative' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={analysisData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {analysisData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
              <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>100%</Typography>
                <Typography variant="caption" color="text.secondary">Total</Typography>
              </Box>
            </Box>
          </Box>

          <Box className="glass-panel" sx={{ p: 4 }}>
                <Typography variant="h6" sx={{ mb: 3, fontFamily: 'Outfit' }}>Recent Activity</Typography>
                <List dense>
                    {recentActivities.map((activity, i) => (
                        <React.Fragment key={activity.id}>
                            <ListItem sx={{ px: 0, py: 1.5 }}>
                                <ListItemIcon sx={{ minWidth: 40 }}>
                                    {activity.type === 'gps' && <MapIcon fontSize="small" sx={{ color: 'primary.main' }} />}
                                    {activity.type === 'watershed' && <TerrainIcon fontSize="small" sx={{ color: 'success.main' }} />}
                                    {activity.type === 'marine' && <WavesIcon fontSize="small" sx={{ color: 'warning.main' }} />}
                                    {activity.type === 'system' && <SettingsIcon fontSize="small" sx={{ color: 'text.secondary' }} />}
                                </ListItemIcon>
                                <ListItemText 
                                    primary={activity.action} 
                                    secondary={`${activity.user} • ${activity.time}`}
                                    primaryTypographyProps={{ fontSize: '0.9rem', fontWeight: 500 }}
                                    secondaryTypographyProps={{ fontSize: '0.75rem' }}
                                />
                            </ListItem>
                            {i < recentActivities.length - 1 && <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />}
                        </React.Fragment>
                    ))}
                </List>
          </Box>
        </Grid>
      </Grid>
    </Container>
  );
};

const DashboardStatCard = ({ title, value, subtitle, icon, color, progress }) => (
    <Card className="glass-card" sx={{ height: '100%' }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Avatar sx={{ bgcolor: `${color}15`, color: color, borderRadius: '12px', width: 48, height: 48 }}>
            {icon}
          </Avatar>
          <Box sx={{ textAlign: 'right' }}>
             <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: -0.5 }}>{value}</Typography>
             <Typography variant="body2" color="text.secondary">{title}</Typography>
          </Box>
        </Box>
        {progress !== undefined ? (
            <Box sx={{ mt: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">{subtitle}</Typography>
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>{Math.round(progress)}%</Typography>
                </Box>
                <LinearProgress 
                    variant="determinate" 
                    value={progress} 
                    sx={{ height: 4, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.05)' }} 
                />
            </Box>
        ) : (
            <Typography variant="caption" sx={{ mt: 3, display: 'block', color: 'success.light', fontWeight: 600 }}>
                {subtitle}
            </Typography>
        )}
      </CardContent>
    </Card>
);

export default Dashboard;