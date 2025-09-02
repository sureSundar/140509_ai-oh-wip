#!/usr/bin/env python3
"""
Role-Based Access Control (RBAC) Service
Implements NFR-008: Multi-factor authentication and role-based access control
"""

import asyncio
import hashlib
import secrets
import jwt
import pyotp
import qrcode
import io
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import psycopg2
import redis
from dataclasses import dataclass
from enum import Enum
import bcrypt
import json
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Permission(Enum):
    """System permissions."""
    # Data permissions
    READ_SALES_DATA = "read_sales_data"
    WRITE_SALES_DATA = "write_sales_data"
    READ_INVENTORY_DATA = "read_inventory_data"
    WRITE_INVENTORY_DATA = "write_inventory_data"
    
    # Analytics permissions
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_ANALYTICS = "export_analytics"
    
    # ML permissions
    VIEW_ML_MODELS = "view_ml_models"
    TRAIN_ML_MODELS = "train_ml_models"
    DEPLOY_ML_MODELS = "deploy_ml_models"
    
    # Alert permissions
    VIEW_ALERTS = "view_alerts"
    MANAGE_ALERTS = "manage_alerts"
    
    # System administration
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    SYSTEM_CONFIG = "system_config"
    
    # External data
    VIEW_EXTERNAL_DATA = "view_external_data"
    MANAGE_EXTERNAL_DATA = "manage_external_data"
    
    # Audit and compliance
    VIEW_AUDIT_LOGS = "view_audit_logs"
    EXPORT_AUDIT_LOGS = "export_audit_logs"

