# 🚀 RetailAI Installation Guide

## Prerequisites
- Ubuntu 20.04+ or similar Linux
- Python 3.8+
- PostgreSQL 12+
- Redis 5+
- 4GB+ RAM, 10GB+ storage

## Quick Install
```bash
# Clone/extract submission
cd hackathon-submission/

# One-click deployment
chmod +x deploy.sh
./deploy.sh

# Access system
open http://localhost:3000/RETAILAI_MAIN_DASHBOARD.html
```

## Manual Installation

### 1. Install System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip postgresql redis-server

# Start services
sudo systemctl start postgresql redis-server
```

### 2. Setup Database  
```bash
sudo -u postgres createdb retailai
sudo -u postgres createuser retailai
sudo -u postgres psql -c "ALTER USER retailai WITH PASSWORD 'retailai123';"
```

### 3. Install Python Dependencies
```bash
pip3 install fastapi uvicorn psycopg2-binary redis pandas numpy scikit-learn
```

### 4. Load Demo Data
```bash  
python3 src/demo/load-demo-data.py
```

### 5. Start Services
```bash
./start_retailai_services.sh
```

### 6. Verify Installation
```bash
curl http://localhost:8003/health  # Alert Engine
curl http://localhost:8004/health  # Authentication
```

## Troubleshooting

### Port Conflicts
```bash  
./stop_retailai_services.sh
pkill -f python3
./start_retailai_services.sh
```

### Database Issues
```bash
sudo -u postgres dropdb retailai
sudo -u postgres createdb retailai
python3 src/demo/load-demo-data.py
```

### Service Logs
```bash
tail -f /tmp/retailai_*_*.log
```

## Demo Accounts
- admin/admin123 (Super Admin)
- manager/manager123 (Store Manager) 
- analyst/analyst123 (Data Analyst)
- demo/demo123 (Read-only Viewer)
