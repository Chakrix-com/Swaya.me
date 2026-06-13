"""
API endpoints for image uploads
"""
import logging
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form, Request
from sqlalchemy.orm import Session
from typing import Literal

logger = logging.getLogger(__name__)

from persistence.database import get_db
from core.auth.dependencies import get_current_user
from core.auth.schemas import UserResponse
from core.storage import ImageService
from persistence.models.quiz import Quiz, Question
from persistence.models.core import Tenant


router = APIRouter(prefix="/quizzes", tags=["uploads"])


@router.post("/{quiz_id}/upload-image")
async def upload_image(
    quiz_id: int,
    request: Request,  # Added to get base URL
    file: UploadFile = File(...),
    image_type: Literal["question", "option_a", "option_b", "option_c", "option_d"] = Form(...),
    question_id: int = Form(None),  # Optional - if None, use temp storage
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an image for a question or answer option
    
    Supports two modes:
    1. Permanent upload (question_id provided) - saves to permanent location
    2. Temporary upload (no question_id) - saves to temp location for later move
    
    Args:
        quiz_id: Quiz ID
        file: Image file (max 2MB, jpg/png/gif/webp)
        image_type: Type of image (question or option_a/b/c/d)
        question_id: Question ID (optional - if None, uses temp storage)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        {
            "image_url": "/api/uploads/...",
            "image_type": "question",
            "is_temp": false,
            "temp_key": null
        }
    """
    # Get quiz and verify ownership
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this quiz")
    
    # Mode 1: Temporary upload (no question_id)
    if question_id is None:
        try:
            relative_path, temp_key = ImageService.save_temp_image(
                file=file,
                tenant_id=current_user.tenant_id,
                quiz_id=quiz_id,
                image_type=image_type
            )
            
            # Build absolute URL
            base_url = str(request.base_url).rstrip('/')
            absolute_url = f"{base_url}/api/uploads/temp/{relative_path}"
            
            return {
                "image_url": absolute_url,
                "image_type": image_type,
                "is_temp": True,
                "temp_key": temp_key
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to upload temp image quiz_id=%s", quiz_id)
            raise HTTPException(status_code=500, detail="Failed to upload image. Please try again.")
    
    # Mode 2: Permanent upload (question_id provided)
    # Get question and verify it belongs to this quiz
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.quiz_id == quiz_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Save image
    try:
        relative_path = ImageService.save_image(
            file=file,
            tenant_id=current_user.tenant_id,
            quiz_id=quiz_id,
            image_type=f"{image_type}_{question_id}"
        )
        
        # Update database based on image type
        if image_type == "question":
            # Delete old question image if exists
            if question.question_image_url:
                ImageService.delete_image(question.question_image_url)
            
            question.question_image_url = relative_path
        else:
            # For options, update the option_images JSON field
            if not question.option_images:
                question.option_images = {}
            
            # Delete old option image if exists
            option_key = image_type.split("_")[1].upper()  # "option_a" -> "A"
            if option_key in question.option_images:
                ImageService.delete_image(question.option_images[option_key])
            
            question.option_images[option_key] = relative_path
        
        db.commit()
        db.refresh(question)
        
        # Return full absolute URL for frontend
        base_url = str(request.base_url).rstrip('/')
        absolute_url = f"{base_url}/api/uploads/images/{relative_path}"
        
        return {
            "image_url": absolute_url,
            "image_type": image_type,
            "is_temp": False,
            "temp_key": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Failed to upload image quiz_id=%s question_id=%s", quiz_id, question_id)
        raise HTTPException(status_code=500, detail="Failed to upload image. Please try again.")


@router.post("/{quiz_id}/questions/{question_id}/move-temp-images")
async def move_temp_images(
    quiz_id: int,
    question_id: int,
    temp_images: list[dict],  # [{"temp_key": "...", "image_type": "..."}]
    request: Request,  # Added for absolute URLs
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Move temporary images to permanent location after question creation
    
    Args:
        quiz_id: Quiz ID
        question_id: Question ID (newly created)
        temp_images: List of temp image metadata
        current_user: Authenticated user
        db: Database session
        
    Returns:
        {
            "question_image_url": "...",
            "option_images": {"A": "...", "B": "..."}
        }
    """
    from pydantic import BaseModel
    
    class TempImageMove(BaseModel):
        temp_key: str
        image_type: Literal["question", "option_a", "option_b", "option_c", "option_d"]
    
    # Validate input
    try:
        temp_image_list = [TempImageMove(**img) for img in temp_images]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid temp_images format: {str(e)}")
    
    # Get quiz and verify ownership
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this quiz")
    
    # Get question
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.quiz_id == quiz_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Move each temp image to permanent location
    try:
        base_url = str(request.base_url).rstrip('/')
        question_image_url = None
        option_images = {}
        
        for temp_img in temp_image_list:
            permanent_path = ImageService.move_temp_to_permanent(
                temp_key=temp_img.temp_key,
                tenant_id=current_user.tenant_id,
                quiz_id=quiz_id,
                question_id=question_id,
                image_type=temp_img.image_type
            )
            
            # Update question record
            if temp_img.image_type == "question":
                question.question_image_url = permanent_path
                question_image_url = f"{base_url}/api/uploads/images/{permanent_path}"
            else:
                if not question.option_images:
                    question.option_images = {}
                
                option_key = temp_img.image_type.split("_")[1].upper()
                question.option_images[option_key] = permanent_path
                option_images[option_key] = f"{base_url}/api/uploads/images/{permanent_path}"
        
        db.commit()
        db.refresh(question)
        
        return {
            "question_image_url": question_image_url,
            "option_images": option_images
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Failed to move temp images quiz_id=%s question_id=%s", quiz_id, question_id)
        raise HTTPException(status_code=500, detail="Failed to process images. Please try again.")



@router.delete("/{quiz_id}/image")
async def delete_image(
    quiz_id: int,
    image_type: Literal["question", "option_a", "option_b", "option_c", "option_d"],
    temp_key: str = None,  # For deleting temp images
    question_id: int = None,  # For deleting permanent images
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an image (temp or permanent)
    
    Args:
        quiz_id: Quiz ID
        image_type: Type of image to delete
        temp_key: Temp filename (if deleting temp image)
        question_id: Question ID (if deleting permanent image)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        {"message": "Image deleted successfully"}
    """
    # Get quiz and verify ownership
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if quiz.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this quiz")
    
    # Delete temp image
    if temp_key:
        success = ImageService.delete_temp_image(
            temp_key=temp_key,
            tenant_id=current_user.tenant_id,
            quiz_id=quiz_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Temp image not found")
        
        return {"message": "Temp image deleted successfully"}
    
    # Delete permanent image
    if question_id is None:
        raise HTTPException(status_code=400, detail="Either temp_key or question_id must be provided")
    
    # Get question
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.quiz_id == quiz_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    try:
        if image_type == "question":
            if question.question_image_url:
                ImageService.delete_image(question.question_image_url)
                question.question_image_url = None
            else:
                raise HTTPException(status_code=404, detail="No question image to delete")
        else:
            option_key = image_type.split("_")[1].upper()
            if question.option_images and option_key in question.option_images:
                ImageService.delete_image(question.option_images[option_key])
                del question.option_images[option_key]
                # Trigger JSON update
                question.option_images = dict(question.option_images)
            else:
                raise HTTPException(status_code=404, detail=f"No image for {image_type}")
        
        db.commit()
        
        return {"message": "Image deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Failed to delete image quiz_id=%s question_id=%s", quiz_id, question_id)
        raise HTTPException(status_code=500, detail="Failed to delete image. Please try again.")
