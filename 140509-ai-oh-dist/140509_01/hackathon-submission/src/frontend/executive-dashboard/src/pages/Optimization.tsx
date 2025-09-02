import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Alert,
  Slider,
  Switch,
  FormControlLabel,
  Divider
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Inventory,
  AttachMoney,
  LocalShipping,
  Warning,
  CheckCircle,
  Settings,
  PlayArrow,
  Tune
} from '@mui/icons-material';

interface OptimizationMetric {
  title: string;
  value: string;
  improvement: string;
  trend: 'up' | 'down';
  icon: React.ReactNode;
  color: string;
}

interface ReorderRecommendation {
  product: string;
  currentStock: number;
  reorderPoint: number;
  eoq: number;
  leadTime: string;
  priority: 'high' | 'medium' | 'low';
  costSaving: string;
  status: 'pending' | 'approved' | 'ordered';
}

interface OptimizationSettings {
  serviceLevel: number;
  costWeight: number;
  leadTimeBuffer: number;
  seasonalityAdjustment: boolean;
  autoReorder: boolean;
}

const Optimization: React.FC = () => {
  const [selectedStore, setSelectedStore] = useState('all');
  const [optimizationMode, setOptimizationMode] = useState('balanced');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  const [settings, setSettings] = useState<OptimizationSettings>({
    serviceLevel: 95,
    costWeight: 70,
    leadTimeBuffer: 20,
    seasonalityAdjustment: true,
    autoReorder: false
  });

  const optimizationMetrics: OptimizationMetric[] = [
    {
      title: 'Inventory Cost Reduction',
      value: '23.8%',
      improvement: '-$1.2M annually',
      trend: 'down',
      icon: <AttachMoney fontSize="large" />,
      color: '#4caf50'
    },
    {
      title: 'Service Level Achievement',
      value: '97.2%',
      improvement: '+2.4% vs target',
      trend: 'up',
      icon: <CheckCircle fontSize="large" />,
      color: '#2196f3'
    },
    {
      title: 'Stockout Reduction',
      value: '68.5%',
      improvement: '47 fewer incidents',
      trend: 'down',
      icon: <Warning fontSize="large" />,
      color: '#ff9800'
    },
    {
      title: 'Inventory Turnover',
      value: '14.2x',
      improvement: '+18% increase',
      trend: 'up',
      icon: <Inventory fontSize="large" />,
      color: '#9c27b0'
    }
  ];

  const reorderRecommendations: ReorderRecommendation[] = [
    {
      product: 'iPhone 15 Pro 128GB',
      currentStock: 45,
      reorderPoint: 78,
      eoq: 150,
      leadTime: '7 days',
      priority: 'high',
      costSaving: '$2,340',
      status: 'pending'
    },
    {
      product: 'MacBook Air M3',
      currentStock: 23,
      reorderPoint: 35,
      eoq: 80,
      leadTime: '10 days',
      priority: 'high',
      costSaving: '$1,850',
      status: 'pending'
    },
    {
      product: 'AirPods Pro 2nd Gen',
      currentStock: 156,
      reorderPoint: 120,
      eoq: 200,
      leadTime: '5 days',
      priority: 'medium',
      costSaving: '$890',
      status: 'approved'
    },
    {
      product: 'iPad Pro 12.9"',
      currentStock: 67,
      reorderPoint: 45,
      eoq: 100,
      leadTime: '8 days',
      priority: 'low',
      costSaving: '$560',
      status: 'ordered'
    },
    {
      product: 'Samsung Galaxy S24',
      currentStock: 89,
      reorderPoint: 95,
      eoq: 120,
      leadTime: '6 days',
      priority: 'medium',
      costSaving: '$1,240',
      status: 'pending'
    }
  ];

  const handleRunOptimization = async () => {
    setIsOptimizing(true);
    // Simulate optimization process
    await new Promise(resolve => setTimeout(resolve, 4000));
    setIsOptimizing(false);
  };

  const handleSettingChange = (setting: keyof OptimizationSettings, value: number | boolean) => {
    setSettings(prev => ({
      ...prev,
      [setting]: value
    }));
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      default:
        return 'success';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'default';
      case 'approved':
        return 'primary';
      case 'ordered':
        return 'success';
      default:
        return 'default';
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            ⚡ Inventory Optimization
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            AI-driven inventory optimization with EOQ, safety stock, and reorder point calculations
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Store</InputLabel>
            <Select
              value={selectedStore}
              label="Store"
              onChange={(e) => setSelectedStore(e.target.value)}
            >
              <MenuItem value="all">All Stores</MenuItem>
              <MenuItem value="ny">New York</MenuItem>
              <MenuItem value="la">Los Angeles</MenuItem>
              <MenuItem value="chi">Chicago</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Mode</InputLabel>
            <Select
              value={optimizationMode}
              label="Mode"
              onChange={(e) => setOptimizationMode(e.target.value)}
            >
              <MenuItem value="cost">Cost Focused</MenuItem>
              <MenuItem value="balanced">Balanced</MenuItem>
              <MenuItem value="service">Service Focused</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<Tune />}
            onClick={() => setShowSettings(!showSettings)}
          >
            Settings
          </Button>
          <Button
            variant="contained"
            startIcon={<PlayArrow />}
            onClick={handleRunOptimization}
            disabled={isOptimizing}
          >
            {isOptimizing ? 'Optimizing...' : 'Optimize Now'}
          </Button>
        </Box>
      </Box>

      {/* Optimization Status */}
      {isOptimizing && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Box display="flex" alignItems="center" gap={2}>
            <Typography>Running inventory optimization algorithms...</Typography>
            <LinearProgress sx={{ width: 200 }} />
          </Box>
        </Alert>
      )}

      {/* Optimization Settings Panel */}
      {showSettings && (
        <Card elevation={2} sx={{ mb: 3, bgcolor: 'grey.50' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <Settings sx={{ mr: 1, verticalAlign: 'middle' }} />
              Optimization Parameters
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography gutterBottom>Service Level Target: {settings.serviceLevel}%</Typography>
                <Slider
                  value={settings.serviceLevel}
                  onChange={(_, value) => handleSettingChange('serviceLevel', value as number)}
                  min={85}
                  max={99}
                  marks={[
                    { value: 85, label: '85%' },
                    { value: 95, label: '95%' },
                    { value: 99, label: '99%' }
                  ]}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography gutterBottom>Cost Optimization Weight: {settings.costWeight}%</Typography>
                <Slider
                  value={settings.costWeight}
                  onChange={(_, value) => handleSettingChange('costWeight', value as number)}
                  min={0}
                  max={100}
                  marks={[
                    { value: 0, label: 'Service' },
                    { value: 50, label: 'Balanced' },
                    { value: 100, label: 'Cost' }
                  ]}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography gutterBottom>Lead Time Buffer: {settings.leadTimeBuffer}%</Typography>
                <Slider
                  value={settings.leadTimeBuffer}
                  onChange={(_, value) => handleSettingChange('leadTimeBuffer', value as number)}
                  min={0}
                  max={50}
                  marks={[
                    { value: 0, label: '0%' },
                    { value: 25, label: '25%' },
                    { value: 50, label: '50%' }
                  ]}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Box display="flex" flexDirection="column" gap={2}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.seasonalityAdjustment}
                        onChange={(e) => handleSettingChange('seasonalityAdjustment', e.target.checked)}
                      />
                    }
                    label="Seasonality Adjustment"
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.autoReorder}
                        onChange={(e) => handleSettingChange('autoReorder', e.target.checked)}
                      />
                    }
                    label="Automatic Reordering"
                  />
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Optimization Metrics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {optimizationMetrics.map((metric, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card elevation={2} sx={{ height: '100%' }}>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                  <Box sx={{ color: metric.color }}>{metric.icon}</Box>
                  <Chip
                    label={metric.improvement}
                    color={metric.trend === 'up' ? 'success' : 'error'}
                    size="small"
                    icon={metric.trend === 'up' ? <TrendingUp /> : <TrendingDown />}
                  />
                </Box>
                <Typography variant="h4" component="h2" gutterBottom sx={{ color: metric.color }}>
                  {metric.value}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {metric.title}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Reorder Recommendations */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card elevation={2}>
            <CardContent>
              <Box display="flex" justifyContent="between" alignItems="center" mb={2}>
                <Typography variant="h6" gutterBottom>
                  🎯 Smart Reorder Recommendations
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Based on EOQ, safety stock, and demand forecasts
                </Typography>
              </Box>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Product</TableCell>
                      <TableCell align="right">Current Stock</TableCell>
                      <TableCell align="right">Reorder Point</TableCell>
                      <TableCell align="right">EOQ</TableCell>
                      <TableCell align="center">Lead Time</TableCell>
                      <TableCell align="center">Priority</TableCell>
                      <TableCell align="right">Cost Saving</TableCell>
                      <TableCell align="center">Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {reorderRecommendations.map((rec, index) => (
                      <TableRow 
                        key={index} 
                        hover
                        sx={{ 
                          backgroundColor: rec.currentStock <= rec.reorderPoint ? 'error.light' : 'inherit',
                          '&:hover': {
                            backgroundColor: rec.currentStock <= rec.reorderPoint ? 'error.main' : 'grey.50'
                          }
                        }}
                      >
                        <TableCell>
                          <Box display="flex" alignItems="center">
                            {rec.currentStock <= rec.reorderPoint && (
                              <Warning color="error" sx={{ mr: 1 }} />
                            )}
                            <Typography variant="subtitle2">{rec.product}</Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <Typography 
                            variant="body2"
                            color={rec.currentStock <= rec.reorderPoint ? 'error' : 'inherit'}
                            fontWeight={rec.currentStock <= rec.reorderPoint ? 'bold' : 'normal'}
                          >
                            {rec.currentStock}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">{rec.reorderPoint}</Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="h6" color="primary">
                            {rec.eoq}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            icon={<LocalShipping />}
                            label={rec.leadTime}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={rec.priority.toUpperCase()}
                            color={getPriorityColor(rec.priority) as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="h6" color="success.main">
                            {rec.costSaving}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={rec.status.toUpperCase()}
                            color={getStatusColor(rec.status) as any}
                            size="small"
                            variant="filled"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Algorithm Insights */}
      <Paper elevation={1} sx={{ mt: 4, p: 3, bgcolor: 'grey.50' }}>
        <Typography variant="h6" gutterBottom color="primary">
          🧠 Optimization Algorithm Insights
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              📊 EOQ Calculation
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Annual demand forecasted using ML models
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Ordering costs: Average $125 per order
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Holding costs: 18% of item value annually
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              🛡️ Safety Stock Strategy
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Demand variability: Real-time calculation
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Lead time uncertainty: Historical analysis
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Service level target: {settings.serviceLevel}% achievement
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              ⚙️ Dynamic Optimization
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Parameters updated every 6 hours
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Seasonal adjustments: {settings.seasonalityAdjustment ? 'Enabled' : 'Disabled'}
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Auto-reordering: {settings.autoReorder ? 'Active' : 'Manual approval'}
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default Optimization;