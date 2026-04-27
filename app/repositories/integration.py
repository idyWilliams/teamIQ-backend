from datetime import datetime
from app.models.integration import IntegrationConnection

def debug_log(msg):
    try:
        with open("/Users/mac/Documents/teamIQ-backend/debug_integration.log", "a") as f:
            f.write(f"{datetime.utcnow()} - {msg}\n")
    except Exception:
        pass

def get_org_provider_connections(db, org_id, provider):
    return db.query(IntegrationConnection)\
        .filter_by(organization_id=org_id, provider=provider, is_active=True).all()

def get_slack_bot_token(db, org_id: str) -> str | None:
    """
    Returns the Slack access_token for the given org, or None if not found.
    """
    conn = db.query(IntegrationConnection).filter_by(
        organization_id=org_id, provider="slack", is_active=True
    ).first()
    return conn.access_token if conn else None

def upsert_integration_connection(db, data):
    org_id = str(data['organization_id'])
    provider = data['provider']
    account_id = str(data['account_id'])
    access_token = data.get('access_token')
    refresh_token = data.get('refresh_token')
    api_key = data.get('api_key')
    user_id = data['connected_by_user_id']

    debug_log(f"Upserting integration: org={org_id}, provider={provider}, account={account_id}")
    conn = db.query(IntegrationConnection)\
        .filter_by(organization_id=org_id, provider=provider, account_id=account_id).first()
    if conn:
        if access_token:
            conn.access_token = access_token
        if refresh_token:
            conn.refresh_token = refresh_token
        if api_key:
            conn.api_key = api_key
        conn.updated_at = datetime.utcnow()
        conn.is_active = True
        debug_log(f"Updated existing integration {conn.id}, set active=True")
    else:
        debug_log("Creating new integration connection")
        conn = IntegrationConnection(
            organization_id=org_id,
            provider=provider,
            account_id=account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            api_key=api_key,
            connected_by_user_id=user_id
        )
        db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn
