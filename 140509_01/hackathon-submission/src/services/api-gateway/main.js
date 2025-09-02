/**
 * API Gateway - AI-Powered Retail Inventory Optimization
 * Central gateway for routing requests to microservices
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { createProxyMiddleware } = require('http-proxy-middleware');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const { Pool } = require('pg');
const Redis = require('redis');
const winston = require('winston');

// Initialize logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
    new winston.transports.Console()
  ]
});

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Database connection
const db = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

// Redis connection
const redis = Redis.createClient({
  url: process.env.REDIS_URL
});

redis.on('error', (err) => logger.error('Redis Client Error', err));
redis.connect();

// Middleware
app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGIN || ['http://localhost:3001', 'http://localhost:3002'],
  credentials: true
}));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(limiter);

// JWT Authentication middleware
const authenticateToken = async (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'retail-ai-secret');
    
    // Get user from database
    const userQuery = await db.query(
      'SELECT id, email, username, role, is_active FROM users WHERE id = $1',
      [decoded.userId]
    );

    if (userQuery.rows.length === 0 || !userQuery.rows[0].is_active) {
      return res.status(401).json({ error: 'Invalid or inactive user' });
    }

    req.user = userQuery.rows[0];
    next();
  } catch (error) {
    logger.error('Token verification failed:', error);
    return res.status(403).json({ error: 'Invalid token' });
  }
};

// Role-based authorization middleware
const authorizeRole = (roles) => {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }
    next();
  };
};

// Request logging middleware
app.use((req, res, next) => {
  logger.info(`${req.method} ${req.url}`, {
    ip: req.ip,
    userAgent: req.get('User-Agent'),
    userId: req.user?.id
  });
  next();
});

// Health check endpoint
app.get('/health', async (req, res) => {
  try {
    // Check database connection
    await db.query('SELECT 1');
    
    // Check Redis connection
    await redis.ping();
    
    // Check microservices health
    const healthChecks = await Promise.allSettled([
      fetch(`${process.env.ML_ENGINE_URL || 'http://ml-engine:8001'}/health`),
      fetch(`${process.env.DATA_INGESTION_URL || 'http://data-ingestion:8002'}/health`),
      fetch(`${process.env.INVENTORY_SERVICE_URL || 'http://inventory-service:8003'}/health`)
    ]);

    const servicesStatus = {
      database: 'healthy',
      redis: 'healthy',
      mlEngine: healthChecks[0].status === 'fulfilled' ? 'healthy' : 'unhealthy',
      dataIngestion: healthChecks[1].status === 'fulfilled' ? 'healthy' : 'unhealthy',
      inventoryService: healthChecks[2].status === 'fulfilled' ? 'healthy' : 'unhealthy'
    };

    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      services: servicesStatus
    });
  } catch (error) {
    logger.error('Health check failed:', error);
    res.status(503).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: error.message
    });
  }
});

// Authentication endpoints
app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password required' });
    }

    // Get user from database
    const userQuery = await db.query(
      'SELECT id, email, username, password_hash, role, is_active FROM users WHERE email = $1',
      [email]
    );

    if (userQuery.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const user = userQuery.rows[0];

    if (!user.is_active) {
      return res.status(401).json({ error: 'Account is inactive' });
    }

    // Verify password
    const validPassword = await bcrypt.compare(password, user.password_hash);
    if (!validPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Generate JWT token
    const token = jwt.sign(
      { 
        userId: user.id, 
        email: user.email, 
        role: user.role 
      },
      process.env.JWT_SECRET || 'retail-ai-secret',
      { expiresIn: '8h' }
    );

    // Store session in Redis
    await redis.setEx(`session:${user.id}`, 28800, token); // 8 hours

    res.json({
      token,
      user: {
        id: user.id,
        email: user.email,
        username: user.username,
        role: user.role
      }
    });

    logger.info('User logged in successfully', { userId: user.id, email: user.email });

  } catch (error) {
    logger.error('Login failed:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.post('/api/auth/logout', authenticateToken, async (req, res) => {
  try {
    // Remove session from Redis
    await redis.del(`session:${req.user.id}`);
    
    res.json({ message: 'Logged out successfully' });
    logger.info('User logged out', { userId: req.user.id });
  } catch (error) {
    logger.error('Logout failed:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.get('/api/auth/me', authenticateToken, (req, res) => {
  res.json({
    user: {
      id: req.user.id,
      email: req.user.email,
      username: req.user.username,
      role: req.user.role
    }
  });
});

// Service proxy configurations
const serviceProxies = {
  '/api/ml': {
    target: process.env.ML_ENGINE_URL || 'http://ml-engine:8001',
    pathRewrite: { '^/api/ml': '/api/v1' },
    changeOrigin: true,
    timeout: 300000, // 5 minutes for ML operations
    onError: (err, req, res) => {
      logger.error('ML Engine proxy error:', err);
      res.status(503).json({ error: 'ML service unavailable' });
    }
  },
  '/api/data': {
    target: process.env.DATA_INGESTION_URL || 'http://data-ingestion:8002',
    pathRewrite: { '^/api/data': '/api/v1' },
    changeOrigin: true,
    timeout: 60000,
    onError: (err, req, res) => {
      logger.error('Data Ingestion proxy error:', err);
      res.status(503).json({ error: 'Data service unavailable' });
    }
  },
  '/api/inventory': {
    target: process.env.INVENTORY_SERVICE_URL || 'http://inventory-service:8003',
    pathRewrite: { '^/api/inventory': '/api/v1' },
    changeOrigin: true,
    timeout: 60000,
    onError: (err, req, res) => {
      logger.error('Inventory Service proxy error:', err);
      res.status(503).json({ error: 'Inventory service unavailable' });
    }
  }
};

// Apply authentication to all API routes except auth endpoints
app.use('/api', (req, res, next) => {
  if (req.path.startsWith('/auth/')) {
    return next();
  }
  return authenticateToken(req, res, next);
});

// Create proxy middleware for each service
Object.entries(serviceProxies).forEach(([path, config]) => {
  app.use(path, createProxyMiddleware(config));
});

// Direct API endpoints for live data (no auth required for demo)
app.get('/api/kpis', async (req, res) => {
  try {
    const response = await fetch(`${process.env.ML_ENGINE_URL || 'http://ml-engine:8001'}/api/kpis`);
    const data = await response.json();
    res.json(data);
  } catch (error) {
    logger.error('Failed to fetch KPIs:', error);
    res.status(500).json({ error: 'Failed to fetch KPIs' });
  }
});

app.get('/api/forecasts', async (req, res) => {
  try {
    const response = await fetch(`${process.env.ML_ENGINE_URL || 'http://ml-engine:8001'}/api/forecasts`);
    const data = await response.json();
    res.json(data);
  } catch (error) {
    logger.error('Failed to fetch forecasts:', error);
    res.status(500).json({ error: 'Failed to fetch forecasts' });
  }
});

app.get('/api/analytics/stores', async (req, res) => {
  try {
    const response = await fetch(`${process.env.ML_ENGINE_URL || 'http://ml-engine:8001'}/api/analytics/stores`);
    const data = await response.json();
    res.json(data);
  } catch (error) {
    logger.error('Failed to fetch store analytics:', error);
    res.status(500).json({ error: 'Failed to fetch store analytics' });
  }
});

// Dashboard data aggregation endpoints
app.get('/api/dashboard/executive', authenticateToken, authorizeRole(['admin', 'manager']), async (req, res) => {
  try {
    // Aggregate data from multiple services for executive dashboard
    const [inventoryKpis, forecastAccuracy, alerts] = await Promise.allSettled([
      fetch(`${process.env.INVENTORY_SERVICE_URL || 'http://inventory-service:8003'}/api/v1/kpis`, {
        headers: { 'Authorization': req.headers.authorization }
      }).then(r => r.json()),
      fetch(`${process.env.ML_ENGINE_URL || 'http://ml-engine:8001'}/api/v1/analytics/accuracy`, {
        headers: { 'Authorization': req.headers.authorization }
      }).then(r => r.json()),
      fetch(`${process.env.INVENTORY_SERVICE_URL || 'http://inventory-service:8003'}/api/v1/alerts?limit=10`, {
        headers: { 'Authorization': req.headers.authorization }
      }).then(r => r.json())
    ]);

    const dashboardData = {
      timestamp: new Date().toISOString(),
      kpis: inventoryKpis.status === 'fulfilled' ? inventoryKpis.value : null,
      forecastAccuracy: forecastAccuracy.status === 'fulfilled' ? forecastAccuracy.value : null,
      recentAlerts: alerts.status === 'fulfilled' ? alerts.value : null,
      summary: {
        totalStores: 150,
        totalProducts: 25000,
        activeAlerts: alerts.status === 'fulfilled' ? alerts.value?.length || 0 : 0,
        systemHealth: 'good'
      }
    };

    res.json(dashboardData);
  } catch (error) {
    logger.error('Executive dashboard data aggregation failed:', error);
    res.status(500).json({ error: 'Failed to load dashboard data' });
  }
});

app.get('/api/dashboard/operational', authenticateToken, async (req, res) => {
  try {
    // Aggregate data for operational dashboard
    const [currentInventory, reorderRecommendations, stockoutRisk] = await Promise.allSettled([
      fetch(`${process.env.INVENTORY_SERVICE_URL || 'http://inventory-service:8003'}/api/v1/inventory/current?limit=50`, {
        headers: { 'Authorization': req.headers.authorization }
      }).then(r => r.json()),
      fetch(`${process.env.INVENTORY_SERVICE_URL || 'http://inventory-service:8003'}/api/v1/reorder/recommendations?limit=20`, {
        headers: { 'Authorization': req.headers.authorization }
      }).then(r => r.json()),
      fetch(`${process.env.INVENTORY_SERVICE_URL || 'http://inventory-service:8003'}/api/v1/analytics/stockout-risk`, {
        headers: { 'Authorization': req.headers.authorization }
      }).then(r => r.json())
    ]);

    const dashboardData = {
      timestamp: new Date().toISOString(),
      inventory: currentInventory.status === 'fulfilled' ? currentInventory.value : null,
      reorderRecommendations: reorderRecommendations.status === 'fulfilled' ? reorderRecommendations.value : null,
      stockoutRisk: stockoutRisk.status === 'fulfilled' ? stockoutRisk.value : null,
      summary: {
        lowStockItems: 15,
        pendingOrders: 8,
        criticalAlerts: 3
      }
    };

    res.json(dashboardData);
  } catch (error) {
    logger.error('Operational dashboard data aggregation failed:', error);
    res.status(500).json({ error: 'Failed to load dashboard data' });
  }
});

// Bulk operations endpoint
app.post('/api/bulk/forecast-and-optimize', 
  authenticateToken, 
  authorizeRole(['admin', 'manager']), 
  async (req, res) => {
    try {
      const { storeIds, categoryIds, forecastDays = 30 } = req.body;

      // Start forecast generation
      const forecastResponse = await fetch(`${process.env.ML_ENGINE_URL || 'http://ml-engine:8001'}/api/v1/forecast/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': req.headers.authorization
        },
        body: JSON.stringify({
          store_ids: storeIds,
          category_ids: categoryIds,
          forecast_horizon_days: forecastDays
        })
      });

      const forecastResult = await forecastResponse.json();

      // Start optimization
      const optimizationResponse = await fetch(`${process.env.INVENTORY_SERVICE_URL || 'http://inventory-service:8003'}/api/v1/optimization/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': req.headers.authorization
        },
        body: JSON.stringify({
          store_ids: storeIds,
          category_ids: categoryIds
        })
      });

      const optimizationResult = await optimizationResponse.json();

      res.json({
        message: 'Bulk forecast and optimization started',
        forecast_task: forecastResult,
        optimization_task: optimizationResult,
        estimated_completion: '45 minutes'
      });

    } catch (error) {
      logger.error('Bulk forecast and optimize failed:', error);
      res.status(500).json({ error: 'Bulk operation failed' });
    }
  }
);

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    timestamp: new Date().toISOString()
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ 
    error: 'Endpoint not found',
    path: req.originalUrl,
    timestamp: new Date().toISOString()
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully');
  
  try {
    await db.end();
    await redis.disconnect();
    process.exit(0);
  } catch (error) {
    logger.error('Error during shutdown:', error);
    process.exit(1);
  }
});

// Start server
app.listen(PORT, () => {
  logger.info(`API Gateway running on port ${PORT}`);
  logger.info('Environment:', process.env.NODE_ENV || 'development');
});

module.exports = app;