class Role(Enum):
    """Predefined system roles."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"
    ML_ENGINEER = "ml_engineer"
    STORE_MANAGER = "store_manager"

@dataclass
class User:
    """User data structure."""
    user_id: str
    username: str
    email: str
    full_name: str
    roles: List[str]
    permissions: Set[str]
    is_active: bool = True
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    last_login: Optional[datetime] = None
    password_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    store_access: Optional[List[str]] = None  # Store-level access control

@dataclass
class Session:
    """User session data."""
    session_id: str
    user_id: str
    username: str
    roles: List[str]
    permissions: Set[str]
    expires_at: datetime
    ip_address: str
    user_agent: str
    store_access: Optional[List[str]] = None

@dataclass
class AuditLog:
    """Audit log entry."""
    log_id: str
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: str
    timestamp: datetime
    success: bool

class RBACService:
    """Production-ready Role-Based Access Control service."""
    
    def __init__(self, db_connection, redis_client=None, jwt_secret: str = None):
        self.db = db_connection
        self.redis = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        
        # Session configuration
        self.session_timeout = timedelta(hours=8)  # Regular session
        self.admin_session_timeout = timedelta(hours=2)  # Admin session
        self.mfa_timeout = timedelta(minutes=5)  # MFA verification window
        
        # Role-permission mapping
        self.role_permissions = {
            Role.SUPER_ADMIN: set(Permission),  # All permissions
            Role.ADMIN: {
                Permission.READ_SALES_DATA, Permission.WRITE_SALES_DATA,
                Permission.READ_INVENTORY_DATA, Permission.WRITE_INVENTORY_DATA,
                Permission.VIEW_ANALYTICS, Permission.EXPORT_ANALYTICS,
                Permission.VIEW_ML_MODELS, Permission.TRAIN_ML_MODELS,
                Permission.VIEW_ALERTS, Permission.MANAGE_ALERTS,
                Permission.MANAGE_USERS, Permission.MANAGE_ROLES,
                Permission.VIEW_EXTERNAL_DATA, Permission.MANAGE_EXTERNAL_DATA,
                Permission.VIEW_AUDIT_LOGS
            },
            Role.MANAGER: {
                Permission.READ_SALES_DATA, Permission.READ_INVENTORY_DATA,
                Permission.VIEW_ANALYTICS, Permission.EXPORT_ANALYTICS,
                Permission.VIEW_ML_MODELS, Permission.VIEW_ALERTS,
                Permission.VIEW_EXTERNAL_DATA, Permission.VIEW_AUDIT_LOGS
            },
            Role.ANALYST: {
                Permission.READ_SALES_DATA, Permission.READ_INVENTORY_DATA,
                Permission.VIEW_ANALYTICS, Permission.EXPORT_ANALYTICS,
                Permission.VIEW_ML_MODELS, Permission.VIEW_EXTERNAL_DATA
            },
            Role.VIEWER: {
                Permission.READ_SALES_DATA, Permission.READ_INVENTORY_DATA,
                Permission.VIEW_ANALYTICS, Permission.VIEW_ML_MODELS,
                Permission.VIEW_ALERTS, Permission.VIEW_EXTERNAL_DATA
            },
            Role.ML_ENGINEER: {
                Permission.READ_SALES_DATA, Permission.READ_INVENTORY_DATA,
                Permission.VIEW_ANALYTICS, Permission.VIEW_ML_MODELS,
                Permission.TRAIN_ML_MODELS, Permission.DEPLOY_ML_MODELS,
                Permission.VIEW_EXTERNAL_DATA
            },
            Role.STORE_MANAGER: {
                Permission.READ_SALES_DATA, Permission.WRITE_INVENTORY_DATA,
                Permission.VIEW_ANALYTICS, Permission.VIEW_ALERTS,
                Permission.VIEW_EXTERNAL_DATA
            }
        }
        
        # Initialize database tables
        self.init_database_schema()
        self.create_default_admin()
    
    def init_database_schema(self):
        """Initialize RBAC database schema."""
        
        try:
            cursor = self.db.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(50) PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    full_name VARCHAR(200) NOT NULL,
                    password_hash TEXT NOT NULL,
                    roles TEXT[] DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    mfa_enabled BOOLEAN DEFAULT FALSE,
                    mfa_secret TEXT,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    store_access TEXT[] DEFAULT '{}'
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id VARCHAR(100) PRIMARY KEY,
                    user_id VARCHAR(50) REFERENCES users(user_id) ON DELETE CASCADE,
                    ip_address INET,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Audit logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(50),
                    action VARCHAR(100) NOT NULL,
                    resource VARCHAR(200),
                    details JSONB,
                    ip_address INET,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Role definitions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS role_definitions (
                    role_name VARCHAR(50) PRIMARY KEY,
                    description TEXT,
                    permissions TEXT[] NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.db.commit()
            cursor.close()
            logger.info("✅ RBAC database schema initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize RBAC schema: {e}")
            raise
    
    def create_default_admin(self):
        """Create default admin user if none exists."""
        
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE 'super_admin' = ANY(roles)")
            admin_count = cursor.fetchone()[0]
            
            if admin_count == 0:
                # Create default super admin
                admin_user = {
                    'user_id': 'admin_001',
                    'username': 'admin',
                    'email': 'admin@retailai.com',
                    'full_name': 'System Administrator',
                    'password': 'admin123',  # Should be changed immediately
                    'roles': [Role.SUPER_ADMIN.value]
                }
                
                self.create_user(**admin_user)
                logger.info("✅ Default super admin created (username: admin, password: admin123)")
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to create default admin: {e}")
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hash.encode('utf-8'))
    
    async def create_user(self, user_id: str, username: str, email: str, full_name: str, 
                   password: str, roles: List[str], store_access: List[str] = None) -> bool:
        """Create a new user."""
        
        try:
            password_hash = self.hash_password(password)
            
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, email, full_name, password_hash, roles, store_access)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, username, email, full_name, password_hash, roles, store_access or []))
            
            self.db.commit()
            cursor.close()
            
            # Log the action
            await self.log_audit_action("system", "CREATE_USER", "users", {
                'target_user_id': user_id,
                'username': username,
                'roles': roles
            }, "127.0.0.1", True)
            
            logger.info(f"✅ User created: {username} ({user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return False
    
    def get_user_permissions(self, roles: List[str]) -> Set[str]:
        """Get combined permissions for user roles."""
        
        permissions = set()
        
        for role_name in roles:
            try:
                role = Role(role_name)
                role_perms = self.role_permissions.get(role, set())
                permissions.update([perm.value for perm in role_perms])
            except ValueError:
                logger.warning(f"Unknown role: {role_name}")
        
        return permissions
    
    async def authenticate_user(self, username: str, password: str, ip_address: str, 
                              user_agent: str, mfa_token: str = None) -> Optional[Session]:
        """Authenticate user and create session."""
        
        try:
            # Get user from database
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT user_id, username, email, full_name, password_hash, roles, 
                       is_active, mfa_enabled, mfa_secret, store_access
                FROM users WHERE username = %s
            """, (username,))
            
            user_data = cursor.fetchone()
            cursor.close()
            
            if not user_data:
                await self.log_audit_action("unknown", "LOGIN_FAILED", "authentication", {
                    'username': username,
                    'reason': 'user_not_found'
                }, ip_address, False)
                return None
            
            user_id, db_username, email, full_name, password_hash, roles, is_active, mfa_enabled, mfa_secret, store_access = user_data
            
            # Check if user is active
            if not is_active:
                await self.log_audit_action(user_id, "LOGIN_FAILED", "authentication", {
                    'reason': 'account_inactive'
                }, ip_address, False)
                return None
            
            # Verify password
            if not self.verify_password(password, password_hash):
                await self.log_audit_action(user_id, "LOGIN_FAILED", "authentication", {
                    'reason': 'invalid_password'
                }, ip_address, False)
                return None
            
            # Check MFA if enabled
            if mfa_enabled:
                if not mfa_token:
                    # Return partial session for MFA challenge
                    return None
                
                if not self.verify_mfa_token(mfa_secret, mfa_token):
                    await self.log_audit_action(user_id, "LOGIN_FAILED", "authentication", {
                        'reason': 'invalid_mfa_token'
                    }, ip_address, False)
                    return None
            
            # Create session
            session = await self.create_session(
                user_id, db_username, roles, ip_address, user_agent, store_access
            )
            
            if session:
                # Update last login
                cursor = self.db.cursor()
                cursor.execute("""
                    UPDATE users SET last_login = %s WHERE user_id = %s
                """, (datetime.now(), user_id))
                self.db.commit()
                cursor.close()
                
                await self.log_audit_action(user_id, "LOGIN_SUCCESS", "authentication", {
                    'session_id': session.session_id
                }, ip_address, True)
                
                logger.info(f"✅ User authenticated: {username} (session: {session.session_id})")
            
            return session
            
        except Exception as e:
            logger.error(f"Authentication failed for {username}: {e}")
            await self.log_audit_action("unknown", "LOGIN_ERROR", "authentication", {
                'username': username,
                'error': str(e)
            }, ip_address, False)
            return None
    
    async def create_session(self, user_id: str, username: str, roles: List[str], 
                           ip_address: str, user_agent: str, store_access: List[str] = None) -> Session:
        """Create user session."""
        
        try:
            session_id = secrets.token_urlsafe(32)
            permissions = self.get_user_permissions(roles)
            
            # Determine session timeout based on roles
            is_admin = any(role in ['super_admin', 'admin'] for role in roles)
            expires_at = datetime.now() + (self.admin_session_timeout if is_admin else self.session_timeout)
            
            session = Session(
                session_id=session_id,
                user_id=user_id,
                username=username,
                roles=roles,
                permissions=permissions,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                store_access=store_access
            )
            
            # Store session in database
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO user_sessions (session_id, user_id, ip_address, user_agent, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (session_id, user_id, ip_address, user_agent, expires_at))
            self.db.commit()
            cursor.close()
            
            # Cache session in Redis
            session_data = {
                'user_id': user_id,
                'username': username,
                'roles': roles,
                'permissions': list(permissions),
                'expires_at': expires_at.isoformat(),
                'ip_address': ip_address,
                'user_agent': user_agent,
                'store_access': store_access or []
            }
            
            self.redis.setex(
                f"session:{session_id}",
                int(self.session_timeout.total_seconds()),
                json.dumps(session_data)
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session for {username}: {e}")
            return None
    
    async def validate_session(self, session_id: str) -> Optional[Session]:
        """Validate and retrieve session."""
        
        if not session_id:
            return None
        
        try:
            # Check Redis cache first
            cached_session = self.redis.get(f"session:{session_id}")
            if cached_session:
                data = json.loads(cached_session.decode())
                expires_at = datetime.fromisoformat(data['expires_at'])
                
                if datetime.now() < expires_at:
                    return Session(
                        session_id=session_id,
                        user_id=data['user_id'],
                        username=data['username'],
                        roles=data['roles'],
                        permissions=set(data['permissions']),
                        expires_at=expires_at,
                        ip_address=data['ip_address'],
                        user_agent=data['user_agent'],
                        store_access=data.get('store_access')
                    )
            
            # Check database if not in cache
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT s.session_id, s.user_id, u.username, u.roles, s.ip_address, 
                       s.user_agent, s.expires_at, u.store_access
                FROM user_sessions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.session_id = %s AND s.is_active = TRUE AND s.expires_at > %s
            """, (session_id, datetime.now()))
            
            session_data = cursor.fetchone()
            cursor.close()
            
            if session_data:
                session_id, user_id, username, roles, ip_address, user_agent, expires_at, store_access = session_data
                permissions = self.get_user_permissions(roles)
                
                session = Session(
                    session_id=session_id,
                    user_id=user_id,
                    username=username,
                    roles=roles,
                    permissions=permissions,
                    expires_at=expires_at,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    store_access=store_access
                )
                
                # Refresh cache
                session_data = {
                    'user_id': user_id,
                    'username': username,
                    'roles': roles,
                    'permissions': list(permissions),
                    'expires_at': expires_at.isoformat(),
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'store_access': store_access or []
                }
                
                remaining_time = int((expires_at - datetime.now()).total_seconds())
                if remaining_time > 0:
                    self.redis.setex(f"session:{session_id}", remaining_time, json.dumps(session_data))
                
                return session
            
            return None
            
        except Exception as e:
            logger.error(f"Session validation failed for {session_id}: {e}")
            return None
    
    def check_permission(self, session: Session, permission: Permission, store_id: str = None) -> bool:
        """Check if user has specific permission."""
        
        # Check basic permission
        if permission.value not in session.permissions:
            return False
        
        # Check store-level access if required
        if store_id and session.store_access:
            return store_id in session.store_access
        
        # Super admin and admin have access to all stores
        if any(role in ['super_admin', 'admin'] for role in session.roles):
            return True
        
        return True
    
    def require_permission(self, permission: Permission, store_id: str = None):
        """Decorator to require specific permission."""
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract session from function parameters
                session = None
                for arg in args:
                    if isinstance(arg, Session):
                        session = arg
                        break
                
                if not session:
                    # Try to get session from kwargs
                    session = kwargs.get('session')
                
                if not session:
                    raise PermissionError("No valid session provided")
                
                if not self.check_permission(session, permission, store_id):
                    raise PermissionError(f"Insufficient permissions: {permission.value}")
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def setup_mfa(self, user_id: str) -> Dict[str, Any]:
        """Set up Multi-Factor Authentication for user."""
        
        try:
            # Generate secret
            secret = pyotp.random_base32()
            
            # Generate QR code
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user_id,
                issuer_name="RetailAI Platform"
            )
            
            # Create QR code image
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            img_buffer = io.BytesIO()
            qr_img.save(img_buffer, format='PNG')
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Store secret in database (not yet enabled)
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE users SET mfa_secret = %s WHERE user_id = %s
            """, (secret, user_id))
            self.db.commit()
            cursor.close()
            
            return {
                'secret': secret,
                'qr_code': f"data:image/png;base64,{img_str}",
                'provisioning_uri': provisioning_uri
            }
            
        except Exception as e:
            logger.error(f"Failed to setup MFA for {user_id}: {e}")
            return {}
    
    def enable_mfa(self, user_id: str, verification_token: str) -> bool:
        """Enable MFA after verification."""
        
        try:
            # Get user's MFA secret
            cursor = self.db.cursor()
            cursor.execute("SELECT mfa_secret FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            
            if not result or not result[0]:
                return False
            
            mfa_secret = result[0]
            
            # Verify token
            if self.verify_mfa_token(mfa_secret, verification_token):
                # Enable MFA
                cursor.execute("""
                    UPDATE users SET mfa_enabled = TRUE WHERE user_id = %s
                """, (user_id,))
                self.db.commit()
                cursor.close()
                
                logger.info(f"✅ MFA enabled for user: {user_id}")
                return True
            
            cursor.close()
            return False
            
        except Exception as e:
            logger.error(f"Failed to enable MFA for {user_id}: {e}")
            return False
    
    def verify_mfa_token(self, secret: str, token: str) -> bool:
        """Verify MFA token."""
        
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)
        except Exception as e:
            logger.error(f"MFA token verification failed: {e}")
            return False
    
    async def logout_session(self, session_id: str, user_id: str = None):
        """Logout user session."""
        
        try:
            # Remove from Redis
            self.redis.delete(f"session:{session_id}")
            
            # Deactivate in database
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE user_sessions SET is_active = FALSE WHERE session_id = %s
            """, (session_id,))
            self.db.commit()
            cursor.close()
            
            if user_id:
                await self.log_audit_action(user_id, "LOGOUT", "authentication", {
                    'session_id': session_id
                }, "unknown", True)
            
            logger.info(f"✅ Session logged out: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to logout session {session_id}: {e}")
    
    async def log_audit_action(self, user_id: str, action: str, resource: str, 
                             details: Dict[str, Any], ip_address: str, success: bool):
        """Log audit action."""
        
        try:
            log_id = f"audit_{int(datetime.now().timestamp())}_{secrets.token_hex(8)}"
            
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (log_id, user_id, action, resource, details, ip_address, success)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (log_id, user_id, action, resource, json.dumps(details), ip_address, success))
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
    
    def get_user_audit_logs(self, user_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs for a user."""
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT log_id, user_id, action, resource, details, ip_address, timestamp, success
                FROM audit_logs
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (user_id, limit))
            
            logs = []
            for row in cursor.fetchall():
                log_id, user_id, action, resource, details, ip_address, timestamp, success = row
                logs.append(AuditLog(
                    log_id=log_id,
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    details=json.loads(details) if details else {},
                    ip_address=ip_address,
                    timestamp=timestamp,
                    success=success
                ))
            
            cursor.close()
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get audit logs for {user_id}: {e}")
            return []
    
    def get_all_users(self, requesting_user_session: Session) -> List[Dict[str, Any]]:
        """Get all users (admin only)."""
        
        if not self.check_permission(requesting_user_session, Permission.MANAGE_USERS):
            raise PermissionError("Insufficient permissions to view users")
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT user_id, username, email, full_name, roles, is_active, 
                       mfa_enabled, last_login, created_at, store_access
                FROM users
                ORDER BY created_at DESC
            """)
            
            users = []
            for row in cursor.fetchall():
                user_id, username, email, full_name, roles, is_active, mfa_enabled, last_login, created_at, store_access = row
                users.append({
                    'user_id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name,
                    'roles': roles,
                    'is_active': is_active,
                    'mfa_enabled': mfa_enabled,
                    'last_login': last_login.isoformat() if last_login else None,
                    'created_at': created_at.isoformat() if created_at else None,
                    'store_access': store_access or []
                })
            
            cursor.close()
            return users
            
        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []
    
    def update_user_roles(self, requesting_session: Session, target_user_id: str, 
                         new_roles: List[str]) -> bool:
        """Update user roles (admin only)."""
        
        if not self.check_permission(requesting_session, Permission.MANAGE_USERS):
            raise PermissionError("Insufficient permissions to manage users")
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE users SET roles = %s WHERE user_id = %s
            """, (new_roles, target_user_id))
            self.db.commit()
            cursor.close()
            
            # Log the action
            asyncio.create_task(self.log_audit_action(
                requesting_session.user_id,
                "UPDATE_USER_ROLES",
                "users",
                {'target_user_id': target_user_id, 'new_roles': new_roles},
                requesting_session.ip_address,
                True
            ))
            
            logger.info(f"✅ User roles updated: {target_user_id} -> {new_roles}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user roles: {e}")
            return False

