"""
Service for managing user-to-tool account mappings
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from fastapi import HTTPException
import logging

from app.models.project import ProjectMember, Project
from app.models.user import User
from app.core.email_utils import email_service

logger = logging.getLogger(__name__)


class UserMappingService:
    """Service for managing external tool account mappings"""

    @staticmethod
    def get_project_member(db: Session, project_id: int, user_id: int) -> ProjectMember:
        """Get project member or raise 404"""
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first()

        if not member:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} is not a member of project {project_id}"
            )

        return member

    @staticmethod
    def map_user_to_external_account(
        db: Session,
        project_id: int,
        user_id: int,
        provider: str,
        external_user_id: str,
        external_username: Optional[str] = None,
        external_email: Optional[str] = None,
        mapped_by_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Map a TeamIQ user to an external tool account

        Args:
            db: Database session
            project_id: Project ID
            user_id: TeamIQ user ID
            provider: Provider name (github, slack, etc.)
            external_user_id: External user ID
            external_username: Optional external username
            external_email: Optional external email
            mapped_by_user_id: ID of user who performed the mapping

        Returns:
            Updated mappings dictionary
        """
        # Get project member
        member = UserMappingService.get_project_member(db, project_id, user_id)

        # Initialize external_mappings if None
        if member.external_mappings is None:
            member.external_mappings = {}

        # Update mapping
        member.external_mappings[provider] = external_user_id

        # Mark as modified for SQLAlchemy to detect JSON change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(member, "external_mappings")

        db.commit()
        db.refresh(member)

        logger.info(f"Mapped user {user_id} to {provider} account {external_user_id} in project {project_id}")

        return {
            "user_id": user_id,
            "project_id": project_id,
            "provider": provider,
            "external_user_id": external_user_id,
            "external_username": external_username,
            "external_email": external_email,
            "all_mappings": member.external_mappings
        }

    @staticmethod
    def unmap_user_from_external_account(
        db: Session,
        project_id: int,
        user_id: int,
        provider: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unmap a TeamIQ user from an external tool account

        Args:
            db: Database session
            project_id: Project ID
            user_id: TeamIQ user ID
            provider: Provider name to unmap from
            reason: Optional reason for unmapping

        Returns:
            Updated mappings dictionary
        """
        # Get project member
        member = UserMappingService.get_project_member(db, project_id, user_id)

        # Check if mapping exists
        if not member.external_mappings or provider not in member.external_mappings:
            raise HTTPException(
                status_code=404,
                detail=f"No mapping found for provider '{provider}'"
            )

        # Remove mapping
        removed_id = member.external_mappings.pop(provider)

        # Mark as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(member, "external_mappings")

        db.commit()
        db.refresh(member)

        logger.info(f"Unmapped user {user_id} from {provider} account {removed_id} in project {project_id}")

        return {
            "user_id": user_id,
            "project_id": project_id,
            "provider": provider,
            "removed_external_id": removed_id,
            "reason": reason,
            "remaining_mappings": member.external_mappings
        }

    @staticmethod
    def get_user_mappings(
        db: Session,
        project_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Get all mappings for a user in a project"""
        member = UserMappingService.get_project_member(db, project_id, user_id)

        # Get user and project details
        user = db.query(User).filter(User.id == user_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()

        return {
            "user_id": user_id,
            "user_email": user.email if user else None,
            "user_name": f"{user.first_name} {user.last_name}" if user and user.first_name else user.username if user else None,
            "project_id": project_id,
            "project_name": project.name if project else None,
            "mappings": member.external_mappings or {}
        }

    @staticmethod
    def get_all_user_mappings(db: Session, user_id: int) -> list[Dict[str, Any]]:
        """Get all mappings for a user across all projects"""
        memberships = db.query(ProjectMember).filter(
            ProjectMember.user_id == user_id
        ).all()

        user = db.query(User).filter(User.id == user_id).first()

        result = []
        for member in memberships:
            if member.external_mappings:
                project = db.query(Project).filter(Project.id == member.project_id).first()
                result.append({
                    "user_id": user_id,
                    "user_email": user.email if user else None,
                    "user_name": f"{user.first_name} {user.last_name}" if user and user.first_name else user.username if user else None,
                    "project_id": member.project_id,
                    "project_name": project.name if project else None,
                    "mappings": member.external_mappings
                })

        return result

    @staticmethod
    async def send_mapping_notification(
        user_email: str,
        user_name: str,
        project_name: str,
        provider: str,
        external_username: str,
        mapped_by: str
    ) -> bool:
        """Send email notification when user is mapped to external account"""
        try:
            return await email_service.send_email(
                to_email=user_email,
                subject=f"You've been mapped to a {provider.title()} account",
                template_name="emails/account_mapped.html",
                template_data={
                    "user_name": user_name,
                    "project_name": project_name,
                    "provider": provider.title(),
                    "external_username": external_username,
                    "mapped_by": mapped_by
                }
            )
        except Exception as e:
            logger.error(f"Failed to send mapping notification: {e}")
            return False

    @staticmethod
    async def send_unmapping_notification(
        user_email: str,
        user_name: str,
        project_name: str,
        provider: str,
        reason: Optional[str] = None
    ) -> bool:
        """Send email notification when user is unmapped from external account"""
        try:
            return await email_service.send_email(
                to_email=user_email,
                subject=f"Your {provider.title()} account mapping has been removed",
                template_name="emails/account_unmapped.html",
                template_data={
                    "user_name": user_name,
                    "project_name": project_name,
                    "provider": provider.title(),
                    "reason": reason or "No reason provided"
                }
            )
        except Exception as e:
            logger.error(f"Failed to send unmapping notification: {e}")
            return False
