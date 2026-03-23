"""Secure credential storage using Fernet symmetric encryption.

Key is derived from the machine's MAC address via PBKDF2 so the encrypted
file is machine-specific and cannot be trivially copied to another host.
"""

import base64
import hashlib
import json
import uuid

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .paths import get_credentials_path

_STATIC_PASSPHRASE = b"mytime-autoclicker-v1"


def _build_fernet() -> Fernet:
    """Derive a Fernet key from the machine MAC address."""
    mac = str(uuid.getnode()).encode()
    salt = hashlib.sha256(mac).digest()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(_STATIC_PASSPHRASE))
    return Fernet(key)


def save_credentials(username: str, password: str) -> None:
    """Encrypt and persist credentials to disk."""
    fernet = _build_fernet()
    payload = json.dumps({"username": username, "password": password}).encode()
    encrypted = fernet.encrypt(payload)
    get_credentials_path().write_bytes(encrypted)


def load_credentials() -> tuple[str, str]:
    """Decrypt and return (username, password). Raises if not found."""
    path = get_credentials_path()
    if not path.exists():
        raise FileNotFoundError("No credentials saved yet.")
    fernet = _build_fernet()
    decrypted = fernet.decrypt(path.read_bytes())
    data = json.loads(decrypted)
    return data["username"], data["password"]


def credentials_exist() -> bool:
    return get_credentials_path().exists()
