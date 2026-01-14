
import platform
import json
from datetime import datetime
from enum import StrEnum
from typing import Any, cast, AsyncGenerator

import httpx
from anthropic import (
    Anthropic,
    AnthropicBedrock,
    AnthropicVertex,
    APIError,
    APIResponseValidationError,
    APIStatusError,
)
from anthropic.types.beta import (
    BetaCacheControlEphemeralParam,
    BetaContentBlockParam,
    BetaImageBlockParam,
    BetaMessage,
    BetaMessageParam,
    BetaTextBlock,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
    BetaToolUseBlockParam,
)

from .tools import (
    TOOL_GROUPS_BY_VERSION,
    ToolCollection,
    ToolResult,
    ToolVersion,
)
from .infra.storage import storage
from .schemas.providers import APIProvider

PROMPT_CACHING_BETA_FLAG = "prompt-caching-2024-07-31"

# Reusing the System Prompt from the original code
SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
* You are utilising an Ubuntu virtual machine using {platform.machine()} architecture with internet access.
* You can feel free to install Ubuntu applications with your bash tool. Use curl instead of wget.
* To open firefox, please just click on the firefox icon.  Note, firefox-esr is what is installed on your system.
* Using bash tool you can start GUI applications, but you need to set export DISPLAY=:1 and use a subshell. For example "(DISPLAY=:1 xterm &)". GUI apps run with bash tool will appear within your desktop environment, but they may take some time to appear. Take a screenshot to confirm it did.
* When using your bash tool with commands that are expected to output very large quantities of text, redirect into a tmp file and use str_replace_based_edit_tool or `grep -n -B <lines before> -A <lines after> <query> <filename>` to confirm output.
* When viewing a page it can be helpful to zoom out so that you can see everything on the page.  Either that, or make sure you scroll down to see everything before deciding something isn't available.
* When using your computer function calls, they take a while to run and send back to you.  Where possible/feasible, try to chain multiple of these calls all into one function calls request.
* The current date is {datetime.today().strftime("%A, %B %-d, %Y")}.
</SYSTEM_CAPABILITY>

