import logging
import docker
import asyncio
import json
from typing import Optional, AsyncGenerator
from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..models.instance import Instance

from ..core.config import settings
from ..core.crypto import CryptoManager
import asyncssh


logger = logging.getLogger(__name__)

class InstanceService:
    def __init__(self, db: Session):
        self.db = db
        self.crypto = CryptoManager()
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.docker_client = None

    # Config
    IMAGE_NAME = settings.instance_image_name
    NETWORK_NAME = settings.instance_network_name
    VNC_PORT_START = settings.vnc_port_start
    VNC_PORT_END = settings.vnc_port_end

    def get_instance(self, session_id: str) -> Optional[Instance]:
        return self.db.query(Instance).filter(Instance.session_id == session_id).first()

    def _wait_for_port(self, ip: str, port: int, timeout: int = 15):
        import socket
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.create_connection((ip, port), timeout=1):
                    return True
            except (OSError, ConnectionRefusedError):
                time.sleep(0.5)
        return False

    def spawn_instance(self, session_id: str) -> Instance:
        if not self.docker_client:
             raise HTTPException(status_code=500, detail="Docker client not available")

        # Check existing
        existing = self.get_instance(session_id)
        if existing:
            # Check if actually running
            try:
                container = self.docker_client.containers.get(existing.container_id)
                if container.status == "running":
                    return existing
                else:
                    # For simplicity, if stopped, we consider it dead and spawn new (or restart)
                    # For MVP: remove old rec and spawn new
                    self._cleanup_instance(existing)
            except docker.errors.NotFound:
                # Ghost record
                self._cleanup_instance(existing)
        
        # Generate SSH Key Pair (Ephemeral)
        private_key, public_key = self.crypto.generate_ssh_keys()

        # Encrypt Private Key
        enc_private_key = self.crypto.encrypt(private_key).decode('utf-8') # Store as base64 string
        ssh_username = settings.ssh_username
        ssh_port = settings.ssh_port

        # Try to spawn with retries on port conflict
        retries = 5
        excluded_ports = []
        
        for attempt in range(retries):
            # Find free port
            vnc_port = self._find_free_port(excluded_ports)
            if not vnc_port:
                 raise HTTPException(status_code=503, detail="No free VNC ports available")

            # Cleanup any existing container with this name (to ensure idempotency)
            # Even if not in DB, we want to own this name.
            container_name = f"worker-{session_id}"
            try:
                old_c = self.docker_client.containers.get(container_name)
                logger.info(f"Removing orphaned container {container_name}")
                old_c.remove(force=True)
            except docker.errors.NotFound:
                pass

            # Spawn
            try:
                logger.info(f"Spawning instance for session {session_id} on port {vnc_port} (attempt {attempt+1})")
                container = self.docker_client.containers.run(
                    self.IMAGE_NAME,
                    name=container_name,
                    detach=True,
                    network=self.NETWORK_NAME,
                    ports={'6080/tcp': vnc_port},
                    environment=[
                        f"SSH_PUBLIC_KEY={public_key}",
                        f"SSH_USERNAME={ssh_username}"
                    ],
                    extra_hosts={"minio": "host-gateway"}
                )
                
                # Create DB Record
                # We need the internal IP.
                # Reload container to get attrs
                container.reload()
                # Net settings
                ip_address = container.attrs['NetworkSettings']['Networks'][self.NETWORK_NAME]['IPAddress']
                
                instance = Instance(
                    session_id=session_id,
                    container_id=container.id,
                    status="starting",
                    host=ip_address,
                    vnc_port=vnc_port,
                    ssh_port=ssh_port,
                    ssh_username=ssh_username,
                    ssh_private_key_enc=enc_private_key
                )
                self.db.add(instance)
                self.db.commit()
                self.db.refresh(instance)
                
                # Wait for SSH port
                self._wait_for_port(ip_address, port=22)
                # Wait for VNC port (5900) to ensure desktop is ready
                self._wait_for_port(ip_address, port=5900)
                # Wait for noVNC port (6080) to ensure web client is ready
                self._wait_for_port(ip_address, port=6080)
                
                return instance

            except docker.errors.APIError as e:
                if "port is already allocated" in str(e):
                    logger.warning(f"Port {vnc_port} already allocated, retrying...")
                    excluded_ports.append(vnc_port)
                    continue
                else:
                    logger.error(f"Failed to spawn container: {e}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"Failed to spawn instance: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to spawn container: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to spawn instance: {str(e)}")
        
        raise HTTPException(status_code=500, detail="Failed to find a free port after retries")

    def _find_free_port(self, excluded_ports: list[int] = []) -> Optional[int]:
        # Simple check against DB records
        # In a robust system, check actual netstat, but DB + try/catch is okay for now
        used_ports = [
            i.vnc_port for i in self.db.query(Instance).filter(Instance.status == "running").all()
            if i.vnc_port
        ]
        
        for port in range(self.VNC_PORT_START, self.VNC_PORT_END + 1):
            if port not in used_ports and port not in excluded_ports:
                return port
        return None

    def _cleanup_instance(self, instance: Instance):
        try:
            if instance.container_id:
                try:
                    c = self.docker_client.containers.get(instance.container_id)
                    c.remove(force=True)
                except docker.errors.NotFound:
                    pass
            self.db.delete(instance)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error cleaning up instance {instance.id}: {e}")

    async def monitor_instance(self, session_id: str) -> AsyncGenerator[str, None]:
        """Stream instance status events."""
        retry_count = 0
        loop = asyncio.get_running_loop()
        
        while True:
            # Poll current status
            instance = await loop.run_in_executor(None, lambda: self.db.commit() or self.get_instance(session_id))
            
            payload = {
                "id": None, 
                "session_id": session_id,
                "status": "pending",
                "vnc_port": None
            }
            
            if instance:
                if instance.status == "starting":
                    # Check if SSH and VNC are ready
                    is_ssh_ready = await loop.run_in_executor(None, lambda: self._wait_for_port(instance.host, 22, timeout=1))
                    is_vnc_ready = await loop.run_in_executor(None, lambda: self._wait_for_port(instance.host, 5900, timeout=1))
                    is_novnc_ready = await loop.run_in_executor(None, lambda: self._wait_for_port(instance.host, 6080, timeout=1))
                    
                    if is_ssh_ready and is_vnc_ready and is_novnc_ready:
                         instance.status = "running"
                         await loop.run_in_executor(None, lambda: self.db.commit())
                
                payload = {
                    "id": instance.id,
                    "session_id": instance.session_id,
                    "status": instance.status,
                    "vnc_port": instance.vnc_port,
                    "created_at": str(instance.created_at),
                    "updated_at": str(instance.updated_at)
                }

            yield json.dumps(payload)

            if payload["status"] == "running":
                break
            
            retry_count += 1
            if retry_count > 300:
                yield json.dumps({"error": "Timeout waiting for instance"})
                break

            await asyncio.sleep(1)
