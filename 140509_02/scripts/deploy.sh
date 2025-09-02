#!/bin/bash
# RetailAI Deployment Script

set -e

echo "🚀 Deploying RetailAI Inventory Optimization System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
}

# Parse command line arguments
ENVIRONMENT=${1:-local}
VALID_ENVIRONMENTS=("local" "staging" "production")

if [[ ! " ${VALID_ENVIRONMENTS[@]} " =~ " ${ENVIRONMENT} " ]]; then
    print_error "Invalid environment: ${ENVIRONMENT}"
    echo "Valid environments: ${VALID_ENVIRONMENTS[@]}"
    exit 1
fi

print_header "Deploying to ${ENVIRONMENT} environment..."

case $ENVIRONMENT in
    "local")
        print_status "Starting local development environment..."
        
        # Create necessary directories
        mkdir -p data logs backups
        
        # Start services with Docker Compose
        docker-compose up -d
        
        # Wait for services to be ready
        print_status "Waiting for services to start..."
        sleep 10
        
        # Health check
        if curl -f http://localhost:8000/api/inventory > /dev/null 2>&1; then
            print_status "✅ API service is healthy"
        else
            print_warning "⚠️  API service health check failed"
        fi
        
        if curl -f http://localhost:3000 > /dev/null 2>&1; then
            print_status "✅ Frontend service is healthy"
        else
            print_warning "⚠️  Frontend service health check failed"
        fi
        
        print_status "🎉 Local deployment completed!"
        echo ""
        echo "Access URLs:"
        echo "  - API: http://localhost:8000"
        echo "  - Frontend: http://localhost:3000"
        echo "  - API Docs: http://localhost:8000/docs"
        echo ""
        echo "To stop: docker-compose down"
        ;;
        
    "staging")
        print_status "Deploying to staging environment..."
        
        # Check if kubectl is available
        if ! command -v kubectl &> /dev/null; then
            print_error "kubectl is not installed. Please install kubectl first."
            exit 1
        fi
        
        # Apply Kubernetes manifests
        kubectl apply -f k8s/namespace.yaml
        kubectl apply -f k8s/configmap.yaml
        kubectl apply -f k8s/pvc.yaml
        kubectl apply -f k8s/deployment.yaml
        
        # Wait for deployment to be ready
        kubectl rollout status deployment/retailai-app -n retailai --timeout=300s
        
        print_status "✅ Staging deployment completed!"
        ;;
        
    "production")
        print_status "Deploying to production environment..."
        
        # Additional safety checks for production
        read -p "Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
        if [[ $confirm != "yes" ]]; then
            print_warning "Production deployment cancelled."
            exit 0
        fi
        
        # Check if kubectl is available
        if ! command -v kubectl &> /dev/null; then
            print_error "kubectl is not installed. Please install kubectl first."
            exit 1
        fi
        
        # Apply Kubernetes manifests with production settings
        kubectl apply -f k8s/namespace.yaml
        kubectl apply -f k8s/configmap.yaml
        kubectl apply -f k8s/pvc.yaml
        kubectl apply -f k8s/deployment.yaml
        
        # Wait for deployment to be ready
        kubectl rollout status deployment/retailai-app -n retailai --timeout=600s
        
        # Run post-deployment tests
        print_status "Running post-deployment health checks..."
        kubectl get pods -n retailai
        
        print_status "✅ Production deployment completed!"
        ;;
esac

print_status "Deployment logs can be found in ./logs/"
print_status "For troubleshooting, run: docker-compose logs -f (local) or kubectl logs -f deployment/retailai-app -n retailai (k8s)"
