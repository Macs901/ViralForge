#!/usr/bin/env python3
"""ViralForge MCP Server Launcher.

Usage:
    python run_mcp_server.py [--transport sse|stdio] [--host HOST] [--port PORT]

Environment Variables:
    MCP_TRANSPORT: Transport protocol (sse or stdio, default: sse)
    MCP_HOST: Host to bind (default: 0.0.0.0)
    MCP_PORT: Port to bind (default: 8001)
"""

import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    parser = argparse.ArgumentParser(description="ViralForge MCP Server")
    parser.add_argument(
        "--transport",
        choices=["sse", "stdio"],
        default=os.getenv("MCP_TRANSPORT", "sse"),
        help="Transport protocol (default: sse)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "0.0.0.0"),
        help="Host to bind for SSE transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8001")),
        help="Port to bind for SSE transport (default: 8001)",
    )
    args = parser.parse_args()

    # Set environment for the server
    os.environ["MCP_HOST"] = args.host
    os.environ["MCP_PORT"] = str(args.port)
    os.environ["MCP_TRANSPORT"] = args.transport

    print(f"Starting ViralForge MCP Server...")
    print(f"  Transport: {args.transport}")
    if args.transport == "sse":
        print(f"  Endpoint:  http://{args.host}:{args.port}/sse")
    print()

    from src.mcp import run_server
    run_server(transport=args.transport)


if __name__ == "__main__":
    main()
