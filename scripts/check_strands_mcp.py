import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "uv", "tool", "run", "--with", "mcp<2", "strands-agents-mcp-server==0.2.7"],
    )
    async with (
        stdio_client(server) as (reader, writer),
        ClientSession(reader, writer) as session,
    ):
        info = await session.initialize()
        listing = await session.list_tools()
        print("Server:", info.server_info.name)
        print("Tools:", ", ".join(t.name for t in listing.tools))
        result = await session.call_tool("search_docs", {"query": "Gemini provider"})
        print("Search succeeded:", not result.is_error)


asyncio.run(main())
