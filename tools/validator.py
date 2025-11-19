"""
Calendar JSON Validator

Validates calendar JSON output against v4.0.0 schema.
Ensures all required fields are present and properly formatted.
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class CalendarValidator:
    """
    Validator for v4.0.0 calendar JSON format.

    Validates:
    - Required top-level fields
    - Campaign event structure
    - Date formats
    - Channel specifications
    - Send time constraints
    """

    REQUIRED_CALENDAR_FIELDS = [
        "version",
        "client_name",
        "start_date",
        "end_date",
        "campaigns",
        "metadata"
    ]

    REQUIRED_CAMPAIGN_FIELDS = [
        "campaign_id",
        "name",
        "send_date",
        "channel",
        "type",
        "audience"
    ]

    VALID_CHANNELS = ["email", "sms"]
    VALID_CAMPAIGN_TYPES = [
        "promotional",
        "educational",
        "seasonal",
        "product_launch",
        "product_spotlight",
        "engagement",
        "win_back",
        "nurture",
        "resend",
        "lifecycle"
    ]

    def __init__(self):
        """Initialize validator."""
        logger.info("CalendarValidator initialized")

    def validate_calendar(self, calendar_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate complete calendar JSON.

        Args:
            calendar_json: Calendar JSON to validate

        Returns:
            Tuple of (is_valid, error_messages)
            - is_valid: True if calendar is valid, False otherwise
            - error_messages: List of validation error messages
        """
        errors = []

        # Check for required top-level fields
        for field in self.REQUIRED_CALENDAR_FIELDS:
            if field not in calendar_json:
                errors.append(f"Missing required field: {field}")

        # Validate version
        if calendar_json.get("version") != "4.0.0":
            errors.append(f"Invalid version: {calendar_json.get('version')} (expected 4.0.0)")

        # Validate date formats
        start_date = calendar_json.get("start_date")
        end_date = calendar_json.get("end_date")

        if start_date:
            if not self._is_valid_date(start_date):
                errors.append(f"Invalid start_date format: {start_date} (expected YYYY-MM-DD)")

        if end_date:
            if not self._is_valid_date(end_date):
                errors.append(f"Invalid end_date format: {end_date} (expected YYYY-MM-DD)")

        # Validate campaigns array
        campaigns = calendar_json.get("campaigns", [])

        if not isinstance(campaigns, list):
            errors.append("'campaigns' must be an array")
        else:
            for idx, campaign in enumerate(campaigns):
                campaign_errors = self._validate_campaign(campaign, idx)
                errors.extend(campaign_errors)

        is_valid = len(errors) == 0

        if is_valid:
            logger.info(f"Calendar validation passed ({len(campaigns)} campaigns)")
        else:
            logger.warning(f"Calendar validation failed with {len(errors)} errors")

        return is_valid, errors

    def _validate_campaign(self, campaign: Dict[str, Any], index: int) -> List[str]:
        """
        Validate a single campaign event.

        Args:
            campaign: Campaign JSON object
            index: Campaign index in array (for error messages)

        Returns:
            List of validation error messages
        """
        errors = []
        prefix = f"Campaign [{index}]"

        # Check required fields
        for field in self.REQUIRED_CAMPAIGN_FIELDS:
            if field not in campaign:
                errors.append(f"{prefix} Missing required field: {field}")

        # Validate channel
        channel = campaign.get("channel")
        if channel and channel not in self.VALID_CHANNELS:
            errors.append(f"{prefix} Invalid channel: {channel} (must be one of {self.VALID_CHANNELS})")

        # Validate campaign type
        campaign_type = campaign.get("type")
        if campaign_type and campaign_type not in self.VALID_CAMPAIGN_TYPES:
            errors.append(f"{prefix} Invalid type: {campaign_type} (must be one of {self.VALID_CAMPAIGN_TYPES})")

        # Validate send_date
        send_date = campaign.get("send_date")
        if send_date:
            if not self._is_valid_date(send_date):
                errors.append(f"{prefix} Invalid send_date format: {send_date} (expected YYYY-MM-DD)")

        # Validate send_time if present
        send_time = campaign.get("send_time")
        if send_time:
            if not self._is_valid_time(send_time):
                errors.append(f"{prefix} Invalid send_time format: {send_time} (expected HH:MM)")

        # Validate audience
        audience = campaign.get("audience")
        if audience and not isinstance(audience, dict):
            errors.append(f"{prefix} 'audience' must be an object")
        else:
            if audience:
                # Check for either segment_id or list_id
                has_segment = "segment_id" in audience or "segment_name" in audience
                has_list = "list_id" in audience or "list_name" in audience

                if not (has_segment or has_list):
                    errors.append(f"{prefix} 'audience' must have either segment or list specification")

        return errors

    def _is_valid_date(self, date_str: str) -> bool:
        """
        Check if date string is in YYYY-MM-DD format.

        Args:
            date_str: Date string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

    def _is_valid_time(self, time_str: str) -> bool:
        """
        Check if time string is in HH:MM format (24-hour) or HH:MM AM/PM format (12-hour).

        Args:
            time_str: Time string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Try 24-hour format first (HH:MM)
            datetime.strptime(time_str, "%H:%M")
            return True
        except (ValueError, TypeError):
            pass

        try:
            # Try 12-hour format with AM/PM (HH:MM AM/PM)
            datetime.strptime(time_str, "%I:%M %p")
            return True
        except (ValueError, TypeError):
            return False

    def validate_planning_output(self, planning_text: str) -> Tuple[bool, List[str]]:
        """
        Validate planning stage output.

        Checks for presence of key sections and content quality indicators.

        Args:
            planning_text: Planning output text

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        # Check minimum length
        if len(planning_text) < 500:
            warnings.append("Planning output is very short (< 500 characters)")

        # Check for key sections (case-insensitive)
        planning_lower = planning_text.lower()

        expected_sections = [
            "strategic",
            "campaign",
            "audience",
            "timing"
        ]

        for section in expected_sections:
            if section not in planning_lower:
                warnings.append(f"Planning output may be missing '{section}' content")

        # Check for date references
        if "2025" not in planning_text and "2024" not in planning_text:
            warnings.append("Planning output may be missing specific date references")

        # Warnings are informational only - they don't invalidate the output
        is_valid = True

        if len(warnings) == 0:
            logger.info("Planning output validation passed")
        else:
            logger.warning(f"Planning output validation has {len(warnings)} warnings")

        return is_valid, warnings

    def validate_briefs_output(self, briefs_text: str, campaign_count: int) -> Tuple[bool, List[str]]:
        """
        Validate briefs stage output.

        Checks for presence of campaign briefs and content quality.

        Args:
            briefs_text: Briefs output text
            campaign_count: Expected number of campaigns

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        # Check minimum length
        min_length = campaign_count * 300  # At least 300 chars per campaign
        if len(briefs_text) < min_length:
            warnings.append(f"Briefs output is short (< {min_length} characters for {campaign_count} campaigns)")

        # Check for key brief sections
        briefs_lower = briefs_text.lower()

        expected_elements = [
            "subject",
            "preview",
            "audience"
        ]

        for element in expected_elements:
            if element not in briefs_lower:
                warnings.append(f"Briefs may be missing '{element}' specifications")

        # Check for send time/send_time (handle both natural language and JSON key format)
        if "send time" not in briefs_lower and "send_time" not in briefs_lower:
            warnings.append(f"Briefs may be missing 'send time' specifications")

        # Warnings are informational only - they don't invalidate the output
        is_valid = True

        if len(warnings) == 0:
            logger.info(f"Briefs output validation passed ({campaign_count} campaigns)")
        else:
            logger.warning(f"Briefs output validation has {len(warnings)} warnings")

        return is_valid, warnings
