from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, fields, replace
from typing import Any
import asyncssh

from anthropic.types.beta import BetaToolUnionParam


class BaseAnthropicTool(metaclass=ABCMeta):
    """Abstract base class for Anthropic-defined tools."""
    
    def __init__(self, ssh_client: asyncssh.SSHClientConnection = None):
        self.ssh_client = ssh_client

    @abstractmethod
    def __call__(self, **kwargs) -> Any:
        """Executes the tool with the given arguments."""
        ...

    @abstractmethod
    def to_params(
        self,
    ) -> BetaToolUnionParam:
        raise NotImplementedError
        
    async def execute_command(self, command: str) -> tuple[str, str, int]:
        """Execute a command either via SSH (if client available) or local subprocess."""
        if self.ssh_client:
            # asyncssh run returns a CompletedProcess-like object
            result = await self.ssh_client.run(command)
            # asyncssh returns stdout as string if encoding is set (default utf-8 in run)
            return (result.stdout or "", result.stderr or "", result.returncode)
        
        raise ToolError("SSH client not available for command execution")



@dataclass(kw_only=True, frozen=True)
class ToolResult:
    """Represents the result of a tool execution."""

    output: str | None = None
    error: str | None = None
    base64_image: str | None = None
    system: str | None = None

    def __bool__(self):
        return any(getattr(self, field.name) for field in fields(self))

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: str | None, other_field: str | None, concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            base64_image=combine_fields(self.base64_image, other.base64_image, False),
            system=combine_fields(self.system, other.system),
        )

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        return replace(self, **kwargs)


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""


class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message
