#!/usr/bin/env python3
"""
Reporting API Server
FastAPI interface for automated reporting and audit trails
"""

import sys
import os
sys.path.append('/home/vboxuser/Documents/140509_ai-oh-wip/140509_01/src/services/reporting')

from fastapi import FastAPI, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional, Any
import psycopg2
import redis
import asyncio
import logging
from datetime import datetime, timedelta
import uvicorn
import json
from pathlib import Path

from reporting_service import (
    ReportingService, ReportType, ReportFormat, ReportFrequency,
    ReportSchedule, ReportExecution, AuditTrail
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="RetailAI Reporting API",
    description="Automated reporting and comprehensive audit trails",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Global services
reporting_service = None
redis_client = None

# Pydantic models
class CreateReportScheduleRequest(BaseModel):
    report_type: str
    frequency: str
    recipients: List[EmailStr]
    format: str
    filters: Optional[Dict[str, Any]] = None

class GenerateReportRequest(BaseModel):
    report_type: str
    format: str
    filters: Optional[Dict[str, Any]] = None

class AuditTrailRequest(BaseModel):
    entity_type: str
    entity_id: str
    action: str
    changes: Optional[Dict[str, Any]] = None
    compliance_tags: Optional[List[str]] = None

class ReportScheduleResponse(BaseModel):
    schedule_id: str
    report_type: str
    frequency: str
    recipients: List[str]
    format: str
    is_active: bool
    created_at: datetime
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

class ReportExecutionResponse(BaseModel):
    execution_id: str
    report_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    output_path: Optional[str] = None
    file_size_mb: Optional[float] = None
    error_message: Optional[str] = None

class AuditTrailResponse(BaseModel):
    audit_id: str
    user_id: str
    entity_type: str
    entity_id: str
    action: str
    changes: Dict[str, Any]
    timestamp: datetime
    success: bool
    compliance_tags: List[str]

class AuditSearchRequest(BaseModel):
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100

def get_db_connection():
    """Get database connection."""
    try:
        return psycopg2.connect(
            host='localhost',
            port=5432,
            database='retailai',
            user='postgres',
            password='postgres'
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Mock user authentication for demo purposes."""
    # In production, this would validate JWT token and return user info
    return "demo_user"

@app.on_event("startup")
async def startup_event():
    """Initialize reporting service on startup."""
    global reporting_service, redis_client
    
    logger.info("🚀 Initializing Reporting API Server...")
    
    try:
        # Initialize Redis (with auth if set)
        redis_client = get_redis_client()
        
        # Initialize reporting service
        db_conn = get_db_connection()
        reporting_service = ReportingService(db_conn, redis_client)
        
        logger.info("✅ Reporting service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    
    try:
        # Check database
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        db_conn.close()
        
        # Check Redis
        redis_client.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "redis": "connected",
            "reporting_service": "initialized" if reporting_service else "not_initialized"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reports/schedules", status_code=status.HTTP_201_CREATED)
async def create_report_schedule(
    request: CreateReportScheduleRequest,
    user_id: str = Depends(get_current_user)
) -> Dict[str, str]:
    """Create a new report schedule."""
    
    try:
        if not reporting_service:
            raise HTTPException(status_code=500, detail="Reporting service not initialized")
        
        # Validate enums
        try:
            report_type = ReportType(request.report_type)
            frequency = ReportFrequency(request.frequency)
            format_type = ReportFormat(request.format)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")
        
        schedule_id = await reporting_service.create_report_schedule(
            report_type=report_type,
            frequency=frequency,
            recipients=[str(email) for email in request.recipients],
            format=format_type,
            filters=request.filters,
            user_id=user_id
        )
        
        return {
            "schedule_id": schedule_id,
            "message": "Report schedule created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create report schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/schedules")
async def get_report_schedules(
    user_id: str = Depends(get_current_user)
) -> List[ReportScheduleResponse]:
    """Get all report schedules."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        cursor.execute("""
            SELECT schedule_id, report_type, frequency, recipients, format, 
                   filters, is_active, created_at, last_run, next_run
            FROM report_schedules
            ORDER BY created_at DESC
        """)
        
        schedules = []
        for row in cursor.fetchall():
            schedules.append(ReportScheduleResponse(
                schedule_id=row[0],
                report_type=row[1],
                frequency=row[2],
                recipients=row[3],
                format=row[4],
                is_active=row[6],
                created_at=row[7],
                last_run=row[8],
                next_run=row[9]
            ))
        
        cursor.close()
        db_conn.close()
        
        return schedules
        
    except Exception as e:
        logger.error(f"Failed to get report schedules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reports/generate")
async def generate_report(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
) -> Dict[str, str]:
    """Generate a report on-demand."""
    
    try:
        if not reporting_service:
            raise HTTPException(status_code=500, detail="Reporting service not initialized")
        
        # Validate enums
        try:
            report_type = ReportType(request.report_type)
            format_type = ReportFormat(request.format)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")
        
        # Generate report in background
        async def generate_report_task():
            try:
                output_path = await reporting_service.generate_report(
                    report_type=report_type,
                    format=format_type,
                    filters=request.filters
                )
                logger.info(f"✅ On-demand report generated: {output_path}")
            except Exception as e:
                logger.error(f"Background report generation failed: {e}")
        
        background_tasks.add_task(generate_report_task)
        
        return {
            "message": "Report generation started",
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start report generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/executions")
async def get_report_executions(
    limit: int = 50,
    user_id: str = Depends(get_current_user)
) -> List[ReportExecutionResponse]:
    """Get report execution history."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        cursor.execute("""
            SELECT execution_id, report_type, status, started_at, completed_at,
                   output_path, file_size_mb, error_message
            FROM report_executions
            ORDER BY started_at DESC
            LIMIT %s
        """, (limit,))
        
        executions = []
        for row in cursor.fetchall():
            executions.append(ReportExecutionResponse(
                execution_id=row[0],
                report_type=row[1],
                status=row[2],
                started_at=row[3],
                completed_at=row[4],
                output_path=row[5],
                file_size_mb=row[6],
                error_message=row[7]
            ))
        
        cursor.close()
        db_conn.close()
        
        return executions
        
    except Exception as e:
        logger.error(f"Failed to get report executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/download/{execution_id}")
async def download_report(
    execution_id: str,
    user_id: str = Depends(get_current_user)
):
    """Download generated report."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        cursor.execute("""
            SELECT output_path, report_type, status
            FROM report_executions
            WHERE execution_id = %s
        """, (execution_id,))
        
        result = cursor.fetchone()
        cursor.close()
        db_conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="Report execution not found")
        
        output_path, report_type, status = result
        
        if status != 'completed':
            raise HTTPException(status_code=400, detail=f"Report not ready (status: {status})")
        
        if not output_path or not os.path.exists(output_path):
            raise HTTPException(status_code=404, detail="Report file not found")
        
        filename = os.path.basename(output_path)
        return FileResponse(
            path=output_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit/log")
async def log_audit_trail(
    request: Request,
    audit_data: AuditTrailRequest,
    user_id: str = Depends(get_current_user)
) -> Dict[str, str]:
    """Log audit trail entry."""
    
    try:
        if not reporting_service:
            raise HTTPException(status_code=500, detail="Reporting service not initialized")
        
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        audit_id = await reporting_service.log_audit_trail(
            user_id=user_id,
            entity_type=audit_data.entity_type,
            entity_id=audit_data.entity_id,
            action=audit_data.action,
            changes=audit_data.changes,
            ip_address=client_ip,
            user_agent=user_agent,
            compliance_tags=audit_data.compliance_tags
        )
        
        return {
            "audit_id": audit_id,
            "message": "Audit trail logged successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to log audit trail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit/search")
async def search_audit_trails(
    search_request: AuditSearchRequest,
    user_id: str = Depends(get_current_user)
) -> List[AuditTrailResponse]:
    """Search audit trails with filters."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        # Build dynamic query
        where_conditions = []
        params = []
        
        if search_request.entity_type:
            where_conditions.append("entity_type = %s")
            params.append(search_request.entity_type)
        
        if search_request.entity_id:
            where_conditions.append("entity_id = %s")
            params.append(search_request.entity_id)
        
        if search_request.user_id:
            where_conditions.append("user_id = %s")
            params.append(search_request.user_id)
        
        if search_request.action:
            where_conditions.append("action = %s")
            params.append(search_request.action)
        
        if search_request.start_date:
            where_conditions.append("timestamp >= %s")
            params.append(search_request.start_date)
        
        if search_request.end_date:
            where_conditions.append("timestamp <= %s")
            params.append(search_request.end_date)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        params.append(search_request.limit)
        
        query = f"""
            SELECT audit_id, user_id, entity_type, entity_id, action, changes,
                   timestamp, success, compliance_tags
            FROM audit_trails
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        cursor.execute(query, params)
        
        audit_trails = []
        for row in cursor.fetchall():
            audit_trails.append(AuditTrailResponse(
                audit_id=row[0],
                user_id=row[1],
                entity_type=row[2],
                entity_id=row[3],
                action=row[4],
                changes=json.loads(row[5]) if row[5] else {},
                timestamp=row[6],
                success=row[7],
                compliance_tags=row[8] if row[8] else []
            ))
        
        cursor.close()
        db_conn.close()
        
        return audit_trails
        
    except Exception as e:
        logger.error(f"Failed to search audit trails: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit/summary")
async def get_audit_summary(
    days: int = 30,
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get audit trail summary statistics."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Total audit entries
        cursor.execute("""
            SELECT COUNT(*) FROM audit_trails WHERE timestamp >= %s
        """, (start_date,))
        total_entries = cursor.fetchone()[0]
        
        # Entries by action
        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM audit_trails
            WHERE timestamp >= %s
            GROUP BY action
            ORDER BY count DESC
        """, (start_date,))
        actions_summary = dict(cursor.fetchall())
        
        # Entries by entity type
        cursor.execute("""
            SELECT entity_type, COUNT(*) as count
            FROM audit_trails
            WHERE timestamp >= %s
            GROUP BY entity_type
            ORDER BY count DESC
        """, (start_date,))
        entities_summary = dict(cursor.fetchall())
        
        # Top users by activity
        cursor.execute("""
            SELECT user_id, COUNT(*) as count
            FROM audit_trails
            WHERE timestamp >= %s
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 10
        """, (start_date,))
        top_users = dict(cursor.fetchall())
        
        # Failed operations
        cursor.execute("""
            SELECT COUNT(*) FROM audit_trails 
            WHERE timestamp >= %s AND success = FALSE
        """, (start_date,))
        failed_operations = cursor.fetchone()[0]
        
        # Compliance-related entries
        cursor.execute("""
            SELECT unnest(compliance_tags) as tag, COUNT(*) as count
            FROM audit_trails
            WHERE timestamp >= %s AND array_length(compliance_tags, 1) > 0
            GROUP BY tag
            ORDER BY count DESC
        """, (start_date,))
        compliance_summary = dict(cursor.fetchall())
        
        cursor.close()
        db_conn.close()
        
        return {
            "period_days": days,
            "total_entries": total_entries,
            "failed_operations": failed_operations,
            "success_rate": ((total_entries - failed_operations) / total_entries * 100) if total_entries > 0 else 0,
            "actions_summary": actions_summary,
            "entities_summary": entities_summary,
            "top_users": top_users,
            "compliance_summary": compliance_summary,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get audit summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/types")
async def get_report_types():
    """Get available report types."""
    
    return {
        "report_types": [
            {"value": rt.value, "description": rt.value.replace("_", " ").title()}
            for rt in ReportType
        ],
        "formats": [
            {"value": rf.value, "description": rf.value.upper()}
            for rf in ReportFormat
        ],
        "frequencies": [
            {"value": rf.value, "description": rf.value.replace("_", " ").title()}
            for rf in ReportFrequency
        ]
    }

@app.delete("/api/reports/schedules/{schedule_id}")
async def delete_report_schedule(
    schedule_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a report schedule."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        cursor.execute("""
            DELETE FROM report_schedules WHERE schedule_id = %s
        """, (schedule_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Report schedule not found")
        
        self.db.commit()
        cursor.close()
        db_conn.close()
        
        return {"message": "Report schedule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete report schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("📊 Starting Reporting API Server")
    print("📈 Automated reporting and scheduling")
    print("🔍 Comprehensive audit trails")
    print("📋 Compliance and data governance")
    print("🌐 API available at: http://localhost:8006")
    
    uvicorn.run(app, host="0.0.0.0", port=8006)
def get_redis_client() -> redis.Redis:
    """Create Redis client using REDIS_URL or host/password envs."""
    url = os.getenv("REDIS_URL")
    if url:
        try:
            return redis.from_url(url)
        except Exception:
            pass
    password = os.getenv("REDIS_PASSWORD")
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    return redis.Redis(host=host, port=port, db=db, password=password)
