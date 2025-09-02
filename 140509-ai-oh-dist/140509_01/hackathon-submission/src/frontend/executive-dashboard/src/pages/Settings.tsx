import React, { useState } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Switch,
  FormControlLabel,
  TextField,
  Button,
  Divider,
  Chip,
  Alert,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Notifications,
  Security,
  Storage,
  Email,
  Smartphone,
  Delete,
  Add,
  Save,
  Refresh,
  Warning,
  CheckCircle,
  Schedule,
  Tune,
  Api,
  Dashboard
} from '@mui/icons-material';

interface NotificationSettings {
  emailAlerts: boolean;
  smsAlerts: boolean;
  stockoutAlerts: boolean;
  forecastAlerts: boolean;
  systemAlerts: boolean;
  weeklyReports: boolean;
}

interface SystemSettings {
  dataRetention: number;
  forecastHorizon: number;
  optimizationFrequency: string;
  serviceLevel: number;
  autoReorder: boolean;
  mlModelUpdate: string;
}

interface UserPreferences {
  theme: string;
  language: string;
  timezone: string;
  currency: string;
  dashboardLayout: string;
}

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState('notifications');
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const [notifications, setNotifications] = useState<NotificationSettings>({
    emailAlerts: true,
    smsAlerts: false,
    stockoutAlerts: true,
    forecastAlerts: true,
    systemAlerts: true,
    weeklyReports: true
  });

  const [systemSettings, setSystemSettings] = useState<SystemSettings>({
    dataRetention: 24,
    forecastHorizon: 30,
    optimizationFrequency: 'hourly',
    serviceLevel: 95,
    autoReorder: false,
    mlModelUpdate: 'daily'
  });

  const [userPreferences, setUserPreferences] = useState<UserPreferences>({
    theme: 'light',
    language: 'en',
    timezone: 'UTC-5',
    currency: 'USD',
    dashboardLayout: 'standard'
  });

  const [apiSettings, setApiSettings] = useState({
    rateLimit: 1000,
    timeout: 30,
    retries: 3,
    caching: true
  });

  const handleNotificationChange = (setting: keyof NotificationSettings) => {
    setNotifications(prev => ({
      ...prev,
      [setting]: !prev[setting]
    }));
  };

  const handleSystemChange = (setting: keyof SystemSettings, value: any) => {
    setSystemSettings(prev => ({
      ...prev,
      [setting]: value
    }));
  };

  const handleUserPrefChange = (setting: keyof UserPreferences, value: any) => {
    setUserPreferences(prev => ({
      ...prev,
      [setting]: value
    }));
  };

  const handleSaveSettings = async () => {
    setSaveStatus('saving');
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));
    setSaveStatus('saved');
    setTimeout(() => setSaveStatus('idle'), 3000);
  };

  const handleResetSettings = () => {
    // Reset to defaults
    setNotifications({
      emailAlerts: true,
      smsAlerts: false,
      stockoutAlerts: true,
      forecastAlerts: true,
      systemAlerts: true,
      weeklyReports: true
    });
  };

  const renderNotificationSettings = () => (
    <Card elevation={2}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={3}>
          <Notifications sx={{ mr: 2, color: 'primary.main' }} />
          <Typography variant="h6">Notification Preferences</Typography>
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle1" gutterBottom>
              📧 Alert Channels
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={notifications.emailAlerts}
                  onChange={() => handleNotificationChange('emailAlerts')}
                />
              }
              label="Email Notifications"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={notifications.smsAlerts}
                  onChange={() => handleNotificationChange('smsAlerts')}
                />
              }
              label="SMS Notifications"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle1" gutterBottom>
              🔔 Alert Types
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={notifications.stockoutAlerts}
                  onChange={() => handleNotificationChange('stockoutAlerts')}
                />
              }
              label="Stockout Alerts"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={notifications.forecastAlerts}
                  onChange={() => handleNotificationChange('forecastAlerts')}
                />
              }
              label="Forecast Accuracy Alerts"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={notifications.systemAlerts}
                  onChange={() => handleNotificationChange('systemAlerts')}
                />
              }
              label="System Status Alerts"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={notifications.weeklyReports}
                  onChange={() => handleNotificationChange('weeklyReports')}
                />
              }
              label="Weekly Summary Reports"
            />
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        <Box>
          <Typography variant="subtitle1" gutterBottom>
            📱 Contact Information
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Email Address"
                defaultValue="admin@retailai.com"
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Phone Number"
                defaultValue="+1 (555) 123-4567"
                variant="outlined"
                size="small"
              />
            </Grid>
          </Grid>
        </Box>
      </CardContent>
    </Card>
  );

  const renderSystemSettings = () => (
    <Card elevation={2}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={3}>
          <Tune sx={{ mr: 2, color: 'primary.main' }} />
          <Typography variant="h6">System Configuration</Typography>
        </Box>

        <Grid container spacing={4}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle1" gutterBottom>
              📊 Data Management
            </Typography>
            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>Data Retention (months): {systemSettings.dataRetention}</Typography>
              <Slider
                value={systemSettings.dataRetention}
                onChange={(_, value) => handleSystemChange('dataRetention', value)}
                min={6}
                max={60}
                marks={[
                  { value: 6, label: '6M' },
                  { value: 12, label: '1Y' },
                  { value: 24, label: '2Y' },
                  { value: 60, label: '5Y' }
                ]}
              />
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>Forecast Horizon (days): {systemSettings.forecastHorizon}</Typography>
              <Slider
                value={systemSettings.forecastHorizon}
                onChange={(_, value) => handleSystemChange('forecastHorizon', value)}
                min={7}
                max={365}
                marks={[
                  { value: 7, label: '1W' },
                  { value: 30, label: '1M' },
                  { value: 90, label: '3M' },
                  { value: 365, label: '1Y' }
                ]}
              />
            </Box>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle1" gutterBottom>
              ⚙️ Optimization Settings
            </Typography>
            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>Service Level Target: {systemSettings.serviceLevel}%</Typography>
              <Slider
                value={systemSettings.serviceLevel}
                onChange={(_, value) => handleSystemChange('serviceLevel', value)}
                min={85}
                max={99}
                marks={[
                  { value: 85, label: '85%' },
                  { value: 95, label: '95%' },
                  { value: 99, label: '99%' }
                ]}
              />
            </Box>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Optimization Frequency</InputLabel>
              <Select
                value={systemSettings.optimizationFrequency}
                label="Optimization Frequency"
                onChange={(e) => handleSystemChange('optimizationFrequency', e.target.value)}
              >
                <MenuItem value="hourly">Every Hour</MenuItem>
                <MenuItem value="daily">Daily</MenuItem>
                <MenuItem value="weekly">Weekly</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>ML Model Updates</InputLabel>
              <Select
                value={systemSettings.mlModelUpdate}
                label="ML Model Updates"
                onChange={(e) => handleSystemChange('mlModelUpdate', e.target.value)}
              >
                <MenuItem value="hourly">Every Hour</MenuItem>
                <MenuItem value="daily">Daily</MenuItem>
                <MenuItem value="weekly">Weekly</MenuItem>
              </Select>
            </FormControl>

            <FormControlLabel
              control={
                <Switch
                  checked={systemSettings.autoReorder}
                  onChange={(e) => handleSystemChange('autoReorder', e.target.checked)}
                />
              }
              label="Enable Automatic Reordering"
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  const renderUserPreferences = () => (
    <Card elevation={2}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={3}>
          <Dashboard sx={{ mr: 2, color: 'primary.main' }} />
          <Typography variant="h6">User Preferences</Typography>
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Theme</InputLabel>
              <Select
                value={userPreferences.theme}
                label="Theme"
                onChange={(e) => handleUserPrefChange('theme', e.target.value)}
              >
                <MenuItem value="light">Light</MenuItem>
                <MenuItem value="dark">Dark</MenuItem>
                <MenuItem value="auto">Auto</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Language</InputLabel>
              <Select
                value={userPreferences.language}
                label="Language"
                onChange={(e) => handleUserPrefChange('language', e.target.value)}
              >
                <MenuItem value="en">English</MenuItem>
                <MenuItem value="es">Spanish</MenuItem>
                <MenuItem value="fr">French</MenuItem>
                <MenuItem value="de">German</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Timezone</InputLabel>
              <Select
                value={userPreferences.timezone}
                label="Timezone"
                onChange={(e) => handleUserPrefChange('timezone', e.target.value)}
              >
                <MenuItem value="UTC-8">Pacific Time (UTC-8)</MenuItem>
                <MenuItem value="UTC-7">Mountain Time (UTC-7)</MenuItem>
                <MenuItem value="UTC-6">Central Time (UTC-6)</MenuItem>
                <MenuItem value="UTC-5">Eastern Time (UTC-5)</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Currency</InputLabel>
              <Select
                value={userPreferences.currency}
                label="Currency"
                onChange={(e) => handleUserPrefChange('currency', e.target.value)}
              >
                <MenuItem value="USD">USD ($)</MenuItem>
                <MenuItem value="EUR">EUR (€)</MenuItem>
                <MenuItem value="GBP">GBP (£)</MenuItem>
                <MenuItem value="CAD">CAD (C$)</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Dashboard Layout</InputLabel>
              <Select
                value={userPreferences.dashboardLayout}
                label="Dashboard Layout"
                onChange={(e) => handleUserPrefChange('dashboardLayout', e.target.value)}
              >
                <MenuItem value="standard">Standard</MenuItem>
                <MenuItem value="compact">Compact</MenuItem>
                <MenuItem value="detailed">Detailed</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  const renderAPISettings = () => (
    <Card elevation={2}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={3}>
          <Api sx={{ mr: 2, color: 'primary.main' }} />
          <Typography variant="h6">API Configuration</Typography>
        </Box>

        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="body2">
            Changes to API settings require system restart and may affect performance.
          </Typography>
        </Alert>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Rate Limit (requests/hour)"
              type="number"
              value={apiSettings.rateLimit}
              onChange={(e) => setApiSettings(prev => ({ ...prev, rateLimit: parseInt(e.target.value) }))}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Timeout (seconds)"
              type="number"
              value={apiSettings.timeout}
              onChange={(e) => setApiSettings(prev => ({ ...prev, timeout: parseInt(e.target.value) }))}
              sx={{ mb: 2 }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Retries"
              type="number"
              value={apiSettings.retries}
              onChange={(e) => setApiSettings(prev => ({ ...prev, retries: parseInt(e.target.value) }))}
              sx={{ mb: 2 }}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={apiSettings.caching}
                  onChange={(e) => setApiSettings(prev => ({ ...prev, caching: e.target.checked }))}
                />
              }
              label="Enable Response Caching"
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  const settingsTabs = [
    { id: 'notifications', label: 'Notifications', icon: <Notifications /> },
    { id: 'system', label: 'System', icon: <Tune /> },
    { id: 'preferences', label: 'Preferences', icon: <Dashboard /> },
    { id: 'api', label: 'API', icon: <Api /> }
  ];

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            ⚙️ System Settings
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Configure system preferences, notifications, and optimization parameters
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleResetSettings}
          >
            Reset to Defaults
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSaveSettings}
            disabled={saveStatus === 'saving'}
          >
            {saveStatus === 'saving' ? 'Saving...' : 'Save Settings'}
          </Button>
        </Box>
      </Box>

      {/* Save Status Alert */}
      {saveStatus === 'saved' && (
        <Alert severity="success" sx={{ mb: 3 }}>
          <Typography>Settings saved successfully!</Typography>
        </Alert>
      )}

      {saveStatus === 'error' && (
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography>Failed to save settings. Please try again.</Typography>
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Settings Navigation */}
        <Grid item xs={12} md={3}>
          <Paper elevation={2} sx={{ p: 2 }}>
            <List>
              {settingsTabs.map((tab) => (
                <ListItem
                  button
                  key={tab.id}
                  selected={activeTab === tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  sx={{
                    borderRadius: 1,
                    mb: 1,
                    '&.Mui-selected': {
                      backgroundColor: 'primary.light',
                      color: 'primary.contrastText'
                    }
                  }}
                >
                  <ListItemIcon sx={{ color: activeTab === tab.id ? 'inherit' : 'text.secondary' }}>
                    {tab.icon}
                  </ListItemIcon>
                  <ListItemText primary={tab.label} />
                </ListItem>
              ))}
            </List>
          </Paper>

          {/* System Status */}
          <Paper elevation={2} sx={{ p: 2, mt: 2 }}>
            <Typography variant="h6" gutterBottom color="primary">
              🚀 System Status
            </Typography>
            <Box display="flex" alignItems="center" mb={1}>
              <CheckCircle color="success" sx={{ mr: 1 }} />
              <Typography variant="body2">All services operational</Typography>
            </Box>
            <Box display="flex" alignItems="center" mb={1}>
              <Schedule sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="body2">Last backup: 2 hours ago</Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
              Next maintenance: Dec 15, 2:00 AM
            </Typography>
          </Paper>
        </Grid>

        {/* Settings Content */}
        <Grid item xs={12} md={9}>
          {activeTab === 'notifications' && renderNotificationSettings()}
          {activeTab === 'system' && renderSystemSettings()}
          {activeTab === 'preferences' && renderUserPreferences()}
          {activeTab === 'api' && renderAPISettings()}
        </Grid>
      </Grid>
    </Container>
  );
};

export default Settings;