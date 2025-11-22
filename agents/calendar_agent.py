"""
Calendar Agent - Single-Agent Workflow Orchestrator

Orchestrates the three-stage calendar generation workflow:
1. Planning - Strategic calendar generation
2. Structuring - Creative to JSON conversion
3. Brief Generation - Detailed execution briefs
"""

import yaml
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from anthropic import Anthropic

from data.mcp_client import MCPClient
from data.rag_client import RAGClient
from data.firestore_client import FirestoreClient
from data.mcp_cache import MCPCache

logger = logging.getLogger(__name__)


class CalendarAgent:
    """
    Single agent orchestrator for calendar generation workflow.

    Uses Claude Sonnet 4.5 with explicit prompts at each stage to generate
    high-quality campaign calendars and execution briefs.
    """

    def __init__(
        self,
        anthropic_api_key: str,
        mcp_client: MCPClient,
        rag_client: RAGClient,
        firestore_client: FirestoreClient,
        cache: MCPCache,
        model: str = "claude-sonnet-4-5-20250929",
        prompts_dir: Optional[str] = None
    ):
        """
        Initialize Calendar Agent.

        Args:
            anthropic_api_key: Anthropic API key
            mcp_client: MCP client for Klaviyo data
            rag_client: RAG client for brand documents
            firestore_client: Firestore client for client metadata
            cache: MCP cache instance
            model: Claude model to use
            prompts_dir: Path to prompts directory (defaults to ../prompts)
        """
        self.client = Anthropic(api_key=anthropic_api_key)
        self.model = model
        self.mcp = mcp_client
        self.rag = rag_client
        self.firestore = firestore_client
        self.cache = cache

        # Set prompts directory
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            # Default to emailpilot-simple/prompts
            self.prompts_dir = Path(__file__).parent.parent / "prompts"

        logger.info(f"CalendarAgent initialized with model: {model}")

    def load_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """
        Load a YAML prompt configuration.

        Args:
            prompt_name: Name of the prompt file (e.g., "planning_v5_1_0.yaml")

        Returns:
            Parsed YAML prompt configuration

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        prompt_path = self.prompts_dir / prompt_name

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_config = yaml.safe_load(f)

        logger.info(f"Loaded prompt: {prompt_name}")
        return prompt_config

    def _build_system_prompt(self, prompt_config: Dict[str, Any]) -> str:
        """
        Build system prompt from YAML configuration.

        Args:
            prompt_config: Loaded YAML prompt configuration

        Returns:
            System prompt string
        """
        return prompt_config.get("system_prompt", "")

    def _build_user_prompt(
        self,
        prompt_config: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> str:
        """
        Build user prompt from YAML configuration with variable substitution.

        Args:
            prompt_config: Loaded YAML prompt configuration
            variables: Variables to substitute in the prompt template

        Returns:
            User prompt string with variables substituted
        """
        user_prompt_template = prompt_config.get("user_prompt", "")

        # Simple variable substitution - use single braces to match YAML prompt templates
        user_prompt = user_prompt_template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"  # Single braces: {key}
            if isinstance(value, str):
                user_prompt = user_prompt.replace(placeholder, value)
            else:
                user_prompt = user_prompt.replace(placeholder, str(value))

        return user_prompt

    async def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000
    ) -> str:
        """
        Call Claude API with system and user prompts.

        Uses streaming for high token counts (>16000) to avoid timeout errors.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Claude's response text
        """
        try:
            logger.info(f"Calling Claude API (model: {self.model}, max_tokens: {max_tokens})")

            # Use streaming for high token counts to avoid timeout
            use_streaming = max_tokens > 16000

            if use_streaming:
                logger.info(f"Using streaming mode for max_tokens={max_tokens}")

                # Initialize response text
                response_text = ""

                # Stream the response
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                ) as stream:
                    for text in stream.text_stream:
                        response_text += text

                logger.info(f"Claude API streaming call successful ({len(response_text)} characters)")

                return response_text

            else:
                # Standard non-streaming call for smaller requests
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )

                # Extract text from response
                response_text = response.content[0].text

                logger.info(f"Claude API call successful ({len(response_text)} characters)")

                return response_text

        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}")
            raise

    async def stage_1_planning(
        self,
        client_name: str,
        start_date: str,
        end_date: str,
        workflow_id: str
    ) -> str:
        """
        Stage 1: Planning - Strategic calendar generation.

        Fetches all necessary data (MCP, RAG, Firestore) and generates
        a strategic campaign calendar.

        Args:
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            workflow_id: Unique workflow identifier

        Returns:
            Planning output (strategic calendar in text format)
        """
        logger.info(f"Stage 1: Planning for {client_name} ({start_date} to {end_date})")

        # Check cache for existing MCP data
        cache_key = f"mcp_data:{client_name}:{start_date}_{end_date}"

        if self.cache.has(cache_key):
            logger.info(f"Using cached MCP data for {client_name}")
            mcp_data = self.cache.get(cache_key)
        else:
            # Fetch all MCP data in parallel
            logger.info(f"Fetching fresh MCP data for {client_name}")
            mcp_data = await self.mcp.fetch_all_data(client_name, start_date, end_date)

            # Cache for future stages
            self.cache.set(cache_key, mcp_data)
            logger.info(f"Cached MCP data with key: {cache_key}")

        # Fetch RAG and Firestore data
        rag_data = self.rag.get_all_data(client_name)
        firestore_data = self.firestore.get_all_data(client_name)

        # Load planning prompt
        planning_prompt = self.load_prompt("planning_v5_1_0.yaml")

        # Format data for prompt
        mcp_formatted = self._format_mcp_data(mcp_data)
        rag_formatted = self.rag.format_for_prompt(client_name)
        firestore_formatted = self.firestore.format_for_prompt(client_name)

        # Extract product catalog separately for prompt template
        product_catalog_data = rag_data.get("product_catalog")
        if product_catalog_data:
            if isinstance(product_catalog_data, dict) and "products" in product_catalog_data:
                # For .txt files: extract the text content from {"products": "text"}
                product_catalog_formatted = product_catalog_data["products"]
            elif isinstance(product_catalog_data, dict):
                # For .json files: convert to formatted JSON string
                product_catalog_formatted = json.dumps(product_catalog_data, indent=2)
            else:
                # Fallback to string conversion
                product_catalog_formatted = str(product_catalog_data)
            logger.info(f"Product catalog extracted: {len(product_catalog_formatted)} characters")
        else:
            product_catalog_formatted = "No product catalog available for this client."
            logger.warning(f"No product catalog found for {client_name}")

        # Build prompt variables
        variables = {
            "client_name": firestore_data.get("display_name", client_name),
            "start_date": start_date,
            "end_date": end_date,
            "mcp_data": mcp_formatted,
            "brand_intelligence": rag_formatted,
            "product_catalog": product_catalog_formatted,
            "client_config": firestore_formatted
        }

        # Build system and user prompts
        system_prompt = self._build_system_prompt(planning_prompt)
        user_prompt = self._build_user_prompt(planning_prompt, variables)

        # Call Claude
        planning_output = await self._call_claude(
            system_prompt,
            user_prompt,
            max_tokens=8000
        )

        logger.info(f"Stage 1: Planning complete ({len(planning_output)} characters)")

        return planning_output

    async def stage_2_structuring(
        self,
        client_name: str,
        start_date: str,
        end_date: str,
        workflow_id: str,
        planning_output: str
    ) -> Dict[str, Any]:
        """
        Stage 2: Structuring - Convert creative calendar to v4.0.0 JSON.

        Takes the planning output and converts it to structured JSON format
        following the v4.0.0 calendar schema.

        Args:
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            workflow_id: Unique workflow identifier
            planning_output: Output from Stage 1

        Returns:
            Structured calendar JSON (as dict)
        """
        logger.info(f"Stage 2: Structuring for {client_name}")

        # Load structuring prompt
        structuring_prompt = self.load_prompt("calendar_structuring_v1_2_2.yaml")

        # Build prompt variables
        variables = {
            "client_name": client_name,
            "start_date": start_date,
            "end_date": end_date,
            "planning_output": planning_output
        }

        # Build system and user prompts
        system_prompt = self._build_system_prompt(structuring_prompt)
        user_prompt = self._build_user_prompt(structuring_prompt, variables)

        # Call Claude
        structuring_output = await self._call_claude(
            system_prompt,
            user_prompt,
            max_tokens=64000  # Increased from 16000 - large calendars can exceed 50k chars
        )

        logger.info(f"Stage 2: Structuring complete ({len(structuring_output)} characters)")

        # Parse JSON from output
        import json
        import re

        # Extract JSON from markdown code blocks if present
        # More robust extraction that handles various fence formats
        json_str = structuring_output.strip()

        # Check if response starts with markdown fence
        if json_str.startswith('```'):
            # Find the first newline after opening fence (skip language identifier)
            first_newline = json_str.find('\n')
            if first_newline != -1:
                # Find closing fence in the substring AFTER first newline
                closing_fence_relative = json_str[first_newline:].rfind('```')
                if closing_fence_relative != -1:
                    # Convert relative position to absolute position
                    closing_fence = first_newline + closing_fence_relative
                    # Extract content between fences
                    json_str = json_str[first_newline + 1:closing_fence].strip()
                    logger.info(f"Extracted JSON from markdown code fence ({len(json_str)} characters)")
                else:
                    # No closing fence - likely truncated output
                    logger.warning("Found opening fence but no closing fence - assuming truncation")
                    # Extract everything after the first newline (remove opening fence)
                    json_str = json_str[first_newline + 1:].strip()
                    logger.warning(f"Attempting to parse potentially incomplete JSON ({len(json_str)} characters)")
            else:
                logger.warning("Found opening fence but no newline - unexpected format")
                # Try to extract JSON anyway (remove opening fence)
                json_str = json_str[3:].strip()

        try:
            calendar_json = json.loads(json_str)
            logger.info(f"Successfully parsed calendar JSON")
            return calendar_json

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse calendar JSON: {str(e)}")
            logger.error(f"JSON parse error at position {e.pos}: {e.msg}")

            # Try to provide helpful error context
            if e.pos is not None and len(json_str) > e.pos:
                context_start = max(0, e.pos - 100)
                context_end = min(len(json_str), e.pos + 100)
                error_context = json_str[context_start:context_end]
                logger.error(f"Error context: ...{error_context}...")

            # Return error structure with diagnostic info
            return {
                "error": "Failed to parse JSON",
                "error_type": "JSONDecodeError",
                "error_message": str(e),
                "error_position": e.pos,
                "output_length": len(structuring_output),
                "json_length": len(json_str),
                "raw_output": structuring_output
            }

    async def stage_3_briefs(
        self,
        client_name: str,
        workflow_id: str,
        calendar_json: Dict[str, Any]
    ) -> str:
        """
        Stage 3: Brief Generation - Create detailed execution briefs.

        Takes the structured calendar JSON and generates comprehensive
        execution briefs for each campaign.

        Args:
            client_name: Client slug
            workflow_id: Unique workflow identifier
            calendar_json: Output from Stage 2

        Returns:
            Detailed execution briefs (text format)
        """
        logger.info(f"Stage 3: Brief Generation for {client_name}")

        # Load brief generation prompt
        briefs_prompt = self.load_prompt("brief_generation_v2_2_0.yaml")

        # Retrieve cached MCP data for context
        # (We need performance data and segment information for briefs)
        cache_key_pattern = f"mcp_data:{client_name}:"
        cache_stats = self.cache.get_stats()

        mcp_data = None
        for key in cache_stats["keys"]:
            if key.startswith(cache_key_pattern):
                mcp_data = self.cache.get(key)
                break

        # Fetch RAG data for design guidelines and product info
        rag_data = self.rag.get_all_data(client_name)

        # Format data for prompt
        import json
        calendar_json_str = json.dumps(calendar_json, indent=2)
        mcp_formatted = self._format_mcp_data(mcp_data) if mcp_data else "No MCP data available"
        rag_formatted = self.rag.format_for_prompt(client_name)

        # Extract product catalog separately for prompt template
        product_catalog_data = rag_data.get("product_catalog")
        if product_catalog_data:
            if isinstance(product_catalog_data, dict) and "products" in product_catalog_data:
                # For .txt files: extract the text content from {"products": "text"}
                product_catalog_formatted = product_catalog_data["products"]
            elif isinstance(product_catalog_data, dict):
                # For .json files: convert to formatted JSON string
                product_catalog_formatted = json.dumps(product_catalog_data, indent=2)
            else:
                # Fallback to string conversion
                product_catalog_formatted = str(product_catalog_data)
            logger.info(f"Product catalog extracted for briefs: {len(product_catalog_formatted)} characters")
        else:
            product_catalog_formatted = "No product catalog available for this client."
            logger.warning(f"No product catalog found for {client_name} briefs stage")

        # Build prompt variables
        variables = {
            "client_name": client_name,
            "calendar_json": calendar_json_str,
            "mcp_data": mcp_formatted,
            "brand_intelligence": rag_formatted,
            "product_catalog": product_catalog_formatted
        }

        # Build system and user prompts
        system_prompt = self._build_system_prompt(briefs_prompt)
        user_prompt = self._build_user_prompt(briefs_prompt, variables)

        # Call Claude
        briefs_output = await self._call_claude(
            system_prompt,
            user_prompt,
            max_tokens=16000  # Briefs are longer
        )

        logger.info(f"Stage 3: Brief Generation complete ({len(briefs_output)} characters)")

        return briefs_output

    async def run_workflow(
        self,
        client_name: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Run the complete three-stage workflow.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Complete workflow output:
            {
                "planning": str,
                "calendar_json": dict,
                "briefs": str,
                "metadata": {
                    "client_name": str,
                    "start_date": str,
                    "end_date": str,
                    "model": str
                }
            }
        """
        workflow_id = f"{client_name}_{start_date}_{end_date}"

        logger.info(f"Starting workflow {workflow_id}")
        logger.info(f"Model: {self.model}")

        try:
            # Stage 1: Planning
            planning_output = await self.stage_1_planning(
                client_name, start_date, end_date, workflow_id
            )

            # Stage 2: Structuring
            calendar_json = await self.stage_2_structuring(
                client_name, start_date, end_date, workflow_id, planning_output
            )

            # Stage 3: Brief Generation
            briefs_output = await self.stage_3_briefs(
                client_name, workflow_id, calendar_json
            )

            # Compile final output
            result = {
                "planning": planning_output,
                "calendar_json": calendar_json,
                "briefs": briefs_output,
                "metadata": {
                    "client_name": client_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "model": self.model,
                    "workflow_id": workflow_id
                }
            }

            logger.info(f"Workflow {workflow_id} completed successfully")

            return result

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {str(e)}")
            raise

    def _format_mcp_data(self, mcp_data: Optional[Dict[str, Any]]) -> str:
        """
        Format MCP data for inclusion in prompts.

        Args:
            mcp_data: MCP data dictionary

        Returns:
            Formatted text representation
        """
        if not mcp_data:
            return "No MCP data available"

        import json

        esp_platform = mcp_data.get("esp_platform", "klaviyo").capitalize()
        sections = []

        # Segments
        if mcp_data.get("segments"):
            segments_count = len(mcp_data["segments"])
            sections.append(f"## Segments ({segments_count} total)\n\n" +
                          json.dumps(mcp_data["segments"], indent=2))

        # Campaigns
        if mcp_data.get("campaigns"):
            campaigns_count = len(mcp_data["campaigns"])
            sections.append(f"## Recent Campaigns ({campaigns_count} total)\n\n" +
                          json.dumps(mcp_data["campaigns"], indent=2))

        # Campaign Report
        if mcp_data.get("campaign_report"):
            sections.append(f"## Campaign Performance\n\n" +
                          json.dumps(mcp_data["campaign_report"], indent=2))

        # Revenue Series (Braze specific)
        if mcp_data.get("revenue_series"):
            sections.append(f"## Revenue Trends (Aggregate)\n\n" +
                          json.dumps(mcp_data["revenue_series"], indent=2))
            sections.append("**NOTE**: Per-campaign revenue attribution is not available via Braze API. Use aggregate trends for forecasting.")

        # Flows
        if mcp_data.get("flows"):
            flows_count = len(mcp_data["flows"])
            sections.append(f"## Active Flows ({flows_count} total)\n\n" +
                          json.dumps(mcp_data["flows"], indent=2))

        # Flow Report
        if mcp_data.get("flow_report"):
            sections.append(f"## Flow Performance\n\n" +
                          json.dumps(mcp_data["flow_report"], indent=2))

        formatted = f"# {esp_platform} Data\n\n" + "\n\n---\n\n".join(sections)

        return formatted

