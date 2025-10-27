import os
from typing import Optional, Any
from types import SimpleNamespace

try:
    from jose import jwt as jose_jwt, JWTError as JoseError  # type: ignore
    _JWT_LIB = "jose"
except Exception:
    try:
        import jwt as pyjwt  # type: ignore
        _JWT_LIB = "pyjwt"
    except Exception:
        _JWT_LIB = None

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


def _decode_token(token: str) -> Optional[dict]:
    if not _JWT_LIB:
        return None
    try:
        if _JWT_LIB == "jose":
            payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        else:
            payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
    except Exception:
        return None


def get_user_from_token(token: str) -> Optional[Any]:
   
    payload = _decode_token(token)
    if not payload:
        return None


    user_id = None
    org_id = None

    if "type" in payload:
        ptype = payload.get("type")
        if ptype == "user":
            raw = payload.get("sub") or payload.get("user_id") or payload.get("id")
            try:
                user_id = int(raw) if raw is not None else None
            except Exception:
                user_id = None
        elif ptype == "org" or ptype == "organization":
            raw = payload.get("sub") or payload.get("organization_id") or payload.get("id")
            try:
                org_id = int(raw) if raw is not None else None
            except Exception:
                org_id = None
    else:

        if payload.get("user_id") is not None:
            try:
                user_id = int(payload.get("user_id"))
            except Exception:
                user_id = None
        elif payload.get("organization_id") is not None:
            try:
                org_id = int(payload.get("organization_id"))
            except Exception:
                org_id = None
        else:
            # try "sub" as user id
            raw = payload.get("sub") or payload.get("id")
            if raw is not None:
                try:
                    user_id = int(raw)
                except Exception:
                    user_id = None


    if user_id is None and org_id is None:
        return None

    
    if user_id is not None:
        org_claim = payload.get("organization_id")
        try:
            organization_id = int(org_claim) if org_claim is not None else None
        except Exception:
            organization_id = None
        return SimpleNamespace(id=user_id, organization_id=organization_id)
    else:
        return SimpleNamespace(id=org_id, organization_id=None)
