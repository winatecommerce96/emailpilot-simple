#!/usr/bin/env python3
"""
Discover available MCP tools by querying the discovery endpoint.

This script makes an authenticated request to /mcp/tools to see
what tools are actually available on the MCP server.
"""

import asyncio
import httpx
import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from data.secret_manager_client import SecretManagerClient


async def discover_tools():
    """Query the MCP server to discover available tools."""

    print("=" * 80)
    print("MCP TOOLS DISCOVERY")
    print("=" * 80)

    # Get Klaviyo API key from Secret Manager
    print("\n1. Fetching Klaviyo API key from Secret Manager...")
    try:
        secret_manager = SecretManagerClient()
        api_key = secret_manager.get_api_key("rogue-creamery")
        print(f"   ✅ API key retrieved: {api_key[:10]}...{api_key[-10:]}")
    except Exception as e:
        print(f"   ❌ Failed to get API key: {e}")
        return

    # Get MCP auth token from environment
    print("\n2. Checking MCP_AUTH_TOKEN environment variable...")
    auth_token = os.getenv("MCP_AUTH_TOKEN")
    if auth_token:
        print(f"   ✅ MCP_AUTH_TOKEN found: {auth_token[:20]}...")
    else:
        print("   ❌ MCP_AUTH_TOKEN not set")
        print("   Please set: export MCP_AUTH_TOKEN=<your-token>")
        return

    # Make authenticated request to discovery endpoint
    print("\n3. Querying /mcp/tools endpoint...")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(
                "http://localhost:3334/mcp/tools",
                headers={
                    "X-Klaviyo-API-Key": api_key,
                    "Authorization": f"Bearer {auth_token}"
                }
            )

            print(f"   Status Code: {response.status_code}")

            if response.status_code == 200:
                print("   ✅ Request successful!")

                # Parse and display tools
                data = response.json()
                print("\n4. Available MCP Tools:")
                print("=" * 80)

                if isinstance(data, dict):
                    tools = data.get("tools", [])
                    if tools:
                        print(f"\nFound {len(tools)} tools:\n")
                        for i, tool in enumerate(tools, 1):
                            if isinstance(tool, dict):
                                name = tool.get("name", "Unknown")
                                description = tool.get("description", "No description")
                                print(f"{i}. {name}")
                                print(f"   {description}\n")
                            else:
                                print(f"{i}. {tool}\n")
                    else:
                        print("\nNo tools found in response")
                        print(f"\nRaw response: {data}")
                else:
                    print(f"\nRaw response: {data}")

            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text}")

        except httpx.HTTPError as e:
            print(f"   ❌ HTTP error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(discover_tools())
