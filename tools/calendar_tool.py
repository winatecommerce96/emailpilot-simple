"""
Calendar Tool - Workflow Wrapper

Provides a structured interface to the CalendarAgent workflow
with validation, error handling, and logging.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

from agents.calendar_agent import CalendarAgent
from tools.validator import CalendarValidator
from tools.format_adapter import CalendarFormatAdapter
from data.enriched_context_manager import EnrichedContextManager

# Import storage client conditionally (may not be available in all environments)
try:
    from data.storage_client import StorageClient
except ImportError:
    StorageClient = None

logger = logging.getLogger(__name__)


class CalendarTool:
    """
    Tool wrapper for CalendarAgent workflow.

    Provides:
    - Input validation before workflow execution
    - Output validation after each stage
    - Error handling and recovery
    - Result persistence (optional)
    - Structured logging
    """

    def __init__(
        self,
        calendar_agent: CalendarAgent,
        output_dir: Optional[str] = None,
        validate_outputs: bool = True,
        storage_client: Optional['StorageClient'] = None
    ):
        """
        Initialize Calendar Tool.

        Args:
            calendar_agent: Configured CalendarAgent instance
            output_dir: Directory to save workflow outputs (optional, for local dev)
            validate_outputs: Whether to validate outputs after each stage
            storage_client: GCS storage client for persistent outputs (optional, for production)
        """
        self.agent = calendar_agent
        self.validator = CalendarValidator()
        self.format_adapter = CalendarFormatAdapter()
        self.output_dir = Path(output_dir) if output_dir else None
        self.validate_outputs = validate_outputs
        self.storage_client = storage_client

        # Create output directory if specified (development)
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory: {self.output_dir}")

        if self.storage_client:
            logger.info("StorageClient configured for persistent output storage")

        logger.info("CalendarTool initialized")

    def validate_inputs(
        self,
        client_name: str,
        start_date: str,
        end_date: str
    ) -> tuple[bool, list[str]]:
        """
        Validate workflow inputs.

        Args:
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate client_name
        if not client_name or not isinstance(client_name, str):
            errors.append("client_name must be a non-empty string")
        elif not client_name.replace("-", "").replace("_", "").isalnum():
            errors.append("client_name must be alphanumeric with hyphens/underscores only")

        # Validate dates
        if not self.validator._is_valid_date(start_date):
            errors.append(f"Invalid start_date format: {start_date} (expected YYYY-MM-DD)")

        if not self.validator._is_valid_date(end_date):
            errors.append(f"Invalid end_date format: {end_date} (expected YYYY-MM-DD)")

        # Check date range
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")

                if end_dt <= start_dt:
                    errors.append("end_date must be after start_date")

                # Check for reasonable range (max 3 months)
                days_diff = (end_dt - start_dt).days
                if days_diff > 90:
                    errors.append(f"Date range too large: {days_diff} days (max 90 days)")

            except ValueError:
                pass  # Date format errors already caught above

        is_valid = len(errors) == 0

        if is_valid:
            logger.info(f"Input validation passed for {client_name} ({start_date} to {end_date})")
        else:
            logger.error(f"Input validation failed: {errors}")

        return is_valid, errors

    async def run_workflow(
        self,
        client_name: str,
        start_date: str,
        end_date: str,
        save_outputs: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete calendar workflow with validation.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            save_outputs: Whether to save outputs to files

        Returns:
            Workflow result with validation status:
            {
                "success": bool,
                "planning": str,
                "calendar_json": dict,
                "briefs": str,
                "validation": {
                    "planning_valid": bool,
                    "calendar_valid": bool,
                    "briefs_valid": bool,
                    "errors": list
                },
                "metadata": dict
            }
        """
        workflow_id = f"{client_name}_{start_date}_{end_date}"
        logger.info(f"Starting workflow: {workflow_id}")

        # Validate inputs
        inputs_valid, input_errors = self.validate_inputs(client_name, start_date, end_date)

        if not inputs_valid:
            logger.error(f"Workflow aborted due to invalid inputs: {input_errors}")
            return {
                "success": False,
                "error": "Input validation failed",
                "validation": {
                    "input_errors": input_errors
                },
                "metadata": {
                    "client_name": client_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "workflow_id": workflow_id,
                    "aborted_at": "input_validation"
                }
            }

        try:
            # Run the workflow
            result = await self.agent.run_workflow(client_name, start_date, end_date)

            # Initialize validation results
            validation_results = {
                "planning_valid": True,
                "calendar_valid": True,
                "briefs_valid": True,
                "errors": [],
                "warnings": []
            }

            # Validate planning output
            logger.info(f"🔍 VALIDATION DEBUG: self.validate_outputs={self.validate_outputs}")
            if self.validate_outputs and result.get("planning"):
                planning_valid, planning_warnings = self.validator.validate_planning_output(
                    result["planning"]
                )
                logger.info(f"🔍 VALIDATION DEBUG: Planning validator returned: valid={planning_valid}, warnings={len(planning_warnings)}")
                validation_results["planning_valid"] = planning_valid
                if planning_warnings:
                    validation_results["warnings"].extend(
                        [f"Planning: {w}" for w in planning_warnings]
                    )
            else:
                logger.info(f"🔍 VALIDATION DEBUG: Skipping planning validation (validate_outputs={self.validate_outputs}, has_planning={bool(result.get('planning'))})")

            # Validate calendar JSON
            if self.validate_outputs and result.get("calendar_json"):
                calendar_valid, calendar_errors = self.validator.validate_calendar(
                    result["calendar_json"]
                )
                logger.info(f"🔍 VALIDATION DEBUG: Calendar validator returned: valid={calendar_valid}, errors={len(calendar_errors)}")
                validation_results["calendar_valid"] = calendar_valid
                if calendar_errors:
                    validation_results["errors"].extend(
                        [f"Calendar: {e}" for e in calendar_errors]
                    )
            else:
                logger.info(f"🔍 VALIDATION DEBUG: Skipping calendar validation (validate_outputs={self.validate_outputs}, has_calendar={bool(result.get('calendar_json'))})")

            # Validate briefs output
            if self.validate_outputs and result.get("briefs"):
                campaign_count = len(result.get("calendar_json", {}).get("campaigns", []))
                briefs_valid, briefs_warnings = self.validator.validate_briefs_output(
                    result["briefs"],
                    campaign_count
                )
                logger.info(f"🔍 VALIDATION DEBUG: Briefs validator returned: valid={briefs_valid}, warnings={len(briefs_warnings)}")
                validation_results["briefs_valid"] = briefs_valid
                if briefs_warnings:
                    validation_results["warnings"].extend(
                        [f"Briefs: {w}" for w in briefs_warnings]
                    )
            else:
                logger.info(f"🔍 VALIDATION DEBUG: Skipping briefs validation (validate_outputs={self.validate_outputs}, has_briefs={bool(result.get('briefs'))})")

            # Determine overall success
            logger.info(f"🔍 VALIDATION DEBUG: Before all_valid calculation - planning_valid={validation_results['planning_valid']}, calendar_valid={validation_results['calendar_valid']}, briefs_valid={validation_results['briefs_valid']}")
            all_valid = (
                validation_results["planning_valid"] and
                validation_results["calendar_valid"] and
                validation_results["briefs_valid"]
            )
            logger.info(f"🔍 VALIDATION DEBUG: all_valid calculated as: {all_valid}")

            # Save outputs if requested
            # TRACE: Debug conditional before save_outputs check
            logger.info(f"🔍 TRACE: Before save conditional - save_outputs={save_outputs}, self.output_dir={self.output_dir}")
            logger.info(f"🔍 TRACE: Conditional result: {save_outputs and self.output_dir}")
            if save_outputs and self.output_dir:
                self._save_outputs(workflow_id, result, validation_results)

            # Compile final result
            final_result = {
                "success": all_valid,
                "planning": result.get("planning"),
                "calendar_json": result.get("calendar_json"),
                "briefs": result.get("briefs"),
                "validation": validation_results,
                "metadata": result.get("metadata", {})
            }

            if all_valid:
                logger.info(f"Workflow {workflow_id} completed successfully")
            else:
                logger.warning(
                    f"Workflow {workflow_id} completed with validation issues: "
                    f"{len(validation_results['errors'])} errors, "
                    f"{len(validation_results['warnings'])} warnings"
                )

            return final_result

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed with exception: {str(e)}", exc_info=True)

            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "client_name": client_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "workflow_id": workflow_id,
                    "failed_at": datetime.utcnow().isoformat()
                }
            }

    async def run_checkpoint_workflow(
        self,
        client_name: str,
        start_date: str,
        end_date: str,
        review_manager: Optional['ReviewStateManager'] = None,
        save_outputs: bool = True
    ) -> Dict[str, Any]:
        """
        Run workflow through Stage 1-2 (checkpoint mode) and save for review.

        This executes the planning and calendar structuring stages, then saves
        the outputs to Firestore for manual review before proceeding to Stage 3.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            review_manager: ReviewStateManager instance for saving review state
            save_outputs: Whether to save outputs to files/GCS

        Returns:
            Workflow result with review state information:
            {
                "success": bool,
                "planning": str,
                "detailed_calendar": dict,
                "simplified_calendar": dict,
                "validation": {
                    "planning_valid": bool,
                    "calendar_valid": bool,
                    "errors": list,
                    "warnings": list
                },
                "review": {
                    "workflow_id": str,
                    "saved_for_review": bool,
                    "review_status": "pending"
                },
                "metadata": dict
            }
        """
        workflow_id = f"{client_name}_{start_date}_{end_date}"
        logger.info(f"Starting checkpoint workflow: {workflow_id}")

        # Validate inputs
        inputs_valid, input_errors = self.validate_inputs(client_name, start_date, end_date)

        if not inputs_valid:
            logger.error(f"Checkpoint workflow aborted due to invalid inputs: {input_errors}")
            return {
                "success": False,
                "error": "Input validation failed",
                "validation": {
                    "input_errors": input_errors
                },
                "metadata": {
                    "client_name": client_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "workflow_id": workflow_id,
                    "aborted_at": "input_validation"
                }
            }

        try:
            # Run Stage 1-2 via agent's checkpoint method
            result = await self.agent.run_checkpoint_workflow(
                client_name, start_date, end_date, workflow_id
            )

            # Initialize validation results
            validation_results = {
                "planning_valid": True,
                "calendar_valid": True,
                "errors": [],
                "warnings": []
            }

            # Validate planning output
            if self.validate_outputs and result.get("planning"):
                planning_valid, planning_warnings = self.validator.validate_planning_output(
                    result["planning"]
                )
                validation_results["planning_valid"] = planning_valid
                if planning_warnings:
                    validation_results["warnings"].extend(
                        [f"Planning: {w}" for w in planning_warnings]
                    )

            # Validate detailed calendar JSON
            if self.validate_outputs and result.get("detailed_calendar"):
                calendar_valid, calendar_errors = self.validator.validate_calendar(
                    result["detailed_calendar"]
                )
                validation_results["calendar_valid"] = calendar_valid
                if calendar_errors:
                    validation_results["errors"].extend(
                        [f"Calendar: {e}" for e in calendar_errors]
                    )

            # Check if Stage 1-2 succeeded
            stage_1_2_valid = (
                validation_results["planning_valid"] and
                validation_results["calendar_valid"]
            )

            # Save to review state if manager provided and stages valid
            review_info = {
                "workflow_id": workflow_id,
                "saved_for_review": False,
                "review_status": None
            }

            if review_manager and stage_1_2_valid:
                saved = review_manager.save_review_state(
                    workflow_id=workflow_id,
                    client_name=client_name,
                    start_date=start_date,
                    end_date=end_date,
                    planning_output=result.get("planning", ""),
                    detailed_calendar=result.get("detailed_calendar", {}),
                    simplified_calendar=result.get("simplified_calendar", {}),
                    validation_results=validation_results,
                    metadata=result.get("metadata", {})
                )
                review_info["saved_for_review"] = saved
                review_info["review_status"] = "pending" if saved else None

                if saved:
                    logger.info(f"Checkpoint workflow {workflow_id} saved for review")
                else:
                    logger.warning(f"Failed to save checkpoint workflow {workflow_id} for review")
            elif not review_manager:
                logger.warning("ReviewStateManager not provided - workflow not saved for review")
            elif not stage_1_2_valid:
                logger.warning("Stage 1-2 validation failed - workflow not saved for review")

            # Save outputs if requested
            if save_outputs and self.output_dir:
                self._save_outputs(workflow_id, result, validation_results)

            # Compile final result
            final_result = {
                "success": stage_1_2_valid and review_info["saved_for_review"],
                "planning": result.get("planning"),
                "detailed_calendar": result.get("detailed_calendar"),
                "simplified_calendar": result.get("simplified_calendar"),
                "validation": validation_results,
                "review": review_info,
                "metadata": result.get("metadata", {})
            }

            if final_result["success"]:
                logger.info(f"Checkpoint workflow {workflow_id} completed successfully and saved for review")
            else:
                logger.warning(
                    f"Checkpoint workflow {workflow_id} completed but may have issues: "
                    f"stage_1_2_valid={stage_1_2_valid}, saved_for_review={review_info['saved_for_review']}"
                )

            return final_result

        except Exception as e:
            logger.error(f"Checkpoint workflow {workflow_id} failed with exception: {str(e)}", exc_info=True)

            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "client_name": client_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "workflow_id": workflow_id,
                    "failed_at": datetime.utcnow().isoformat()
                }
            }

    async def resume_workflow(
        self,
        workflow_id: str,
        review_manager: 'ReviewStateManager',
        save_outputs: bool = True
    ) -> Dict[str, Any]:
        """
        Resume an approved workflow to execute Stage 3 (brief generation).

        This loads the approved Stage 1-2 outputs from Firestore and executes
        Stage 3 to generate campaign briefs.

        Args:
            workflow_id: Workflow identifier (format: client_start_end)
            review_manager: ReviewStateManager instance for loading review state
            save_outputs: Whether to save outputs to files/GCS

        Returns:
            Workflow result with Stage 3 outputs:
            {
                "success": bool,
                "briefs": str,
                "validation": {
                    "briefs_valid": bool,
                    "errors": list,
                    "warnings": list
                },
                "review": {
                    "workflow_id": str,
                    "review_status": "approved",
                    "reviewed_at": str,
                    "reviewed_by": str
                },
                "metadata": dict
            }
        """
        logger.info(f"Resuming workflow: {workflow_id}")

        try:
            # Load review state
            review_state = review_manager.get_review_state(workflow_id)
            if not review_state:
                logger.error(f"Review state not found for workflow: {workflow_id}")
                return {
                    "success": False,
                    "error": f"Review state not found for workflow: {workflow_id}",
                    "metadata": {
                        "workflow_id": workflow_id,
                        "failed_at": "review_state_load"
                    }
                }

            # Verify review is approved
            from data.review_state_manager import ReviewStatus
            if review_state.get("review_status") != ReviewStatus.APPROVED.value:
                logger.error(
                    f"Workflow {workflow_id} not approved. Status: {review_state.get('review_status')}"
                )
                return {
                    "success": False,
                    "error": f"Workflow must be approved before resuming. Current status: {review_state.get('review_status')}",
                    "metadata": {
                        "workflow_id": workflow_id,
                        "review_status": review_state.get("review_status"),
                        "failed_at": "review_status_check"
                    }
                }

            # Resume workflow via agent's resume method
            result = await self.agent.resume_workflow_from_review(
                review_state=review_state,
                workflow_id=workflow_id
            )

            # Initialize validation results
            validation_results = {
                "briefs_valid": True,
                "errors": [],
                "warnings": []
            }

            # Validate briefs output
            if self.validate_outputs and result.get("briefs"):
                # Get campaign count from review state
                detailed_calendar = review_state.get("detailed_calendar", {})
                campaign_count = len(detailed_calendar.get("campaigns", []))

                briefs_valid, briefs_warnings = self.validator.validate_briefs_output(
                    result["briefs"],
                    campaign_count
                )
                validation_results["briefs_valid"] = briefs_valid
                if briefs_warnings:
                    validation_results["warnings"].extend(
                        [f"Briefs: {w}" for w in briefs_warnings]
                    )

            # Save outputs if requested
            if save_outputs:
                # Combine review state and result for comprehensive output
                combined_result = {
                    "planning": review_state.get("planning_output"),
                    "detailed_calendar": review_state.get("detailed_calendar"),
                    "simplified_calendar": review_state.get("simplified_calendar"),
                    "briefs": result.get("briefs"),
                    "metadata": result.get("metadata", {})
                }

                if self.output_dir:
                    self._save_outputs(workflow_id, combined_result, validation_results)

            # Extract review metadata
            review_info = {
                "workflow_id": workflow_id,
                "review_status": review_state.get("review_status"),
                "reviewed_at": review_state.get("reviewed_at"),
                "reviewed_by": review_state.get("reviewed_by")
            }

            # Compile final result
            final_result = {
                "success": validation_results["briefs_valid"],
                "briefs": result.get("briefs"),
                "validation": validation_results,
                "review": review_info,
                "metadata": result.get("metadata", {})
            }

            if final_result["success"]:
                logger.info(f"Resume workflow {workflow_id} completed successfully")
            else:
                logger.warning(
                    f"Resume workflow {workflow_id} completed with validation issues: "
                    f"{len(validation_results['errors'])} errors, "
                    f"{len(validation_results['warnings'])} warnings"
                )

            return final_result

        except Exception as e:
            logger.error(f"Resume workflow {workflow_id} failed with exception: {str(e)}", exc_info=True)

            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "workflow_id": workflow_id,
                    "failed_at": datetime.utcnow().isoformat()
                }
            }

    def _save_outputs(
        self,
        workflow_id: str,
        result: Dict[str, Any],
        validation: Dict[str, Any]
    ) -> None:
        """
        Save workflow outputs to GCS and/or local files.

        Args:
            workflow_id: Workflow identifier
            result: Workflow result
            validation: Validation results
        """
        # TRACE: Method entry confirmation
        logger.info(f"🔍 TRACE: _save_outputs called with workflow_id={workflow_id}")
        logger.info(f"🔍 TRACE: Result keys: {list(result.keys())}")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{workflow_id}_{timestamp}"

        try:
            # Save planning output
            if result.get("planning"):
                filename = f"{base_filename}_planning.txt"

                # Save to GCS if available (production)
                if self.storage_client:
                    self.storage_client.save_output(filename, result["planning"], "text/plain")

                # Also save locally if output_dir set (development)
                if self.output_dir:
                    planning_path = self.output_dir / filename
                    with open(planning_path, 'w', encoding='utf-8') as f:
                        f.write(result["planning"])
                    logger.info(f"Saved planning output locally: {planning_path}")

            # Save detailed calendar (v4.0.0 format for brief generation)
            if result.get("detailed_calendar"):
                filename = f"{base_filename}_calendar_detailed.json"
                content = json.dumps(result["detailed_calendar"], indent=2)

                if self.storage_client:
                    self.storage_client.save_output(filename, content, "application/json")

                if self.output_dir:
                    calendar_path = self.output_dir / filename
                    with open(calendar_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"Saved detailed calendar locally: {calendar_path}")

            # Save simplified calendar (upload format)
            if result.get("simplified_calendar"):
                filename = f"{base_filename}_calendar_simplified.json"
                content = json.dumps(result["simplified_calendar"], indent=2)

                if self.storage_client:
                    self.storage_client.save_output(filename, content, "application/json")

                if self.output_dir:
                    calendar_path = self.output_dir / filename
                    with open(calendar_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"Saved simplified calendar locally: {calendar_path}")

            # Save strategy summary (extracted from metadata)
            if result.get("strategy_summary"):
                filename = f"{base_filename}_strategy_summary.json"
                content = json.dumps(result["strategy_summary"], indent=2)

                if self.storage_client:
                    self.storage_client.save_output(filename, content, "application/json")

                if self.output_dir:
                    summary_path = self.output_dir / filename
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"✓ Saved strategy summary locally: {summary_path}")

            # TRACE: Execution checkpoint before enriched context block
            logger.info("🔍 TRACE: About to start enriched context generation block (line 675)")

            # Generate and save enriched context for data preservation
            # DEBUG: Log result keys to diagnose conditional check
            logger.info(f"DEBUG: Result keys available: {list(result.keys())}")
            logger.info(f"DEBUG: Checking enriched context conditions - simplified_calendar: {bool(result.get('simplified_calendar'))}, detailed_calendar: {bool(result.get('detailed_calendar'))}")

            if result.get("simplified_calendar") and result.get("detailed_calendar"):
                logger.info("DEBUG: Both calendars present, generating enriched context...")
                try:
                    # Extract client name from workflow_id
                    client_name = workflow_id.split('_')[0]
                    logger.info(f"DEBUG: Extracted client_name: {client_name}")

                    # Instantiate enriched context manager
                    enriched_manager = EnrichedContextManager(output_dir=str(self.output_dir) if self.output_dir else "./outputs")
                    logger.info(f"DEBUG: EnrichedContextManager instantiated with output_dir: {self.output_dir}")

                    # Create enriched context from both calendar formats
                    logger.info("DEBUG: Calling create_enriched_context...")
                    enriched_context = enriched_manager.create_enriched_context(
                        client_name=client_name,
                        simplified_calendar=result["simplified_calendar"],
                        detailed_calendar=result["detailed_calendar"],
                        context_key=workflow_id  # Use workflow_id as context key for consistency
                    )
                    logger.info(f"DEBUG: Enriched context created with {len(enriched_context.get('events', {}))} events")

                    # Save enriched context
                    filename = f"{base_filename}_enriched_context.json"
                    content = json.dumps(enriched_context, indent=2)
                    logger.info(f"DEBUG: Serialized enriched context, size: {len(content)} bytes")

                    if self.storage_client:
                        self.storage_client.save_output(filename, content, "application/json")
                        logger.info(f"DEBUG: Saved to GCS: {filename}")

                    if self.output_dir:
                        enriched_path = self.output_dir / filename
                        with open(enriched_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"Saved enriched context locally: {enriched_path}")

                    logger.info(f"✅ Enriched context preserved with key: {workflow_id}")

                except Exception as e:
                    logger.error(f"❌ Failed to save enriched context: {str(e)}")
                    logger.exception("Full exception traceback:")
            else:
                logger.warning(f"DEBUG: Enriched context NOT generated - simplified_calendar present: {bool(result.get('simplified_calendar'))}, detailed_calendar present: {bool(result.get('detailed_calendar'))}")

            # Transform and save app format (from detailed calendar)
            if result.get("detailed_calendar"):
                try:
                    client_id = workflow_id.split('_')[0]
                    app_calendar = self.format_adapter.transform_to_app_format(
                        result["detailed_calendar"],
                        client_id=client_id
                    )
                    filename = f"{base_filename}_calendar_app.json"
                    content = json.dumps(app_calendar, indent=2)

                    if self.storage_client:
                        self.storage_client.save_output(filename, content, "application/json")

                    if self.output_dir:
                        app_path = self.output_dir / filename
                        with open(app_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"Saved app format calendar locally: {app_path}")
                except Exception as e:
                    logger.error(f"Failed to save app format: {str(e)}")

            # Transform and save Import Specification format (from detailed calendar)
            if result.get("detailed_calendar"):
                try:
                    client_id = workflow_id.split('_')[0]
                    import_spec_calendar = self.format_adapter.transform_to_import_spec_format(
                        result["detailed_calendar"],
                        client_id=client_id,
                        workflow_id=workflow_id
                    )
                    filename = f"{base_filename}_calendar_import.json"
                    content = json.dumps(import_spec_calendar, indent=2)

                    if self.storage_client:
                        self.storage_client.save_output(filename, content, "application/json")

                    if self.output_dir:
                        import_path = self.output_dir / filename
                        with open(import_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"✅ Saved Import Specification calendar locally: {import_path}")
                        logger.info(f"   Linked to enriched context: {workflow_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to save Import Specification format: {str(e)}")
                    logger.exception("Full exception traceback:")

            # Save briefs output
            if result.get("briefs"):
                filename = f"{base_filename}_briefs.txt"

                if self.storage_client:
                    self.storage_client.save_output(filename, result["briefs"], "text/plain")

                if self.output_dir:
                    briefs_path = self.output_dir / filename
                    with open(briefs_path, 'w', encoding='utf-8') as f:
                        f.write(result["briefs"])
                    logger.info(f"Saved briefs output locally: {briefs_path}")

            # Save validation report
            filename = f"{base_filename}_validation.json"
            content = json.dumps(validation, indent=2)

            if self.storage_client:
                self.storage_client.save_output(filename, content, "application/json")

            if self.output_dir:
                validation_path = self.output_dir / filename
                with open(validation_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Saved validation report locally: {validation_path}")

        except Exception as e:
            logger.error(f"Failed to save outputs: {str(e)}")

    async def run_stage(
        self,
        stage: int,
        client_name: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run a single workflow stage.

        Useful for testing or debugging individual stages.

        Args:
            stage: Stage number (1, 2, or 3)
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            **kwargs: Additional stage-specific arguments

        Returns:
            Stage output
        """
        workflow_id = f"{client_name}_{start_date}_{end_date}"

        logger.info(f"Running stage {stage} for {workflow_id}")

        try:
            if stage == 1:
                output = await self.agent.stage_1_planning(
                    client_name, start_date, end_date, workflow_id
                )
                return {"stage": 1, "output": output, "success": True}

            elif stage == 2:
                planning_output = kwargs.get("planning_output")
                if not planning_output:
                    raise ValueError("stage 2 requires 'planning_output' kwarg")

                output = await self.agent.stage_2_structuring(
                    client_name, start_date, end_date, workflow_id, planning_output
                )
                return {"stage": 2, "output": output, "success": True}

            elif stage == 3:
                calendar_json = kwargs.get("calendar_json")
                if not calendar_json:
                    raise ValueError("stage 3 requires 'calendar_json' kwarg")

                output = await self.agent.stage_3_briefs(
                    client_name, workflow_id, calendar_json
                )
                return {"stage": 3, "output": output, "success": True}

            else:
                raise ValueError(f"Invalid stage: {stage} (must be 1, 2, or 3)")

        except Exception as e:
            logger.error(f"Stage {stage} failed: {str(e)}", exc_info=True)
            return {
                "stage": stage,
                "success": False,
                "error": str(e)
            }
