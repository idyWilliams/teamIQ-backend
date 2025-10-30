from sqlalchemy.orm import Session
from app.models.integration import LinkedAccount, OrganizationIntegration
from app.schemas.integration import LinkAccount, IntegrationCreate

class IntegrationRepository:
    def create(self, db: Session, obj_in: IntegrationCreate) -> OrganizationIntegration:
        db_obj = OrganizationIntegration(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: int) -> OrganizationIntegration:
        return db.query(OrganizationIntegration).filter(OrganizationIntegration.id == id).first()

    def link_account(self, db: Session, link: LinkAccount, user_id: int = None, org_id: int = None):
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

    def get_linked_accounts(self, db: Session, user_id: int = None, org_id: int = None):
        query = db.query(LinkedAccount)
        if user_id:
            query = query.filter(LinkedAccount.user_id == user_id)
        if org_id:
            query = query.filter(LinkedAccount.organization_id == org_id)
        return query.all()

integration_repository = IntegrationRepository()
