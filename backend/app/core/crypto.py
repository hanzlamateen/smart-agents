from cryptography.fernet import Fernet
from app.core.config import settings

class CryptoManager:
    """Helper for encrypting and decrypting sensitive data like private keys."""
    
    def __init__(self):
        # Fernet handles AES-128-CBC + HMAC + Timestamp
        self.fernet = Fernet(settings.ssh_encryption_key)

    def encrypt(self, data: str) -> bytes:
        """Encrypt string data to bytes."""
        return self.fernet.encrypt(data.encode('utf-8'))

    def decrypt(self, data: bytes) -> str:
        """Decrypt bytes to string data."""
        return self.fernet.decrypt(data).decode('utf-8')

    def generate_ssh_keys(self) -> tuple[str, str]:
        """Generate an RSA keypair for SSH access. Returns (private_key, public_key)."""
        from cryptography.hazmat.primitives import serialization as crypto_serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend

        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        private_key = key.private_bytes(
            encoding=crypto_serialization.Encoding.PEM,
            format=crypto_serialization.PrivateFormat.PKCS8,
            encryption_algorithm=crypto_serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key = key.public_key().public_bytes(
            encoding=crypto_serialization.Encoding.OpenSSH,
            format=crypto_serialization.PublicFormat.OpenSSH
        ).decode('utf-8')

        return private_key, public_key
