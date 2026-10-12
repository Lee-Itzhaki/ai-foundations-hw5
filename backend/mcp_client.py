"""MCP client used by the API layer and the human-approval path.

This is not a second data layer: it only calls tools on the same
campus-customs MCP server the agents use, over stdio.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from . import config


class MCPCallError(RuntimeError):
    pass


def _transport() -> StdioTransport:
    return StdioTransport(command=config.MCP_PYTHON, args=[str(config.MCP_SERVER_SCRIPT)],
                          cwd=str(config.PROJECT_ROOT))


class MCPGateway:
    """A long-lived MCP client connection, serialized with a lock."""

    def __init__(self) -> None:
        self._client: Client | None = None
        self._lock = asyncio.Lock()

    async def _ensure(self) -> Client:
        if self._client is None:
            client = Client(_transport())
            await client.__aenter__()
            self._client = client
        return self._client

    async def call(self, tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._lock:
            client = await self._ensure()
            try:
                res = await client.call_tool(tool, args or {}, raise_on_error=False)
            except Exception as exc:
                await self._close_locked()
                raise MCPCallError(f"MCP call {tool} failed: {exc}") from exc
        if res.is_error or not isinstance(res.structured_content, dict):
            raise MCPCallError(f"MCP tool {tool} returned an error: {str(res.content)[:300]}")
        return res.structured_content

    async def restart(self) -> None:
        """Drop the server process (and any SQLite handles it holds)."""
        async with self._lock:
            await self._close_locked()

    async def close(self) -> None:
        await self.restart()

    async def _close_locked(self) -> None:
        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
            finally:
                self._client = None
