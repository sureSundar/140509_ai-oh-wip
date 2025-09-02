/**
 * Executive Dashboard - AI-Powered Retail Inventory Optimization
 * Main dashboard application for executives and management
 */

import React, { useState, useEffect } from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate
} from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Components
import Sidebar from './components/Layout/Sidebar';
import TopBar from './components/Layout/TopBar';
import LoginPage from './pages/LoginPage';
import Overview from './pages/Overview';
import Analytics from './pages/Analytics';
import Forecasting from './pages/Forecasting';
import Optimization from './pages/Optimization';
import Reports from './pages/Reports';
import Settings from './pages/Settings';

// Context
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';

// Services
import { apiClient } from './services/api';

// Styles
import './App.css';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

// Material-UI theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          borderRadius: 8,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 6,
        },
      },
    },
  },
});

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box display=\"flex\" justifyContent=\"center\" alignItems=\"center\" height=\"100vh\">
        <div>Loading...</div>
      </Box>
    );
  }

  if (!user) {
    return <Navigate to=\"/login\" replace />;
  }

  return <>{children}</>;
};

// Main App Layout
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { user } = useAuth();

  if (!user) {
    return <>{children}</>;
  }

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <Sidebar 
        open={sidebarOpen} 
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      <Box
        component=\"main\"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          marginLeft: sidebarOpen ? '240px' : '60px',
          transition: 'margin-left 0.3s ease',
        }}
      >
        <TopBar onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
        <Box
          sx={{
            flexGrow: 1,
            overflow: 'auto',
            padding: 3,
            backgroundColor: 'background.default',
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
};

// Main App Component
const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <NotificationProvider>
            <Router>
              <AppLayout>
                <Routes>
                  <Route path=\"/login\" element={<LoginPage />} />
                  <Route
                    path=\"/\"
                    element={
                      <ProtectedRoute>
                        <Overview />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path=\"/analytics\"
                    element={
                      <ProtectedRoute>
                        <Analytics />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path=\"/forecasting\"
                    element={
                      <ProtectedRoute>
                        <Forecasting />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path=\"/optimization\"
                    element={
                      <ProtectedRoute>
                        <Optimization />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path=\"/reports\"
                    element={
                      <ProtectedRoute>
                        <Reports />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path=\"/settings\"
                    element={
                      <ProtectedRoute>
                        <Settings />
                      </ProtectedRoute>
                    }
                  />
                  <Route path=\"*\" element={<Navigate to=\"/\" replace />} />
                </Routes>
              </AppLayout>
              <ToastContainer
                position=\"top-right\"
                autoClose={5000}
                hideProgressBar={false}
                newestOnTop
                closeOnClick
                rtl={false}
                pauseOnFocusLoss
                draggable
                pauseOnHover
              />
            </Router>
          </NotificationProvider>
        </AuthProvider>
      </ThemeProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
};

export default App;