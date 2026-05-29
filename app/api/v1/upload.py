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


@router.delete("/image")
async def delete_image(
    image_url: str = Query(..., description="Full URL of the image to delete")
):
    """
    🗑️ Delete an image from Supabase Storage
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


@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    project_id: int = Query(None, description="Optional: ID of the project this document belongs to"),
    db: Session = Depends(get_db)
):
    """
    📄 Document Upload Endpoint

    Upload a project-related document (PDF, Word, etc.) and get back its metadata and URL.
    Also extracts text content for AI processing.
    """
    from app.services.storage_service import upload_document_to_supabase
    from app.models.project import Project
    from app.core.document_utils import extract_text_from_file

    try:
        # Extract text content first (since reading the file might consume the stream)
        # Actually, we should read the file once and pass the bytes.
        # document_utils already handles reading and extracting.
        # But wait, we need the file for Supabase too.
        
        # Save a copy of the file for Supabase
        import copy
        # Workaround: Upload document to supabase first, then extract text?
        # Or better: read it once, use it twice.
        
        # We need to be careful with the file pointer.
        file_content = await file.read()
        await file.seek(0) # Reset pointer for Supabase upload if needed
        
        # Upload to Supabase Storage
        doc_data = await upload_document_to_supabase(file, folder="project_docs")

        # Now extract text from the content we already read
        # (Need to modify document_utils or just use its helper)
        from app.core.document_utils import extract_text_from_pdf, extract_text_from_docx, extract_text_from_csv
        
        extracted_text = ""
        filename = file.filename.lower()
        if filename.endswith(".pdf"):
            extracted_text = extract_text_from_pdf(file_content)
        elif filename.endswith((".docx", ".doc")):
            extracted_text = extract_text_from_docx(file_content)
        elif filename.endswith(".csv"):
            extracted_text = extract_text_from_csv(file_content)
        elif filename.endswith(".txt"):
            extracted_text = file_content.decode("utf-8", errors="ignore")
        
        # Add extracted text to metadata (limit size for DB)
        doc_data["extracted_text"] = extracted_text[:100000] # Limit to 100k chars for now

        # If project_id is provided, we can optionally link it immediately
        if project_id:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                current_docs = project.linked_documents or []
                current_docs.append(doc_data)
                project.linked_documents = current_docs
                db.commit()
                doc_data["project_linked"] = True

        return {
            "success": True,
            "message": "Document uploaded and processed successfully",
            "data": doc_data
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Document upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
