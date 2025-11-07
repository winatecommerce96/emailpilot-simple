"""
Native MCP Client - Child Process Implementation
Mimics Claude Desktop App's approach of spawning MCP servers as child processes
and communicating via stdio using JSON-RPC protocol.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import subprocess
from dataclasses import dataclass

import httpx
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server from .mcp.json"""
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]


class MCPServerProcess:
    """Manages a single MCP server child process"""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the MCP server process"""
        try:
            # Merge environment variables
            env = os.environ.copy()
            env.update(self.config.env)

            # Spawn the process
            self.process = subprocess.Popen(
                [self.config.command] + self.config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1
            )

            logger.info(f"Started MCP server: {self.config.name} (PID: {self.process.pid})")

            # Initialize the connection
            await self._initialize()

        except Exception as e:
            logger.error(f"Failed to start MCP server {self.config.name}: {e}")
            raise

    async def _initialize(self):
        """Send initialize request to MCP server"""
        try:
            init_request = {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {
                            "listChanged": True
                        }
                    },
                    "clientInfo": {
                        "name": "emailpilot-simple",
                        "version": "1.0.0"
                    }
                }
            }

            response = await self._send_request(init_request)
            logger.info(f"MCP server {self.config.name} initialized: {response.get('result', {}).get('serverInfo', {})}")

        except Exception as e:
            logger.error(f"Failed to initialize MCP server {self.config.name}: {e}")
            raise

    def _next_request_id(self) -> int:
        """Generate next request ID"""
        self.request_id += 1
        return self.request_id

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and wait for response"""
        async with self._lock:
            if not self.process or not self.process.stdin or not self.process.stdout:
                raise RuntimeError(f"MCP server {self.config.name} not running")

            try:
                # Send request
                request_str = json.dumps(request) + "\n"
                self.process.stdin.write(request_str)
                self.process.stdin.flush()

                # Read response
                response_str = self.process.stdout.readline()
                if not response_str:
                    raise RuntimeError(f"MCP server {self.config.name} closed connection")

                response = json.loads(response_str)

                # Check for errors
                if "error" in response:
                    error = response["error"]
                    raise RuntimeError(f"MCP error: {error.get('message', 'Unknown error')}")

                return response

            except Exception as e:
                logger.error(f"Error communicating with MCP server {self.config.name}: {e}")
                raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            response = await self._send_request(request)
            return response.get("result", {}).get("content", [])

        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {self.config.name}: {e}")
            raise

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/list",
                "params": {}
            }

            response = await self._send_request(request)
            return response.get("result", {}).get("tools", [])

        except Exception as e:
            logger.error(f"Failed to list tools on {self.config.name}: {e}")
            raise

    async def stop(self):
        """Stop the MCP server process"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info(f"Stopped MCP server: {self.config.name}")
            except subprocess.TimeoutExpired:
                self.process.kill()
                logger.warning(f"Force killed MCP server: {self.config.name}")
            except Exception as e:
                logger.error(f"Error stopping MCP server {self.config.name}: {e}")


class NativeMCPClient:
    """
    Native MCP client that spawns MCP servers as child processes.
    Mimics the Claude Desktop App's approach.
    """

    def __init__(
        self,
        project_id: str = "emailpilot-438321",
        clients_api_url: str = "https://emailpilot-orchestrator-935786836546.us-central1.run.app/api/clients",
        config_path: Optional[str] = None
    ):
        """
        Initialize native MCP client.

        Args:
            project_id: GCP project ID for Secret Manager
            clients_api_url: URL of the Clients API
            config_path: Path to .mcp.json config file (fallback if API unavailable)
        """
        self.project_id = project_id
        self.clients_api_url = clients_api_url
        self.config_path = config_path or os.path.join(os.path.expanduser("~"), ".mcp.json")
        self.secret_manager_client = secretmanager.SecretManagerServiceClient()
        self.servers: Dict[str, MCPServerProcess] = {}
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self):
        """Initialize all MCP servers from config"""
        if self._initialized:
            return

        try:
            # Load configuration
            configs = await self._load_config()

            # Start all MCP servers
            start_tasks = []
            for config in configs:
                server = MCPServerProcess(config)
                self.servers[config.name] = server
                start_tasks.append(server.start())

            # Wait for all servers to start
            await asyncio.gather(*start_tasks, return_exceptions=True)

            self._initialized = True
            logger.info(f"Initialized {len(self.servers)} MCP servers")

        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            await self.cleanup()
            raise

    async def _load_config(self) -> List[MCPServerConfig]:
        """
        Load MCP server configurations.
        Prefer local .mcp.json for development, fallback to Clients API for production.
        """
        # First, try local config file (for development)
        if self.config_path and os.path.exists(self.config_path):
            logger.info(f"Found local config file: {self.config_path}")
            try:
                configs = await self._load_config_from_file()
                if configs:
                    logger.info(f"Loaded {len(configs)} MCP server configurations from local file")
                    return configs
            except Exception as e:
                logger.warning(f"Failed to load local config: {e}, falling back to Clients API")

        # Fallback to Clients API (for production)
        try:
            configs = await self._load_config_from_api()
            if configs:
                logger.info(f"Loaded {len(configs)} MCP server configurations from Clients API")
                return configs
        except Exception as e:
            logger.error(f"Failed to load config from Clients API: {e}")

        raise ValueError("Could not load MCP configuration from local file or Clients API")

    async def _load_config_from_api(self) -> List[MCPServerConfig]:
        """Load MCP server configurations from Clients API and Secret Manager"""
        try:
            # Fetch clients from Clients API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.clients_api_url)
                response.raise_for_status()
                clients = response.json()

            configs = []

            # Process each LIVE client with Klaviyo configuration
            for client_config in clients:
                # Only process LIVE clients
                if client_config.get('status') != 'LIVE':
                    logger.debug(f"Skipping non-LIVE client: {client_config.get('name')}")
                    continue

                # Must have klaviyo_secret_name
                secret_name = client_config.get('klaviyo_secret_name')
                if not secret_name:
                    logger.debug(f"Skipping client without klaviyo_secret_name: {client_config.get('name')}")
                    continue

                client_name = client_config.get('name', 'Unknown')

                try:
                    # Retrieve API key from Secret Manager
                    secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                    secret_response = self.secret_manager_client.access_secret_version(
                        request={"name": secret_path}
                    )
                    api_key = secret_response.payload.data.decode('UTF-8')

                    # Build MCP server configuration
                    config = MCPServerConfig(
                        name=f"{client_name} Klaviyo",
                        command="/usr/local/bin/uvx",  # Container path for uvx
                        args=["klaviyo-mcp-server@latest"],
                        env={
                            "PRIVATE_API_KEY": api_key,
                            "READ_ONLY": "true"
                        }
                    )
                    configs.append(config)
                    logger.info(f"Loaded MCP config for {client_name} using secret {secret_name}")

                except Exception as e:
                    logger.error(f"Failed to load API key for {client_name} from {secret_name}: {e}")
                    continue

            return configs

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching clients from API: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load config from API: {e}")
            raise

    async def _load_config_from_file(self) -> List[MCPServerConfig]:
        """Fallback: Load MCP server configurations from .mcp.json file"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.warning(f"MCP config file not found: {self.config_path}")
                return []

            with open(config_file, 'r') as f:
                config_data = json.load(f)

            configs = []
            mcp_servers = config_data.get("mcpServers", {})

            for name, server_config in mcp_servers.items():
                # Only load Klaviyo servers (skip Wise, etc.)
                if "Klaviyo" not in name:
                    continue

                env = server_config.get("env", {}).copy()

                config = MCPServerConfig(
                    name=name,
                    command=server_config.get("command", "/usr/local/bin/uvx"),
                    args=server_config.get("args", []),
                    env=env
                )
                configs.append(config)

            logger.info(f"Loaded {len(configs)} Klaviyo MCP server configurations from file")
            return configs

        except Exception as e:
            logger.error(f"Failed to load MCP config from file: {e}")
            raise

    def _get_server_for_client(self, client_name: str) -> Optional[MCPServerProcess]:
        """Get the MCP server for a client name"""
        # Normalize client name
        normalized = client_name.lower().replace("-", " ").replace("_", " ")

        # Find matching server
        for server_name, server in self.servers.items():
            server_normalized = server_name.lower().replace("-", " ").replace("_", " ")
            if normalized in server_normalized or server_normalized.startswith(normalized):
                return server

        logger.warning(f"No MCP server found for client: {client_name}")
        return None

    def _validate_mcp_data(
        self,
        mcp_data: Dict[str, Any],
        client_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> None:
        """
        Validate that MCP data contains REAL data, not empty structures.

        Args:
            mcp_data: The fetched MCP data dictionary
            client_name: Client name for error messages
            start_date: Start date for context in error messages
            end_date: End date for context in error messages

        Raises:
            ValueError: If critical data is missing or invalid
        """
        errors = []
        warnings = []

        # Critical validations (HALT if these fail)
        segments = mcp_data.get("segments", [])
        campaigns = mcp_data.get("campaigns", [])
        flows = mcp_data.get("flows", [])

        if not segments or len(segments) == 0:
            errors.append("No segments retrieved from Klaviyo - cannot generate audience-targeted campaigns")

        if (not campaigns or len(campaigns) == 0) and (not flows or len(flows) == 0):
            errors.append("No historical campaigns or flows found - cannot base recommendations on past performance")

        # Warnings (log but don't halt)
        if not flows or len(flows) == 0:
            warnings.append("No flows found - this may be expected for newer accounts")

        # If we have errors, raise an exception with detailed context
        if errors:
            date_range = ""
            if start_date and end_date:
                date_range = f" ({start_date} to {end_date})"

            error_msg = f"\n❌ MCP Data Validation Failed for {client_name}{date_range}\n\n"
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
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch all Klaviyo data for a client.
        NOW INCLUDES VALIDATION - Will raise ValueError if critical data is missing.

        Args:
            client_name: Client name (e.g., "rogue-creamery")
            start_date: Start date for campaign reports (YYYY-MM-DD)
            end_date: End date for campaign reports (YYYY-MM-DD)

        Returns:
            Dictionary with segments, campaigns, flows, metrics, lists, etc.

        Raises:
            ValueError: If MCP data validation fails (no segments, no campaigns/flows, etc.)
            RuntimeError: If critical MCP API calls fail
        """
        server = self._get_server_for_client(client_name)
        if not server:
            raise ValueError(f"No MCP server found for client: {client_name}")

        logger.info(f"Fetching all MCP data for {client_name}")

        # Fetch data in parallel
        segments_task = self._fetch_segments(server)
        campaigns_task = self._fetch_campaigns(server, start_date, end_date)
        flows_task = self._fetch_flows(server)
        metrics_task = self._fetch_metrics(server)
        lists_task = self._fetch_lists(server)

        segments, campaigns, flows, metrics, lists_data = await asyncio.gather(
            segments_task,
            campaigns_task,
            flows_task,
            metrics_task,
            lists_task,
            return_exceptions=True
        )

        # Fail immediately if any critical API call failed
        critical_errors = []

        if isinstance(segments, Exception):
            critical_errors.append(f"Segments API failed: {str(segments)}")

        if isinstance(campaigns, Exception):
            critical_errors.append(f"Campaigns API failed: {str(campaigns)}")

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

        if isinstance(metrics, Exception):
            logger.warning(f"Metrics API failed (non-critical): {str(metrics)}")
            metrics = []

        if isinstance(lists_data, Exception):
            logger.warning(f"Lists API failed (non-critical): {str(lists_data)}")
            lists_data = []

        result = {
            "segments": segments,
            "campaigns": campaigns,
            "flows": flows,
            "metrics": metrics,
            "lists": lists_data
        }

        logger.info(
            f"MCP data fetch complete for {client_name}: "
            f"{len(result['segments'])} segments, "
            f"{len(result['campaigns'])} campaigns, "
            f"{len(result['flows'])} flows"
        )

        # Validate that we have REAL data, not empty structures
        logger.info(f"Validating MCP data for {client_name}...")
        self._validate_mcp_data(result, client_name, start_date, end_date)

        logger.info(
            f"✅ MCP data validation passed: "
            f"{len(segments)} segments, "
            f"{len(campaigns)} campaigns, "
            f"{len(flows)} flows"
        )

        return result

    async def _fetch_segments(self, server: MCPServerProcess) -> List[Dict[str, Any]]:
        """Fetch segments from Klaviyo"""
        try:
            result = await server.call_tool(
                "klaviyo_get_segments",
                {
                    "model": "claude",
                    "fields": ["name", "definition", "created", "updated", "is_active"]
                }
            )

            # Parse result
            if result and len(result) > 0:
                content = result[0]
                if content.get("type") == "text":
                    data = json.loads(content.get("text", "{}"))
                    return data.get("data", [])

            return []

        except Exception as e:
            logger.error(f"Failed to fetch segments: {e}")
            raise

    async def _fetch_campaigns(
        self,
        server: MCPServerProcess,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Fetch campaigns from Klaviyo"""
        try:
            # Fetch both email and SMS campaigns
            email_result = await server.call_tool(
                "klaviyo_get_campaigns",
                {
                    "model": "claude",
                    "channel": "email",
                    "fields": ["name", "status", "created_at", "send_time", "audiences"]
                }
            )

            campaigns = []
            if email_result and len(email_result) > 0:
                content = email_result[0]
                if content.get("type") == "text":
                    data = json.loads(content.get("text", "{}"))
                    campaigns.extend(data.get("data", []))

            return campaigns

        except Exception as e:
            logger.error(f"Failed to fetch campaigns: {e}")
            raise

    async def _fetch_flows(self, server: MCPServerProcess) -> List[Dict[str, Any]]:
        """Fetch flows from Klaviyo"""
        try:
            result = await server.call_tool(
                "klaviyo_get_flows",
                {
                    "model": "claude",
                    "fields": ["name", "status", "created", "updated", "trigger_type"]
                }
            )

            if result and len(result) > 0:
                content = result[0]
                if content.get("type") == "text":
                    data = json.loads(content.get("text", "{}"))
                    return data.get("data", [])

            return []

        except Exception as e:
            logger.error(f"Failed to fetch flows: {e}")
            raise

    async def _fetch_metrics(self, server: MCPServerProcess) -> List[Dict[str, Any]]:
        """Fetch metrics from Klaviyo"""
        try:
            result = await server.call_tool(
                "klaviyo_get_metrics",
                {
                    "model": "claude",
                    "fields": ["name", "created", "updated"]
                }
            )

            if result and len(result) > 0:
                content = result[0]
                if content.get("type") == "text":
                    data = json.loads(content.get("text", "{}"))
                    return data.get("data", [])

            return []

        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            raise

    async def _fetch_lists(self, server: MCPServerProcess) -> List[Dict[str, Any]]:
        """Fetch lists from Klaviyo"""
        try:
            result = await server.call_tool(
                "klaviyo_get_lists",
                {
                    "model": "claude",
                    "fields": ["name", "created", "updated"]
                }
            )

            if result and len(result) > 0:
                content = result[0]
                if content.get("type") == "text":
                    data = json.loads(content.get("text", "{}"))
                    return data.get("data", [])

            return []

        except Exception as e:
            logger.error(f"Failed to fetch lists: {e}")
            raise

    async def cleanup(self):
        """Stop all MCP server processes"""
        if not self.servers:
            return

        try:
            stop_tasks = [server.stop() for server in self.servers.values()]
            await asyncio.gather(*stop_tasks, return_exceptions=True)
            self.servers.clear()
            self._initialized = False
            logger.info("MCP client cleanup complete")
        except Exception as e:
            logger.error(f"Error during MCP client cleanup: {e}")
