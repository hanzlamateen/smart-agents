from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    cors_origins: list[str] = ["http://localhost:3000"]
    environment: str = "local" # local, production
    anthropic_api_key: str = "" # Specifically for Anthropic
    api_key: str = "" # Metadata-agnostic API key fallback

    # Database Config
    database_url: str = "sqlite:///./test.db"

    # S3 Config
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "smart-agents-images"
    s3_public_url: str = "http://localhost:9000"

    # Instance Spawning Config
    instance_image_name: str = "smart-agents-worker:latest"
    instance_network_name: str = "smart-agents_smart_agents_net" # The network interface is created with repo/folder name.
    vnc_port_start: int = 6081
    vnc_port_end: int = 6100

    # SSH Config
    ssh_encryption_key: str # Required. Generate with Fernet.generate_key()
    ssh_username: str = "smart-agents"
    ssh_port: int = 22

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    # Anthropic config directory (like streamlit)
    config_dir: Path = Path.home() / ".anthropic"
    
    def get_anthropic_api_key(self) -> str:
        """Get Anthropic API key using same logic as streamlit"""
        # Try to load from file first (like streamlit load_from_storage)
        api_key_file = self.config_dir / "api_key"
        if api_key_file.exists():
            try:
                return api_key_file.read_text().strip()
            except Exception:
                pass
        
        # Fall back to environment variable (like streamlit)
        return self.anthropic_api_key
    
    def save_anthropic_api_key(self, api_key: str) -> None:
        """Save API key to file (like streamlit save_to_storage)"""
        self.config_dir.mkdir(exist_ok=True)
        api_key_file = self.config_dir / "api_key"
        api_key_file.write_text(api_key)

    class Config:
        env_file = ".env"

settings = Settings()
