from sqlalchemy.orm import Session
from app.models.integration import LinkedAccount
from app.schemas.integration import LinkAccount

def link_account(db: Session, link: LinkAccount, user_id: int = None, org_id: int = None):
    account = LinkedAccount(
        user_id=user_id,
        organization_id=org_id,
        provider=link.provider,
        provider_id=link.provider_id
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account

def get_linked_accounts(db: Session, user_id: int = None, org_id: int = None):
    query = db.query(LinkedAccount)
    if user_id:
        query = query.filter(LinkedAccount.user_id == user_id)
    if org_id:
        query = query.filter(LinkedAccount.organization_id == org_id)
    return query.all()