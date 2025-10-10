import hmac
import hashlib
from fastapi import APIRouter, Request, Header, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import dashboard_service
from app.models.integration import LinkedAccount
from app.core.config import settings
from app.schemas.response_model import create_response

router = APIRouter(prefix="/integrations", tags=["integrations"])

def verify_github_signature(secret: str, body: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False
    sha_name, signature = signature_header.split('=')
    if sha_name != 'sha256':
        return False
    mac = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)

def map_github_actor_to_user_ids(db: Session, actor_login: str) -> list:
    """Map GitHub actor login to user_ids via linked accounts."""
    linked_accounts = db.query(LinkedAccount).filter(LinkedAccount.provider == "github", LinkedAccount.provider_id == actor_login).all()
    return [account.user_id for account in linked_accounts]

@router.post("/github/webhook")
async def github_webhook(request: Request, x_hub_signature_256: str = Header(None), background_tasks: BackgroundTasks = None, db: Session = Depends(get_db)):
    body = await request.body()
    if not verify_github_signature(settings.GITHUB_WEBHOOK_SECRET, body, x_hub_signature_256):
        raise HTTPException(status_code=400, detail="Invalid signature")
    payload = await request.json()

    user_ids = []
    if payload.get("ref") and payload.get("commits"):
        actor_login = payload.get("pusher", {}).get("name") or payload.get("sender", {}).get("login")
        if actor_login:
            user_ids = map_github_actor_to_user_ids(db, actor_login)

    org_id = None
    if payload.get("repository") and payload.get("repository", {}).get("owner", {}).get("login"):
        org_account = db.query(LinkedAccount).filter(LinkedAccount.provider == "github", LinkedAccount.provider_id == payload["repository"]["owner"]["login"]).first()
        if org_account:
            org_id = org_account.organization_id

    for uid in user_ids:
        background_tasks.add_task(dashboard_service.compute_and_upsert_dashboard_metrics, db, uid)
    if org_id:
        background_tasks.add_task(dashboard_service.compute_org_metrics, db, org_id)

    return create_response(success=True, message="Webhook received successfully")
