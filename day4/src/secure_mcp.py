import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.auth import require_scopes

load_dotenv()


verifier = StaticTokenVerifier(
    tokens={
        os.environ["MCP_STUDENT_TOKEN"]: {
            "client_id": "student",
            "scopes": ["read:public"],
        },
        os.environ["MCP_ADMIN_TOKEN"]: {
            "client_id": "admin",
            "scopes": ["read:public", "read:internal"],
        },
    }
)

mcp = FastMCP("Secure Tools", auth=verifier)


@mcp.tool
def get_server_time() -> str:
    """Return the current server time."""
    from datetime import datetime
    return datetime.now().astimezone().isoformat()

@mcp.tool(auth=require_scopes("read:internal"))
def get_internal_report() -> dict:
    """Return protected internal data."""
    return {
        "status": "ok",
        "message": "This is protected internal data.",
    }


@mcp.tool(auth=require_scopes("read:internal"))
def get_student_performance() -> dict:
    """Return protected student performance data."""
    return {
        "students": [
            {
                "name": "Student A",
                "math": 85,
                "programming": 90,
                "data_science": 88,
            },
            {
                "name": "Student B",
                "math": 72,
                "programming": 80,
                "data_science": 75,
            },
            {
                "name": "Student C",
                "math": 95,
                "programming": 92,
                "data_science": 94,
            },
            {
                "name": "Student D",
                "math": 68,
                "programming": 70,
                "data_science": 73,
            },
        ]
    }

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8002,
    )