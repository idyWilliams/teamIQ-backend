from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.storage_service import upload_image_to_supabase
from app.core.security import get_current_user_or_organization
from app.models.user import User
from app.models.organization import Organization
from enum import Enum

router = APIRouter()


# Define allowed image types
class ImageType(str, Enum):
    PROFILE = "profile"
    ORGANIZATION = "organization"
    GENERAL = "general"
    TASK = "task"
    PROJECT = "project"


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    image_type: ImageType = Query(ImageType.GENERAL, description="Type of image being uploaded"),
    update_db: bool = Query(False, description="Auto-update user/org profile in database"),
    db: Session = Depends(get_db)
):
    """
    📤 Universal Image Upload Endpoint

    Upload any image and get back a Supabase CDN URL.

    **Parameters:**
    - `file`: The image file to upload
    - `image_type`: Type of image (profile, organization, general, task, project)
    - `update_db`: If true, automatically update user/org profile image in database (requires auth)

    **Usage Examples:**

    1. General upload (no auth):
    ```
    POST /api/v1/upload/image?image_type=general
    ```

    2. Profile image with DB update (requires auth):
    ```
    POST /api/v1/upload/image?image_type=profile&update_db=true
    Headers: { Authorization: 'Bearer <token>' }
    ```

    3. Organization logo with DB update (requires auth):
    ```
    POST /api/v1/upload/image?image_type=organization&update_db=true
    Headers: { Authorization: 'Bearer <token>' }
    ```

    4. Task/Project image (no DB update):
    ```
    POST /api/v1/upload/image?image_type=task
    ```
    """
    try:
        # Map image type to folder name
        folder_mapping = {
            ImageType.PROFILE: "profiles",
            ImageType.ORGANIZATION: "organizations",
            ImageType.GENERAL: "general",
            ImageType.TASK: "tasks",
            ImageType.PROJECT: "projects"
        }

        folder = folder_mapping.get(image_type, "uploads")

        # Upload to Supabase Storage
        image_url = await upload_image_to_supabase(file, folder=folder)

        response_data = {
            "success": True,
            "message": f"{image_type.value.capitalize()} image uploaded successfully",
            "data": {
                "url": image_url,
                "type": image_type.value,
                "folder": folder
            }
        }

        # Optional: Update database if requested
        if update_db:
            # Get current authenticated entity (user or organization)
            try:
                current_entity = get_current_user_or_organization(db=db)
            except HTTPException:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to update database"
                )

            # Determine if it's a User or Organization
            if isinstance(current_entity, User):
                # Update user's profile_image
                if image_type == ImageType.PROFILE:
                    current_entity.profile_image = image_url
                    db.commit()
                    db.refresh(current_entity)
                    response_data["data"]["user_updated"] = True
                    response_data["data"]["user_id"] = current_entity.id
                    response_data["data"]["entity_type"] = "user"
                else:
                    response_data["data"]["warning"] = "User can only update profile images"

            elif isinstance(current_entity, Organization):
                # Update organization's organization_image
                if image_type == ImageType.ORGANIZATION:
                    current_entity.organization_image = image_url
                    db.commit()
                    db.refresh(current_entity)
                    response_data["data"]["organization_updated"] = True
                    response_data["data"]["organization_id"] = current_entity.id
                    response_data["data"]["entity_type"] = "organization"
                else:
                    response_data["data"]["warning"] = "Organization can only update organization images"

        return response_data

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# Optional: Endpoint to delete an image
@router.delete("/image")
async def delete_image(
    image_url: str = Query(..., description="Full URL of the image to delete")
):
    """
    🗑️ Delete an image from Supabase Storage

    **Usage:**
    ```
    DELETE /api/v1/upload/image?image_url=https://xxx.supabase.co/storage/.../file.jpg
    ```
    """
    from app.services.storage_service import delete_image_from_supabase

    try:
        success = await delete_image_from_supabase(image_url)

        if success:
            return {
                "success": True,
                "message": "Image deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Image not found or already deleted")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
