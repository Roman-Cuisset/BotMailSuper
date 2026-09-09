"""
Crypto Utilities
Handles password encryption and decryption for multi-account support
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

load_dotenv("secrets.env")

def get_fernet():
    """
    Derive a Fernet key from the SECRET_KEY
    This ensures we can decrypt passwords even if the app restarts,
    as long as SECRET_KEY remains the same.
    """
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise ValueError("SECRET_KEY must be set in secrets.env")
    
    # Use a static salt for deterministic key generation from SECRET_KEY
    # In a more advanced setup, we might store a random salt per user, 
    # but for this bot, a static salt derived from the app context is acceptable simplicity.
    salt = b'telegram_mail_bot_static_salt' 
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return Fernet(key)

def encrypt_password(password):
    """Encrypt a password string"""
    if not password:
        return None
    f = get_fernet()
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    """Decrypt a password string"""
    if not encrypted_password:
        return None
    f = get_fernet()
    return f.decrypt(encrypted_password.encode()).decode()
