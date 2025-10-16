# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# def get_password_hash(password: str) -> str:
#     return pwd_context.hash(password)

# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)


from passlib.context import CryptContext

# Explicitly set argon2 as the ONLY scheme
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__rounds=4,  # Explicitly configure argon2
)

def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Hashing error: {e}")
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Verification error: {e}")
        raise