from cryptography.fernet import Fernet
print(f"SSH_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
