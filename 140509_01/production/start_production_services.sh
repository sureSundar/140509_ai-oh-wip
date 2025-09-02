#!/bin/bash

# Production Service Startup Script for 140509_01 Project
# Starts all production services with proper project integration

echo "🚀 Starting 140509_01 Production Services"
echo "========================================"

# Set project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRODUCTION_DIR="$PROJECT_ROOT/production"
LOGS_DIR="$PROJECT_ROOT/logs"

echo "📁 Project Root: $PROJECT_ROOT"
echo "🏭 Production Dir: $PRODUCTION_DIR"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Function to start a production service
start_production_service() {
    local service_name=$1
    local service_file=$2
    local port=$3
    local description=$4
    
    echo ""
    echo "🔄 Starting $service_name..."
    echo "   📄 File: $service_file"
    echo "   🌐 Port: $port"
    echo "   📝 Description: $description"
    
    if [ -f "$PRODUCTION_DIR/$service_file" ]; then
        cd "$PROJECT_ROOT"
        
        # Kill any existing process on the port
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "   ⚠️  Port $port in use, stopping existing service..."
            pkill -f "$service_file" 2>/dev/null || true
            sleep 2
        fi
        
        # Start the service
        nohup python3 "$PRODUCTION_DIR/$service_file" > "$LOGS_DIR/${service_name,,}_production.log" 2>&1 &
        local pid=$!
        
        echo "   ✅ $service_name started (PID: $pid)"
        echo "   📋 Log: $LOGS_DIR/${service_name,,}_production.log"
        
        # Wait a moment for service to start
        sleep 3
        
        # Test if service is responding
        if curl -s -f "http://localhost:$port/health" >/dev/null 2>&1; then
            echo "   🟢 Service responding on port $port"
        else
            echo "   🟡 Service started but may still be initializing..."
        fi
    else
        echo "   ❌ Service file not found: $PRODUCTION_DIR/$service_file"
        return 1
    fi
}

echo ""
echo "🔍 Pre-flight Checks..."
echo "----------------------"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Check if required production files exist
required_files=(
    "auth_service_production.py"
    "ml_engine_production.py"
    "integrated_tests.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$PRODUCTION_DIR/$file" ]; then
        echo "✅ Found: $file"
    else
        echo "❌ Missing: $file"
        exit 1
    fi
done

echo ""
echo "🚀 Starting Production Services..."
echo "----------------------------------"

# Start Authentication Service (Port 8004)
start_production_service \
    "Authentication" \
    "auth_service_production.py" \
    8004 \
    "Enterprise-grade RBAC and JWT authentication"

# Start ML Engine Service (Port 8001) 
start_production_service \
    "ML_Engine" \
    "ml_engine_production.py" \
    8001 \
    "Production ML forecasting and analytics"

echo ""
echo "⏳ Waiting for services to fully initialize..."
sleep 5

echo ""
echo "🔍 Production Service Status Check..."
echo "------------------------------------"

# Check service status
services=(
    "Authentication:8004:/health"
    "ML_Engine:8001:/health"
)

all_healthy=true

for service_info in "${services[@]}"; do
    IFS=':' read -r name port endpoint <<< "$service_info"
    
    echo -n "🔍 Checking $name ($port)... "
    
    if response=$(curl -s "http://localhost:$port$endpoint" 2>/dev/null); then
        if echo "$response" | grep -q '"status":"healthy"'; then
            project=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('project', 'unknown'))" 2>/dev/null)
            version=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('version', 'unknown'))" 2>/dev/null)
            echo "✅ HEALTHY (Project: $project, Version: $version)"
        else
            echo "🟡 RESPONDING (Status unclear)"
            all_healthy=false
        fi
    else
        echo "❌ NOT RESPONDING"
        all_healthy=false
    fi
done

echo ""
echo "🌐 Production Service Endpoints:"
echo "--------------------------------"
echo "🔐 Authentication API:     http://localhost:8004"
echo "   📖 API Documentation:   http://localhost:8004/docs"
echo "   🏥 Health Check:        http://localhost:8004/health"
echo ""
echo "🧠 ML Engine API:          http://localhost:8001"
echo "   📖 API Documentation:   http://localhost:8001/docs"
echo "   🏥 Health Check:        http://localhost:8001/health"
echo "   📊 KPIs Endpoint:       http://localhost:8001/api/kpis"
echo ""
echo "🎯 Demo Applications:"
echo "🌐 Integrated Business Demo:    http://localhost:9000/INTEGRATED_BUSINESS_DEMO.html"
echo "🌐 Comprehensive Landing Page:  http://localhost:9000/COMPREHENSIVE_LANDING_PAGE.html"

echo ""
echo "🧪 Testing & Monitoring:"
echo "------------------------"
echo "📋 Run Integration Tests:  python3 production/integrated_tests.py"
echo "📂 View Logs:             tail -f logs/*.log"
echo "📊 Production Report:     cat logs/production_integration_report.json"

echo ""
echo "🔧 Service Management:"
echo "----------------------"
echo "🛑 Stop Services:         pkill -f 'production.*py'"
echo "📋 Check Processes:       ps aux | grep 'production.*py'"
echo "📊 Monitor Logs:          tail -f $LOGS_DIR/*.log"

echo ""
if [ "$all_healthy" = true ]; then
    echo "🎉 140509_01 Production System is READY!"
    echo "✅ All services healthy and properly integrated"
    echo "🚀 Ready for production deployment"
else
    echo "⚠️  140509_01 Production System started with issues"
    echo "🔧 Some services may need attention"
    echo "📋 Check logs and run integration tests"
fi

echo ""
echo "📋 Quick Health Check:"
echo "curl -s http://localhost:8004/health | jq '.project'"
echo "curl -s http://localhost:8001/health | jq '.project'"

echo ""
echo "========================================"
echo "🏭 140509_01 Production Services Running"