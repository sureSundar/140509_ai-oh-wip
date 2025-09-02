#!/bin/bash
# RetailAI Hackathon Deployment Script - One-Click Deploy
set -e

echo "🚀 RetailAI Platform - One-Click Deployment"
echo "============================================="

# Prerequisites check
echo "📋 Checking prerequisites..."
command -v python3 >/dev/null || { echo "❌ Python3 required"; exit 1; }
command -v pip3 >/dev/null || { echo "❌ pip3 required"; exit 1; }

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install fastapi uvicorn psycopg2-binary redis bcrypt passlib python-jose[cryptography] >/dev/null 2>&1

# Setup database
echo "🗄️ Setting up database..."
sudo -u postgres createdb retailai 2>/dev/null || echo "Database exists"
sudo -u postgres createuser retailai 2>/dev/null || echo "User exists" 
sudo -u postgres psql -c "ALTER USER retailai WITH PASSWORD 'retailai123';" >/dev/null 2>&1

# Start Redis
echo "🔄 Starting Redis..."
redis-server --daemonize yes 2>/dev/null || echo "Redis running"

# Start services
echo "🚀 Starting RetailAI services..."
./start_retailai_services.sh

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================"
echo "🌐 Main Dashboard: http://localhost:3000/RETAILAI_MAIN_DASHBOARD.html"
echo "🔐 Authentication: http://localhost:8004"  
echo "⚠️  Alerts: http://localhost:8003"
echo ""
echo "📋 Login: admin/admin123 or demo/demo123"
echo "🎯 Ready for hackathon demo!"