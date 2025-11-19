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
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from anthropic import Anthropic

from data.native_mcp_client import NativeMCPClient as MCPClient
from data.enhanced_rag_client import EnhancedRAGClient as RAGClient
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
        import time
        call_start = time.time()
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        try:
            logger.debug(f"[Claude API] Call started at {timestamp}")
            logger.debug(f"[Claude API] Model: {self.model}")
            logger.debug(f"[Claude API] Max tokens: {max_tokens:,}")
            logger.debug(f"[Claude API] System prompt size: {len(system_prompt):,} characters")
            logger.debug(f"[Claude API] User prompt size: {len(user_prompt):,} characters")

            logger.info(f"Calling Claude API (model: {self.model}, max_tokens: {max_tokens})")

            # Use streaming for high token counts to avoid timeout
            use_streaming = max_tokens > 16000

            if use_streaming:
                logger.debug(f"[Claude API] Streaming mode selected (max_tokens {max_tokens:,} > 16000 threshold)")
            else:
                logger.debug(f"[Claude API] Non-streaming mode selected (max_tokens {max_tokens:,} <= 16000 threshold)")

            if use_streaming:
                logger.info(f"Using streaming mode for max_tokens={max_tokens}")

                api_call_start = time.time()
                logger.debug(f"[Claude API] Starting streaming request...")

                # Initialize response text
                response_text = ""
                chunk_count = 0

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
                        chunk_count += 1

                api_call_duration = time.time() - api_call_start

                logger.debug(f"[Claude API] Streaming complete: {chunk_count} chunks received")
                logger.debug(f"[Claude API] Response size: {len(response_text):,} characters")
                logger.debug(f"[Claude API] API call duration: {api_call_duration:.2f}s")
                logger.info(f"Claude API streaming call successful ({len(response_text)} characters)")

                total_duration = time.time() - call_start
                logger.debug(f"[Claude API] Total call duration: {total_duration:.2f}s")

                return response_text

            else:
                # Standard non-streaming call for smaller requests
                api_call_start = time.time()
                logger.debug(f"[Claude API] Starting non-streaming request...")

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )

                api_call_duration = time.time() - api_call_start

                # Extract text from response
                response_text = response.content[0].text

                # Log response metadata if available
                logger.debug(f"[Claude API] Response size: {len(response_text):,} characters")
                logger.debug(f"[Claude API] API call duration: {api_call_duration:.2f}s")

                # Log token usage if available
                if hasattr(response, 'usage'):
                    logger.debug(f"[Claude API] Input tokens: {response.usage.input_tokens:,}")
                    logger.debug(f"[Claude API] Output tokens: {response.usage.output_tokens:,}")
                    logger.debug(f"[Claude API] Total tokens: {response.usage.input_tokens + response.usage.output_tokens:,}")

                # Log stop reason if available
                if hasattr(response, 'stop_reason'):
                    logger.debug(f"[Claude API] Stop reason: {response.stop_reason}")

                logger.info(f"Claude API call successful ({len(response_text)} characters)")

                total_duration = time.time() - call_start
                logger.debug(f"[Claude API] Total call duration: {total_duration:.2f}s")

                return response_text

        except Exception as e:
            error_duration = time.time() - call_start
            logger.error(f"Claude API call failed after {error_duration:.2f}s: {str(e)}")
            logger.debug(f"[Claude API] Error details - Model: {self.model}, Max tokens: {max_tokens:,}")
            logger.debug(f"[Claude API] Error details - System prompt: {len(system_prompt):,} chars, User prompt: {len(user_prompt):,} chars")
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
        import time
        stage_start = time.time()

        logger.info(f"Stage 1: Planning for {client_name} ({start_date} to {end_date})")
        logger.debug(f"[Stage 1] Workflow ID: {workflow_id}")
        logger.debug(f"[Stage 1] Start timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Check cache for existing MCP data
        cache_key = f"mcp_data:{client_name}:{start_date}_{end_date}"
        logger.debug(f"[Stage 1] MCP cache key: {cache_key}")

        if self.cache.has(cache_key):
            cache_fetch_start = time.time()
            logger.info(f"Using cached MCP data for {client_name}")
            logger.debug(f"[Stage 1] Cache HIT for key: {cache_key}")
            mcp_data = self.cache.get(cache_key)
            cache_fetch_duration = time.time() - cache_fetch_start
            logger.debug(f"[Stage 1] Cache retrieval took {cache_fetch_duration:.2f}s")

            # Calculate data size
            import json
            mcp_data_size = len(json.dumps(mcp_data))
            logger.debug(f"[Stage 1] Cached MCP data size: {mcp_data_size:,} bytes")

            # 🔥 NEW: Validate cached data too (in case it was cached before validation was added)
            try:
                validation_start = time.time()
                self.mcp._validate_mcp_data(mcp_data, client_name, start_date, end_date)
                validation_duration = time.time() - validation_start
                logger.debug(f"[Stage 1] Cached MCP data validation successful ({validation_duration:.2f}s)")
            except ValueError as e:
                logger.error(f"Cached MCP data failed validation - refetching")
                logger.debug(f"[Stage 1] Validation error: {str(e)}")
                self.cache.delete(cache_key)
                logger.debug(f"[Stage 1] Cache entry deleted: {cache_key}")
                mcp_data = None

        if not self.cache.has(cache_key):
            # Fetch all MCP data in parallel
            logger.info(f"Fetching fresh MCP data for {client_name}")
            logger.debug(f"[Stage 1] Cache MISS for key: {cache_key}")

            mcp_fetch_start = time.time()
            try:
                mcp_data = await self.mcp.fetch_all_data(client_name, start_date, end_date)
                mcp_fetch_duration = time.time() - mcp_fetch_start
                logger.debug(f"[Stage 1] MCP data fetch took {mcp_fetch_duration:.2f}s")

                # Calculate fetched data size
                import json
                mcp_data_size = len(json.dumps(mcp_data))
                logger.debug(f"[Stage 1] Fetched MCP data size: {mcp_data_size:,} bytes")
                logger.debug(f"[Stage 1] MCP data contains: segments={len(mcp_data.get('segments', []))}, campaigns={len(mcp_data.get('campaigns', []))}, flows={len(mcp_data.get('flows', []))}, catalog_items={len(mcp_data.get('catalog_items', []))}")
                # ✅ Validation happens inside fetch_all_data() now

            except (ValueError, RuntimeError) as e:
                # Re-raise validation errors with clear context
                logger.error(f"❌ MCP data validation failed: {str(e)}")
                logger.debug(f"[Stage 1] MCP fetch failed after {time.time() - mcp_fetch_start:.2f}s")
                raise ValueError(
                    f"Cannot generate calendar for {client_name} - MCP data validation failed.\n\n{str(e)}"
                ) from e

            # Cache for future stages
            cache_set_start = time.time()
            self.cache.set(cache_key, mcp_data)
            cache_set_duration = time.time() - cache_set_start
            logger.info(f"Cached validated MCP data with key: {cache_key}")
            logger.debug(f"[Stage 1] Cache set took {cache_set_duration:.2f}s")

        # Fetch RAG and Firestore data
        logger.info(f"Fetching RAG and Firestore data for {client_name}")

        rag_fetch_start = time.time()
        rag_data = await self.rag.get_all_data(client_name)
        rag_fetch_duration = time.time() - rag_fetch_start
        rag_categories_with_content = len([v for v in rag_data.values() if v])
        logger.debug(f"[Stage 1] RAG data fetch took {rag_fetch_duration:.2f}s")
        logger.debug(f"[Stage 1] RAG data: {rag_categories_with_content} categories with content")

        firestore_fetch_start = time.time()
        firestore_data = self.firestore.get_all_data(client_name)
        firestore_fetch_duration = time.time() - firestore_fetch_start
        firestore_fields_count = len(firestore_data) if firestore_data else 0
        logger.debug(f"[Stage 1] Firestore data fetch took {firestore_fetch_duration:.2f}s")
        logger.debug(f"[Stage 1] Firestore data: {firestore_fields_count} fields retrieved")

        # Load planning prompt
        logger.debug(f"[Stage 1] Loading planning prompt: planning_v5_1_0.yaml")
        planning_prompt = self.load_prompt("planning_v5_1_0.yaml")

        # Format data for prompt
        logger.debug(f"[Stage 1] Formatting data for prompt...")

        format_mcp_start = time.time()
        mcp_formatted = self._format_mcp_data(mcp_data)
        format_mcp_duration = time.time() - format_mcp_start
        logger.debug(f"[Stage 1] MCP formatting took {format_mcp_duration:.2f}s ({len(mcp_formatted):,} characters)")

        format_rag_start = time.time()
        rag_formatted = await self.rag.format_for_prompt(client_name)
        format_rag_duration = time.time() - format_rag_start
        logger.debug(f"[Stage 1] RAG formatting took {format_rag_duration:.2f}s ({len(rag_formatted):,} characters)")

        format_firestore_start = time.time()
        firestore_formatted = self.firestore.format_for_prompt(client_name)
        format_firestore_duration = time.time() - format_firestore_start
        logger.debug(f"[Stage 1] Firestore formatting took {format_firestore_duration:.2f}s ({len(firestore_formatted):,} characters)")

        # Extract product catalog from MCP data
        logger.debug(f"[Stage 1] Extracting product catalog from MCP...")
        catalog_items = mcp_data.get("catalog_items", [])
        if catalog_items and len(catalog_items) > 0:
            # Convert MCP catalog items to formatted JSON string for prompt
            product_catalog_formatted = json.dumps(catalog_items, indent=2)
            logger.info(f"Product catalog extracted from MCP: {len(catalog_items)} items, {len(product_catalog_formatted)} characters")
            logger.debug(f"[Stage 1] MCP catalog items: {len(catalog_items)}, size: {len(product_catalog_formatted):,} characters")
        else:
            product_catalog_formatted = "No product catalog available for this client."
            logger.warning(f"No catalog items found in MCP data for {client_name}")
            logger.debug(f"[Stage 1] No MCP catalog items available")

        # Build prompt variables
        logger.debug(f"[Stage 1] Building prompt variables...")
        variables = {
            "client_name": firestore_data.get("display_name", client_name),
            "start_date": start_date,
            "end_date": end_date,
            "mcp_data": mcp_formatted,
            "brand_intelligence": rag_formatted,
            "product_catalog": product_catalog_formatted,
            "client_config": firestore_formatted
        }
        logger.debug(f"[Stage 1] Prompt variables: {len(variables)} total")

        # Build system and user prompts
        logger.debug(f"[Stage 1] Building system and user prompts...")
        prompt_build_start = time.time()
        system_prompt = self._build_system_prompt(planning_prompt)
        user_prompt = self._build_user_prompt(planning_prompt, variables)
        prompt_build_duration = time.time() - prompt_build_start
        logger.debug(f"[Stage 1] Prompt building took {prompt_build_duration:.2f}s")
        logger.debug(f"[Stage 1] System prompt size: {len(system_prompt):,} characters")
        logger.debug(f"[Stage 1] User prompt size: {len(user_prompt):,} characters")

        # Call Claude
        logger.debug(f"[Stage 1] Calling Claude API...")
        claude_call_start = time.time()
        planning_output = await self._call_claude(
            system_prompt,
            user_prompt,
            max_tokens=8000
        )
        claude_call_duration = time.time() - claude_call_start
        logger.debug(f"[Stage 1] Claude API call took {claude_call_duration:.2f}s")
        logger.debug(f"[Stage 1] Planning output size: {len(planning_output):,} characters")

        stage_total_duration = time.time() - stage_start
        logger.info(f"Stage 1: Planning complete ({len(planning_output)} characters)")
        logger.debug(f"[Stage 1] Total stage duration: {stage_total_duration:.2f}s")
        logger.debug(f"[Stage 1] End timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

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
        Stage 2: Structuring - Convert creative calendar to dual JSON outputs.

        Takes the planning output and generates TWO structured JSON formats:
        1. Detailed v4.0.0 calendar (for internal processing and brief generation)
        2. Simplified calendar (conforming to CALENDAR_JSON_UPLOAD_FORMAT.md spec)

        Args:
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            workflow_id: Unique workflow identifier
            planning_output: Output from Stage 1

        Returns:
            Dict containing both outputs:
            {
                "detailed_calendar": {...},  # v4.0.0 format
                "simplified_calendar": {...}  # Upload format
            }
        """
        import time
        stage_start = time.time()

        logger.info(f"Stage 2: Structuring for {client_name}")
        logger.debug(f"[Stage 2] Workflow ID: {workflow_id}")
        logger.debug(f"[Stage 2] Start timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.debug(f"[Stage 2] Planning output size: {len(planning_output):,} characters")

        # Load structuring prompt
        logger.debug(f"[Stage 2] Loading structuring prompt...")
        prompt_load_start = time.time()
        structuring_prompt = self.load_prompt("calendar_structuring_v1_2_2.yaml")
        prompt_load_duration = time.time() - prompt_load_start
        logger.debug(f"[Stage 2] Prompt loading took {prompt_load_duration:.2f}s")

        # Build prompt variables
        logger.debug(f"[Stage 2] Building prompt variables...")

        # Fetch segment data from MCP
        logger.debug(f"[Stage 2] Fetching segment data from MCP...")
        mcp_data = await self.mcp.fetch_all_data(client_name, start_date, end_date)
        segments = mcp_data.get("segments", [])
        segment_list = ", ".join([seg.get("name", "Unknown") for seg in segments])
        logger.debug(f"[Stage 2] Found {len(segments)} segments for segment_list")

        variables = {
            "client_name": client_name,
            "start_date": start_date,
            "end_date": end_date,
            "creative_content": planning_output,
            "segment_list": segment_list
        }
        logger.debug(f"[Stage 2] Prompt variables: {len(variables)} total")

        # Build system and user prompts
        logger.debug(f"[Stage 2] Building system and user prompts...")
        prompt_build_start = time.time()
        system_prompt = self._build_system_prompt(structuring_prompt)
        user_prompt = self._build_user_prompt(structuring_prompt, variables)
        prompt_build_duration = time.time() - prompt_build_start
        logger.debug(f"[Stage 2] Prompt building took {prompt_build_duration:.2f}s")
        logger.debug(f"[Stage 2] System prompt size: {len(system_prompt):,} characters")
        logger.debug(f"[Stage 2] User prompt size: {len(user_prompt):,} characters")

        # Call Claude
        logger.debug(f"[Stage 2] Calling Claude API...")
        claude_call_start = time.time()
        structuring_output = await self._call_claude(
            system_prompt,
            user_prompt,
            max_tokens=64000  # Increased from 16000 - large calendars can exceed 50k chars
        )
        claude_call_duration = time.time() - claude_call_start
        logger.debug(f"[Stage 2] Claude API call took {claude_call_duration:.2f}s")
        logger.debug(f"[Stage 2] Structuring output size: {len(structuring_output):,} characters")

        logger.info(f"Stage 2: Structuring complete ({len(structuring_output)} characters)")

        # Parse dual JSON outputs
        import json
        import re
        from tools.calendar_format_validator import validate_calendar_data

        logger.debug(f"[Stage 2] Parsing dual JSON outputs from response...")

        # Extract content from markdown fences if present
        content = structuring_output.strip()

        # Remove markdown fences if present
        if content.startswith('```'):
            logger.debug(f"[Stage 2] Detected markdown code fence - extracting content")
            first_newline = content.find('\n')
            if first_newline != -1:
                closing_fence_relative = content[first_newline:].rfind('```')
                if closing_fence_relative != -1:
                    closing_fence = first_newline + closing_fence_relative
                    content = content[first_newline + 1:closing_fence].strip()
                    logger.debug(f"[Stage 2] Extracted content size: {len(content):,} characters")
                else:
                    # No closing fence - remove opening fence only
                    content = content[first_newline + 1:].strip()
                    logger.warning(f"[Stage 2] No closing fence - attempting to parse content")
            else:
                content = content[3:].strip()

        parse_start = time.time()

        try:
            # Strategy: Parse TWO consecutive JSON objects
            # The response should contain two complete JSON objects back-to-back

            # Strip markdown code fences if present
            # Claude sometimes wraps JSON in ```json ... ```
            import re
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            logger.debug(f"[Stage 2] Stripped markdown code fences from content")

            logger.debug(f"[Stage 2] Attempting to parse first JSON (detailed calendar)...")

            # Extract JSON from content that may have explanatory text
            # Claude sometimes returns text like "Here is the JSON:" before the actual JSON
            json_start = content.find('{')
            if json_start == -1:
                json_start = content.find('[')

            if json_start == -1:
                logger.error(f"[Stage 2] No JSON object or array found in content")
                logger.error(f"[Stage 2] Content preview (first 500 chars): {content[:500]}")
                raise ValueError("No JSON object or array found in LLM response")

            # Log skipped text only if there was text before the JSON
            if json_start > 0:
                skipped_text = content[:json_start].strip()
                logger.debug(f"[Stage 2] Found JSON starting at position {json_start}, skipping {json_start} characters of explanatory text")
                logger.debug(f"[Stage 2] Skipped text: {skipped_text[:200]}")

            # Always slice to JSON start and strip leading whitespace (even when json_start == 0)
            content = content[json_start:].lstrip()
            logger.debug(f"[Stage 2] Content after slicing starts with: {content[:50]!r}")

            # Parse first JSON object (detailed v4.0.0 calendar)
            # Track which JSON parsing stage for accurate error context
            parsing_stage = "first"
            parsing_source = content
            decoder = json.JSONDecoder()
            detailed_calendar, idx = decoder.raw_decode(content)

            logger.debug(f"[Stage 2] First JSON parsed successfully (ended at position {idx})")
            campaign_count = len(detailed_calendar.get('campaigns', []))
            logger.debug(f"[Stage 2] Detailed calendar contains {campaign_count} campaigns")

            # Skip whitespace between JSON objects
            remaining = content[idx:].lstrip()

            if not remaining:
                # No second JSON found - handle gracefully
                logger.warning(f"[Stage 2] No second JSON found - only detailed calendar present")
                logger.warning(f"[Stage 2] This may indicate prompt did not generate simplified calendar")

                # Return with only detailed calendar (backward compatibility)
                stage_total_duration = time.time() - stage_start
                logger.debug(f"[Stage 2] Total stage duration: {stage_total_duration:.2f}s")
                logger.debug(f"[Stage 2] End timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

                return {
                    "detailed_calendar": detailed_calendar,
                    "simplified_calendar": None,
                    "warning": "Simplified calendar not generated by prompt"
                }

            logger.debug(f"[Stage 2] Attempting to parse second JSON (simplified calendar)...")
            logger.debug(f"[Stage 2] Remaining content size: {len(remaining):,} characters")

            # Parse second JSON object (simplified calendar)
            # Update tracking for second JSON parsing
            parsing_stage = "second"
            parsing_source = remaining
            simplified_calendar, _ = decoder.raw_decode(remaining)

            parse_duration = time.time() - parse_start
            logger.info(f"Successfully parsed dual JSON outputs")
            logger.debug(f"[Stage 2] JSON parsing took {parse_duration:.2f}s")

            # Validate simplified calendar format
            logger.debug(f"[Stage 2] Validating simplified calendar format...")
            validation_start = time.time()
            is_valid, errors, warnings = validate_calendar_data(simplified_calendar)
            validation_duration = time.time() - validation_start

            if is_valid:
                logger.info(f"Simplified calendar validation passed")
                logger.debug(f"[Stage 2] Validation took {validation_duration:.2f}s")
                if warnings:
                    logger.warning(f"Simplified calendar has {len(warnings)} warnings:")
                    for warning in warnings[:5]:  # Log first 5 warnings
                        logger.warning(f"  - {warning}")
                    if len(warnings) > 5:
                        logger.warning(f"  ... and {len(warnings) - 5} more warnings")
            else:
                logger.error(f"Simplified calendar validation failed with {len(errors)} errors:")
                for error in errors[:10]:  # Log first 10 errors
                    logger.error(f"  - {error}")
                if len(errors) > 10:
                    logger.error(f"  ... and {len(errors) - 10} more errors")

            # Extract event count from simplified calendar
            simplified_events = simplified_calendar.get('events', [])
            if not isinstance(simplified_events, list):
                # Try alternative key names
                if 'calendar' in simplified_calendar:
                    simplified_events = simplified_calendar.get('calendar', [])
                else:
                    simplified_events = []

            event_count = len(simplified_events) if isinstance(simplified_events, list) else 0
            logger.debug(f"[Stage 2] Simplified calendar contains {event_count} events")

            # Verify counts match between detailed and simplified
            if campaign_count != event_count:
                logger.warning(
                    f"[Stage 2] Count mismatch: detailed calendar has {campaign_count} campaigns "
                    f"but simplified calendar has {event_count} events"
                )

            stage_total_duration = time.time() - stage_start
            logger.debug(f"[Stage 2] Total stage duration: {stage_total_duration:.2f}s")
            logger.debug(f"[Stage 2] End timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

            # Return both outputs
            result = {
                "detailed_calendar": detailed_calendar,
                "simplified_calendar": simplified_calendar,
                "validation": {
                    "is_valid": is_valid,
                    "errors": errors,
                    "warnings": warnings
                }
            }

            return result

        except json.JSONDecodeError as e:
            parse_duration = time.time() - parse_start
            logger.error(f"Failed to parse JSON: {str(e)}")
            logger.error(f"JSON parse error at position {e.pos}: {e.msg}")
            logger.debug(f"[Stage 2] JSON parsing failed after {parse_duration:.2f}s")

            # Try to provide helpful error context
            if e.pos is not None and len(parsing_source) > e.pos:
                context_start = max(0, e.pos - 100)
                context_end = min(len(parsing_source), e.pos + 100)
                error_context = parsing_source[context_start:context_end]
                logger.error(f"Error context ({parsing_stage} JSON): ...{error_context}...")
                logger.debug(f"[Stage 2] Error context window: chars {context_start} to {context_end}")

            stage_total_duration = time.time() - stage_start
            logger.debug(f"[Stage 2] Total stage duration (with error): {stage_total_duration:.2f}s")
            logger.debug(f"[Stage 2] End timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

            # Return error structure with diagnostic info
            return {
                "error": "Failed to parse JSON",
                "error_type": "JSONDecodeError",
                "error_message": str(e),
                "error_position": e.pos,
                "output_length": len(structuring_output),
                "content_length": len(content),
                "raw_output": structuring_output
            }

        except Exception as e:
            parse_duration = time.time() - parse_start
            logger.error(f"Unexpected error during JSON parsing: {str(e)}")
            logger.debug(f"[Stage 2] Unexpected error after {parse_duration:.2f}s: {type(e).__name__}")

            stage_total_duration = time.time() - stage_start
            logger.debug(f"[Stage 2] Total stage duration (with error): {stage_total_duration:.2f}s")

            return {
                "error": "Unexpected parsing error",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "output_length": len(structuring_output),
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
        import time
        stage_start = time.time()

        logger.info(f"Stage 3: Brief Generation for {client_name}")
        logger.debug(f"[Stage 3] Workflow ID: {workflow_id}")
        logger.debug(f"[Stage 3] Start timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Log calendar JSON size
        campaign_count = len(calendar_json.get('campaigns', []))
        logger.debug(f"[Stage 3] Calendar JSON contains {campaign_count} campaigns")

        # Load brief generation prompt
        logger.debug(f"[Stage 3] Loading brief generation prompt...")
        prompt_load_start = time.time()
        briefs_prompt = self.load_prompt("brief_generation_v2_2_0.yaml")
        prompt_load_duration = time.time() - prompt_load_start
        logger.debug(f"[Stage 3] Prompt loading took {prompt_load_duration:.2f}s")

        # Retrieve cached MCP data for context
        # (We need performance data and segment information for briefs)
        logger.debug(f"[Stage 3] Retrieving cached MCP data...")
        cache_retrieve_start = time.time()
        cache_key_pattern = f"mcp_data:{client_name}:"
        cache_stats = self.cache.get_stats()

        mcp_data = None
        for key in cache_stats["keys"]:
            if key.startswith(cache_key_pattern):
                mcp_data = self.cache.get(key)
                logger.debug(f"[Stage 3] Found cached MCP data with key: {key}")
                break

        cache_retrieve_duration = time.time() - cache_retrieve_start
        if mcp_data:
            logger.debug(f"[Stage 3] Cache retrieval took {cache_retrieve_duration:.2f}s (hit)")
        else:
            logger.debug(f"[Stage 3] Cache retrieval took {cache_retrieve_duration:.2f}s (miss)")

        # Fetch RAG data for design guidelines and product info
        logger.debug(f"[Stage 3] Fetching RAG data...")
        rag_fetch_start = time.time()
        rag_data = await self.rag.get_all_data(client_name)
        rag_fetch_duration = time.time() - rag_fetch_start
        rag_categories_found = len([v for v in rag_data.values() if v is not None])
        logger.debug(f"[Stage 3] RAG data fetch took {rag_fetch_duration:.2f}s ({rag_categories_found} categories)")

        # Format data for prompt
        logger.debug(f"[Stage 3] Formatting data for prompt...")
        format_start = time.time()
        import json
        calendar_json_str = json.dumps(calendar_json, indent=2)
        logger.debug(f"[Stage 3] Calendar JSON size: {len(calendar_json_str):,} characters")

        mcp_formatted = self._format_mcp_data(mcp_data) if mcp_data else "No MCP data available"
        logger.debug(f"[Stage 3] MCP data formatted: {len(mcp_formatted):,} characters")

        rag_formatted = await self.rag.format_for_prompt(client_name)
        logger.debug(f"[Stage 3] RAG data formatted: {len(rag_formatted):,} characters")

        format_duration = time.time() - format_start
        logger.debug(f"[Stage 3] Data formatting took {format_duration:.2f}s")

        # Extract product catalog from MCP data (same as Stage 1)
        logger.debug(f"[Stage 3] Extracting product catalog from MCP...")
        catalog_extract_start = time.time()
        catalog_items = mcp_data.get("catalog_items", []) if mcp_data else []
        if catalog_items and len(catalog_items) > 0:
            # Convert MCP catalog items to formatted JSON string for prompt
            product_catalog_formatted = json.dumps(catalog_items, indent=2)
            logger.info(f"Product catalog extracted from MCP: {len(catalog_items)} items, {len(product_catalog_formatted)} characters")
            logger.debug(f"[Stage 3] MCP catalog items: {len(catalog_items)}, size: {len(product_catalog_formatted):,} characters")
        else:
            product_catalog_formatted = "No product catalog available for this client."
            logger.warning(f"No catalog items found in MCP data for {client_name} briefs stage")
            logger.debug(f"[Stage 3] No MCP catalog items available")

        catalog_extract_duration = time.time() - catalog_extract_start
        logger.debug(f"[Stage 3] Product catalog extraction took {catalog_extract_duration:.2f}s")

        # Build prompt variables
        logger.debug(f"[Stage 3] Building prompt variables...")
        variables = {
            "client_name": client_name,
            "calendar_json": calendar_json_str,
            "mcp_data": mcp_formatted,
            "brand_intelligence": rag_formatted,
            "product_catalog": product_catalog_formatted
        }
        logger.debug(f"[Stage 3] Prompt variables: {len(variables)} total")

        # Build system and user prompts
        logger.debug(f"[Stage 3] Building system and user prompts...")
        prompt_build_start = time.time()
        system_prompt = self._build_system_prompt(briefs_prompt)
        user_prompt = self._build_user_prompt(briefs_prompt, variables)
        prompt_build_duration = time.time() - prompt_build_start
        logger.debug(f"[Stage 3] Prompt building took {prompt_build_duration:.2f}s")
        logger.debug(f"[Stage 3] System prompt size: {len(system_prompt):,} characters")
        logger.debug(f"[Stage 3] User prompt size: {len(user_prompt):,} characters")

        # Call Claude
        logger.debug(f"[Stage 3] Calling Claude API...")
        claude_call_start = time.time()
        briefs_output = await self._call_claude(
            system_prompt,
            user_prompt,
            max_tokens=16000  # Briefs are longer
        )
        claude_call_duration = time.time() - claude_call_start
        logger.debug(f"[Stage 3] Claude API call took {claude_call_duration:.2f}s")
        logger.debug(f"[Stage 3] Briefs output size: {len(briefs_output):,} characters")

        logger.info(f"Stage 3: Brief Generation complete ({len(briefs_output)} characters)")

        stage_total_duration = time.time() - stage_start
        logger.debug(f"[Stage 3] Total stage duration: {stage_total_duration:.2f}s")
        logger.debug(f"[Stage 3] End timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

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

            # Stage 2: Structuring (returns dual outputs)
            stage_2_output = await self.stage_2_structuring(
                client_name, start_date, end_date, workflow_id, planning_output
            )

            # Extract both calendar formats from stage 2
            detailed_calendar = stage_2_output.get("detailed_calendar")
            simplified_calendar = stage_2_output.get("simplified_calendar")
            stage_2_validation = stage_2_output.get("validation", {})

            # EXTRACT STRATEGY SUMMARY from detailed_calendar.metadata
            strategy_summary = None
            if detailed_calendar and "metadata" in detailed_calendar:
                strategy_summary = detailed_calendar["metadata"].get("strategy_summary")

                if strategy_summary:
                    logger.info(f"✓ Extracted Strategy Summary with {len(strategy_summary.get('key_insights', []))} insights")
                else:
                    logger.warning("⚠ Strategy Summary not found in detailed_calendar.metadata")

            # Validate stage 2 output before proceeding
            if detailed_calendar is None:
                error_msg = f"Stage 2 failed to produce valid calendar JSON for {client_name}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Stage 3: Brief Generation (uses detailed calendar)
            briefs_output = await self.stage_3_briefs(
                client_name, workflow_id, detailed_calendar
            )

            # Compile final output with both calendar formats
            result = {
                "planning": planning_output,
                "detailed_calendar": detailed_calendar,
                "simplified_calendar": simplified_calendar,
                "calendar_json": detailed_calendar,  # Backward compatibility
                "briefs": briefs_output,
                "strategy_summary": strategy_summary,
                "stage_2_validation": stage_2_validation,
                "metadata": {
                    "client_name": client_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "model": self.model,
                    "workflow_id": workflow_id,
                    "has_strategy_summary": strategy_summary is not None
                }
            }

            logger.info(f"Workflow {workflow_id} completed successfully")
            logger.info(f"Generated detailed calendar ({len(detailed_calendar.get('campaigns', []))} campaigns)")
            logger.info(f"Generated simplified calendar ({len(simplified_calendar.get('events', []))} events)")

            return result

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {str(e)}")
            raise

    async def run_workflow_with_checkpoint(
        self,
        client_name: str,
        start_date: str,
        end_date: str,
        review_manager: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Run workflow through Stage 1-2, then save state for manual review.

        This enables the "checkpoint" workflow pattern where execution pauses
        after Stage 2 to allow human review/approval before proceeding to Stage 3.

        Args:
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            review_manager: ReviewStateManager instance (optional)

        Returns:
            Workflow output through Stage 2:
            {
                "workflow_id": str,
                "planning": str,
                "detailed_calendar": dict,
                "simplified_calendar": dict,
                "stage_2_validation": dict,
                "review_status": "pending",
                "metadata": dict
            }
        """
        workflow_id = f"{client_name}_{start_date}_{end_date}"

        logger.info(f"Starting checkpoint workflow {workflow_id}")
        logger.info(f"Model: {self.model}")

        try:
            # Stage 1: Planning
            planning_output = await self.stage_1_planning(
                client_name, start_date, end_date, workflow_id
            )

            # Stage 2: Structuring (returns dual outputs)
            stage_2_output = await self.stage_2_structuring(
                client_name, start_date, end_date, workflow_id, planning_output
            )

            # Extract both calendar formats
            detailed_calendar = stage_2_output.get("detailed_calendar")
            simplified_calendar = stage_2_output.get("simplified_calendar")
            stage_2_validation = stage_2_output.get("validation", {})

            # EXTRACT STRATEGY SUMMARY from detailed_calendar.metadata
            strategy_summary = None
            if detailed_calendar and "metadata" in detailed_calendar:
                strategy_summary = detailed_calendar["metadata"].get("strategy_summary")

                if strategy_summary:
                    logger.info(f"✓ Extracted Strategy Summary with {len(strategy_summary.get('key_insights', []))} insights")
                else:
                    logger.warning("⚠ Strategy Summary not found in detailed_calendar.metadata")

            # Save review state to Firestore if manager provided
            if review_manager and review_manager.is_available():
                logger.info(f"Saving review state to Firestore: {workflow_id}")

                metadata = {
                    "model": self.model,
                    "checkpoint_created_at": datetime.utcnow().isoformat()
                }

                saved = review_manager.save_review_state(
                    workflow_id=workflow_id,
                    client_name=client_name,
                    start_date=start_date,
                    end_date=end_date,
                    planning_output=planning_output,
                    detailed_calendar=detailed_calendar,
                    simplified_calendar=simplified_calendar,
                    validation_results=stage_2_validation,
                    metadata=metadata
                )

                if saved:
                    logger.info(f"Review state saved successfully: {workflow_id}")
                else:
                    logger.warning(f"Failed to save review state: {workflow_id}")

            # Return checkpoint result
            result = {
                "workflow_id": workflow_id,
                "planning": planning_output,
                "detailed_calendar": detailed_calendar,
                "simplified_calendar": simplified_calendar,
                "strategy_summary": strategy_summary,
                "stage_2_validation": stage_2_validation,
                "review_status": "pending",
                "metadata": {
                    "client_name": client_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "model": self.model,
                    "workflow_id": workflow_id,
                    "checkpoint_at": "stage_2",
                    "has_strategy_summary": strategy_summary is not None
                }
            }

            logger.info(f"Checkpoint workflow {workflow_id} completed - awaiting review")

            # Log calendar generation results with null safety
            if detailed_calendar:
                logger.info(f"Generated detailed calendar ({len(detailed_calendar.get('campaigns', []))} campaigns)")
            else:
                logger.error("Failed to generate detailed calendar - detailed_calendar is None")

            if simplified_calendar:
                logger.info(f"Generated simplified calendar ({len(simplified_calendar.get('events', []))} events)")
            else:
                logger.error("Failed to generate simplified calendar - simplified_calendar is None")

            return result

        except Exception as e:
            logger.error(f"Checkpoint workflow {workflow_id} failed: {str(e)}")
            raise

    async def resume_workflow_from_review(
        self,
        workflow_id: str,
        review_manager: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Resume workflow from saved review state and complete Stage 3.

        Loads saved state from Firestore and runs Stage 3 (Brief Generation).

        Args:
            workflow_id: Workflow identifier
            review_manager: ReviewStateManager instance (optional)

        Returns:
            Complete workflow output:
            {
                "planning": str,
                "detailed_calendar": dict,
                "simplified_calendar": dict,
                "briefs": str,
                "review_status": "approved",
                "metadata": dict
            }

        Raises:
            ValueError: If review state not found or not approved
        """
        logger.info(f"Resuming workflow from review: {workflow_id}")

        # Load review state from Firestore
        if not review_manager or not review_manager.is_available():
            raise ValueError("ReviewStateManager required to resume workflow")

        review_state = review_manager.get_review_state(workflow_id)

        if not review_state:
            raise ValueError(f"No review state found for workflow: {workflow_id}")

        # Check review status
        review_status = review_state.get("review_status")
        if review_status != "approved":
            raise ValueError(
                f"Workflow {workflow_id} not approved. Current status: {review_status}"
            )

        # Extract saved data
        client_name = review_state.get("client_name")
        detailed_calendar = review_state.get("detailed_calendar")
        simplified_calendar = review_state.get("simplified_calendar")
        planning_output = review_state.get("planning_output")
        stage_2_validation = review_state.get("validation_results", {})

        # EXTRACT STRATEGY SUMMARY from detailed_calendar.metadata
        strategy_summary = None
        if detailed_calendar and "metadata" in detailed_calendar:
            strategy_summary = detailed_calendar["metadata"].get("strategy_summary")

            if strategy_summary:
                logger.info(f"✓ Extracted Strategy Summary with {len(strategy_summary.get('key_insights', []))} insights")
            else:
                logger.warning("⚠ Strategy Summary not found in detailed_calendar.metadata")

        logger.info(f"Loaded review state for {client_name}")
        logger.debug(f"Resume: Detailed calendar has {len(detailed_calendar.get('campaigns', []))} campaigns")

        try:
            # Stage 3: Brief Generation (uses detailed calendar)
            briefs_output = await self.stage_3_briefs(
                client_name, workflow_id, detailed_calendar
            )

            # Compile final output
            result = {
                "planning": planning_output,
                "detailed_calendar": detailed_calendar,
                "simplified_calendar": simplified_calendar,
                "calendar_json": detailed_calendar,  # Backward compatibility
                "strategy_summary": strategy_summary,
                "briefs": briefs_output,
                "stage_2_validation": stage_2_validation,
                "review_status": "approved",
                "metadata": {
                    "client_name": client_name,
                    "start_date": review_state.get("start_date"),
                    "end_date": review_state.get("end_date"),
                    "model": self.model,
                    "workflow_id": workflow_id,
                    "reviewed_by": review_state.get("reviewed_by"),
                    "reviewed_at": review_state.get("reviewed_at"),
                    "review_notes": review_state.get("review_notes"),
                    "has_strategy_summary": strategy_summary is not None
                }
            }

            logger.info(f"Resumed workflow {workflow_id} completed successfully")
            logger.info(f"Generated briefs ({len(briefs_output)} characters)")

            return result

        except Exception as e:
            logger.error(f"Resumed workflow {workflow_id} failed at Stage 3: {str(e)}")
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

        # Flows
        if mcp_data.get("flows"):
            flows_count = len(mcp_data["flows"])
            sections.append(f"## Active Flows ({flows_count} total)\n\n" +
                          json.dumps(mcp_data["flows"], indent=2))

        # Flow Report
        if mcp_data.get("flow_report"):
            sections.append(f"## Flow Performance\n\n" +
                          json.dumps(mcp_data["flow_report"], indent=2))

        formatted = "# Klaviyo Data\n\n" + "\n\n---\n\n".join(sections)

        return formatted