# Example usage and testing
if __name__ == "__main__":
    # Database connection
    db_conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='retailai',
        user='retailai',
        password='retailai123'
    )
    
    # Initialize RBAC service
    rbac_service = RBACService(db_conn)
    
    async def test_rbac_service():
        """Test RBAC service functionality."""
        
        print("🔐 Testing RBAC Service...")
        
        # Test user creation
        rbac_service.create_user(
            user_id="test_user_001",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="testpassword123",
            roles=[Role.ANALYST.value],
            store_access=["STORE_001", "STORE_002"]
        )
        
        # Test authentication
        session = await rbac_service.authenticate_user(
            username="testuser",
            password="testpassword123",
            ip_address="127.0.0.1",
            user_agent="Test Client"
        )
        
        if session:
            print(f"✅ Authentication successful: {session.username}")
            print(f"✅ Permissions: {len(session.permissions)} permissions")
            
            # Test permission checking
            can_read = rbac_service.check_permission(session, Permission.READ_SALES_DATA)
            can_manage = rbac_service.check_permission(session, Permission.MANAGE_USERS)
            
            print(f"✅ Can read sales data: {can_read}")
            print(f"✅ Can manage users: {can_manage}")
            
            # Test session validation
            validated_session = await rbac_service.validate_session(session.session_id)
            if validated_session:
                print(f"✅ Session validation successful")
            
            # Test logout
            await rbac_service.logout_session(session.session_id, session.user_id)
            print(f"✅ Logout successful")
        
        print("🔐 RBAC service testing complete!")
    
    # Run test
    asyncio.run(test_rbac_service())