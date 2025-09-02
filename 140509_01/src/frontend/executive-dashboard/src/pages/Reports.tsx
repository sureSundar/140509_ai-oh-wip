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
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import {
  Download,
  Email,
  Schedule,
  Assessment,
  TrendingUp,
  TrendingDown,
  PictureAsPdf,
  Description,
  TableChart,
  InsertChart,
  Event,
  AutorenewOutlined
} from '@mui/icons-material';

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  frequency: string;
  lastGenerated: string;
  status: 'active' | 'inactive' | 'generating';
  format: 'pdf' | 'excel' | 'csv';
  recipients: string[];
}

interface ScheduledReport {
  name: string;
  schedule: string;
  nextRun: string;
  status: 'active' | 'paused';
  format: string;
  recipients: number;
}

interface ReportMetric {
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
  period: string;
}

const Reports: React.FC = () => {
  const [selectedReportType, setSelectedReportType] = useState('executive');
  const [selectedPeriod, setSelectedPeriod] = useState('monthly');
  const [selectedFormat, setSelectedFormat] = useState('pdf');
  const [isGenerating, setIsGenerating] = useState(false);

  const reportTemplates: ReportTemplate[] = [
    {
      id: 'executive-summary',
      name: 'Executive Summary',
      description: 'High-level KPIs and business performance overview',
      frequency: 'Weekly',
      lastGenerated: '2 hours ago',
      status: 'active',
      format: 'pdf',
      recipients: ['ceo@company.com', 'cfo@company.com']
    },
    {
      id: 'inventory-analysis',
      name: 'Inventory Analysis',
      description: 'Detailed inventory turnover, stock levels, and optimization metrics',
      frequency: 'Daily',
      lastGenerated: '6 hours ago',
      status: 'active',
      format: 'excel',
      recipients: ['operations@company.com', 'inventory@company.com']
    },
    {
      id: 'forecast-accuracy',
      name: 'Forecast Accuracy Report',
      description: 'ML model performance and prediction accuracy analysis',
      frequency: 'Weekly',
      lastGenerated: '1 day ago',
      status: 'active',
      format: 'pdf',
      recipients: ['ml-team@company.com', 'data-science@company.com']
    },
    {
      id: 'cost-optimization',
      name: 'Cost Optimization Report',
      description: 'Cost savings, efficiency gains, and ROI analysis',
      frequency: 'Monthly',
      lastGenerated: '3 days ago',
      status: 'active',
      format: 'pdf',
      recipients: ['finance@company.com', 'operations@company.com']
    },
    {
      id: 'supplier-performance',
      name: 'Supplier Performance',
      description: 'Supplier metrics, lead times, and reliability scores',
      frequency: 'Monthly',
      lastGenerated: '5 days ago',
      status: 'inactive',
      format: 'excel',
      recipients: ['procurement@company.com']
    }
  ];

  const scheduledReports: ScheduledReport[] = [
    {
      name: 'Daily Operations Dashboard',
      schedule: 'Daily at 6:00 AM',
      nextRun: 'Tomorrow 6:00 AM',
      status: 'active',
      format: 'PDF',
      recipients: 5
    },
    {
      name: 'Weekly Executive Summary',
      schedule: 'Every Monday at 8:00 AM',
      nextRun: 'Monday 8:00 AM',
      status: 'active',
      format: 'PDF',
      recipients: 3
    },
    {
      name: 'Monthly Financial Impact',
      schedule: '1st of each month at 9:00 AM',
      nextRun: 'Dec 1st 9:00 AM',
      status: 'active',
      format: 'Excel',
      recipients: 4
    },
    {
      name: 'Quarterly Business Review',
      schedule: 'Quarterly on 1st business day',
      nextRun: 'Jan 2nd 10:00 AM',
      status: 'paused',
      format: 'PDF',
      recipients: 8
    }
  ];

  const reportMetrics: ReportMetric[] = [
    {
      title: 'Reports Generated This Month',
      value: '847',
      change: '+12.3%',
      trend: 'up',
      period: 'vs last month'
    },
    {
      title: 'Automated Distribution',
      value: '94.2%',
      change: '+2.1%',
      trend: 'up',
      period: 'delivery success rate'
    },
    {
      title: 'Average Generation Time',
      value: '2.3min',
      change: '-15%',
      trend: 'down',
      period: 'improvement'
    },
    {
      title: 'Active Recipients',
      value: '156',
      change: '+8',
      trend: 'up',
      period: 'new this month'
    }
  ];

  const handleGenerateReport = async () => {
    setIsGenerating(true);
    // Simulate report generation
    await new Promise(resolve => setTimeout(resolve, 3000));
    setIsGenerating(false);
  };

  const handleDownloadReport = (reportId: string) => {
    console.log(`Downloading report: ${reportId}`);
  };

  const handleScheduleReport = (reportId: string) => {
    console.log(`Scheduling report: ${reportId}`);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'generating':
        return 'warning';
      case 'paused':
        return 'default';
      default:
        return 'error';
    }
  };

  const getFormatIcon = (format: string) => {
    switch (format.toLowerCase()) {
      case 'pdf':
        return <PictureAsPdf />;
      case 'excel':
        return <TableChart />;
      case 'csv':
        return <Description />;
      default:
        return <Assessment />;
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            📋 Business Reports
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Automated reporting and business intelligence dashboards
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Report Type</InputLabel>
            <Select
              value={selectedReportType}
              label="Report Type"
              onChange={(e) => setSelectedReportType(e.target.value)}
            >
              <MenuItem value="executive">Executive</MenuItem>
              <MenuItem value="operational">Operational</MenuItem>
              <MenuItem value="financial">Financial</MenuItem>
              <MenuItem value="technical">Technical</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Period</InputLabel>
            <Select
              value={selectedPeriod}
              label="Period"
              onChange={(e) => setSelectedPeriod(e.target.value)}
            >
              <MenuItem value="daily">Daily</MenuItem>
              <MenuItem value="weekly">Weekly</MenuItem>
              <MenuItem value="monthly">Monthly</MenuItem>
              <MenuItem value="quarterly">Quarterly</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Format</InputLabel>
            <Select
              value={selectedFormat}
              label="Format"
              onChange={(e) => setSelectedFormat(e.target.value)}
            >
              <MenuItem value="pdf">PDF</MenuItem>
              <MenuItem value="excel">Excel</MenuItem>
              <MenuItem value="csv">CSV</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="contained"
            startIcon={<InsertChart />}
            onClick={handleGenerateReport}
            disabled={isGenerating}
          >
            {isGenerating ? 'Generating...' : 'Generate Report'}
          </Button>
        </Box>
      </Box>

      {/* Generation Status */}
      {isGenerating && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Box display="flex" alignItems="center" gap={2}>
            <Typography>Generating {selectedReportType} report in {selectedFormat.toUpperCase()} format...</Typography>
            <LinearProgress sx={{ width: 200 }} />
          </Box>
        </Alert>
      )}

      {/* Report Metrics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {reportMetrics.map((metric, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card elevation={2} sx={{ height: '100%' }}>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                  <Assessment color="primary" />
                  <Chip
                    label={metric.change}
                    color={metric.trend === 'up' ? 'success' : 'error'}
                    size="small"
                    icon={metric.trend === 'up' ? <TrendingUp /> : <TrendingDown />}
                  />
                </Box>
                <Typography variant="h4" component="h2" gutterBottom color="primary">
                  {metric.value}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {metric.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {metric.period}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Report Templates */}
        <Grid item xs={12} lg={8}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                📊 Available Report Templates
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Report Name</TableCell>
                      <TableCell>Frequency</TableCell>
                      <TableCell>Last Generated</TableCell>
                      <TableCell align="center">Status</TableCell>
                      <TableCell align="center">Format</TableCell>
                      <TableCell align="center">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {reportTemplates.map((template) => (
                      <TableRow key={template.id} hover>
                        <TableCell>
                          <Box>
                            <Typography variant="subtitle2" gutterBottom>
                              {template.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {template.description}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            icon={<Schedule />}
                            label={template.frequency}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {template.lastGenerated}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={template.status.toUpperCase()}
                            color={getStatusColor(template.status) as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="center">
                          <Box display="flex" alignItems="center" justifyContent="center">
                            {getFormatIcon(template.format)}
                            <Typography variant="caption" sx={{ ml: 0.5 }}>
                              {template.format.toUpperCase()}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="center">
                          <Box display="flex" gap={1} justifyContent="center">
                            <Button
                              size="small"
                              startIcon={<Download />}
                              onClick={() => handleDownloadReport(template.id)}
                            >
                              Download
                            </Button>
                            <Button
                              size="small"
                              startIcon={<Email />}
                              variant="outlined"
                              onClick={() => handleScheduleReport(template.id)}
                            >
                              Send
                            </Button>
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

        {/* Scheduled Reports */}
        <Grid item xs={12} lg={4}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                ⏰ Scheduled Reports
              </Typography>
              <List>
                {scheduledReports.map((report, index) => (
                  <React.Fragment key={index}>
                    <ListItem>
                      <ListItemIcon>
                        <Event color={report.status === 'active' ? 'primary' : 'disabled'} />
                      </ListItemIcon>
                      <ListItemText
                        primary={report.name}
                        secondary={
                          <Box>
                            <Typography variant="caption" display="block">
                              {report.schedule}
                            </Typography>
                            <Typography variant="caption" display="block" color="text.secondary">
                              Next: {report.nextRun}
                            </Typography>
                            <Box display="flex" alignItems="center" gap={1} mt={0.5}>
                              <Chip
                                label={report.status}
                                color={report.status === 'active' ? 'success' : 'default'}
                                size="small"
                              />
                              <Typography variant="caption">
                                {report.recipients} recipients
                              </Typography>
                            </Box>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < scheduledReports.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Report Insights */}
      <Paper elevation={1} sx={{ mt: 4, p: 3, bgcolor: 'grey.50' }}>
        <Typography variant="h6" gutterBottom color="primary">
          📈 Reporting Analytics & Insights
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              🎯 Most Popular Reports
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Executive Summary: <strong>89% open rate</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Inventory Analysis: <strong>76% open rate</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Cost Optimization: <strong>82% open rate</strong>
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              ⚡ Performance Metrics
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Average generation time: <strong>2.3 minutes</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Successful deliveries: <strong>94.2%</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Data freshness: <strong>&lt; 1 hour</strong>
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle1" gutterBottom>
              🔄 Automation Status
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Scheduled reports: <strong>15 active</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Auto-distribution: <strong>Enabled</strong>
            </Typography>
            <Typography variant="body2" gutterBottom>
              • Next scheduled run: <strong>Tomorrow 6:00 AM</strong>
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default Reports;