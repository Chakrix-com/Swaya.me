"""
Image upload and management service
"""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException
from PIL import Image, ImageOps
import io


class ImageService:
    """Service for handling image uploads, validation, and storage"""
    
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
    ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    OPTIMIZED_MAX_DIMENSION = 1920  # Resize oversized images to screen-friendly dimensions
    
    UPLOAD_BASE_DIR = Path(__file__).parents[2] / "uploads" / "images"
    TEMP_BASE_DIR = Path(__file__).parents[2] / "uploads" / "temp"
    
    @classmethod
    def validate_image(cls, file: UploadFile) -> bool:
        """
        Validate uploaded image file
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If validation fails
        """
        # Check MIME type
        if file.content_type not in cls.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(cls.ALLOWED_MIME_TYPES)}"
            )
        
        # Check file extension
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        ext = file.filename.split(".")[-1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension. Allowed: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if size > cls.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {cls.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        if size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Validate image using Pillow
        try:
            contents = file.file.read()
            file.file.seek(0)  # Reset for later use
            
            img = Image.open(io.BytesIO(contents))
            img.verify()
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        return True

    @classmethod
    def _prepare_image_bytes(cls, file: UploadFile) -> tuple[bytes, str]:
        """
        Validate and normalize image bytes for storage.
        Oversized images are resized instead of rejected.
        """
        cls.validate_image(file)

        ext = file.filename.split(".")[-1].lower()
        save_format = {
            "jpg": "JPEG",
            "jpeg": "JPEG",
            "png": "PNG",
            "gif": "GIF",
            "webp": "WEBP",
        }.get(ext, "PNG")

        try:
            original_bytes = file.file.read()
            file.file.seek(0)

            img = Image.open(io.BytesIO(original_bytes))
            img = ImageOps.exif_transpose(img)

            # Preserve animated GIFs as-is.
            if save_format == "GIF" and getattr(img, "is_animated", False):
                return original_bytes, ext

            if (
                img.width > cls.OPTIMIZED_MAX_DIMENSION
                or img.height > cls.OPTIMIZED_MAX_DIMENSION
            ):
                resampling = getattr(Image, "Resampling", Image).LANCZOS
                img.thumbnail((cls.OPTIMIZED_MAX_DIMENSION, cls.OPTIMIZED_MAX_DIMENSION), resampling)

            if save_format in {"JPEG", "WEBP"} and img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            output = io.BytesIO()
            save_kwargs = {}
            if save_format == "JPEG":
                save_kwargs = {"quality": 85, "optimize": True}
            elif save_format == "PNG":
                save_kwargs = {"optimize": True}
            elif save_format == "WEBP":
                save_kwargs = {"quality": 82, "method": 6}
            elif save_format == "GIF":
                save_kwargs = {"optimize": True}

            img.save(output, format=save_format, **save_kwargs)
            return output.getvalue(), ext
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image file")
    
    @classmethod
    def save_image(
        cls,
        file: UploadFile,
        tenant_id: int,
        quiz_id: int,
        image_type: str
    ) -> str:
        """
        Save uploaded image to filesystem
        
        Args:
            file: FastAPI UploadFile object
            tenant_id: Tenant ID for isolation
            quiz_id: Quiz ID for organization
            image_type: Type of image (e.g., "question", "option_a")
            
        Returns:
            Relative path to saved image (for storing in DB)
        """
        # Validate and optimize image bytes
        optimized_bytes, ext = cls._prepare_image_bytes(file)
        
        # Create directory structure: {tenant_id}/{quiz_id}/
        upload_dir = cls.UPLOAD_BASE_DIR / str(tenant_id) / str(quiz_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        unique_id = uuid.uuid4().hex[:12]
        filename = f"{image_type}_{unique_id}.{ext}"
        
        file_path = upload_dir / filename
        
        # Save file
        try:
            with open(file_path, "wb") as f:
                f.write(optimized_bytes)
            
            # Set permissions (readable by nginx/web server)
            os.chmod(file_path, 0o644)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")
        finally:
            file.file.close()
        
        # Return relative path (for DB storage and URL generation)
        relative_path = f"{tenant_id}/{quiz_id}/{filename}"
        return relative_path
    
    @classmethod
    def delete_image(cls, image_path: str) -> bool:
        """
        Delete image from filesystem
        
        Args:
            image_path: Relative path to image (e.g., "1/5/question_abc123.jpg")
            
        Returns:
            True if deleted, False if not found
        """
        if not image_path:
            return False
        
        full_path = cls.UPLOAD_BASE_DIR / image_path
        
        try:
            if full_path.exists() and full_path.is_file():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    @classmethod
    def save_temp_image(
        cls,
        file: UploadFile,
        tenant_id: int,
        quiz_id: int,
        image_type: str
    ) -> tuple[str, str]:
        """
        Save uploaded image to temporary location (before question created)
        
        Args:
            file: FastAPI UploadFile object
            tenant_id: Tenant ID for isolation
            quiz_id: Quiz ID for organization
            image_type: Type of image (e.g., "question", "option_a")
            
        Returns:
            Tuple of (relative_url_path, temp_key) for moving later
        """
        # Validate and optimize image bytes
        optimized_bytes, ext = cls._prepare_image_bytes(file)
        
        # Create temp directory structure: {tenant_id}/{quiz_id}/
        temp_dir = cls.TEMP_BASE_DIR / str(tenant_id) / str(quiz_id)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique temp filename
        unique_id = uuid.uuid4().hex[:12]
        filename = f"temp_{image_type}_{unique_id}.{ext}"
        
        file_path = temp_dir / filename
        
        # Save file
        try:
            with open(file_path, "wb") as f:
                f.write(optimized_bytes)
            
            # Set permissions
            os.chmod(file_path, 0o644)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save temp image: {str(e)}")
        finally:
            file.file.close()
        
        # Return relative path for URL and temp_key for moving
        relative_path = f"{tenant_id}/{quiz_id}/{filename}"
        temp_key = filename
        return relative_path, temp_key
    
    @classmethod
    def move_temp_to_permanent(
        cls,
        temp_key: str,
        tenant_id: int,
        quiz_id: int,
        question_id: int,
        image_type: str
    ) -> str:
        """
        Move temporary image to permanent location
        
        Args:
            temp_key: Temporary filename (e.g., "temp_question_abc123.jpg")
            tenant_id: Tenant ID
            quiz_id: Quiz ID
            question_id: Question ID (now available)
            image_type: Type of image
            
        Returns:
            Relative path to permanent image location
        """
        # Source: temp directory
        temp_path = cls.TEMP_BASE_DIR / str(tenant_id) / str(quiz_id) / temp_key
        
        if not temp_path.exists():
            raise HTTPException(status_code=404, detail=f"Temp image not found: {temp_key}")
        
        # Destination: permanent directory
        permanent_dir = cls.UPLOAD_BASE_DIR / str(tenant_id) / str(quiz_id)
        permanent_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate permanent filename with question_id
        ext = temp_key.split(".")[-1].lower()
        unique_id = uuid.uuid4().hex[:12]
        permanent_filename = f"{image_type}_{question_id}_{unique_id}.{ext}"
        
        permanent_path = permanent_dir / permanent_filename
        
        # Move file (rename)
        try:
            temp_path.rename(permanent_path)
            os.chmod(permanent_path, 0o644)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to move temp image: {str(e)}")
        
        # Return relative path for DB storage
        relative_path = f"{tenant_id}/{quiz_id}/{permanent_filename}"
        return relative_path
    
    @classmethod
    def delete_temp_image(cls, temp_key: str, tenant_id: int, quiz_id: int) -> bool:
        """
        Delete temporary image
        
        Args:
            temp_key: Temporary filename
            tenant_id: Tenant ID
            quiz_id: Quiz ID
            
        Returns:
            True if deleted, False otherwise
        """
        temp_path = cls.TEMP_BASE_DIR / str(tenant_id) / str(quiz_id) / temp_key
        
        try:
            if temp_path.exists() and temp_path.is_file():
                temp_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    @classmethod
    def cleanup_old_temp_files(cls, max_age_hours: int = 2) -> int:
        """
        Cleanup temporary files older than specified age
        
        Args:
            max_age_hours: Maximum age in hours before deletion
            
        Returns:
            Number of files deleted
        """
        import time
        
        if not cls.TEMP_BASE_DIR.exists():
            return 0
        
        deleted_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        try:
            # Walk through temp directory
            for root, dirs, files in os.walk(cls.TEMP_BASE_DIR):
                for filename in files:
                    file_path = Path(root) / filename
                    
                    # Check file age
                    file_age = current_time - file_path.stat().st_mtime
                    
                    if file_age > max_age_seconds:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception:
                            pass  # Skip files we can't delete
        except Exception:
            pass  # Continue cleanup even if errors
        
        return deleted_count
    
    @classmethod
    def delete_quiz_images(cls, tenant_id: int, quiz_id: int) -> int:
        """
        Delete all images for a quiz
        
        Args:
            tenant_id: Tenant ID
            quiz_id: Quiz ID
            
        Returns:
            Number of files deleted
        """
        quiz_dir = cls.UPLOAD_BASE_DIR / str(tenant_id) / str(quiz_id)
        
        if not quiz_dir.exists():
            return 0
        
        count = 0
        try:
            for file_path in quiz_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
                    count += 1
            
            # Remove empty directory
            if not any(quiz_dir.iterdir()):
                quiz_dir.rmdir()
        except Exception:
            pass
        
        return count
    
    @classmethod
    def get_image_url(cls, image_path: Optional[str]) -> Optional[str]:
        """
        Convert relative path to full URL (relative)
        
        Args:
            image_path: Relative path (e.g., "1/5/question_abc123.jpg")
            
        Returns:
            Full URL or None
        """
        if not image_path:
            return None
        
        return f"/api/uploads/images/{image_path}"
    
    @classmethod
    def to_absolute_url(cls, relative_path: Optional[str], base_url: str) -> Optional[str]:
        """
        Convert relative image path to absolute URL
        
        Args:
            relative_path: Relative path (e.g., "2/13/question_abc.png" or "temp/2/13/temp_question_xyz.png")
            base_url: Base URL (e.g., "http://localhost:8000")
            
        Returns:
            Absolute URL or None if path is None
        """
        if not relative_path:
            return None
        
        base = base_url.rstrip('/')
        
        # Check if this is a temp image path
        # Temp paths are stored as "2/13/temp_question_xyz.png" in DB
        # So we check if filename starts with "temp_"
        if 'temp_' in relative_path:
            return f"{base}/api/uploads/temp/{relative_path}"
        else:
            return f"{base}/api/uploads/images/{relative_path}"
