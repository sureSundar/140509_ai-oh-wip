#!/usr/bin/env python3
"""
Production Authentication Service - Integrated into 140509_01 project
Enterprise-grade RBAC with proper project structure
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'auth'))

from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator, EmailStr
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import secrets
import bcrypt
import jwt
import uuid
import json
import uvicorn

# Configure logging to project directory
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auth_production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RetailAI Production Authentication",
    description="Enterprise-grade authentication integrated into 140509_01 project",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:9000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Production security configuration
JWT_SECRET = "retailai-140509-production-secret-key-2024"
JWT_ALGORITHM = "HS256"
security = HTTPBearer()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v.lower().strip()

class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    roles: List[str] = ["viewer"]
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:  # Relaxed for demo
            raise ValueError('Password must be at least 6 characters')
        return v

# Production role permissions
ROLE_PERMISSIONS = {
    "super_admin": {
        "permissions": [
            "read_sales_data", "write_sales_data", "read_inventory_data", "write_inventory_data",
            "view_analytics", "export_analytics", "view_ml_models", "train_ml_models", 
            "deploy_ml_models", "view_alerts", "manage_alerts", "manage_users", "system_admin",
            "view_audit_logs", "manage_system_settings", "access_all_stores"
        ],
        "description": "Full system access and administration"
    },
    "admin": {
        "permissions": [
            "read_sales_data", "write_sales_data", "read_inventory_data", "write_inventory_data",
            "view_analytics", "export_analytics", "view_ml_models", "view_alerts", "manage_alerts"
        ],
        "description": "Store administration and operations management"
    },
    "manager": {
        "permissions": [
            "read_sales_data", "read_inventory_data", "view_analytics", "export_analytics",
            "view_ml_models", "view_alerts"
        ],
        "description": "Department and team management"
    },
    "analyst": {
        "permissions": [
            "read_sales_data", "read_inventory_data", "view_analytics", "view_ml_models", "view_alerts"
        ],
        "description": "Data analysis and reporting"
    },
    "viewer": {
        "permissions": [
            "read_sales_data", "read_inventory_data", "view_analytics", "view_alerts"
        ],
        "description": "Read-only access to dashboards"
    }
}

# Production user management
class ProductionAuthManager:
    def __init__(self):
        self.users_db = {}
        self.sessions_db = {}
        self.audit_logs = []
        self.failed_attempts = {}
        
    def hash_password(self, password: str) -> str:
        """Production password hashing."""
        salt = bcrypt.gensalt(rounds=10)  # Balanced for production
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, hash_str: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hash_str.encode('utf-8'))

    def get_permissions_for_roles(self, roles: List[str]) -> List[str]:
        """Get all permissions for given roles."""
        permissions = set()
        for role in roles:
            permissions.update(ROLE_PERMISSIONS.get(role, {}).get("permissions", []))
        return list(permissions)

    def create_jwt_token(self, user_data: Dict, remember_me: bool = False) -> str:
        """Create production JWT token."""
        expiration = datetime.utcnow() + timedelta(days=7 if remember_me else 1)
        
        payload = {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "roles": user_data["roles"],
            "permissions": user_data.get("permissions", []),
            "exp": expiration,
            "iat": datetime.utcnow(),
            "iss": "retailai-140509-production"
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def verify_jwt_token(self, token: str) -> Dict:
        """Verify production JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def log_audit_event(self, event_type: str, user_id: str, details: Dict, ip_address: str = None):
        """Production audit logging."""
        audit_event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address or "unknown",
            "details": details,
            "project": "140509_01",
            "environment": "production"
        }
        
        self.audit_logs.append(audit_event)
        logger.info(f"AUDIT: {event_type} - User: {user_id} - IP: {ip_address}")

    def initialize_production_users(self):
        """Initialize production demo users."""
        demo_users = [
            {
                "user_id": "admin_140509_001",
                "username": "admin",
                "email": "admin@retailai-140509.com",
                "full_name": "Production Administrator",
                "password": "admin123",
                "roles": ["super_admin"],
                "store_access": ["ALL_STORES"]
            },
            {
                "user_id": "manager_140509_001", 
                "username": "manager",
                "email": "manager@retailai-140509.com",
                "full_name": "Production Manager",
                "password": "manager123",
                "roles": ["manager"],
                "store_access": ["STORE_001", "STORE_002"]
            },
            {
                "user_id": "analyst_140509_001",
                "username": "analyst",
                "email": "analyst@retailai-140509.com",
                "full_name": "Production Analyst",
                "password": "analyst123",
                "roles": ["analyst"],
                "store_access": ["STORE_001", "STORE_002", "STORE_003"]
            },
            {
                "user_id": "demo_140509_001",
                "username": "demo",
                "email": "demo@retailai-140509.com", 
                "full_name": "Production Demo User",
                "password": "demo123",
                "roles": ["viewer"],
                "store_access": ["STORE_001"]
            }
        ]
        
        for user_data in demo_users:
            password_hash = self.hash_password(user_data["password"])
            self.users_db[user_data["username"]] = {
                "user_id": user_data["user_id"],
                "username": user_data["username"],
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "password_hash": password_hash,
                "roles": user_data["roles"],
                "store_access": user_data["store_access"],
                "permissions": self.get_permissions_for_roles(user_data["roles"]),
                "created_at": datetime.utcnow().isoformat(),
                "last_login": None,
                "login_count": 0,
                "is_active": True,
                "project": "140509_01",
                "environment": "production"
            }

