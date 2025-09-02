import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const user = localStorage.getItem('retailai_user');
    if (user) {
      try {
        const userData = JSON.parse(user);
        if (userData.token) {
          config.headers.Authorization = `Bearer ${userData.token}`;
        }
      } catch (error) {
        console.error('Error parsing user data:', error);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('retailai_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const api = {
  // Health check
  health: () => apiClient.get('/health'),
  
  // Authentication (not needed for demo)
  auth: {
    login: (credentials: { email: string; password: string }) =>
      apiClient.post('/api/auth/login', credentials),
    logout: () => apiClient.post('/api/auth/logout'),
  },
  
  // Real ML Forecasting
  forecasting: {
    generate: (params: any) => apiClient.post('/api/forecast', params),
    getAccuracy: () => apiClient.get('/api/analytics/performance'),
  },
  
  // Real Inventory Optimization
  inventory: {
    optimize: (params: any) => apiClient.post('/api/optimize', params),
    getCurrent: () => apiClient.get('/api/products'),
    getRecommendations: () => apiClient.get('/api/reorder-recommendations'),
  },
  
  // Real Analytics with actual KPIs
  analytics: {
    getKPIs: () => apiClient.get('/api/kpis'),
    getReports: () => apiClient.get('/api/demo/run-analysis'),
    getStores: () => apiClient.get('/api/stores'),
    getProducts: () => apiClient.get('/api/products'),
  },
};