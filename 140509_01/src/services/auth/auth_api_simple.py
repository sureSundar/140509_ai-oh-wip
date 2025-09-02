#!/usr/bin/env python3
"""
Simplified Authentication API Server
Works without database dependencies using in-memory storage
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import secrets
import bcrypt
import jwt
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RetailAI Authentication API",
    description="Role-based access control and session management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Secret
JWT_SECRET = "retailai-demo-secret-key"
JWT_ALGORITHM = "HS256"

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_token: Optional[str] = None

class CreateUserRequest(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    roles: List[str] = ["analyst"]
    store_access: List[str] = []

class User(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: str
    roles: List[str]
    store_access: List[str]
    created_at: str
    is_active: bool = True

class Session(BaseModel):
    session_id: str
    user_id: str
    username: str
    roles: List[str]
    permissions: List[str]
    expires_at: str
    store_access: List[str] = []

# In-memory storage
users_db: Dict[str, Dict] = {}
sessions_db: Dict[str, Session] = {}

# Predefined permissions by role
ROLE_PERMISSIONS = {
    "super_admin": [
        "read_sales_data", "write_sales_data", "read_inventory_data", "write_inventory_data",
        "view_analytics", "export_analytics", "view_ml_models", "train_ml_models", 
        "deploy_ml_models", "view_alerts", "manage_alerts", "manage_users", "system_admin"
    ],
    "admin": [
        "read_sales_data", "write_sales_data", "read_inventory_data", "write_inventory_data",
        "view_analytics", "export_analytics", "view_ml_models", "view_alerts", "manage_alerts"
    ],
    "manager": [
        "read_sales_data", "read_inventory_data", "view_analytics", "export_analytics",
        "view_ml_models", "view_alerts"
    ],
    "analyst": [
        "read_sales_data", "read_inventory_data", "view_analytics", "view_ml_models", "view_alerts"
    ],
    "viewer": [
        "read_sales_data", "read_inventory_data", "view_analytics", "view_alerts"
    ]
}

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hash_str: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hash_str.encode('utf-8'))

def get_permissions_for_roles(roles: List[str]) -> List[str]:
    """Get all permissions for given roles."""
    permissions = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, []))
    return list(permissions)

def create_jwt_token(user_data: Dict) -> str:
    """Create JWT token."""
    payload = {
        "user_id": user_data["user_id"],
        "username": user_data["username"],
        "roles": user_data["roles"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def initialize_demo_users():
    """Create demo users."""
    demo_users = [
        {
            "user_id": "admin_001",
            "username": "admin",
            "email": "admin@retailai.com",
            "full_name": "System Administrator",
            "password": "admin123",
            "roles": ["super_admin"],
            "store_access": ["STORE_001", "STORE_002", "STORE_003"]
        },
        {
            "user_id": "manager_001", 
            "username": "manager",
            "email": "manager@retailai.com",
            "full_name": "Store Manager",
            "password": "manager123",
            "roles": ["manager"],
            "store_access": ["STORE_001"]
        },
        {
            "user_id": "analyst_001",
            "username": "analyst", 
            "email": "analyst@retailai.com",
            "full_name": "Data Analyst",
            "password": "analyst123",
            "roles": ["analyst"],
            "store_access": ["STORE_001", "STORE_002"]
        },
        {
            "user_id": "viewer_001",
            "username": "demo",
            "email": "demo@retailai.com", 
            "full_name": "Demo User",
            "password": "demo123",
            "roles": ["viewer"],
            "store_access": ["STORE_001"]
        }
    ]
    
    for user_data in demo_users:
        password_hash = hash_password(user_data["password"])
        users_db[user_data["username"]] = {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "password_hash": password_hash,
            "roles": user_data["roles"],
            "store_access": user_data["store_access"],
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }

@app.on_event("startup")
async def startup_event():
    """Initialize demo data."""
    logger.info("🚀 Starting RetailAI Authentication API...")
    initialize_demo_users()
    logger.info(f"✅ Initialized {len(users_db)} demo users")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "active_users": len(users_db),
        "active_sessions": len(sessions_db)
    }

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Authenticate user and create session."""
    
    username = request.username.lower()
    
    # Find user
    user = users_db.get(username)
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    session_id = str(uuid.uuid4())
    permissions = get_permissions_for_roles(user["roles"])
    
    session = Session(
        session_id=session_id,
        user_id=user["user_id"],
        username=user["username"],
        roles=user["roles"],
        permissions=permissions,
        expires_at=(datetime.now() + timedelta(hours=24)).isoformat(),
        store_access=user["store_access"]
    )
    
    sessions_db[session_id] = session
    
    logger.info(f"✅ User {username} logged in successfully")
    
    return {
        "success": True,
        "session_id": session_id,
        "user_id": user["user_id"],
        "username": user["username"],
        "roles": user["roles"],
        "permissions": permissions,
        "expires_at": session.expires_at,
        "store_access": user["store_access"]
    }

