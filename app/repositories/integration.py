from datetime import datetime
from app.models.integration import IntegrationConnection

def get_org_provider_connections(db, org_id, provider):
    return db.query(IntegrationConnection)\
        .filter_by(organization_id=org_id, provider=provider, is_active=True).all()

def upsert_integration_connection(db, data):
    org_id = data['organization_id']
    provider = data['provider']
    account_id = data['account_id']
    access_token = data.get('access_token')
    refresh_token = data.get('refresh_token')
    api_key = data.get('api_key')
    user_id = data['connected_by_user_id']

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
    else:
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
