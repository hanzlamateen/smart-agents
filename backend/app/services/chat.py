import logging
import json
import asyncio
import httpx
from typing import List, Dict, Any, AsyncGenerator, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from ..models import Session as DBSession, Message as DBMessage, AgentSettings
from ..schemas import ChatRequest
from ..schemas.providers import APIProvider
from ..loop import sampling_loop
from ..infra.storage import storage
from ..core.message_utils import MessageUtils
from ..services.agent_settings import AgentSettingsService
from ..services.session import SessionService
from ..services.instance import InstanceService
from ..core.config import settings as app_settings
import asyncssh

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.settings_service = AgentSettingsService(db)
        self.session_service = SessionService(db)
        self.instance_service = InstanceService(db)

    def validate_session(self, session_id: str) -> DBSession:
        """Fetch and validate session exists."""
        try:
            db_session = self.db.query(DBSession).filter(DBSession.id == session_id).first()
            if not db_session:
                logger.warning(f"Session validation failed: Session {session_id} not found")
                raise HTTPException(status_code=404, detail="Session not found")
            return db_session
        except SQLAlchemyError as e:
            logger.error(f"Database error validating session {session_id}: {e}", exc_info=True)
            raise

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Reconstruct chat history from DB for Anthropic API."""
        try:
            db_messages = self.db.query(DBMessage).filter(DBMessage.session_id == session_id).order_by(DBMessage.created_at).all()
            
            messages = []
            for msg in db_messages:
                content_blocks = self._process_message_content(msg.content)
                messages.append({
                    "role": msg.role,
                    "content": content_blocks
                })

            MessageUtils.prune_broken_history(messages, db_messages)
            return messages
        except SQLAlchemyError as e:
            logger.error(f"Failed to get history for session {session_id}: {e}", exc_info=True)
            raise

    def save_message(self, session_id: str, role: str, content: Any) -> DBMessage:
        """Save a single message to the database."""
        try:
            db_msg = DBMessage(
                session_id=session_id,
                role=role,
                content=content
            )
            self.db.add(db_msg)
            self.db.commit()
            return db_msg
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to save message to session {session_id}: {e}", exc_info=True)
            raise

    async def run_chat(self, session_id: str, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Orchestrate the chat interaction.
        1. Validate Session & Instance.
        2. Prepare History & Settings.
        3. Run Local Sampling Loop (SSH to Worker).
        """
        # 1. Validate Session & Get Instance
        self.validate_session(session_id)
        instance = self.instance_service.get_instance(session_id)
        
        if not instance or instance.status != "running":
             try:
                 logger.info(f"Instance not ready for {session_id}, spawning now...")
                 instance = self.instance_service.spawn_instance(session_id)
             except Exception as e:
                 raise HTTPException(status_code=503, detail=f"Failed to spawn instance: {e}")
        
        # Extract credentials early to avoid detachment issues after db.commit()
        ssh_host = instance.host
        ssh_port = instance.ssh_port
        ssh_username = instance.ssh_username or app_settings.ssh_username
        ssh_private_key_enc = instance.ssh_private_key_enc

        # 2. Prepare Data
        history = self.get_history(session_id)
        settings = self.settings_service.get_settings()
        
        # Save User Message locally
        user_content = [{"type": "text", "text": request.message}]
        self.save_message(session_id, "user", user_content)
        
        # Append to history for payload
        history.append({"role": "user", "content": user_content})

        # 3. Running Local Loop
        # We process events to save history and yield to SSE 
        
        async def chat_generator():
            s3_key_map = {}
            current_assistant_content = []
            
            # Helper to save whatever we have collected so far
            def save_assistant_partial():
                nonlocal current_assistant_content
                if current_assistant_content:
                    self.save_message(session_id, "assistant", current_assistant_content)
                    current_assistant_content = [] # Create new reference

            # Initialize SSH Connection and Loop
            try:
                # Decrypt Key
                if not ssh_private_key_enc:
                    raise Exception("SSH Private Key not found")
                
                private_key_str = self.instance_service.crypto.decrypt(ssh_private_key_enc)
                priv_key_obj = asyncssh.import_private_key(private_key_str)
                
                logger.info(f"Connecting to SSH at {ssh_host}:{ssh_port}...")
                
                async with asyncssh.connect(
                    ssh_host, 
                    port=ssh_port,
                    username=ssh_username, 
                    client_keys=[priv_key_obj],
                    known_hosts=None
                ) as ssh_client:
                    
                    logger.info("SSH Connection established.")
            
                    # Initialize Sampling Loop
                    loop_gen = sampling_loop(
                        model=settings.model,
                        provider=APIProvider(settings.provider),
                        system_prompt_suffix=settings.system_prompt_suffix,
                        messages=history,
                        api_key=settings.api_key,
                        only_n_most_recent_images=settings.only_n_most_recent_images,
                        max_tokens=settings.max_tokens,
                        thinking_budget=settings.thinking_budget,
                        token_efficient_tools_beta=settings.enable_token_efficient_tools,
                        tool_version=settings.tool_version,
                        session_id=session_id,
                        ssh_client=ssh_client
                    )

                    async for event in loop_gen:
                        yield json.dumps(event)
                        
                        if event.get("type") == "done":
                            break
                        
                        if event.get("type") in ["text", "thinking", "tool_use"]:
                             # Accumulate for saving
                            if event.get("type") == "text":
                                current_assistant_content.append({"type": "text", "text": event["content"]})
                            elif event.get("type") == "thinking":
                                current_assistant_content.append({"type": "thinking", "thinking": event["content"]})
                            elif event.get("type") == "tool_use":
                                current_assistant_content.append({
                                    "type": "tool_use",
                                    "id": event["id"],
                                    "name": event["name"],
                                    "input": event["input"]
                                })

                        if event.get("type") == "tool_result":
                            save_assistant_partial()

                            if event.get("s3_key"):
                                s3_key_map[event["tool_use_id"]] = event["s3_key"]

                            # Optimize and Save Tool Result
                            tool_result_block = {
                                "type": "tool_result",
                                "tool_use_id": event["tool_use_id"],
                                "content": [],
                                "is_error": event.get("error", False)
                            }
                            if event.get("output"):
                                tool_result_block["content"].append({"type": "text", "text": event["output"]})
                            
                            content_to_save = [tool_result_block]
                            content_to_save = self._optimize_content_for_storage(content_to_save, s3_key_map)
                            self.save_message(session_id, "user", content_to_save)

                    # End of Stream
                    save_assistant_partial()
                    
            except Exception as e:
                logger.error(f"Chat Loop Error: {e}", exc_info=True)
                # In SSE, we can yield an event or just log
                yield json.dumps({'type': 'error', 'message': str(e)})

        return chat_generator()

    # --- Private Helpers ---

    def _process_message_content(self, content: Any) -> Any:
        """Process stored message content (rehydration, format compatibility)."""
        if not isinstance(content, list):
            return content

        processed_blocks = []
        for block in content:
            if isinstance(block, dict):
                # Handle Tool Result (S3 Rehydration)
                if block.get("type") == "tool_result":
                    hydrated = MessageUtils.hydrate_anthropic_block(block, storage)
                    if hydrated:
                        processed_blocks.append(hydrated)
                        continue
                    
                    # Handle Legacy/Flat Tool Result conversion
                    converted = MessageUtils.convert_legacy_tool_result(block)
                    if converted:
                        processed_blocks.append(converted)
                        continue
            
            # Default: append as-is
            processed_blocks.append(block)
        
        return processed_blocks

    def _optimize_content_for_storage(self, content: Any, s3_key_map: Dict) -> Any:
        """Replace base64 images with S3 keys in tool results before saving."""
        if not isinstance(content, list):
            return content

        clean_content = []
        modified = False
        
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                tool_use_id = block.get("tool_use_id")
                
                # Check directly mapped S3 keys (from this run)
                if tool_use_id and tool_use_id in s3_key_map:
                    clean_content.append(MessageUtils.create_s3_reference_block(block, s3_key_map[tool_use_id]))
                    modified = True
                    continue
                
            clean_content.append(block)
        
        return clean_content if modified else content

