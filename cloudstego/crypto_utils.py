from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


MAGIC = b"CSTG"  # CloudStego
VERSION = 1
SALT_LENGTH_BYTES = 16
NONCE_LENGTH_BYTES = 12  # AES-GCM standard nonce size
KDF_ITERATIONS = 200_000


@dataclass
class EncryptedPayload:
    header: bytes  # MAGIC (4) + VERSION (1) + SALT (16) + NONCE (12)
    ciphertext_and_tag: bytes  # AES-GCM returns ciphertext with tag appended

    def to_bytes(self) -> bytes:
        return self.header + self.ciphertext_and_tag


def _derive_key(password: str, salt: bytes) -> bytes:
    if not isinstance(password, str) or password == "":
        raise ValueError("Password must be a non-empty string")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_bytes(plaintext: bytes, password: str, associated_data: bytes | None = None) -> bytes:
    """
    Encrypts plaintext using AES-GCM with a password-derived key (PBKDF2-SHA256).

    Returns a self-describing byte sequence:
        MAGIC(4) | VERSION(1) | SALT(16) | NONCE(12) | CIPHERTEXT||TAG
    """
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError("Plaintext must be bytes")

    salt = os.urandom(SALT_LENGTH_BYTES)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_LENGTH_BYTES)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    header = MAGIC + bytes([VERSION]) + salt + nonce
    payload = EncryptedPayload(header=header, ciphertext_and_tag=ciphertext)
    return payload.to_bytes()


def _parse_encrypted_payload(data: bytes) -> Tuple[int, bytes, bytes, bytes]:
    """
    Parses header and returns (version, salt, nonce, ciphertext_and_tag)
    """
    if len(data) < 4 + 1 + SALT_LENGTH_BYTES + NONCE_LENGTH_BYTES + 16:
        # require at least one AES block + tag
        raise ValueError("Data too short to be a valid encrypted payload")
    if data[:4] != MAGIC:
        raise ValueError("Invalid magic header; not a CloudStego payload")
    version = data[4]
    if version != VERSION:
        raise ValueError(f"Unsupported payload version: {version}")
    salt_start = 5
    salt_end = salt_start + SALT_LENGTH_BYTES
    nonce_end = salt_end + NONCE_LENGTH_BYTES
    salt = data[salt_start:salt_end]
    nonce = data[salt_end:nonce_end]
    ciphertext_and_tag = data[nonce_end:]
    return version, salt, nonce, ciphertext_and_tag


def decrypt_bytes(encrypted: bytes, password: str, associated_data: bytes | None = None) -> bytes:
    version, salt, nonce, ciphertext_and_tag = _parse_encrypted_payload(encrypted)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data)

