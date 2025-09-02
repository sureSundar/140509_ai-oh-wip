"""Model management endpoints."""
import os
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import get_current_active_user, get_db
from config import settings
from models.model import Model as DBModel
from schemas.model import Model, ModelCreate, ModelUpdate
from services.model_service import ModelService
from utils.file_utils import save_upload_file
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
model_service = ModelService()

@router.get("/", response_model=List[Model])
async def list_models(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve models.
    """
    models = db.query(DBModel).offset(skip).limit(limit).all()
    return models

@router.post("/", response_model=Model, status_code=status.HTTP_201_CREATED)
async def create_model(
    *,
    db: Session = Depends(get_db),
    model_in: ModelCreate,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Create new model.
    """
    # Check if model with same name exists
    db_model = db.query(DBModel).filter(DBModel.name == model_in.name).first()
    if db_model:
        raise HTTPException(
            status_code=400,
            detail="A model with this name already exists",
        )
    
    # Create new model
    db_model = DBModel(
        name=model_in.name,
        description=model_in.description,
        version=model_in.version,
        framework=model_in.framework,
        path=model_in.path,
        is_active=model_in.is_active,
        created_by=current_user.id,
    )
    
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return db_model

@router.put("/{model_id}", response_model=Model)
async def update_model(
    *,
    db: Session = Depends(get_db),
    model_id: int,
    model_in: ModelUpdate,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Update a model.
    """
    db_model = db.query(DBModel).filter(DBModel.id == model_id).first()
    if not db_model:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )
    
    # Update model fields
    update_data = model_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_model, field, value)
    
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return db_model

@router.get("/{model_id}", response_model=Model)
async def get_model(
    *,
    db: Session = Depends(get_db),
    model_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Get model by ID.
    """
    db_model = db.query(DBModel).filter(DBModel.id == model_id).first()
    if not db_model:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )
    
    return db_model

@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    *,
    db: Session = Depends(get_db),
    model_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Delete a model.
    """
    db_model = db.query(DBModel).filter(DBModel.id == model_id).first()
    if not db_model:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )
    
    # Delete model file if it exists
    if db_model.path and os.path.exists(db_model.path):
        try:
            os.remove(db_model.path)
        except Exception as e:
            logger.error(f"Error deleting model file {db_model.path}: {str(e)}")
    
    db.delete(db_model)
    db.commit()
    
    return {"ok": True}

@router.post("/{model_id}/upload", response_model=Model)
async def upload_model_file(
    *,
    db: Session = Depends(get_db),
    model_id: int,
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Upload a model file.
    """
    db_model = db.query(DBModel).filter(DBModel.id == model_id).first()
    if not db_model:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )
    
    # Save the uploaded file
    upload_dir = os.path.join(settings.UPLOAD_FOLDER, "models")
    success, result = save_upload_file(file, upload_dir)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {result}",
        )
    
    # Update model path
    db_model.path = result
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return db_model

@router.post("/{model_id}/activate")
async def activate_model(
    *,
    db: Session = Depends(get_db),
    model_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Activate a model for predictions.
    """
    return model_service.activate_model(db, model_id, current_user)

@router.get("/active/model", response_model=Model)
async def get_active_model(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Get the currently active model.
    """
    return model_service.get_active_model(db)
