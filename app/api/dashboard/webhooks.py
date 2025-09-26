import hmac
import hashlib
from fastapi import APIRouter, Request, Header, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.dashboard import services
from app.api.users.models import LinkedAccount  # Adjust import to your linked accounts model

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

GITHUB_WEBHOOK_SECRET = "replace-with-your-secret"  # store in env safe

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
    if not LinkedAccount:
        return []
    linked_accounts = db.query(LinkedAccount).filter(LinkedAccount.provider == "github", LinkedAccount.provider_id == actor_login).all()
    return [account.user_id for account in linked_accounts]

@router.post("/github/webhook")
async def github_webhook(request: Request, x_hub_signature_256: str = Header(None), background_tasks: BackgroundTasks = None, db: Session = Depends(get_db)):
    body = await request.body()
    if not verify_github_signature(GITHUB_WEBHOOK_SECRET, body, x_hub_signature_256):
        raise HTTPException(status_code=400, detail="Invalid signature")
    payload = await request.json()

    # Parse payload for commit events (assuming push event)
    user_ids = []
    if payload.get("ref") and payload.get("commits"):
        actor_login = payload.get("pusher", {}).get("login") or payload.get("sender", {}).get("login")
        if actor_login:
            user_ids = map_github_actor_to_user_ids(db, actor_login)

    # Handle organization updates if applicable (e.g., project-related commits)
    org_id = None
    if payload.get("repository") and payload.get("repository", {}).get("owner", {}).get("login"):
        org = db.query(LinkedAccount).filter(LinkedAccount.provider == "github", LinkedAccount.provider_id == payload["repository"]["owner"]["login"]).first()
        if org:
            org_id = org.organization_id

    for uid in user_ids:
        background_tasks.add_task(services.compute_and_upsert_dashboard_metrics, db, uid)
    if org_id:
        background_tasks.add_task(services.compute_org_metrics, db, org_id)

    return {"ok": True}