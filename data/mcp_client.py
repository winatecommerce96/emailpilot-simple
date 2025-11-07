"""
MCP Client for Klaviyo Data Fetching

Fetches campaign, flow, and segment data from the MCP service
running on port 3334. Uses async HTTP requests for parallel data fetching.
"""

import httpx
import asyncio
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from .secret_manager_client import SecretManagerClient

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for fetching Klaviyo data via MCP (Model Context Protocol).

    The MCP service runs on localhost:3334 and provides access to
    Klaviyo data for multiple client accounts.
    """

    def __init__(
        self,
        secret_manager_client: SecretManagerClient,
        host: str = "localhost",
        port: int = 3334,
        timeout: int = 60
    ):
        """
        Initialize MCP client.

        Args:
            secret_manager_client: Client for fetching API keys from Secret Manager
            host: MCP service host (default: localhost)
            port: MCP service port (default: 3334)
            timeout: Request timeout in seconds (default: 60)
        """
        self.secret_manager_client = secret_manager_client
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self.client_name: Optional[str] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_mcp_account_name(self, client_name: str) -> str:
        """
        Convert client name to MCP account name.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            MCP account name (e.g., "Rogue_Creamery_Klaviyo")
        """
        # Map client names to MCP account names
        # This should match the .mcp.json configuration
        mcp_mapping = {
            "rogue-creamery": "Rogue Creamery Klaviyo",
            "vlasic": "Vlasic Klaviyo",
            "colorado-hemp-honey": "Colorado Hemp Honey Klaviyo",
            "wheelchair-getaways": "Wheelchair Getaways Klaviyo",
            "milagro": "Milagro Klaviyo",
            "faso": "FASO Klaviyo",
            "chris-bean": "Chris Bean Klaviyo"
        }

        return mcp_mapping.get(client_name, f"{client_name}_Klaviyo")

    def _get_private_api_key(self, client_name: str) -> str:
        """
        Read PRIVATE_API_KEY from .mcp.json for the client's account.

        This ensures we use the exact API key that the MCP server expects,
        which is embedded in each server instance's environment.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            PRIVATE_API_KEY from .mcp.json

        Raises:
            ValueError: If account not found in .mcp.json
            FileNotFoundError: If .mcp.json doesn't exist
        """
        import json
        from pathlib import Path

        # Path to .mcp.json (three levels up: data/ -> emailpilot-simple/ -> klaviyo-audit-automation/)
        mcp_config_path = Path(__file__).parent.parent.parent / ".mcp.json"

        if not mcp_config_path.exists():
            raise FileNotFoundError(f".mcp.json not found at {mcp_config_path}")

        with open(mcp_config_path, 'r') as f:
            config = json.load(f)

        # Get the account name (e.g., "Rogue Creamery Klaviyo")
        account_name = self._get_mcp_account_name(client_name)

        # Extract account configuration
        account_config = config.get('mcpServers', {}).get(account_name)

        if not account_config:
            raise ValueError(f"Account '{account_name}' not found in .mcp.json")

        # Extract PRIVATE_API_KEY from env
        private_key = account_config.get('env', {}).get('PRIVATE_API_KEY')

        if not private_key:
            raise ValueError(f"PRIVATE_API_KEY not found for account '{account_name}'")

        logger.info(f"Loaded PRIVATE_API_KEY for {account_name} from .mcp.json")

        return private_key

    async def _call_mcp_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call an MCP tool via HTTP.

        Args:
            tool_name: Name of the MCP tool (e.g., "klaviyo_get_campaigns")
            parameters: Tool parameters

        Returns:
            Tool response data

        Raises:
            httpx.HTTPError: If request fails
            RuntimeError: If MCPClient not used as context manager or client_name not set
        """
        if not self._client:
            raise RuntimeError("MCPClient must be used as async context manager")

        if not self.client_name:
            raise RuntimeError("client_name must be set before calling MCP tools")

        # Fetch API key from .mcp.json for this client
        logger.info(f"Fetching API key for {self.client_name} from .mcp.json")
        api_key = self._get_private_api_key(self.client_name)

        # Fetch MCP auth token from environment
        auth_token = os.getenv('MCP_AUTH_TOKEN')
        if not auth_token:
            raise RuntimeError("MCP_AUTH_TOKEN environment variable not set")

        endpoint = f"{self.base_url}/mcp/tools/{tool_name}"

        logger.info(f"Calling MCP tool: {tool_name} with params: {parameters}")

        try:
            response = await self._client.post(
                endpoint,
                json={"params": parameters},
                headers={
                    "X-Klaviyo-API-Key": api_key,
                    "Authorization": f"Bearer {auth_token}"
                }
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"MCP tool {tool_name} succeeded")
            return result

        except httpx.HTTPError as e:
            logger.error(f"MCP tool {tool_name} failed: {str(e)}")
            raise

    async def fetch_segments(
        self,
        client_name: str,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all segments for a client.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")
            fields: Fields to return (default: name, created, updated, is_active)

        Returns:
            List of segment data dictionaries
        """
        self.client_name = client_name

        if fields is None:
            fields = ["name", "created", "updated", "is_active"]

        result = await self._call_mcp_tool(
            "get_segments",
            {
                "model": "claude",
                "fields": fields
            }
        )

        return result.get("data", [])

    async def fetch_campaigns(
        self,
        client_name: str,
        start_date: str,
        end_date: str,
        channel: str = "email",
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch campaigns for a client within a date range.

        Args:
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            channel: Campaign channel (email, sms, mobile_push)
            fields: Fields to return

        Returns:
            List of campaign data dictionaries
        """
        self.client_name = client_name

        if fields is None:
            fields = [
                "name", "status", "send_time", "audiences",
                "send_strategy", "created_at", "scheduled_at"
            ]

        # Convert dates to datetime for filtering
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # Fetch campaigns with date filters
        result = await self._call_mcp_tool(
            "get_campaigns",
            {
                "model": "claude",
                "channel": channel,
                "fields": fields,
                "filters": [
                    {
                        "field": "send_time",
                        "operator": "greater-or-equal",
                        "value": start_dt.isoformat()
                    }
                ]
            }
        )

        # Filter campaigns within the date range
        campaigns = result.get("data", [])
        filtered_campaigns = []

        for campaign in campaigns:
            send_time = campaign.get("attributes", {}).get("send_time")
            if send_time:
                campaign_dt = datetime.fromisoformat(send_time.replace('Z', '+00:00'))
                if start_dt <= campaign_dt <= end_dt:
                    filtered_campaigns.append(campaign)

        return filtered_campaigns

    async def fetch_campaign_report(
        self,
        client_name: str,
        start_date: str,
        end_date: str,
        statistics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch campaign performance report.

        Args:
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            statistics: Performance metrics to fetch

        Returns:
            Campaign report data
        """
        self.client_name = client_name

        if statistics is None:
            statistics = [
                "recipients", "opens", "opens_unique", "clicks", "clicks_unique",
                "open_rate", "click_rate", "click_to_open_rate",
                "bounced", "bounce_rate", "unsubscribes", "unsubscribe_rate",
                "conversions", "conversion_rate", "revenue_per_recipient"
            ]

        # Get metric ID for conversions (usually "Placed Order")
        metrics = await self._call_mcp_tool(
            "get_metrics",
            {
                "model": "claude",
                "fields": ["name"]
            }
        )

        # Find "Placed Order" metric or use first available
        conversion_metric_id = None
        for metric in metrics.get("data", []):
            if metric.get("attributes", {}).get("name") == "Placed Order":
                conversion_metric_id = metric.get("id")
                break

        if not conversion_metric_id and metrics.get("data"):
            conversion_metric_id = metrics["data"][0].get("id")

        if not conversion_metric_id:
            logger.warning("No conversion metric found, skipping value statistics")
            value_statistics = []
        else:
            value_statistics = ["average_order_value", "conversion_value"]

        # Use the get_campaign_performance tool (no account prefix needed)
        result = await self._call_mcp_tool(
            "get_campaign_performance",
            {
                "model": "claude",
                "statistics": statistics,
                "conversion_metric_id": conversion_metric_id,
                "value_statistics": value_statistics,
                "timeframe": {
                    "value": {
                        "start": start_date,
                        "end": end_date
                    }
                }
            }
        )

        return result.get("data", {})

    async def fetch_flows(
        self,
        client_name: str,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all flows for a client.

        Args:
            client_name: Client slug
            fields: Fields to return

        Returns:
            List of flow data dictionaries
        """
        self.client_name = client_name

        if fields is None:
            fields = ["name", "status", "trigger_type", "created", "updated"]

        result = await self._call_mcp_tool(
            "get_flows",
            {
                "model": "claude",
                "fields": fields
            }
        )

        return result.get("data", [])

    async def fetch_flow_report(
        self,
        client_name: str,
        start_date: str,
        end_date: str,
        statistics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch flow performance report.

        Args:
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            statistics: Performance metrics to fetch

        Returns:
            Flow report data
        """
        self.client_name = client_name

        if statistics is None:
            statistics = [
                "recipients", "opens", "opens_unique", "clicks", "clicks_unique",
                "open_rate", "click_rate", "conversions", "conversion_rate"
            ]

        # Get metric ID for conversions
        metrics = await self._call_mcp_tool(
            "get_metrics",
            {
                "model": "claude",
                "fields": ["name"]
            }
        )

        conversion_metric_id = None
        for metric in metrics.get("data", []):
            if metric.get("attributes", {}).get("name") == "Placed Order":
                conversion_metric_id = metric.get("id")
                break

        if not conversion_metric_id and metrics.get("data"):
            conversion_metric_id = metrics["data"][0].get("id")

        if not conversion_metric_id:
            return {"data": {}}

        # TODO: Flow report tool not available on MCP server
        # Server only provides: get_flows, get_flow, update_flow_status
        # Future: Use query_metric_aggregates to build custom flow reports
        logger.warning(
            f"Flow report functionality not yet implemented - no dedicated flow report tool on MCP server. "
            f"Returning empty data for {client_name} ({start_date} to {end_date})"
        )

        return {"data": {}}

    def _validate_mcp_data(
        self,
        mcp_data: Dict[str, Any],
        client_name: str,
        start_date: str,
        end_date: str
    ) -> None:
        """
        Validate that MCP data contains REAL data, not empty structures.

        This ensures the workflow cannot proceed with empty or missing Klaviyo data,
        preventing generation of calendars based solely on industry benchmarks.

        Args:
            mcp_data: Dictionary containing fetched MCP data
            client_name: Client slug (e.g., "rogue-creamery")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Raises:
            ValueError: If critical data is missing or invalid
        """
        errors = []
        warnings = []

        # Critical validations (HALT if these fail)
        segments = mcp_data.get("segments", [])
        campaigns = mcp_data.get("campaigns", [])
        flows = mcp_data.get("flows", [])
        campaign_report = mcp_data.get("campaign_report", {})

        # Verify segments exist (critical for audience targeting)
        if not segments:
            errors.append("No segments retrieved from Klaviyo - cannot generate audience-targeted campaigns")
        elif len(segments) == 0:
            errors.append("Segments array is empty - API call succeeded but returned no data")

        # Verify at least some historical data exists
        if not campaigns and not flows:
            errors.append("No historical campaigns or flows found - cannot base recommendations on past performance")

        # Verify performance data exists
        if not campaign_report or not campaign_report.get("data"):
            errors.append("No campaign performance data - cannot calculate ROI or optimize send times")

        # Warnings (log but don't halt)
        if not flows:
            warnings.append("No flows found - this may be expected for newer accounts")

        # If we have errors, raise an exception with detailed context
        if errors:
            error_msg = f"\n❌ MCP Data Validation Failed for {client_name} ({start_date} to {end_date})\n\n"
            error_msg += "Critical Issues:\n"
            for error in errors:
                error_msg += f"  • {error}\n"

            if warnings:
                error_msg += "\nWarnings:\n"
                for warning in warnings:
                    error_msg += f"  ⚠️  {warning}\n"

            error_msg += "\n🛑 WORKFLOW HALTED - Cannot generate calendar without real Klaviyo data"

            raise ValueError(error_msg)

        if warnings:
            for warning in warnings:
                logger.warning(warning)

    async def fetch_all_data(
        self,
        client_name: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Fetch all MCP data for a client in parallel.

        This is the main method used in Stage 1 (Planning) to fetch
        all necessary Klaviyo data at once.

        Args:
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary containing all fetched data:
            {
                "segments": [...],
                "campaigns": [...],
                "campaign_report": {...},
                "flows": [...],
                "flow_report": {...},
                "metadata": {
                    "client_name": str,
                    "start_date": str,
                    "end_date": str,
                    "fetched_at": str
                }
            }
        """
        logger.info(f"Fetching all MCP data for {client_name} ({start_date} to {end_date})")

        # Fetch all data in parallel
        segments_task = self.fetch_segments(client_name)
        campaigns_task = self.fetch_campaigns(client_name, start_date, end_date)
        campaign_report_task = self.fetch_campaign_report(client_name, start_date, end_date)
        flows_task = self.fetch_flows(client_name)
        flow_report_task = self.fetch_flow_report(client_name, start_date, end_date)

        # Wait for all tasks to complete
        segments, campaigns, campaign_report, flows, flow_report = await asyncio.gather(
            segments_task,
            campaigns_task,
            campaign_report_task,
            flows_task,
            flow_report_task,
            return_exceptions=True
        )

        # 🔥 NEW: Fail immediately if any critical API call failed
        critical_errors = []

        if isinstance(segments, Exception):
            critical_errors.append(f"Segments API failed: {str(segments)}")

        if isinstance(campaigns, Exception):
            critical_errors.append(f"Campaigns API failed: {str(campaigns)}")

        if isinstance(campaign_report, Exception):
            critical_errors.append(f"Campaign report API failed: {str(campaign_report)}")

        if critical_errors:
            error_msg = f"\n❌ Critical MCP API Failures for {client_name}\n\n"
            for error in critical_errors:
                error_msg += f"  • {error}\n"
            error_msg += "\n🛑 WORKFLOW HALTED - Cannot proceed without Klaviyo API access"

            raise RuntimeError(error_msg)

        # Non-critical failures can be warnings
        if isinstance(flows, Exception):
            logger.warning(f"Flows API failed (non-critical): {str(flows)}")
            flows = []

        if isinstance(flow_report, Exception):
            logger.warning(f"Flow report API failed (non-critical): {str(flow_report)}")
            flow_report = {}

        result = {
            "segments": segments,
            "campaigns": campaigns,
            "campaign_report": campaign_report,
            "flows": flows,
            "flow_report": flow_report,
            "metadata": {
                "client_name": client_name,
                "start_date": start_date,
                "end_date": end_date,
                "fetched_at": datetime.utcnow().isoformat()
            }
        }

        # 🔥 NEW: Validate that we have REAL data, not empty structures
        logger.info(f"Validating MCP data for {client_name}...")
        self._validate_mcp_data(result, client_name, start_date, end_date)

        logger.info(f"✅ MCP data validation passed: {len(segments)} segments, {len(campaigns)} campaigns, {len(flows)} flows")

        return result
