"""Security utilities for handling sensitive data."""

import os
import hashlib
import hmac
import json
from base64 import b64encode, b64decode
from cryptography.fernet import Fernet
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SecureConfig:
    """Handle secure storage and retrieval of sensitive configuration."""

    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".projectresearch"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.key_file = self.config_dir / ".key"
        self.config_file = self.config_dir / "secure_config.json"

    def _get_or_create_key(self) -> bytes:
        """Get existing encryption key or create new one."""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(self.key_file, 0o600)
            return key

    def encrypt_config(self, config: Dict[str, Any]) -> None:
        """Encrypt and save configuration."""
        try:
            key = self._get_or_create_key()
            f = Fernet(key)
            config_json = json.dumps(config)
            encrypted_data = f.encrypt(config_json.encode())

            with open(self.config_file, 'wb') as file:
                file.write(encrypted_data)
            os.chmod(self.config_file, 0o600)

        except Exception as e:
            logger.error(f"Failed to encrypt config: {e}")
            raise

    def decrypt_config(self) -> Dict[str, Any]:
        """Decrypt and load configuration."""
        try:
            if not self.config_file.exists():
                return {}

            key = self._get_or_create_key()
            f = Fernet(key)

            with open(self.config_file, 'rb') as file:
                encrypted_data = file.read()

            decrypted_data = f.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())

        except Exception as e:
            logger.error(f"Failed to decrypt config: {e}")
            return {}


def validate_url(url: str) -> bool:
    """Validate URL to prevent security issues."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)

        # Check for allowed schemes
        if parsed.scheme not in ['http', 'https']:
            return False

        # Check for localhost/private IPs (optional)
        if parsed.hostname in ['localhost', '127.0.0.1'] or \
           (parsed.hostname and parsed.hostname.startswith('192.168.')):
            logger.warning(f"Potentially unsafe URL detected: {url}")

        return True
    except Exception:
        return False


def sanitize_content(content: str, max_length: int = 100000) -> str:
    """Sanitize content to prevent issues."""
    if not content:
        return ""

    # Remove potentially dangerous HTML/script content
    import re
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<[^>]+>', '', content)

    # Limit length
    if len(content) > max_length:
        content = content[:max_length] + "...[truncated]"

    return content


def hash_sensitive_data(data: str) -> str:
    """Create hash of sensitive data for logging."""
    return hashlib.sha256(data.encode()).hexdigest()[:16]