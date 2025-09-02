#!/bin/bash

# Comprehensive Production Service Startup Script for 140509_01 Project
# Starts all 8 microservices with proper project integration

echo "🚀 Starting Complete 140509_01 Production Ecosystem"
echo "=================================================="

# Set project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRODUCTION_DIR="$PROJECT_ROOT/production"
LOGS_DIR="$PROJECT_ROOT/logs"

echo "📁 Project Root: $PROJECT_ROOT"
echo "🏭 Production Dir: $PRODUCTION_DIR"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Function to start a production service
start_service() {
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
        nohup python3 "$PRODUCTION_DIR/$service_file" > "$LOGS_DIR/${service_name,,}.log" 2>&1 &
        local pid=$!
        
        echo "   ✅ $service_name started (PID: $pid)"
        echo "   📋 Log: $LOGS_DIR/${service_name,,}.log"
        
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
    "inventory_service.py"
    "customer_service.py"
    "supply_chain_service.py"
    "financial_service.py"
    "operations_service.py"
    "marketing_service.py"
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
echo "🚀 Starting All Production Services..."
echo "-------------------------------------"

# Start all 8 microservices
start_service "ML_Engine" "ml_engine_production.py" 8001 "Production ML forecasting and analytics"
start_service "Inventory" "inventory_service.py" 8002 "Real-time inventory management and tracking"  
start_service "Customer" "customer_service.py" 8003 "Customer analytics and segmentation"
start_service "Authentication" "auth_service_production.py" 8004 "Enterprise RBAC and JWT authentication"
start_service "Supply_Chain" "supply_chain_service.py" 8005 "End-to-end supply chain visibility"
start_service "Financial" "financial_service.py" 8006 "Comprehensive financial analytics"
start_service "Operations" "operations_service.py" 8007 "Real-time operations monitoring"
start_service "Marketing" "marketing_service.py" 8008 "Digital marketing performance analytics"

echo ""
echo "⏳ Waiting for all services to fully initialize..."
sleep 8

echo ""
echo "🔍 Production Service Status Check..."
echo "------------------------------------"

# Check service status
services=(
    "ML_Engine:8001:/health"
    "Inventory:8002:/health"
    "Customer:8003:/health"
    "Authentication:8004:/health"
    "Supply_Chain:8005:/health"
    "Financial:8006:/health"
    "Operations:8007:/health"
    "Marketing:8008:/health"
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
echo "🌐 Complete Production API Ecosystem:"
echo "------------------------------------"
echo "🧠 ML Engine API:           http://localhost:8001"
echo "   📊 KPIs:                 http://localhost:8001/api/kpis"
echo "   🔮 Forecasting:          http://localhost:8001/api/forecast"
echo "   📈 Analysis:             http://localhost:8001/api/demo/run-analysis"
echo ""
echo "📦 Inventory Management:    http://localhost:8002"  
echo "   📋 Stock Levels:         http://localhost:8002/api/inventory"
echo "   ⚠️  Alerts:              http://localhost:8002/api/inventory/alerts"
echo "   🛒 Reorder Recommendations: http://localhost:8002/api/inventory/reorder-recommendations"
echo ""
echo "👥 Customer Analytics:      http://localhost:8003"
echo "   📊 Segments:             http://localhost:8003/api/customers/segments"  
echo "   🎯 Behavior:             http://localhost:8003/api/customers/behavior"
echo "   💎 Loyalty:              http://localhost:8003/api/customers/loyalty"
echo ""
echo "🔐 Authentication:          http://localhost:8004"
echo "   🔑 Login:                http://localhost:8004/api/auth/login"
echo "   👤 Users:                http://localhost:8004/api/auth/users"
echo "   📜 Audit Logs:           http://localhost:8004/api/auth/audit-logs"
echo ""
echo "🚚 Supply Chain:            http://localhost:8005"
echo "   📋 Overview:             http://localhost:8005/api/supply-chain/overview"
echo "   📦 Shipments:            http://localhost:8005/api/supply-chain/shipments"
echo "   ⚠️  Disruptions:         http://localhost:8005/api/supply-chain/disruptions"
echo ""
echo "💰 Financial Analytics:     http://localhost:8006"
echo "   📊 Overview:             http://localhost:8006/api/finance/overview"
echo "   📈 Revenue Analysis:     http://localhost:8006/api/finance/revenue-analysis"
echo "   💸 Cost Analysis:        http://localhost:8006/api/finance/cost-analysis"
echo ""
echo "⚙️ Operations Management:   http://localhost:8007"
echo "   📋 Overview:             http://localhost:8007/api/operations/overview"
echo "   👥 Workforce:            http://localhost:8007/api/operations/workforce"
echo "   ⚠️  Alerts:              http://localhost:8007/api/operations/alerts"
echo ""
echo "📢 Marketing Analytics:     http://localhost:8008"
echo "   📊 Overview:             http://localhost:8008/api/marketing/overview" 
echo "   🎯 Campaigns:            http://localhost:8008/api/marketing/campaigns"
echo "   👥 Audience:             http://localhost:8008/api/marketing/audience"
echo ""
echo "🎯 Frontend Application:"
echo "🌐 Integrated Business Demo: http://localhost:9000/INTEGRATED_BUSINESS_DEMO.html"
echo ""

echo "🧪 System Integration:"
echo "----------------------"
echo "📋 Run Integration Tests:   python3 production/integrated_tests.py"
echo "📂 View All Logs:          tail -f logs/*.log"
echo "📊 System Health:          curl http://localhost:800{1..8}/health"
echo ""

echo "🔧 Service Management:"
echo "----------------------"
echo "🛑 Stop All Services:       pkill -f 'production.*service'"
echo "📋 Check All Processes:     ps aux | grep 'production.*service'"
echo "📊 Monitor System:          htop"
echo ""

if [ "$all_healthy" = true ]; then
    echo "🎉 140509_01 COMPLETE PRODUCTION ECOSYSTEM IS READY!"
    echo "✅ All 8 microservices healthy and properly integrated"
    echo "🚀 Ready for comprehensive business demonstrations"
    echo ""
    echo "💡 Key Features Available:"
    echo "• Real-time business KPIs and analytics"
    echo "• AI-powered forecasting and predictions" 
    echo "• Complete inventory and supply chain visibility"
    echo "• Customer behavior analytics and segmentation"
    echo "• Financial reporting and budget analysis"
    echo "• Operations monitoring and workforce management"
    echo "• Marketing campaign performance and optimization"
    echo "• Enterprise-grade authentication and audit trails"
else
    echo "⚠️  140509_01 Production System started with some issues"
    echo "🔧 Some services may need attention"
    echo "📋 Check individual service logs for details"
fi

echo ""
echo "=================================================="
echo "🏭 140509_01 Complete Production System Running"