<IMPORTANT>
* When using Firefox, if a startup wizard appears, IGNORE IT.  Do not even click "skip this step".  Instead, click on the address bar where it says "Search or enter address", and enter the appropriate search term or URL there.
* If the item you are looking at is a pdf, if after taking a single screenshot of the pdf it seems that you want to read the entire document instead of trying to continue to read the pdf from your screenshots + navigation, determine the URL, use curl to download the pdf, install and use pdftotext to convert it to a text file, and then read that text file directly with your str_replace_based_edit_tool.
</IMPORTANT>"""

import logging

# Configure logger
logger = logging.getLogger("smart_agents")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

async def sampling_loop(
    *,
    model: str,
    provider: APIProvider,
    system_prompt_suffix: str,
    messages: list[BetaMessageParam],
    api_key: str,
    only_n_most_recent_images: int | None = None,
    max_tokens: int = 4096,
    tool_version: ToolVersion = "computer_use_20250124", # Defaulting if not specified
    thinking_budget: int | None = None,
    token_efficient_tools_beta: bool = False,
    session_id: str | None = None,
    on_message: Any | None = None, # Callable[[dict], Awaitable[None]]
    ssh_client: Any | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Agentic sampling loop that calls the Claude API and local implementation of anthropic-defined computer use tools.
    Yields events:
    - { type: "text", content: str }
    - { type: "thinking", content: str }
    - { type: "tool_use", ... }
    - { type: "tool_result", ... }
    - { type: "error", message: str }
    """
    
    # Initialize tools
    try:
        tool_group = TOOL_GROUPS_BY_VERSION[tool_version]
    except KeyError:
         # Fallback or strict error? Let's default if key missing, but here we assume correct input
         # For safety if tool_version is invalid string from API
         tool_group = TOOL_GROUPS_BY_VERSION["computer_use_20250124"]

    tool_collection = ToolCollection(*(ToolCls(ssh_client=ssh_client) for ToolCls in tool_group.tools))
    
    system = BetaTextBlockParam(
        type="text",
        text=f"{SYSTEM_PROMPT}{' ' + system_prompt_suffix if system_prompt_suffix else ''}",
    )

    while True:
        try:
            enable_prompt_caching = False
            betas = [tool_group.beta_flag] if tool_group.beta_flag else []
            if token_efficient_tools_beta:
                betas.append("token-efficient-tools-2025-02-19")
                
            image_truncation_threshold = only_n_most_recent_images or 0
            
            client = None
            if provider == APIProvider.ANTHROPIC:
                if not api_key:
                    msg = {"type": "error", "message": "API Key required for Anthropic"}
                    logger.error(f"Yielding error: {msg}")
                    yield msg
                    return
                client = Anthropic(api_key=api_key, max_retries=4)
                enable_prompt_caching = True
            elif provider == APIProvider.VERTEX:
                client = AnthropicVertex()
            elif provider == APIProvider.BEDROCK:
                client = AnthropicBedrock()

            if enable_prompt_caching:
                betas.append(PROMPT_CACHING_BETA_FLAG)
                _inject_prompt_caching(messages)
                only_n_most_recent_images = 0
                system["cache_control"] = {"type": "ephemeral"} # type: ignore

            if only_n_most_recent_images:
                _maybe_filter_to_n_most_recent_images(
                    messages,
                    only_n_most_recent_images,
                    min_removal_threshold=image_truncation_threshold,
                )
                
            extra_body = {}
            if thinking_budget:
                extra_body = {
                    "thinking": {"type": "enabled", "budget_tokens": thinking_budget}
                }

            try:
                # Using raw_response to get the response, but we might want stream=True to be cooler?
                # The original code used create() (non-streaming) but we want to stream tokens if possible?
                # Original code: client.beta.messages.with_raw_response.create(...)
                # If we want to stream text tokens, we should use .stream(). 
                # BUT, tool use is easier to handle with non-streaming or careful stream handling.
                # For this MVP refactor, let's stick to non-streaming REQUEST to Anthropic (wait for full message),
                # but stream the RESULT to our client. 
                # Optimization: If the user wants real-time token streaming from Claude, we'd need to change this to .stream()
                # and handle partial events. 
                # Given the original code wasn't using stream=True for the API call (it was just await-ing), 
                # I will preserve the logic: Wait for Claude -> Get Message -> Display -> Run Tools -> Repeat.
                
                # Wait, `client` needs to be initialized.
                if not client:
                    yield {"type": "error", "message": f"Provider {provider} not supported or configured"}
                    return

                raw_response = client.beta.messages.with_raw_response.create(
                    max_tokens=max_tokens,
                    messages=messages,
                    model=model,
                    system=[system],
                    tools=tool_collection.to_params(),
                    betas=betas,
                    extra_body=extra_body,
                )
            except (APIStatusError, APIResponseValidationError) as e:
                yield {"type": "error", "message": str(e)}
                return
            except APIError as e:
                yield {"type": "error", "message": str(e)}
                return
            except Exception as e:
                yield {"type": "error", "message": f"Unexpected error: {str(e)}"}
                return

            response = raw_response.parse()
            
            # Parse response into params
            response_params = _response_to_params(response)
            
            # Append assistant message to history
            assistant_msg = {
                "role": "assistant",
                "content": response_params,
            }
            messages.append(assistant_msg)
            if on_message:
                await on_message(assistant_msg)

            # Yield content blocks (Text, Thinking, ToolUse)
            for content_block in response_params:
                if isinstance(content_block, dict):
                    if content_block.get("type") == "text":
                        msg = {"type": "text", "content": content_block.get("text")}
                        logger.info(f"Yielding text: {msg['content'][:50]}...")
                        yield msg
                    elif content_block.get("type") == "thinking":
                        msg = {"type": "thinking", "content": content_block.get("thinking")}
                        logger.info("Yielding thinking block")
                        yield msg
                    elif content_block.get("type") == "tool_use":
                        msg = {"type": "tool_use", "name": content_block["name"], "input": content_block.get("input"), "id": content_block["id"]}
                        logger.info(f"Yielding tool use: {msg['name']}")
                        yield msg
            
            tool_result_content: list[BetaToolResultBlockParam] = []
            
            # Process tool calls
            for content_block in response_params:
                if isinstance(content_block, dict) and content_block.get("type") == "tool_use":
                    tool_use_block = cast(BetaToolUseBlockParam, content_block)
                    tool_id = tool_use_block["id"]
                    tool_name = tool_use_block["name"]
                    tool_input = cast(dict[str, Any], tool_use_block.get("input", {}))
                    
                    # Execute tool
                    logger.info(f"Running tool: {tool_name}")
                    result = await tool_collection.run(
                        name=tool_name,
                        tool_input=tool_input
                    )
                    
                    # Create result block
                    result_block = _make_api_tool_result(result, tool_id)
                    tool_result_content.append(result_block)
                    
                    # Upload image to S3 if present
                    image_url = None
                    s3_key = None
                    if result.base64_image:
                        logger.info("Uploading image to S3...")
                        folder = f"{session_id}/screenshots" if session_id else "screenshots"
                        s3_result = storage.upload_base64_image(result.base64_image, folder=folder)
                        if s3_result:
                            image_url = s3_result["public_url"]
                            s3_key = s3_result["s3_key"]
                            logger.info(f"Image uploaded to S3: {s3_key}")
                        else:
                            logger.error("Failed to upload image, falling back to base64")

                    # Yield tool result
                    msg = {
                        "type": "tool_result", 
                        "tool_use_id": tool_id, 
                        "output": result.output, 
                        "error": result.error,
                        # Send URL if available, otherwise fallback (or None)
                        "image_url": image_url,
                        "s3_key": s3_key,
                        "base64_image": result.base64_image if not s3_key else None
                    }
                    logger.info(f"Yielding tool result for {tool_name}")
                    yield msg

            if not tool_result_content:
                # Stop if no tools called
                logger.info("No tool calls, finishing stream")
                yield {"type": "done"}
                return # Exits loop

            # Prepare for next turn
            tool_msg = {"content": tool_result_content, "role": "user"}
            messages.append(tool_msg)
            if on_message:
                await on_message(tool_msg)
        
        except Exception as e:
            logger.error(f"Error in sampling loop: {e}", exc_info=True)
            yield {"type": "error", "message": f"Internal Error: {e}"}
            return


