import os
import base64
import hashlib
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

def _get_fernet_key() -> bytes:
    """Generate a 32-byte url-safe base64 key from settings SECRET_KEY or FIELD_ENCRYPTION_KEY."""
    raw_key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None) or getattr(settings, 'SECRET_KEY', 'default-secret-key-church')
    # Hash raw key to 32 bytes using SHA-256 and base64 encode
    key_32bytes = hashlib.sha256(raw_key.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(key_32bytes)

_fernet_instance = None

def get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        _fernet_instance = Fernet(_get_fernet_key())
    return _fernet_instance

def encrypt_val(val: str) -> str:
    """Encrypt a plaintext string to Fernet ciphertext string."""
    if not val:
        return val
    if val.startswith('gAAAAA'):
        # Already encrypted
        return val
    f = get_fernet()
    encrypted_bytes = f.encrypt(val.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_val(val: str) -> str:
    """Decrypt a Fernet ciphertext string to plaintext string. If not encrypted, returns raw val."""
    if not val:
        return val
    if not val.startswith('gAAAAA'):
        # Legacy plain text or unencrypted string
        return val
    try:
        f = get_fernet()
        decrypted_bytes = f.decrypt(val.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except (InvalidToken, Exception):
        # Fallback if decryption fails
        return val
