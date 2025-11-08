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
            if self.validate_outputs and result.get("planning"):
                planning_valid, planning_warnings = self.validator.validate_planning_output(
                    result["planning"]
                )
                validation_results["planning_valid"] = planning_valid
                if planning_warnings:
                    validation_results["warnings"].extend(
                        [f"Planning: {w}" for w in planning_warnings]
                    )

            # Validate calendar JSON
            if self.validate_outputs and result.get("calendar_json"):
                calendar_valid, calendar_errors = self.validator.validate_calendar(
                    result["calendar_json"]
                )
                validation_results["calendar_valid"] = calendar_valid
                if calendar_errors:
                    validation_results["errors"].extend(
                        [f"Calendar: {e}" for e in calendar_errors]
                    )

            # Validate briefs output
            if self.validate_outputs and result.get("briefs"):
                campaign_count = len(result.get("calendar_json", {}).get("campaigns", []))
                briefs_valid, briefs_warnings = self.validator.validate_briefs_output(
                    result["briefs"],
                    campaign_count
                )
                validation_results["briefs_valid"] = briefs_valid
                if briefs_warnings:
                    validation_results["warnings"].extend(
                        [f"Briefs: {w}" for w in briefs_warnings]
                    )

            # Determine overall success
            all_valid = (
                validation_results["planning_valid"] and
                validation_results["calendar_valid"] and
                validation_results["briefs_valid"]
            )

            # Save outputs if requested
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

            # Save calendar JSON
            if result.get("calendar_json"):
                filename = f"{base_filename}_calendar.json"
                content = json.dumps(result["calendar_json"], indent=2)

                if self.storage_client:
                    self.storage_client.save_output(filename, content, "application/json")

                if self.output_dir:
                    calendar_path = self.output_dir / filename
                    with open(calendar_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"Saved calendar JSON locally: {calendar_path}")

            # Transform and save app format
            if result.get("calendar_json"):
                try:
                    client_id = workflow_id.split('_')[0]
                    app_calendar = self.format_adapter.transform_to_app_format(
                        result["calendar_json"],
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
