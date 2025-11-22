"""FORKFUZZ MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from forkfuzz.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-forkfuzz[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-forkfuzz[mcp]'")
        return 1
    app = FastMCP("forkfuzz")

    @app.tool()
    def forkfuzz_scan(target: str) -> str:
        """Mainnet-fork invariant fuzzer that replays your contract against live state and stateful sequences to break protocol invariants before deploy.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
