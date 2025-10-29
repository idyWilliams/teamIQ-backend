# from app.models.user_organizations import UserOrganization

# def link_user_to_org(db, user_id: int, org_id: int):
#     existing = (
#         db.query(UserOrganization)
#         .filter(UserOrganization.user_id == user_id, UserOrganization.organization_id == org_id)
#         .first()
#     )
#     if not existing:
#         db.add(UserOrganization(user_id=user_id, organization_id=org_id))



from app.models.user_organizations import UserOrganization
from sqlalchemy.orm import Session


def link_user_to_org(db: Session, user_id: int, org_id: int):
    """
    Link a user to an organization via the user_organizations junction table.

    Args:
        db: Database session
        user_id: The user's ID (must not be None - user must be flushed first)
        org_id: The organization's ID

    Note: Does not commit - caller must handle transaction
    """
    # Defensive check
    if user_id is None:
        raise ValueError("user_id cannot be None. User must be flushed before linking to organization.")
    if org_id is None:
        raise ValueError("org_id cannot be None.")

    # Check if link already exists
    existing = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == org_id
        )
        .first()
    )

    # Only create if link doesn't exist
    if not existing:
        user_org = UserOrganization(
            user_id=user_id,
            organization_id=org_id
        )
        db.add(user_org)
        # Don't commit - let the caller manage the transaction
