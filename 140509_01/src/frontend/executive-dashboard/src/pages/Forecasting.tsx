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
  Divider
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Timeline,
  Psychology,
  Science,
  AutoGraph,
  Refresh,
  PlayArrow,
  Stop
} from '@mui/icons-material';

interface ModelPerformance {
  name: string;
  accuracy: number;
  mape: string;
  status: 'active' | 'training' | 'inactive';
  lastUpdated: string;
}

interface ForecastResult {
  product: string;
  currentDemand: number;
  forecastedDemand: number;
  confidence: number;
  trend: 'up' | 'down' | 'stable';
  recommendation: string;
}

const Forecasting: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState('ensemble');
  const [forecastHorizon, setForecastHorizon] = useState('30');
  const [selectedProduct, setSelectedProduct] = useState('all');
  const [isRunning, setIsRunning] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const modelPerformance: ModelPerformance[] = [
    {
      name: 'ARIMA',
      accuracy: 87.2,
      mape: '8.4%',
      status: 'active',
      lastUpdated: '2 hours ago'
    },
    {
      name: 'LSTM Neural Network',
      accuracy: 91.4,
      mape: '6.2%',
      status: 'active',
      lastUpdated: '1 hour ago'
    },
    {
      name: 'Prophet',
      accuracy: 89.8,
      mape: '7.1%',
      status: 'active',
      lastUpdated: '3 hours ago'
    },
    {
      name: 'Ensemble Model',
      accuracy: 93.1,
      mape: '5.8%',
      status: 'active',
      lastUpdated: '30 minutes ago'
    }
  ];

  const forecastResults: ForecastResult[] = [
    {
      product: 'iPhone 15 Pro',
      currentDemand: 245,
      forecastedDemand: 312,
      confidence: 92,
      trend: 'up',
      recommendation: 'Increase stock by 30%'
    },
    {
      product: 'Samsung Galaxy S24',
      currentDemand: 189,
      forecastedDemand: 156,
      confidence: 88,
      trend: 'down',
      recommendation: 'Reduce orders by 20%'
    },
    {
      product: 'AirPods Pro',
      currentDemand: 423,
      forecastedDemand: 445,
      confidence: 95,
      trend: 'stable',
      recommendation: 'Maintain current levels'
    },
    {
      product: 'MacBook Air M3',
      currentDemand: 87,
      forecastedDemand: 134,
      confidence: 85,
      trend: 'up',
      recommendation: 'Increase stock by 45%'
    },
    {
      product: 'iPad Pro',
      currentDemand: 156,
      forecastedDemand: 142,
      confidence: 90,
      trend: 'down',
      recommendation: 'Slight reduction needed'
    }
  ];

  const handleRunForecast = async () => {
    setIsRunning(true);
    // Simulate forecast generation
    await new Promise(resolve => setTimeout(resolve, 3000));
    setIsRunning(false);
    setLastUpdate(new Date());
  };

  const handleStopForecast = () => {
    setIsRunning(false);
  };

  const getModelIcon = (modelName: string) => {
    switch (modelName.toLowerCase()) {
      case 'arima':
        return <Timeline />;
      case 'lstm neural network':
        return <Psychology />;
      case 'prophet':
        return <Science />;
      default:
        return <AutoGraph />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'training':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp color="success" />;
      case 'down':
        return <TrendingDown color="error" />;
      default:
        return <TrendingUp color="primary" style={{ transform: 'rotate(90deg)' }} />;
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            🔮 AI Forecasting Engine
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Multi-model demand prediction and inventory planning
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Model</InputLabel>
            <Select
              value={selectedModel}
              label="Model"
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              <MenuItem value="ensemble">Ensemble</MenuItem>
              <MenuItem value="arima">ARIMA</MenuItem>
              <MenuItem value="lstm">LSTM</MenuItem>
              <MenuItem value="prophet">Prophet</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Horizon</InputLabel>
            <Select
              value={forecastHorizon}
              label="Horizon"
              onChange={(e) => setForecastHorizon(e.target.value)}
            >
              <MenuItem value="7">7 days</MenuItem>
              <MenuItem value="14">14 days</MenuItem>
              <MenuItem value="30">30 days</MenuItem>
              <MenuItem value="90">90 days</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Product</InputLabel>
            <Select
              value={selectedProduct}
              label="Product"
              onChange={(e) => setSelectedProduct(e.target.value)}
            >
              <MenuItem value="all">All Products</MenuItem>
              <MenuItem value="electronics">Electronics</MenuItem>
              <MenuItem value="clothing">Clothing</MenuItem>
              <MenuItem value="home">Home & Garden</MenuItem>
            </Select>
          </FormControl>
          {!isRunning ? (
            <Button
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={handleRunForecast}
              disabled={isRunning}
            >
              Run Forecast
            </Button>
          ) : (
            <Button
              variant="outlined"
              color="error"
              startIcon={<Stop />}
              onClick={handleStopForecast}
            >
              Stop
            </Button>
          )}
        </Box>
      </Box>

      {/* Status Alert */}
      {isRunning && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Box display="flex" alignItems="center" gap={2}>
            <Typography>Generating forecasts using {selectedModel} model for {forecastHorizon} days ahead...</Typography>
            <LinearProgress sx={{ width: 200 }} />
          </Box>
        </Alert>
      )}

      {/* Model Performance Cards */}
      <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
        🤖 Model Performance Overview
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {modelPerformance.map((model, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card 
              elevation={selectedModel === model.name.toLowerCase().replace(' neural network', '').replace(' ', '_') ? 4 : 2}
              sx={{ 
                height: '100%',
                border: selectedModel === model.name.toLowerCase().replace(' neural network', '').replace(' ', '_') ? 2 : 0,
                borderColor: 'primary.main'
              }}
            >
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                  <Box sx={{ color: 'primary.main' }}>{getModelIcon(model.name)}</Box>
                  <Chip
                    label={model.status}
                    color={getStatusColor(model.status) as any}
                    size="small"
                  />
                </Box>
                <Typography variant="h6" gutterBottom>
                  {model.name}
                </Typography>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2" color="text.secondary">
                    Accuracy
                  </Typography>
                  <Typography variant="h6" color="success.main">
                    {model.accuracy}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={model.accuracy}
                  sx={{
                    mb: 2,
                    height: 6,
                    borderRadius: 3,
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: model.accuracy >= 90 ? '#4caf50' : '#2196f3'
                    }
                  }}
                />
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="caption" color="text.secondary">
                    MAPE: {model.mape}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {model.lastUpdated}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Forecast Results */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card elevation={2}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  📊 Latest Forecast Results
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Last updated: {lastUpdate.toLocaleTimeString()}
                </Typography>
              </Box>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Product</TableCell>
                      <TableCell align="right">Current Demand</TableCell>
                      <TableCell align="right">Forecasted Demand</TableCell>
                      <TableCell align="center">Trend</TableCell>
                      <TableCell align="right">Confidence</TableCell>
                      <TableCell>AI Recommendation</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {forecastResults.map((result, index) => (
                      <TableRow key={index} hover>
                        <TableCell>
                          <Typography variant="subtitle2">{result.product}</Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">{result.currentDemand}</Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="h6"
                            color={
                              result.forecastedDemand > result.currentDemand
                                ? 'success.main'
                                : result.forecastedDemand < result.currentDemand
                                ? 'error.main'
                                : 'primary.main'
                            }
                          >
                            {result.forecastedDemand}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          {getTrendIcon(result.trend)}
                        </TableCell>
                        <TableCell align="right">
                          <Box display="flex" alignItems="center" gap={1}>
                            <LinearProgress
                              variant="determinate"
                              value={result.confidence}
                              sx={{
                                width: 60,
                                height: 6,
                                borderRadius: 3,
                                '& .MuiLinearProgress-bar': {
                                  backgroundColor: result.confidence >= 90 ? '#4caf50' : '#2196f3'
                                }
                              }}
                            />
                            <Typography variant="body2">{result.confidence}%</Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={result.recommendation}
                            size="small"
                            color={
                              result.trend === 'up'
                                ? 'success'
                                : result.trend === 'down'
                                ? 'warning'
                                : 'default'
                            }
                            variant="outlined"
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

      {/* Forecast Insights */}
      <Paper elevation={1} sx={{ mt: 4, p: 3, bgcolor: 'grey.50' }}>
        <Typography variant="h6" gutterBottom color="primary">
          🎯 Forecast Insights & External Factors
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              📈 Seasonal Patterns
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Holiday season demand surge expected (+35%)
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Back-to-school electronics peak in August
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Summer outdoor equipment increased demand
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              🌍 External Factors
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Supply chain disruptions: <strong>Medium risk</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Economic indicators: <strong>Stable growth</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Weather patterns: <strong>Normal seasonal</strong>
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              ⚙️ Model Configuration
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Ensemble weights: Auto-optimized daily
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Training data: Last 24 months
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Update frequency: Every 4 hours
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default Forecasting;