def _maybe_filter_to_n_most_recent_images(
    messages: list[BetaMessageParam],
    images_to_keep: int,
    min_removal_threshold: int,
):
    if images_to_keep is None:
        return messages

    tool_result_blocks = cast(
        list[BetaToolResultBlockParam],
        [
            item
            for message in messages
            for item in (
                message["content"] if isinstance(message["content"], list) else []
            )
            if isinstance(item, dict) and item.get("type") == "tool_result"
        ],
    )

    total_images = sum(
        1
        for tool_result in tool_result_blocks
        for content in tool_result.get("content", [])
        if isinstance(content, dict) and content.get("type") == "image"
    )

    images_to_remove = total_images - images_to_keep
    images_to_remove -= images_to_remove % min_removal_threshold

    for tool_result in tool_result_blocks:
        if isinstance(tool_result.get("content"), list):
            new_content = []
            for content in tool_result.get("content", []):
                if isinstance(content, dict) and content.get("type") == "image":
                    if images_to_remove > 0:
                        images_to_remove -= 1
                        continue
                new_content.append(content)
            tool_result["content"] = new_content


def _response_to_params(
    response: BetaMessage,
) -> list[BetaContentBlockParam]:
    res: list[BetaContentBlockParam] = []
    for block in response.content:
        if isinstance(block, BetaTextBlock):
            if block.text:
                res.append(BetaTextBlockParam(type="text", text=block.text))
            elif getattr(block, "type", None) == "thinking":
                thinking_block = {
                    "type": "thinking",
                    "thinking": getattr(block, "thinking", None),
                }
                if hasattr(block, "signature"):
                    thinking_block["signature"] = getattr(block, "signature", None)
                res.append(cast(BetaContentBlockParam, thinking_block))
        else:
            res.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return res


def _inject_prompt_caching(
    messages: list[BetaMessageParam],
):
    breakpoints_remaining = 3
    for message in reversed(messages):
        if message["role"] == "user" and isinstance(
            content := message["content"], list
        ):
            if breakpoints_remaining:
                breakpoints_remaining -= 1
                content[-1]["cache_control"] = BetaCacheControlEphemeralParam( # type: ignore
                    {"type": "ephemeral"}
                )
            else:
                if isinstance(content[-1], dict) and "cache_control" in content[-1]:
                    del content[-1]["cache_control"] # type: ignore
                break


def _make_api_tool_result(
    result: ToolResult, tool_use_id: str
) -> BetaToolResultBlockParam:
    tool_result_content: list[BetaTextBlockParam | BetaImageBlockParam] | str = []
    is_error = False
    if result.error:
        is_error = True
        tool_result_content = [
            {
                "type": "text",
                "text": _maybe_prepend_system_tool_result(result, result.error),
            }
        ]
    else:
        if result.output:
            tool_result_content.append(
                {
                    "type": "text",
                    "text": _maybe_prepend_system_tool_result(result, result.output),
                }
            )
        if result.base64_image:
            tool_result_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": result.base64_image,
                    },
                }
            )
    tool_result_block = {
        "type": "tool_result",
        "content": tool_result_content,
        "tool_use_id": tool_use_id,
    }
    
    if is_error:
        tool_result_block["is_error"] = True
        
    return tool_result_block


def _maybe_prepend_system_tool_result(result: ToolResult, result_text: str):
    if result.system:
        result_text = f"<system>{result.system}</system>\n{result_text}"
    return result_text
