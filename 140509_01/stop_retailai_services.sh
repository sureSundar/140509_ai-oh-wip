#!/bin/bash

# RetailAI Platform - Service Shutdown Script
# Gracefully stops all microservices

echo "🛑 Stopping RetailAI Platform Services..."
echo "========================================="

# Stop all FastAPI services
echo "🔄 Stopping API services..."
pkill -f "python3.*_api.py" 2>/dev/null

# Stop any remaining Python services on our ports
ports=(8001 8002 8003 8004 8005 8006 8007)
for port in "${ports[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "🔄 Stopping service on port $port..."
        lsof -Pi :$port -sTCP:LISTEN -t | xargs kill -TERM 2>/dev/null || true
    fi
done

# Wait a moment for graceful shutdown
sleep 3

# Force kill any remaining processes
for port in "${ports[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Force stopping service on port $port..."
        lsof -Pi :$port -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    fi
done

echo ""
echo "🧹 Cleaning up log files..."
rm -f /tmp/retailai_*_*.log 2>/dev/null || true

echo ""
echo "🔍 Final status check..."
active_services=0
for port in "${ports[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "❌ Port $port still active"
        active_services=$((active_services + 1))
    else
        echo "✅ Port $port free"
    fi
done

if [ $active_services -eq 0 ]; then
    echo ""
    echo "✅ All RetailAI services stopped successfully!"
else
    echo ""
    echo "⚠️  $active_services services may still be running"
    echo "Use 'ps aux | grep python3' to check manually"
fi

echo "========================================="