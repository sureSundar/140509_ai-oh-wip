#!/bin/bash

# RetailAI Platform - Service Startup Script
# Starts all microservices in the correct order

echo "🚀 Starting RetailAI Platform Services..."
echo "========================================"

# Set base directory
BASE_DIR="/home/vboxuser/Documents/140509_ai-oh-wip/140509_01/src/services"

# Function to start a service
start_service() {
    local service_name=$1
    local service_dir=$2
    local service_file=$3
    local port=$4
    
    echo "🔄 Starting $service_name on port $port..."
    
    if [ -f "$BASE_DIR/$service_dir/$service_file" ]; then
        cd "$BASE_DIR/$service_dir"
        nohup python3 "$service_file" > "/tmp/retailai_${service_name,,}_$port.log" 2>&1 &
        echo "✅ $service_name started (PID: $!) - Log: /tmp/retailai_${service_name,,}_$port.log"
        sleep 2
    else
        echo "❌ $service_name file not found: $BASE_DIR/$service_dir/$service_file"
    fi
}

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        echo "⚠️  Port $port is already in use"
        return 1
    fi
    return 0
}

echo ""
echo "📋 Pre-flight checks..."
echo "----------------------"

# Check if required ports are available
ports=(8001 8002 8003 8004 8005 8006 8007)
for port in "${ports[@]}"; do
    if ! check_port $port; then
        echo "Stopping existing service on port $port..."
        pkill -f ":$port" 2>/dev/null || true
        sleep 1
    fi
done

echo ""
echo "🚀 Starting services in dependency order..."
echo "--------------------------------------------"

# 1. Start ML Engine (8001) - Core AI/ML services
start_service "ML Engine" "ml-engine" "ml_api.py" 8001

# 2. Start External Data Service (8002) - Weather, events, demographics
start_service "External Data" "external-data" "external_data_api.py" 8002

# 3. Start Alert Engine (8003) - Business rule alerts
start_service "Alert Engine" "alert-engine" "alert_api.py" 8003

# 4. Start Authentication & RBAC (8004) - Security layer
start_service "Authentication & RBAC" "auth" "auth_api.py" 8004

# 5. Start Dashboard Service (8005) - Operational dashboard
start_service "Dashboard" "dashboard" "dashboard_api.py" 8005

# 6. Start Reporting Service (8006) - Automated reports and audit
start_service "Reporting" "reporting" "reporting_api.py" 8006

# 7. Start Performance Monitoring (8007) - System monitoring
start_service "Performance Monitoring" "monitoring" "monitoring_api.py" 8007

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 5

echo ""
echo "🔍 Service Status Check..."
echo "-------------------------"

# Check if services are responding
services=(
    "ML Engine:8001:/health"
    "External Data:8002:/health"  
    "Alert Engine:8003:/health"
    "Authentication:8004:/health"
    "Dashboard:8005:/health"
    "Reporting:8006:/health"
    "Monitoring:8007:/health"
)

for service in "${services[@]}"; do
    IFS=':' read -r name port endpoint <<< "$service"
    
    if curl -s -f "http://localhost:$port$endpoint" >/dev/null 2>&1; then
        echo "✅ $name ($port) - HEALTHY"
    else
        echo "❌ $name ($port) - NOT RESPONDING"
    fi
done

echo ""
echo "🌐 Frontend Demo Pages Available:"
echo "---------------------------------"
echo "📊 Main Dashboard:           file:///$(pwd)/REAL_AI_DEMO.html"
echo "🧠 ML Engine Demo:           file:///$(pwd)/ML_AI_DEMO.html" 
echo "🔐 Authentication Demo:      file:///$(pwd)/AUTH_RBAC_DEMO.html"
echo "📊 Reporting Demo:           file:///$(pwd)/REPORTING_AUDIT_DEMO.html"
echo "🔍 Performance Monitor:      file:///$(pwd)/PERFORMANCE_MONITORING_DEMO.html"
echo "🧪 API Testing Dashboard:    file:///$(pwd)/API_TESTING_DEMO.html"

echo ""
echo "📖 API Documentation:        file:///$(pwd)/API_DOCUMENTATION.md"

echo ""
echo "🔧 Service Management:"
echo "----------------------"
echo "View logs:     tail -f /tmp/retailai_*_*.log"
echo "Stop all:      pkill -f 'python3.*_api.py'"
echo "List processes: ps aux | grep -E '800[1-7]|_api.py'"

echo ""
echo "🎉 RetailAI Platform is now running!"
echo "Open the HTML demo files in your browser to interact with the system."
echo "========================================"