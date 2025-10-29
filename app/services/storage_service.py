from supabase import create_client, Client
from fastapi import UploadFile, HTTPException
from app.core.config import settings
import uuid
from datetime import datetime

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def upload_image_to_supabase(file: UploadFile, folder: str = "uploads") -> str:
    """
    Upload image to Supabase Storage and return public URL

    Args:
        file: The uploaded file from FastAPI
        folder: Folder name in the bucket (e.g., 'profiles', 'organizations')

    Returns:
        str: Public URL of the uploaded image
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

        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        unique_filename = f"{folder}/{timestamp}_{unique_id}.{file_extension}"

        # Upload to Supabase Storage
        response = supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
            path=unique_filename,
            file=file_content,
            file_options={"content-type": file.content_type}
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


async def delete_image_from_supabase(image_url: str) -> bool:
    """
    Delete image from Supabase Storage

    Args:
        image_url: Full URL of the image

    Returns:
        bool: True if deletion successful
    """
    try:
        # Extract file path from URL
        # URL format: https://xxx.supabase.co/storage/v1/object/public/bucket-name/path/to/file.jpg
        parts = image_url.split(f"{settings.SUPABASE_BUCKET_NAME}/")
        if len(parts) < 2:
            return False

        file_path = parts[1]

        # Delete from Supabase
        supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).remove([file_path])
        print(f"🗑️ Image deleted: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Delete error: {str(e)}")
        return False
