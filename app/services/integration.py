# app/services/integration.py

import os
from app.services.integration_defaults import INTEGRATION_DEFAULTS
from app.repositories.org_integration_credential import get_org_credentials

def resolve_creds(db, org_id, provider):
    """
    Resolves credentials for any supported provider.
    Tries org-specific (BYOC) values first, then defaults found in environment.
    Returns all necessary OAuth/api key data.
    """
    defaults = INTEGRATION_DEFAULTS.get(provider)
    if not defaults:
        raise ValueError(f"Unknown provider: {provider}")

    # Global env: fallback (SaaS default key model)
    env_id = os.getenv(defaults.get("client_id_env", ""), "")
    env_secret = os.getenv(defaults.get("client_secret_env", ""), "")
    env_redirect = os.getenv(defaults.get("redirect_uri_env", ""), "")

    # Org-specific (BYOC)
    org_cred = get_org_credentials(db, org_id, provider)

    val = {
        # Which client/secret to use
        "client_id": org_cred.client_id if org_cred and org_cred.client_id else env_id,
        "client_secret": org_cred.client_secret if org_cred and org_cred.client_secret else env_secret,
        "redirect_uri": env_redirect,  # Use your backend env for redirect callback unless you need to customize per org
        "scopes": defaults.get('scopes', ''),
        "authorize_url": defaults.get("authorize_url", ""),
        "token_url": defaults.get("token_url", ""),
        "type": defaults.get("type", ""),
        "api_key": org_cred.api_key if org_cred and org_cred.api_key else None,
    }

    # Providers with no OAuth (API key only)
    # The env value for their API key isn't used in this flow
    if val["type"] == "apikey":
        val["client_id"] = None
        val["client_secret"] = None
        val["redirect_uri"] = None

    return val
