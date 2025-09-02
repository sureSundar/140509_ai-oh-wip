"""Prediction endpoints."""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import get_current_active_user, get_db
from config import settings
from models.prediction import Prediction as DBPrediction
from schemas.prediction import (
    Prediction,
    PredictionBatch,
    PredictionCreate,
    PredictionResult,
    PredictionUpdate,
)
from services.prediction_service import PredictionService
from utils.file_utils import is_file_allowed, save_upload_file
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
prediction_service = PredictionService()

@router.post("/", response_model=PredictionResult, status_code=status.HTTP_201_CREATED)
async def create_prediction(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Create a new prediction from an uploaded image.
    """
    # Check if the file is an allowed image type
    if not is_file_allowed(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )
    
    try:
        # Save the uploaded file temporarily
        upload_dir = os.path.join(settings.UPLOAD_FOLDER, "predictions")
        success, file_path = save_upload_file(file, upload_dir)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving file: {file_path}",
            )
        
        # Process the prediction
        result = await prediction_service.predict(file_path, current_user.id, db)
        
        # Clean up the temporary file
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Error deleting temporary file {file_path}: {str(e)}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error processing prediction: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing prediction: {str(e)}",
        )

@router.post("/batch", response_model=List[PredictionResult])
async def create_batch_predictions(
    *,
    db: Session = Depends(get_db),
    batch: PredictionBatch,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Create multiple predictions in a batch.
    """
    try:
        results = []
        for file_path in batch.file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue
                
            result = await prediction_service.predict(file_path, current_user.id, db)
            results.append(result)
        
        return results
    
    except Exception as e:
        logger.error(f"Error processing batch predictions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing batch predictions: {str(e)}",
        )

@router.get("/{prediction_id}", response_model=Prediction)
async def get_prediction(
    *,
    db: Session = Depends(get_db),
    prediction_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Get a prediction by ID.
    """
    db_prediction = db.query(DBPrediction).filter(DBPrediction.id == prediction_id).first()
    if not db_prediction:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found",
        )
    
    # Check if the user has permission to view this prediction
    if db_prediction.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return db_prediction

@router.get("/", response_model=List[Prediction])
async def list_predictions(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve predictions.
    """
    if current_user.is_superuser:
        predictions = db.query(DBPrediction).offset(skip).limit(limit).all()
    else:
        predictions = (
            db.query(DBPrediction)
            .filter(DBPrediction.user_id == current_user.id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    return predictions

@router.put("/{prediction_id}", response_model=Prediction)
async def update_prediction(
    *,
    db: Session = Depends(get_db),
    prediction_id: int,
    prediction_in: PredictionUpdate,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Update a prediction (e.g., to provide feedback on prediction accuracy).
    """
    db_prediction = db.query(DBPrediction).filter(DBPrediction.id == prediction_id).first()
    if not db_prediction:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found",
        )
    
    # Check if the user has permission to update this prediction
    if db_prediction.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Update prediction fields
    update_data = prediction_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_prediction, field, value)
    
    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    
    return db_prediction

@router.get("/stats/accuracy", response_model=dict)
async def get_accuracy_stats(
    *,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Get accuracy statistics for predictions.
    """
    return prediction_service.get_accuracy_stats(db, current_user)

@router.get("/stats/defect-types", response_model=dict)
async def get_defect_type_stats(
    *,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """
    Get statistics on defect types.
    """
    return prediction_service.get_defect_type_stats(db, current_user)
