from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.repositories import user_repository
from app.core.database import get_db
from app.core.security import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Extract the current user from the JWT access token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = user_repository.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception

    return user

# Basic require_role implementation
def require_role(role: str):
    def role_checker(current_user=Depends(get_current_user)):
        if not hasattr(current_user, 'role') or current_user.role.value != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker