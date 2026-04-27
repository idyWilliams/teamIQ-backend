from app.models.org_integration_credential import OrgIntegrationCredential

def get_org_credentials(db, org_id, provider):
    return db.query(OrgIntegrationCredential)\
        .filter_by(organization_id=org_id, provider=provider).first()

def upsert_org_credentials(db, data):
    org_id = data['organization_id']
    provider = data['provider']
    client_id = data.get('client_id')
    client_secret = data.get('client_secret')
    api_key = data.get('api_key')
    cred = db.query(OrgIntegrationCredential)\
        .filter_by(organization_id=org_id, provider=provider).first()
    if cred:
        if client_id:
            cred.client_id = client_id
        if client_secret:
            cred.client_secret = client_secret
        if api_key:
            cred.api_key = api_key
    else:
        cred = OrgIntegrationCredential(
            organization_id=org_id,
            provider=provider,
            client_id=client_id,
            client_secret=client_secret,
            api_key=api_key
        )
        db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred
