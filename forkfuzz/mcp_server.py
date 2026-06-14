"""FORKFUZZ MCP server — exposes fuzz() as an MCP tool for Cognis.Studio."""
from __future__ import annotations

import json


def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-forkfuzz[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-forkfuzz[mcp]'")
        return 1

    from forkfuzz.core import SpecError, fuzz, load_spec

    app = FastMCP("forkfuzz")

    @app.tool()
    def forkfuzz_scan(spec_path: str) -> str:
        """Fuzz a JSON contract spec for invariant violations. Returns JSON findings."""
        try:
            spec = load_spec(spec_path)
        except FileNotFoundError:
            return json.dumps({"error": f"spec file not found: {spec_path}"})
        except SpecError as exc:
            return json.dumps({"error": str(exc)})
        report = fuzz(spec)
        return json.dumps(report.to_dict(), indent=2, default=str)

    app.run()
    return 0
