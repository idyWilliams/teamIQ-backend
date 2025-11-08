"""
Encryption service for securing API keys and tokens
Uses Fernet (symmetric encryption) from cryptography library
"""

from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import os


class EncryptionService:
    """Handle encryption/decryption of sensitive data"""

    def __init__(self):
        # Get encryption key from environment or generate one
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)

    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment"""
        if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY:
            return settings.ENCRYPTION_KEY.encode()

        # For development only - generate key
        print("⚠️  WARNING: No ENCRYPTION_KEY found, generating one for development")
        key = Fernet.generate_key()
        print(f"🔑 Generated key: {key.decode()}")
        print("Add this to your .env file: ENCRYPTION_KEY={key.decode()}")
        return key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string"""
        if not plaintext:
            return plaintext

        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a string"""
        if not encrypted:
            return encrypted

        decrypted = self.cipher.decrypt(encrypted.encode())
        return decrypted.decode()


# Global instance
encryption_service = EncryptionService()


def encrypt_field(value: str) -> str:
    """Helper function to encrypt a field"""
    return encryption_service.encrypt(value)


def decrypt_field(value: str) -> str:
    """Helper function to decrypt a field"""
    return encryption_service.decrypt(value)
