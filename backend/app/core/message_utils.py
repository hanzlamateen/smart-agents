from typing import List, Dict, Any, Optional
import json
from ..models import Message as DBMessage

class MessageUtils:
    @staticmethod
    def hydrate_anthropic_block(block: Dict, storage_client) -> Optional[Dict]:
        """
        Check for S3 key and return hydrated Anthropic block.
        """
        s3_key = block.get("s3_key")
        if not s3_key:
            return None

        base64_img = storage_client.get_image_base64(s3_key)
        if not base64_img:
            return None

        is_error = block.get("error") is not None
        
        if is_error:
            # API Restriction: No images allowed directly if is_error is True
            # Use error message as text content
            error_msg = block.get("error") if isinstance(block.get("error"), str) else "Error occurred"
            
            return {
                "type": "tool_result",
                "tool_use_id": block.get("tool_use_id"),
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True
            }

        hydrated_content = []
        if block.get("output"):
            hydrated_content.append({"type": "text", "text": block.get("output")})
        
        hydrated_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64_img
            }
        })
        
        return {
            "type": "tool_result",
            "tool_use_id": block.get("tool_use_id"),
            "content": hydrated_content,
            "is_error": False
        }

    @staticmethod
    def create_s3_reference_block(original_block: Dict, s3_key: str) -> Dict:
        """Create a lightweight DB block pointing to S3."""
        clean_block = {
            "type": "tool_result",
            "tool_use_id": original_block.get("tool_use_id"),
            "s3_key": s3_key,
            "output": None,
            "error": original_block.get("is_error")
        }
        
        # Extract text output if present
        if isinstance(original_block.get("content"), list):
            texts = [b.get("text") for b in original_block["content"] if b.get("type") == "text"]
            if texts:
                clean_block["output"] = "\n".join(texts)
                
        return clean_block

    @staticmethod
    def convert_legacy_tool_result(block: Dict) -> Dict | None:
        """Convert loop.py's flat yield format to API nested content format if needed."""
        if "content" in block:
            return None 

        api_content = []
        if block.get("output"):
            api_content.append({"type": "text", "text": block.get("output")})
        
        if block.get("base64_image"):
            api_content.append({
                "type": "image", 
                "source": {"type": "base64", "media_type": "image/png", "data": block.get("base64_image")}
            })

        is_error = block.get("is_error")
        if is_error is None and block.get("error"):
             is_error = True

        if is_error:
             # Reduce to text only
             api_content = []
             if block.get("output"):
                 api_content.append({"type": "text", "text": block.get("output")})
             elif block.get("error") and isinstance(block.get("error"), str):
                 api_content.append({"type": "text", "text": block.get("error")})
                 
             return {
                "type": "tool_result",
                "tool_use_id": block.get("tool_use_id"),
                "content": api_content,
                "is_error": True
            }

        return {
            "type": "tool_result",
            "tool_use_id": block.get("tool_use_id"),
            "content": api_content,
            "is_error": False
        }

    @staticmethod
    def prune_broken_history(messages: List[Dict], db_messages: List[DBMessage]):
        """
        Sanitize history to ensure strict ToolUse -> ToolResult pairing.
        1. Remove 'dangling' tool_use blocks (not followed by result).
        2. Remove 'orphaned' tool_result blocks (not preceded by use).
        """
        if not messages:
            return

        # --- Pass 1: Prune Dangling Tool Uses ---
        # We modify messages in-place or build new list. In-place is harder with indices.
        # Let's verify each Assistant message.
        
        for i, msg in enumerate(messages):
            if msg["role"] == "assistant" and isinstance(msg["content"], list):
                # Check for tool_uses
                new_content = []
                has_changes = False
                
                for block in msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tid = block.get("id")
                        # Look ahead to i+1
                        is_answered = False
                        if i + 1 < len(messages):
                            next_msg = messages[i+1]
                            if next_msg["role"] == "user" and isinstance(next_msg["content"], list):
                                # Does next_msg contain result for tid?
                                for nb in next_msg["content"]:
                                    if isinstance(nb, dict) and nb.get("type") == "tool_result" and nb.get("tool_use_id") == tid:
                                        is_answered = True
                                        break
                        
                        if is_answered:
                            new_content.append(block)
                        else:
                            # Dangling! Strip it.
                            print(f"Pruning dangling tool_use {tid} in message {i}")
                            has_changes = True
                    else:
                        new_content.append(block)
                
                if has_changes:
                    msg["content"] = new_content

        # Remove empty assistant messages (if they became empty after pruning)
        # (Though we might want to keep empty text? No, empty content is invalid).
        messages[:] = [m for m in messages if not (m["role"] == "assistant" and not m["content"])]

        # --- Pass 2: Prune Orphaned Tool Results ---
        # (Standard logic: Ensure every result has a pending use)
        
        cleaned_messages = []
        pending_tool_ids = set()
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "assistant":
                pending_tool_ids = set()
                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            pending_tool_ids.add(b.get("id"))
                cleaned_messages.append(msg)
                
            elif role == "user":
                if isinstance(content, list):
                    new_content = []
                    modified = False
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            tid = b.get("tool_use_id")
                            if tid and tid in pending_tool_ids:
                                new_content.append(b)
                                pending_tool_ids.remove(tid)
                            else:
                                print(f"Pruning orphaned tool_result {tid}")
                                modified = True
                        else:
                            new_content.append(b)
                    
                    if modified:
                        if new_content:
                            msg["content"] = new_content
                            cleaned_messages.append(msg)
                        else:
                            # User message became empty? 
                            # If it was just results, drop it.
                            # If it had text, keep text.
                            pass
                    else:
                        cleaned_messages.append(msg)
                else:
                    cleaned_messages.append(msg)
                
                # Reset pending (strict turns)
                pending_tool_ids = set()

        messages.clear()
        messages.extend(cleaned_messages)