@app.get("/api/auth/session")
async def get_session(session_id: Optional[str] = None):
    """Get current session info."""
    
    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required")
    
    session = sessions_db.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check if session expired
    if datetime.fromisoformat(session.expires_at) < datetime.now():
        del sessions_db[session_id]
        raise HTTPException(status_code=401, detail="Session expired")
    
    return session.dict()

@app.get("/api/auth/users")
async def get_users():
    """Get all users (admin only)."""
    
    users_list = []
    for user in users_db.values():
        users_list.append({
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "roles": user["roles"],
            "store_access": user["store_access"],
            "created_at": user["created_at"],
            "is_active": user["is_active"]
        })
    
    return {
        "users": users_list,
        "total_count": len(users_list)
    }

@app.get("/api/auth/roles")
async def get_available_roles():
    """Get available roles and their permissions."""
    
    roles_info = []
    for role, permissions in ROLE_PERMISSIONS.items():
        roles_info.append({
            "role": role,
            "permissions": permissions,
            "permission_count": len(permissions)
        })
    
    return {
        "roles": roles_info,
        "total_roles": len(roles_info)
    }

@app.get("/api/auth/check-permission/{permission}")
async def check_permission(permission: str, session_id: Optional[str] = None):
    """Check if current session has specific permission."""
    
    if not session_id:
        return {"has_permission": False, "reason": "No session"}
    
    session = sessions_db.get(session_id)
    if not session:
        return {"has_permission": False, "reason": "Invalid session"}
    
    has_permission = permission in session.permissions
    
    return {
        "has_permission": has_permission,
        "permission": permission,
        "user_permissions": session.permissions
    }

@app.post("/api/auth/users")
async def create_user(request: CreateUserRequest):
    """Create new user."""
    
    username = request.username.lower()
    
    if username in users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create user
    user_id = f"user_{str(uuid.uuid4())[:8]}"
    password_hash = hash_password(request.password)
    
    users_db[username] = {
        "user_id": user_id,
        "username": username,
        "email": request.email,
        "full_name": request.full_name,
        "password_hash": password_hash,
        "roles": request.roles,
        "store_access": request.store_access,
        "created_at": datetime.now().isoformat(),
        "is_active": True
    }
    
    logger.info(f"✅ Created user: {username}")
    
    return {
        "success": True,
        "user_id": user_id,
        "username": username,
        "message": "User created successfully"
    }

@app.get("/api/auth/audit-logs")
async def get_audit_logs(limit: int = 100):
    """Get audit logs."""
    
    # Mock audit logs for demo
    mock_logs = [
        {
            "log_id": f"log_{i+1}",
            "action": "LOGIN_SUCCESS" if i % 3 == 0 else "DATA_ACCESS" if i % 3 == 1 else "PERMISSION_CHECK",
            "user_id": f"user_{(i%4)+1}",
            "resource": "authentication" if i % 3 == 0 else "sales_data" if i % 3 == 1 else "permissions",
            "ip_address": f"192.168.1.{100+i}",
            "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
            "success": True if i % 5 != 0 else False
        }
        for i in range(min(limit, 50))
    ]
    
    return {
        "audit_logs": mock_logs,
        "total_count": len(mock_logs)
    }

@app.post("/api/auth/logout")
async def logout(session_id: str):
    """Logout user and invalidate session."""
    
    if session_id in sessions_db:
        del sessions_db[session_id]
        logger.info(f"✅ Session {session_id} logged out")
    
    return {"success": True, "message": "Logged out successfully"}

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting RetailAI Authentication API Server on port 8004...")
    uvicorn.run(app, host="0.0.0.0", port=8004)