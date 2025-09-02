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
  LinearProgress
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Inventory,
  AttachMoney,
  Store,
  Assessment,
  Analytics as AnalyticsIcon,
  Refresh,
  Download
} from '@mui/icons-material';

interface MetricData {
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
  icon: React.ReactNode;
  color: string;
}

interface StoreAnalytics {
  store: string;
  revenue: string;
  turnover: string;
  stockouts: number;
  efficiency: number;
}

const Analytics: React.FC = () => {
  const [timeRange, setTimeRange] = useState('30d');
  const [selectedStore, setSelectedStore] = useState('all');
  const [loading, setLoading] = useState(false);

  const metrics: MetricData[] = [
    {
      title: 'Revenue Impact',
      value: '+$2.4M',
      change: '+12.3% vs baseline',
      trend: 'up',
      icon: <AttachMoney fontSize="large" />,
      color: '#4caf50'
    },
    {
      title: 'Cost Savings',
      value: '$850K',
      change: '+18.7% reduction',
      trend: 'up',
      icon: <TrendingDown fontSize="large" />,
      color: '#2196f3'
    },
    {
      title: 'Inventory Efficiency',
      value: '94.2%',
      change: '+5.8% improvement',
      trend: 'up',
      icon: <Inventory fontSize="large" />,
      color: '#ff9800'
    },
    {
      title: 'Forecast Accuracy',
      value: '89.3%',
      change: '+2.1% increase',
      trend: 'up',
      icon: <Assessment fontSize="large" />,
      color: '#9c27b0'
    }
  ];

  const storeAnalytics: StoreAnalytics[] = [
    { store: 'New York', revenue: '$485K', turnover: '12.8x', stockouts: 3, efficiency: 98 },
    { store: 'Los Angeles', revenue: '$412K', turnover: '11.2x', stockouts: 5, efficiency: 96 },
    { store: 'Chicago', revenue: '$378K', turnover: '13.1x', stockouts: 2, efficiency: 97 },
    { store: 'Houston', revenue: '$356K', turnover: '10.9x', stockouts: 7, efficiency: 95 },
    { store: 'Phoenix', revenue: '$298K', turnover: '14.2x', stockouts: 1, efficiency: 99 }
  ];

  const productCategories = [
    { name: 'Electronics', contribution: 28.5, trend: 'up', improvement: '+3.2%' },
    { name: 'Clothing', contribution: 22.1, trend: 'up', improvement: '+1.8%' },
    { name: 'Home & Garden', contribution: 18.7, trend: 'down', improvement: '-0.5%' },
    { name: 'Sports & Outdoors', contribution: 12.3, trend: 'up', improvement: '+2.1%' },
    { name: 'Books & Media', contribution: 10.2, trend: 'up', improvement: '+0.7%' },
    { name: 'Automotive', contribution: 8.2, trend: 'down', improvement: '-1.1%' }
  ];

  const handleRefresh = async () => {
    setLoading(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));
    setLoading(false);
  };

  const handleExport = () => {
    // Simulate export functionality
    console.log('Exporting analytics data...');
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            📊 Advanced Analytics
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Deep insights into inventory performance and business impact
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              label="Time Range"
              onChange={(e) => setTimeRange(e.target.value)}
            >
              <MenuItem value="7d">Last 7 days</MenuItem>
              <MenuItem value="30d">Last 30 days</MenuItem>
              <MenuItem value="90d">Last 90 days</MenuItem>
              <MenuItem value="1y">Last year</MenuItem>
            </Select>
          </FormControl>
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
              <MenuItem value="hou">Houston</MenuItem>
              <MenuItem value="phx">Phoenix</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={handleExport}
          >
            Export
          </Button>
        </Box>
      </Box>

      {/* Key Performance Metrics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {metrics.map((metric, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card elevation={2} sx={{ height: '100%' }}>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                  <Box sx={{ color: metric.color }}>{metric.icon}</Box>
                  <Chip
                    label={metric.change}
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

      <Grid container spacing={3}>
        {/* Store Performance Analysis */}
        <Grid item xs={12} lg={8}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                🏪 Store Performance Analysis
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Store Location</TableCell>
                      <TableCell align="right">Revenue</TableCell>
                      <TableCell align="right">Inventory Turnover</TableCell>
                      <TableCell align="right">Stockouts</TableCell>
                      <TableCell align="right">Efficiency</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {storeAnalytics.map((row) => (
                      <TableRow key={row.store} hover>
                        <TableCell>
                          <Box display="flex" alignItems="center">
                            <Store sx={{ mr: 1, color: 'primary.main' }} />
                            <Typography variant="subtitle2">{row.store}</Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="h6" color="success.main">
                            {row.revenue}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">{row.turnover}</TableCell>
                        <TableCell align="right">
                          <Chip
                            label={row.stockouts}
                            color={row.stockouts <= 3 ? 'success' : row.stockouts <= 5 ? 'warning' : 'error'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Box display="flex" alignItems="center" gap={1}>
                            <LinearProgress
                              variant="determinate"
                              value={row.efficiency}
                              sx={{
                                width: 60,
                                height: 6,
                                borderRadius: 3,
                                '& .MuiLinearProgress-bar': {
                                  backgroundColor: row.efficiency >= 97 ? '#4caf50' : '#2196f3'
                                }
                              }}
                            />
                            <Typography variant="body2">{row.efficiency}%</Typography>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Product Category Performance */}
        <Grid item xs={12} lg={4}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                📈 Category Performance
              </Typography>
              <Box sx={{ mt: 2 }}>
                {productCategories.map((category, index) => (
                  <Box key={category.name} sx={{ mb: 3 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Typography variant="body1">{category.name}</Typography>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body2" color="text.secondary">
                          {category.contribution}%
                        </Typography>
                        <Chip
                          label={category.improvement}
                          color={category.trend === 'up' ? 'success' : 'error'}
                          size="small"
                          icon={category.trend === 'up' ? <TrendingUp /> : <TrendingDown />}
                        />
                      </Box>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={category.contribution}
                      sx={{
                        height: 8,
                        borderRadius: 4,
                        bgcolor: 'grey.200',
                        '& .MuiLinearProgress-bar': {
                          bgcolor: category.trend === 'up' ? '#4caf50' : '#f44336'
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

      {/* AI Performance Insights */}
      <Paper elevation={1} sx={{ mt: 4, p: 3, bgcolor: 'grey.50' }}>
        <Typography variant="h6" gutterBottom color="primary">
          🤖 AI Performance Insights
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              🎯 Model Accuracy Trends
            </Typography>
            <Typography variant="body2" gutterBottom>
              • ARIMA model: <strong>87.2%</strong> (+0.3% this month)
            </Typography>
            <Typography variant="body2" gutterBottom>
              • LSTM neural network: <strong>91.4%</strong> (+1.2% this month)
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Prophet seasonal: <strong>89.8%</strong> (+0.7% this month)
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              ⚡ Optimization Impact
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Reduced overstock by <strong>23.5%</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Decreased stockouts by <strong>41.2%</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Improved customer satisfaction: <strong>+8.3%</strong>
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              📊 Real-time Processing
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Processing <strong>15.2K</strong> transactions/hour
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Average prediction latency: <strong>120ms</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • System uptime: <strong>99.97%</strong>
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default Analytics;