import React from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Paper,
  LinearProgress
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Inventory,
  AttachMoney,
  Store,
  Assessment
} from '@mui/icons-material';

const MetricCard: React.FC<{
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
  icon: React.ReactNode;
  color: string;
}> = ({ title, value, change, trend, icon, color }) => (
  <Card elevation={2} sx={{ height: '100%' }}>
    <CardContent>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Box sx={{ color: color }}>{icon}</Box>
        <Chip
          label={change}
          color={trend === 'up' ? 'success' : 'error'}
          size="small"
          icon={trend === 'up' ? <TrendingUp /> : <TrendingDown />}
        />
      </Box>
      <Typography variant="h4" component="h2" gutterBottom sx={{ color: color }}>
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {title}
      </Typography>
    </CardContent>
  </Card>
);

const Overview: React.FC = () => {
  const kpis = [
    {
      title: 'Cost Reduction',
      value: '18.7%',
      change: '+2.3% vs last month',
      trend: 'up' as const,
      icon: <AttachMoney fontSize="large" />,
      color: '#4caf50'
    },
    {
      title: 'Service Level',
      value: '97.2%',
      change: '+1.8% improvement',
      trend: 'up' as const,
      icon: <Assessment fontSize="large" />,
      color: '#2196f3'
    },
    {
      title: 'Inventory Turnover',
      value: '12.4x',
      change: '+15% increase',
      trend: 'up' as const,
      icon: <Inventory fontSize="large" />,
      color: '#ff9800'
    },
    {
      title: 'Active Stores',
      value: '10',
      change: 'All operational',
      trend: 'up' as const,
      icon: <Store fontSize="large" />,
      color: '#9c27b0'
    }
  ];

  const stores = [
    { name: 'New York', performance: 98, status: 'Excellent' },
    { name: 'Los Angeles', performance: 96, status: 'Good' },
    { name: 'Chicago', performance: 97, status: 'Excellent' },
    { name: 'Houston', performance: 95, status: 'Good' },
    { name: 'Phoenix', performance: 99, status: 'Excellent' }
  ];

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Executive Overview
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Real-time inventory optimization insights and key performance indicators
      </Typography>

      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {kpis.map((kpi, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <MetricCard {...kpi} />
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Forecast Performance */}
        <Grid item xs={12} md={8}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                📈 AI Forecasting Performance
              </Typography>
              <Box sx={{ 
                height: 300, 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                bgcolor: 'grey.50',
                borderRadius: 1
              }}>
                <Box textAlign="center">
                  <Typography variant="h2" color="primary" gutterBottom>
                    89.3%
                  </Typography>
                  <Typography variant="h6" gutterBottom>
                    Forecast Accuracy
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Ensemble model combining ARIMA, LSTM, and Prophet algorithms
                  </Typography>
                  <Box sx={{ mt: 2, maxWidth: 400, mx: 'auto' }}>
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2">ARIMA</Typography>
                      <Typography variant="body2">87%</Typography>
                    </Box>
                    <LinearProgress variant="determinate" value={87} sx={{ mb: 1 }} />
                    
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2">LSTM</Typography>
                      <Typography variant="body2">91%</Typography>
                    </Box>
                    <LinearProgress variant="determinate" value={91} sx={{ mb: 1 }} />
                    
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2">Prophet</Typography>
                      <Typography variant="body2">90%</Typography>
                    </Box>
                    <LinearProgress variant="determinate" value={90} />
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Store Performance */}
        <Grid item xs={12} md={4}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                🏪 Store Performance
              </Typography>
              <Box sx={{ mt: 2 }}>
                {stores.map((store, index) => (
                  <Box key={store.name} sx={{ mb: 2 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Typography variant="body1">{store.name}</Typography>
                      <Chip 
                        label={`${store.performance}%`}
                        color={store.performance >= 97 ? 'success' : 'primary'}
                        size="small"
                      />
                    </Box>
                    <LinearProgress 
                      variant="determinate" 
                      value={store.performance} 
                      sx={{ 
                        height: 6,
                        borderRadius: 3,
                        bgcolor: 'grey.200',
                        '& .MuiLinearProgress-bar': {
                          bgcolor: store.performance >= 97 ? '#4caf50' : '#2196f3'
                        }
                      }}
                    />
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Demo Information */}
      <Paper elevation={1} sx={{ mt: 4, p: 3, bgcolor: 'grey.50' }}>
        <Typography variant="h6" gutterBottom color="primary">
          🎯 Live Demo System Status
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle1" gutterBottom>
              📊 Demo Dataset Loaded
            </Typography>
            <Typography variant="body2" gutterBottom>
              • <strong>538,036</strong> sales transactions processed
            </Typography>
            <Typography variant="body2" gutterBottom>
              • <strong>500</strong> products across 10 categories
            </Typography>
            <Typography variant="body2" gutterBottom>
              • <strong>10</strong> stores in major US cities
            </Typography>
            <Typography variant="body2" gutterBottom>
              • <strong>15</strong> suppliers with realistic lead times
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle1" gutterBottom>
              🚀 AI/ML Capabilities Active
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Multi-model forecasting (ARIMA + LSTM + Prophet)
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Real-time inventory optimization algorithms
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Predictive stockout alerting system
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Seasonal demand pattern recognition
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default Overview;