from app.models.user_organizations import UserOrganization

def link_user_to_org(db, user_id: int, org_id: int):
    existing = (
        db.query(UserOrganization)
        .filter(UserOrganization.user_id == user_id, UserOrganization.organization_id == org_id)
        .first()
    )
    if not existing:
        db.add(UserOrganization(user_id=user_id, organization_id=org_id))
        db.commit()
