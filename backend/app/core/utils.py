import secrets
import string

ALPHABET = string.ascii_letters + string.digits

def generate_id(length: int = 16) -> str:
    """Generate a secure, URL-safe alphanumeric ID."""
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))
