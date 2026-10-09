"""Field-Level Encryption at Rest for High-Sensitivity Healthcare Data.

Uses AES-256-GCM authenticated encryption complying with HIPAA, DISHA,
and ISO/IEC 27001 requirements for encryption of protected health information (PHI).
"""

import os
import base64
import hashlib
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from packages.config.settings import settings


class EncryptionError(Exception):
    """Raised when encryption or decryption fails due to corruption or tampering."""
    pass


class AESGCMFieldEncryption:
    """Authenticated field-level encryption using AES-256-GCM."""

    def __init__(self, key_material: Optional[str] = None):
        secret = key_material or settings.SECRET_KEY
        # Derive 256-bit (32 bytes) cryptographic key using SHA-256
        self._key = hashlib.sha256(secret.encode("utf-8")).digest()
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypts plaintext string using AES-256-GCM with a random 12-byte nonce.
        Returns: base64-encoded string (nonce + ciphertext + tag)
        """
        if not plaintext:
            return ""

        nonce = os.urandom(12)  # 96-bit unique nonce
        data_bytes = plaintext.encode("utf-8")
        ciphertext = self._aesgcm.encrypt(nonce, data_bytes, None)

        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("utf-8")

    def decrypt(self, encoded_ciphertext: str) -> str:
        """Decrypts base64-encoded ciphertext, verifying authentication tag.
        Raises EncryptionError if authentication fails.
        """
        if not encoded_ciphertext:
            return ""

        try:
            combined = base64.b64decode(encoded_ciphertext.encode("utf-8"))
            if len(combined) < 28:  # 12 nonce + 16 tag minimum
                raise EncryptionError("Ciphertext payload too short.")

            nonce = combined[:12]
            ciphertext = combined[12:]

            decrypted_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted_bytes.decode("utf-8")
        except Exception as exc:
            raise EncryptionError(f"Decryption failed or payload tampered: {str(exc)}") from exc


field_encryption = AESGCMFieldEncryption()
