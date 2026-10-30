import os
import uuid
import hashlib
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image, ImageOps
from fastapi import UploadFile, HTTPException
from app.config import settings

def calculate_file_hash(file_bytes: bytes) -> str:
    return hashlib.md5(file_bytes).hexdigest()

def validate_image_file(upload_file: UploadFile, file_bytes: bytes):
    if len(file_bytes) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"Image size exceeds maximum allowed ({settings.MAX_IMAGE_SIZE_MB}MB)"
        )
    
    ext = upload_file.filename.split(".")[-1].lower() if "." in upload_file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format: .{ext}. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

def process_and_save_image(
    file_bytes: bytes,
    original_filename: str
) -> Tuple[str, str, str, int, str]:
    """
    Processes image:
    1. Corrects EXIF mobile orientation.
    2. Resizes display image to max 1600px dimension.
    3. Generates 400x400 thumbnail.
    4. Returns (unique_filename, filepath, thumbnail_path, file_size, image_hash).
    """
    image_hash = calculate_file_hash(file_bytes)
    unique_id = uuid.uuid4().hex[:12]
    ext = original_filename.split(".")[-1].lower() if "." in original_filename else "jpg"
    if ext not in settings.ALLOWED_EXTENSIONS:
        ext = "jpg"
    
    filename = f"{unique_id}.{ext}"
    thumb_filename = f"thumb_{unique_id}.jpg"
    
    full_path = settings.UPLOAD_DIR / filename
    thumb_path = settings.UPLOAD_DIR / "thumbnails" / thumb_filename
    
    import io
    image_stream = io.BytesIO(file_bytes)
    
    try:
        with Image.open(image_stream) as img:
            # Fix mobile photo orientation from EXIF
            img = ImageOps.exif_transpose(img)
            
            # Convert RGBA to RGB for JPEG compatibility if saving as jpg
            if img.mode in ("RGBA", "P") and ext in ("jpg", "jpeg"):
                img = img.convert("RGB")
            
            # 1. Main Display Image (rescale if larger than 1600px)
            display_img = img.copy()
            max_size = (1600, 1600)
            display_img.thumbnail(max_size, Image.Resampling.LANCZOS)
            display_img.save(full_path, quality=85, optimize=True)
            
            # 2. Thumbnail (400x400 fitted)
            thumb_img = img.copy()
            if thumb_img.mode in ("RGBA", "P"):
                thumb_img = thumb_img.convert("RGB")
            thumb_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            thumb_img.save(thumb_path, "JPEG", quality=80, optimize=True)
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")
        
    file_size = os.path.getsize(full_path)
    rel_filepath = f"/static_uploads/{filename}"
    rel_thumbpath = f"/static_uploads/thumbnails/{thumb_filename}"
    
    return filename, rel_filepath, rel_thumbpath, file_size, image_hash

def remove_image_files(filename: str, thumbnail_path: Optional[str] = None):
    try:
        main_file = settings.UPLOAD_DIR / filename
        if main_file.exists():
            main_file.unlink()
        if thumbnail_path:
            thumb_name = os.path.basename(thumbnail_path)
            thumb_file = settings.UPLOAD_DIR / "thumbnails" / thumb_name
            if thumb_file.exists():
                thumb_file.unlink()
    except Exception as e:
        print(f"Warning: Failed to delete image files: {e}")

