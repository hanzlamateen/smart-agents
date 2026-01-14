import asyncio
import os
from typing import Any, Literal
import asyncssh

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult


class _BashSession:
    """A session of a bash shell."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 120.0  # seconds
    _sentinel: str = "<<exit>>"

    def __init__(self, ssh_client: asyncssh.SSHClientConnection = None):
        self._started = False
        self._timed_out = False
        self.ssh_client = ssh_client

    async def start(self):
        if self._started:
            return

        if self.ssh_client:
            # Start persistent bash session via SSH
            self._process = await self.ssh_client.create_process(
                self.command,
                term_type="xterm", # Request PTY for interactive behavior
            )
        else:
            raise ToolError("SSH client is required for BashTool")

        self._started = True
        
        # Merge stderr into stdout to avoid blocking on stderr reads
        # Also disable echo to prevent command repetition in output
        self._process.stdin.write("stty -echo; exec 2>&1\n")
        await self._process.stdin.drain()

    def stop(self):
        """Terminate the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return
        self._process.terminate()

    async def run(self, command: str):
        """Execute a command in the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return ToolResult(
                system="tool must be restarted",
                error=f"bash has exited with returncode {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            )

        # we know these are not None because we created the process with PIPEs
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # send command to the process
        self._process.stdin.write(
            command + f"; echo '{self._sentinel}'\n"
        )
        await self._process.stdin.drain()

        # read output from the process, until the sentinel is found
        output = ""
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    if self._sentinel in output:
                        # strip the sentinel and break
                        output = output[: output.index(self._sentinel)]
                        break
                    
                    # Read up to 4kb at a time
                    chunk = await self._process.stdout.read(4096)
                    if not chunk:
                        break
                    output += chunk
                    
        except asyncio.TimeoutError:
            self._timed_out = True
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            ) from None

        if output.endswith("\n"):
            output = output[:-1]

        # Stderr is merged into stdout, so 'error' is always empty here
        error = ""

        return CLIResult(output=output, error=error)


class BashTool20250124(BaseAnthropicTool):
    """
    A tool that allows the agent to run bash commands.
    The tool parameters are defined by Anthropic and are not editable.
    """

    _session: _BashSession | None

    api_type: Literal["bash_20250124"] = "bash_20250124"
    name: Literal["bash"] = "bash"

    def __init__(self, ssh_client: asyncssh.SSHClientConnection = None):
        self._session = None
        self.ssh_client = ssh_client
        super().__init__(ssh_client=ssh_client)

    def to_params(self) -> Any:
        return {
            "type": self.api_type,
            "name": self.name,
        }

    async def __call__(
        self, command: str | None = None, restart: bool = False, **kwargs
    ):
        if restart:
            if self._session:
                self._session.stop()
            self._session = _BashSession(ssh_client=self.ssh_client)
            await self._session.start()

            return ToolResult(system="tool has been restarted.")

        if self._session is None:
            self._session = _BashSession(ssh_client=self.ssh_client)
            await self._session.start()

        if command is not None:
            return await self._session.run(command)

        raise ToolError("no command provided.")


class BashTool20241022(BashTool20250124):
    api_type: Literal["bash_20250124"] = "bash_20250124"  # pyright: ignore[reportIncompatibleVariableOverride]
