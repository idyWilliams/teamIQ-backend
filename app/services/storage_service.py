from supabase import create_client, Client
from fastapi import UploadFile, HTTPException
from app.core.config import settings
import uuid
from datetime import datetime



supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY  
)


async def upload_image_to_supabase(file: UploadFile, folder: str = "general") -> str:
    """
    Upload image to Supabase Storage and return public URL
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )

        # Read file content
        file_content = await file.read()

        # Validate file size (max 10MB for images)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="Image size exceeds 10MB limit")

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        unique_filename = f"{folder}/{timestamp}_{unique_id}.{file_extension}"

        # Upload to Supabase Storage
        supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
            path=unique_filename,
            file=file_content,
            file_options={
                "content-type": file.content_type,
                "cache-control": "3600",
                "upsert": "false"
            }
        )

        # Get public URL
        public_url = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(unique_filename)

        print(f"✅ Image uploaded: {public_url}")
        return public_url

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def upload_document_to_supabase(file: UploadFile, folder: str = "documents") -> dict:
    """
    Upload a document (PDF, Doc, etc.) to Supabase Storage and return its metadata

    Returns:
        dict: {name, url, type, size, uploaded_at}
    """
    try:
        # Validate file type
        allowed_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "text/plain",
            "text/csv"
        ]
        
        if file.content_type not in allowed_types:
            # Fallback check for extensions if content_type is generic
            ext = file.filename.split(".")[-1].lower()
            allowed_exts = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv"]
            if ext not in allowed_exts:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type. Allowed: PDF, Word, Excel, PPT, TXT, CSV"
                )

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size (max 25MB for documents)
        max_size = 25 * 1024 * 1024  # 25MB
        if file_size > max_size:
            raise HTTPException(status_code=400, detail="Document size exceeds 25MB limit")

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "doc"
        unique_filename = f"{folder}/{timestamp}_{unique_id}.{file_extension}"

        # Upload to Supabase Storage
        supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
            path=unique_filename,
            file=file_content,
            file_options={
                "content-type": file.content_type,
                "cache-control": "3600",
                "upsert": "false"
            }
        )

        # Get public URL
        public_url = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(unique_filename)

        print(f"✅ Document uploaded: {public_url}")
        
        return {
            "name": file.filename,
            "url": public_url,
            "type": file.content_type,
            "size": file_size,
            "uploaded_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Document upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


async def delete_image_from_supabase(image_url: str) -> bool:
    """
    Delete image from Supabase Storage

    Args:
        image_url: Full URL of the image

    Returns:
        bool: True if deletion successful
    """
    try:

        parts = image_url.split(f"{settings.SUPABASE_BUCKET_NAME}/")
        if len(parts) < 2:
            print(f"⚠️  Invalid URL format: {image_url}")
            return False

        file_path = parts[1]

        # Delete from Supabase
        supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).remove([file_path])
        print(f"🗑️ Image deleted: {file_path}")
        return True

    except Exception as e:
        print(f"❌ Delete error: {str(e)}")
        return False


async def get_signed_url(file_path: str, expires_in: int = 3600) -> str:
    """
    Get a signed URL for private file access

    Args:
        file_path: Path to file in bucket
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns:
        str: Signed URL
    """
    try:
        signed_url = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).create_signed_url(
            path=file_path,
            expires_in=expires_in
        )
        return signed_url['signedURL']

    except Exception as e:
        print(f"❌ Signed URL error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create signed URL: {str(e)}")
