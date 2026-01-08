"""MCP (Model Context Protocol) router for Claude.ai integration."""

import asyncio
import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.mcp.server import MCPServer
from app.mcp.tools import MCP_TOOLS


router = APIRouter()


class MCPMessageRequest(BaseModel):
    """Request body for MCP messages endpoint."""

    type: str  # "tool_call" or "list_tools"
    name: Optional[str] = None  # Tool name (for tool_call)
    arguments: Optional[dict[str, Any]] = None  # Tool arguments (for tool_call)


class MCPToolCallResponse(BaseModel):
    """Response for MCP tool calls."""

    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@router.get("/sse")
async def sse_connection(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """SSE connection endpoint for Claude.ai MCP integration.

    Sends:
    1. `event: open` - Connection confirmation
    2. `event: tools` - List of available tools

    Then maintains connection with periodic keep-alive.
    """

    async def event_stream():
        # Send connection open event
        yield 'event: open\ndata: {"status": "connected"}\n\n'

        # Send tools list
        tools_data = json.dumps({"tools": MCP_TOOLS})
        yield f"event: tools\ndata: {tools_data}\n\n"

        # Keep connection alive
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Send keep-alive ping every 30 seconds
                yield ": keep-alive\n\n"
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sse")
async def sse_post_handler(
    request: MCPMessageRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Handle POST requests to SSE endpoint (Claude.ai sends tool calls here)."""
    if request.type == "list_tools":
        return {"tools": MCP_TOOLS}

    elif request.type == "tool_call":
        if not request.name:
            return {"error": "Tool name is required for tool_call"}

        mcp_server = MCPServer(session)
        result = await mcp_server.call_tool(
            request.name,
            request.arguments or {},
        )
        return result

    else:
        return {"error": f"Unknown message type: {request.type}"}


@router.post("/messages")
async def handle_message(
    request: MCPMessageRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Handle MCP messages from Claude.ai.

    Supports:
    - `type: "list_tools"` - Returns list of available tools
    - `type: "tool_call"` - Executes a tool and returns result
    """
    if request.type == "list_tools":
        return {"tools": MCP_TOOLS}

    elif request.type == "tool_call":
        if not request.name:
            return {"error": "Tool name is required for tool_call"}

        mcp_server = MCPServer(session)
        result = await mcp_server.call_tool(
            request.name,
            request.arguments or {},
        )
        return result

    else:
        return {"error": f"Unknown message type: {request.type}"}
