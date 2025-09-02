# Manufacturing Quality Control AI Vision System - Deployment Guide

## Quick Start (One Command)

```bash
./scripts/setup.sh
```

This will automatically:
- Check system requirements
- Set up Python environment
- Install dependencies
- Initialize computer vision models
- Create project structure
- Configure environment

## Deployment Options

### 1. 🐳 Docker (Recommended)

**Single Container:**
```bash
docker build -t manufacturing-ai-vision .
docker run -p 8000:8000 -p 3000:80 manufacturing-ai-vision
```

**Multi-Service with Docker Compose:**
```bash
docker-compose up -d
```

Access:
- Web Interface: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 2. ☸️ Kubernetes

**Deploy to cluster:**
```bash
kubectl apply -f k8s/
```

**Check status:**
```bash
kubectl get pods -n manufacturing-ai
kubectl logs -f deployment/manufacturing-ai-app -n manufacturing-ai
```

### 3. 🐍 Python Development

**Manual setup:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 src/models/train.py
uvicorn src.api.main:app --reload
```

## CI/CD Pipeline

The project includes GitHub Actions workflow for:
- ✅ Automated testing (Python 3.9, 3.10, 3.11)
- 🔒 Security scanning with Trivy
- 🏗️ Docker image building and pushing
- 🚀 Automated deployment to staging/production
- 📊 Performance testing
- 📢 Slack notifications

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=postgresql://user:password@localhost/quality_control
JWT_SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
LOG_LEVEL=INFO
MODEL_PATH=data/models/
```

## Production Checklist

- [ ] Update JWT_SECRET_KEY in production
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS certificates
- [ ] Configure monitoring and logging
- [ ] Set up database backups
- [ ] Configure resource limits
- [ ] Set up health checks
- [ ] Configure auto-scaling

## Monitoring & Observability

**Health Checks:**
- API: `GET /api/health`
- Database: Automatic PostgreSQL health check
- Model: Model inference endpoint
- Frontend: HTTP 200 response

**Logs Location:**
- Container: `/app/logs/`
- Host: `./logs/`

**Metrics:**
- Application metrics via FastAPI
- Container metrics via Docker/Kubernetes
- Custom business metrics in dashboard

## Troubleshooting

**Common Issues:**

1. **Port conflicts:**
   ```bash
   docker-compose down
   lsof -ti:8000 | xargs kill -9
   ```

2. **Database initialization:**
   ```bash
   python scripts/setup.py
   ```

3. **Permission issues:**
   ```bash
   chmod +x scripts/*.sh
   sudo chown -R $USER:$USER .
   ```

4. **Memory issues:**
   ```bash
   docker system prune -a
   ```

## Scaling

**Horizontal Scaling:**
- Kubernetes: `kubectl scale deployment manufacturing-ai-app --replicas=5 -n manufacturing-ai`
- Docker Swarm: `docker service scale manufacturing-ai_app=5`

**Vertical Scaling:**
- Update resource limits in k8s/deployment.yaml
- Modify Docker Compose resource constraints

## Security

**Container Security:**
- Non-root user execution
- Minimal base image (python:3.9-slim)
- Security scanning in CI/CD
- Read-only filesystem where possible

**Application Security:**
- JWT authentication
- CORS configuration
- Input validation
- SQL injection prevention

## Backup & Recovery

**Automated Backups:**
- Database: Daily PostgreSQL backups (7-day retention)
- Models: Versioned model artifacts
- Logs: Rotated and archived
- Configuration: Version controlled

**Recovery:**
```bash
cp backups/quality_control_YYYYMMDD_HHMMSS.sql data/
psql quality_control < backups/quality_control_YYYYMMDD_HHMMSS.sql
docker-compose restart
```
