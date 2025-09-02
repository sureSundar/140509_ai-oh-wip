"""Defect management endpoints."""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_active_user, get_db
from models.defect import Defect as DBDefect
from schemas.defect import Defect, DefectCreate, DefectUpdate
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/", response_model=List[Defect])
async def list_defects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve defects.
    """
    defects = db.query(DBDefect).offset(skip).limit(limit).all()
    return defects

@router.post("/", response_model=Defect, status_code=status.HTTP_201_CREATED)
async def create_defect(
    *,
    db: Session = Depends(get_db),
    defect_in: DefectCreate,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Create new defect type.
    """
    # Check if defect with same code exists
    db_defect = db.query(DBDefect).filter(DBDefect.code == defect_in.code).first()
    if db_defect:
        raise HTTPException(
            status_code=400,
            detail="A defect with this code already exists",
        )
    
    # Create new defect
    db_defect = DBDefect(
        code=defect_in.code,
        name=defect_in.name,
        description=defect_in.description,
        severity=defect_in.severity,
        category=defect_in.category,
        is_active=defect_in.is_active,
    )
    
    db.add(db_defect)
    db.commit()
    db.refresh(db_defect)
    
    return db_defect

@router.get("/{defect_id}", response_model=Defect)
async def get_defect(
    *,
    db: Session = Depends(get_db),
    defect_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Get defect by ID.
    """
    db_defect = db.query(DBDefect).filter(DBDefect.id == defect_id).first()
    if not db_defect:
        raise HTTPException(
            status_code=404,
            detail="Defect not found",
        )
    
    return db_defect

@router.put("/{defect_id}", response_model=Defect)
async def update_defect(
    *,
    db: Session = Depends(get_db),
    defect_id: int,
    defect_in: DefectUpdate,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Update a defect type.
    """
    db_defect = db.query(DBDefect).filter(DBDefect.id == defect_id).first()
    if not db_defect:
        raise HTTPException(
            status_code=404,
            detail="Defect not found",
        )
    
    # Check if code is being updated to an existing one
    if defect_in.code and defect_in.code != db_defect.code:
        existing_defect = db.query(DBDefect).filter(DBDefect.code == defect_in.code).first()
        if existing_defect:
            raise HTTPException(
                status_code=400,
                detail="A defect with this code already exists",
            )
    
    # Update defect fields
    update_data = defect_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_defect, field, value)
    
    db.add(db_defect)
    db.commit()
    db.refresh(db_defect)
    
    return db_defect

@router.delete("/{defect_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_defect(
    *,
    db: Session = Depends(get_db),
    defect_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Delete a defect type.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    db_defect = db.query(DBDefect).filter(DBDefect.id == defect_id).first()
    if not db_defect:
        raise HTTPException(
            status_code=404,
            detail="Defect not found",
        )
    
    # Check if defect is used in any predictions
    # from models.prediction import Prediction
    # prediction_count = db.query(Prediction).filter(Prediction.defect_id == defect_id).count()
    # if prediction_count > 0:
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Cannot delete defect type that is used in predictions",
    #     )
    
    db.delete(db_defect)
    db.commit()
    
    return {"ok": True}

@router.get("/categories/list", response_model=List[str])
async def list_defect_categories() -> Any:
    """
    Get list of available defect categories.
    """
    # This could be moved to a configuration or database table
    return [
        "surface",
        "structural",
        "color",
        "dimension",
        "finish",
        "assembly",
        "material",
        "other",
    ]

@router.get("/severity/levels", response_model=List[str])
async def list_severity_levels() -> Any:
    """
    Get list of available severity levels.
    """
    # This could be moved to a configuration or database table
    return [
        "critical",
        "high",
        "medium",
        "low",
        "cosmetic",
    ]
