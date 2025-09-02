#!/bin/bash
# Setup script for AI-Powered Retail Inventory Optimization System

set -e

echo "🚀 Setting up RetailAI Inventory Optimizer..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p logs
mkdir -p data/postgres
mkdir -p data/clickhouse
mkdir -p data/redis
mkdir -p data/mlflow

# Set permissions for data directories
chmod -R 755 data/

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️ Creating environment configuration..."
    cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://retailai:retailai123@postgres:5432/retailai
CLICKHOUSE_URL=http://clickhouse:8123
REDIS_URL=redis://redis:6379

# ML Configuration
MLFLOW_TRACKING_URI=http://mlflow:5000

# API Configuration
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
API_PORT=3000
CORS_ORIGIN=http://localhost:3001,http://localhost:3002

# External APIs (configure these with your actual API keys)
WEATHER_API_KEY=your-weather-api-key
EVENTS_API_KEY=your-events-api-key

# Email Configuration (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# SMS Configuration (optional)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number

# Environment
NODE_ENV=development
LOG_LEVEL=info
EOF
    echo "📝 Created .env file. Please update it with your actual configuration values."
fi

# Install Python dependencies for ML services
echo "🐍 Setting up Python environment for ML services..."
if command -v python3 &> /dev/null; then
    python3 -m pip install --user virtualenv
    
    # Create virtual environment for ML engine
    if [ ! -d "services/ml-engine/venv" ]; then
        cd services/ml-engine
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cd ../../
    fi
    
    echo "✅ Python environment ready"
else
    echo "⚠️ Python 3 not found. Please install Python 3.9+ for local development."
fi

# Install Node.js dependencies for API Gateway
echo "📦 Setting up Node.js dependencies..."
if command -v npm &> /dev/null; then
    cd services/api-gateway
    npm install
    cd ../../
    
    # Install frontend dependencies
    cd frontend/executive-dashboard
    npm install
    cd ../../
    
    cd frontend/operational-dashboard
    npm install
    cd ../../
    
    echo "✅ Node.js dependencies installed"
else
    echo "⚠️ Node.js not found. Please install Node.js 16+ for local development."
fi

# Build Docker images
echo "🐳 Building Docker images..."
docker-compose build --parallel

# Initialize database
echo "🗄️ Initializing databases..."
docker-compose up -d postgres clickhouse redis

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 30

# Run database migrations
echo "📊 Setting up database schema..."
docker-compose exec postgres psql -U retailai -d retailai -f /docker-entrypoint-initdb.d/init.sql

# Start all services
echo "🚀 Starting all services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 60

# Health check
echo "🔍 Checking service health..."
services=(
    "http://localhost:3000/health"
    "http://localhost:8001/health"
    "http://localhost:8002/health"
    "http://localhost:8003/health"
)

all_healthy=true
for service in "${services[@]}"; do
    if curl -f -s "$service" > /dev/null; then
        echo "✅ $service is healthy"
    else
        echo "❌ $service is not responding"
        all_healthy=false
    fi
done

if [ "$all_healthy" = true ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "📊 Services are running on:"
    echo "   • API Gateway: http://localhost:3000"
    echo "   • Executive Dashboard: http://localhost:3001"
    echo "   • Operational Dashboard: http://localhost:3002"
    echo "   • ML Engine: http://localhost:8001"
    echo "   • Data Ingestion: http://localhost:8002"
    echo "   • Inventory Service: http://localhost:8003"
    echo "   • MLflow UI: http://localhost:5000"
    echo ""
    echo "🔑 Default login credentials:"
    echo "   • Username: admin@retailai.com"
    echo "   • Password: admin123"
    echo ""
    echo "📖 Next steps:"
    echo "   1. Configure external API keys in .env file"
    echo "   2. Upload sample data using the data ingestion APIs"
    echo "   3. Train ML models using the ML engine"
    echo "   4. Access dashboards to view inventory insights"
    echo ""
    echo "🛠️ Useful commands:"
    echo "   • View logs: docker-compose logs -f [service-name]"
    echo "   • Stop services: docker-compose down"
    echo "   • Restart services: docker-compose restart"
    echo "   • Run tests: ./scripts/run-tests.sh"
else
    echo ""
    echo "⚠️ Some services are not healthy. Check the logs:"
    echo "   docker-compose logs"
    echo ""
    echo "To restart services:"
    echo "   docker-compose down && docker-compose up -d"
fi