# Initialize production auth manager
auth_manager = ProductionAuthManager()

@app.on_event("startup")
async def startup_event():
    """Initialize production authentication system."""
    logger.info("🚀 Starting Production Authentication System...")
    
    # Create logs directory in project
    os.makedirs('logs', exist_ok=True)
    
    # Initialize users
    auth_manager.initialize_production_users()
    logger.info(f"✅ Initialized {len(auth_manager.users_db)} production users for 140509_01")
    
    logger.info("✅ Production Authentication System Ready")

@app.get("/health")
async def health_check():
    """Production health check with project information."""
    return {
        "status": "healthy",
        "service": "authentication-production",
        "version": "2.0.0",
        "project": "140509_01", 
        "timestamp": datetime.utcnow().isoformat(),
        "project_path": os.getcwd(),
        "components": {
            "users": len(auth_manager.users_db),
            "active_sessions": len(auth_manager.sessions_db),
            "audit_events": len(auth_manager.audit_logs)
        },
        "environment": "production"
    }

@app.post("/api/auth/login")
async def production_login(request: LoginRequest, client_request: Request):
    """Production login with comprehensive logging."""
    client_ip = client_request.client.host
    username = request.username
    
    try:
        # Find user
        user = auth_manager.users_db.get(username)
        if not user or not user["is_active"]:
            auth_manager.log_audit_event("LOGIN_FAILED", username, {"reason": "invalid_user", "ip": client_ip}, client_ip)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not auth_manager.verify_password(request.password, user["password_hash"]):
            auth_manager.log_audit_event("LOGIN_FAILED", username, {"reason": "invalid_password", "ip": client_ip}, client_ip)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create session
        session_id = str(uuid.uuid4())
        token = auth_manager.create_jwt_token(user, request.remember_me)
        
        # Store session
        session_data = {
            "session_id": session_id,
            "user_id": user["user_id"],
            "username": user["username"],
            "roles": user["roles"],
            "permissions": user["permissions"],
            "store_access": user["store_access"],
            "ip_address": client_ip,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7 if request.remember_me else 1)).isoformat()
        }
        
        auth_manager.sessions_db[session_id] = session_data
        
        # Update user stats
        auth_manager.users_db[username]["last_login"] = datetime.utcnow().isoformat()
        auth_manager.users_db[username]["login_count"] += 1
        
        # Log successful login
        auth_manager.log_audit_event("LOGIN_SUCCESS", user["user_id"], {
            "ip": client_ip, 
            "remember_me": request.remember_me,
            "session_id": session_id
        }, client_ip)
        
        logger.info(f"✅ Production login successful: {username} from {client_ip}")
        
        return {
            "success": True,
            "token": token,
            "session_id": session_id,
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "email": user["email"],
                "roles": user["roles"],
                "permissions": user["permissions"],
                "store_access": user["store_access"]
            },
            "expires_at": session_data["expires_at"],
            "project": "140509_01",
            "environment": "production"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Production login error: {e}")
        auth_manager.log_audit_event("LOGIN_ERROR", username, {"error": str(e), "ip": client_ip}, client_ip)
        raise HTTPException(status_code=500, detail="Authentication service error")

@app.get("/api/auth/users")
async def get_production_users():
    """Get production user list."""
    
    users_list = []
    for user in auth_manager.users_db.values():
        users_list.append({
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "roles": user["roles"],
            "store_access": user["store_access"],
            "created_at": user["created_at"],
            "last_login": user["last_login"],
            "login_count": user["login_count"],
            "is_active": user["is_active"]
        })
    
    return {
        "users": users_list,
        "total_count": len(users_list),
        "project": "140509_01",
        "environment": "production"
    }

@app.get("/api/auth/roles")
async def get_production_roles():
    """Get production role definitions."""
    
    roles_info = []
    for role, config in ROLE_PERMISSIONS.items():
        roles_info.append({
            "role": role,
            "description": config["description"],
            "permissions": config["permissions"],
            "permission_count": len(config["permissions"])
        })
    
    return {
        "roles": roles_info,
        "total_roles": len(roles_info),
        "project": "140509_01"
    }

@app.get("/api/auth/audit-logs")
async def get_production_audit_logs(limit: int = 100):
    """Get production audit logs."""
    
    # Sort by timestamp (newest first) and limit
    sorted_logs = sorted(auth_manager.audit_logs, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    return {
        "audit_logs": sorted_logs,
        "total_count": len(auth_manager.audit_logs),
        "project": "140509_01",
        "environment": "production",
        "available_event_types": list(set(log["event_type"] for log in auth_manager.audit_logs))
    }

@app.post("/api/auth/logout")
async def production_logout(session_id: str):
    """Production logout with session cleanup."""
    
    try:
        if session_id in auth_manager.sessions_db:
            session = auth_manager.sessions_db[session_id]
            user_id = session.get("user_id", "unknown")
            
            # Remove session
            del auth_manager.sessions_db[session_id]
            
            # Log logout
            auth_manager.log_audit_event("LOGOUT", user_id, {"session_id": session_id})
            
            logger.info(f"✅ Production logout: session {session_id}")
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {"success": True, "message": "Logged out"}  # Always return success for security

if __name__ == "__main__":
    logger.info("🚀 Starting Production Authentication Service on port 8004...")
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")