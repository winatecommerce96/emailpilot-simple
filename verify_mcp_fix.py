#!/usr/bin/env python3
"""
Verification script for NativeMCPClient fixes.
Tests that we can spawn MCP servers and fetch Klaviyo data including reports.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

# Ensure we can import from data
import sys
sys.path.insert(0, str(Path(__file__).parent))

from data.native_mcp_client import NativeMCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def verify_mcp_fix():
    """Test native MCP client with Rogue Creamery"""
    logger.info("Starting NativeMCPClient verification...")

    # Use the ~/.mcp.json config file
    config_path = Path.home() / ".mcp.json"
    if not config_path.exists():
        logger.error(f"MCP config not found at {config_path}")
        return

    logger.info(f"Using MCP config: {config_path}")

    try:
        # Initialize native MCP client
        async with NativeMCPClient(config_path=str(config_path)) as mcp_client:
            logger.info("MCP client initialized successfully")

            # Test fetching data for Rogue Creamery
            client_name = "rogue-creamery"
            logger.info(f"\nFetching data for {client_name}...")

            data = await mcp_client.fetch_all_data(
                client_name=client_name,
                start_date="2025-01-01",
                end_date="2025-01-31"
            )

            # Print results
            logger.info("\n" + "=" * 80)
            logger.info("RESULTS")
            logger.info("=" * 80)
            logger.info(f"Segments: {len(data.get('segments', []))}")
            logger.info(f"Campaigns: {len(data.get('campaigns', []))}")
            logger.info(f"Flows: {len(data.get('flows', []))}")
            logger.info(f"Metrics: {len(data.get('metrics', []))}")
            logger.info(f"Lists: {len(data.get('lists', []))}")
            logger.info(f"Catalog Items: {len(data.get('catalog_items', []))}")

            campaign_report = data.get('campaign_report', {})
            logger.info(f"Campaign Report Keys: {list(campaign_report.keys()) if campaign_report else 'None'}")
            
            flow_report = data.get('flow_report', {})
            logger.info(f"Flow Report Keys: {list(flow_report.keys()) if flow_report else 'None'}")

            if data.get('error'):
                logger.error(f"Error: {data['error']}")

            logger.info("\n" + "=" * 80)
            logger.info("VERIFICATION COMPLETE")
            logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(verify_mcp_fix())
