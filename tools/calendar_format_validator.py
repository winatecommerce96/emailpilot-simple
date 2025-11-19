"""
Calendar JSON Format Validator

Validates calendar JSON files against the CALENDAR_JSON_UPLOAD_FORMAT.md specification.
Ensures compliance with required fields, data types, and business rules.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path


class CalendarFormatValidator:
    """Validator for calendar JSON format compliance."""

    # Valid campaign types from spec
    VALID_EMAIL_TYPES = {
        "email", "promotional", "content", "engagement",
        "seasonal", "special", "educational", "product_launch",
        "win_back", "nurture"
    }

    VALID_SMS_TYPES = {
        "sms", "sms-promotional", "sms-content",
        "sms-engagement", "sms-seasonal", "sms-special"
    }

    VALID_PUSH_TYPES = {
        "push", "push-promotional", "push-reminder"
    }

    VALID_TYPES = VALID_EMAIL_TYPES | VALID_SMS_TYPES | VALID_PUSH_TYPES

    # Field length limits
    MAX_TITLE_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_FILE_SIZE_MB = 5
    MAX_CAMPAIGNS_PER_FILE = 1000

    # Date validation ranges
    MIN_YEAR = 2020
    MAX_YEAR = 2030

    # Field name alternatives
    TITLE_ALTERNATIVES = {"title", "name", "subject_line_a"}
    SEGMENT_ALTERNATIVES = {"segment", "segments"}
    SMS_VARIANT_ALTERNATIVES = {"secondary_message", "sms_variant"}

    def __init__(self):
        """Initialize validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_json_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a JSON file against calendar format specification.

        Args:
            file_path: Path to JSON file

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        try:
            # Check file size
            file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            if file_size_mb > self.MAX_FILE_SIZE_MB:
                self.errors.append(
                    f"File size {file_size_mb:.2f}MB exceeds maximum {self.MAX_FILE_SIZE_MB}MB"
                )
                return False, self.errors, self.warnings

            # Load JSON
            with open(file_path, 'r') as f:
                data = json.load(f)

        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON format: {e}")
            return False, self.errors, self.warnings
        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return False, self.errors, self.warnings

        # Validate structure and extract events
        events = self._extract_events(data)
        if not events:
            return False, self.errors, self.warnings

        # Validate event count
        if len(events) > self.MAX_CAMPAIGNS_PER_FILE:
            self.errors.append(
                f"Number of campaigns ({len(events)}) exceeds maximum {self.MAX_CAMPAIGNS_PER_FILE}"
            )
            return False, self.errors, self.warnings

        # Validate each event
        for idx, event in enumerate(events, 1):
            self._validate_event(event, idx)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def validate_json_data(self, data: Any) -> Tuple[bool, List[str], List[str]]:
        """
        Validate JSON data (already parsed) against calendar format specification.

        Args:
            data: Parsed JSON data (dict or list)

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # Validate structure and extract events
        events = self._extract_events(data)
        if not events:
            return False, self.errors, self.warnings

        # Validate event count
        if len(events) > self.MAX_CAMPAIGNS_PER_FILE:
            self.errors.append(
                f"Number of campaigns ({len(events)}) exceeds maximum {self.MAX_CAMPAIGNS_PER_FILE}"
            )
            return False, self.errors, self.warnings

        # Validate each event
        for idx, event in enumerate(events, 1):
            self._validate_event(event, idx)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _extract_events(self, data: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Extract events array from JSON data, handling multiple formats.

        Supports:
        - {"events": [...]}
        - {"calendar": [...]}
        - Direct array [...]

        Args:
            data: Parsed JSON data

        Returns:
            List of event dictionaries, or None if format invalid
        """
        if isinstance(data, list):
            # Direct array format
            return data
        elif isinstance(data, dict):
            if "events" in data:
                if isinstance(data["events"], list):
                    return data["events"]
                else:
                    self.errors.append("'events' property must be an array")
                    return None
            elif "calendar" in data:
                if isinstance(data["calendar"], list):
                    return data["calendar"]
                else:
                    self.errors.append("'calendar' property must be an array")
                    return None
            else:
                self.errors.append(
                    "Unrecognized JSON format. Must be array or object with 'events' or 'calendar' property"
                )
                return None
        else:
            self.errors.append(
                "Invalid JSON root type. Must be array or object"
            )
            return None

    def _validate_event(self, event: Dict[str, Any], index: int) -> None:
        """
        Validate a single event object.

        Args:
            event: Event dictionary
            index: Event index (for error messages)
        """
        prefix = f"Event #{index}"

        if not isinstance(event, dict):
            self.errors.append(f"{prefix}: Must be an object/dictionary")
            return

        # Validate required fields
        self._validate_date(event, prefix)
        self._validate_title(event, prefix)
        self._validate_type(event, prefix)

        # Validate optional fields if present
        if "description" in event:
            self._validate_description(event["description"], prefix)

        if "week_number" in event:
            self._validate_week_number(event["week_number"], prefix)

        if "send_time" in event:
            self._validate_send_time(event["send_time"], prefix)

        # Validate field lengths for various text fields
        text_fields = [
            "subject_line_a", "subject_line_b", "preview_text",
            "hero_h1", "sub_head", "hero_image", "cta_copy",
            "offer", "ab_test_idea", "secondary_message", "sms_variant"
        ]
        for field in text_fields:
            if field in event and event[field]:
                if not isinstance(event[field], str):
                    self.warnings.append(f"{prefix}: '{field}' should be a string")

    def _validate_date(self, event: Dict[str, Any], prefix: str) -> None:
        """Validate date field."""
        if "date" not in event and "send_date" not in event:
            self.errors.append(f"{prefix}: Missing required 'date' field")
            return

        date_value = event.get("date") or event.get("send_date")

        if not isinstance(date_value, str):
            self.errors.append(f"{prefix}: 'date' must be a string")
            return

        # Validate YYYY-MM-DD format
        try:
            date_obj = datetime.strptime(date_value, "%Y-%m-%d")

            # Validate year range
            if not (self.MIN_YEAR <= date_obj.year <= self.MAX_YEAR):
                self.errors.append(
                    f"{prefix}: Year {date_obj.year} outside valid range "
                    f"{self.MIN_YEAR}-{self.MAX_YEAR}"
                )

        except ValueError:
            self.errors.append(
                f"{prefix}: Invalid date format '{date_value}'. Must be YYYY-MM-DD"
            )

    def _validate_title(self, event: Dict[str, Any], prefix: str) -> None:
        """Validate title field (or alternatives: name, subject_line_a)."""
        title_field = None
        title_value = None

        # Check for title alternatives
        for field in self.TITLE_ALTERNATIVES:
            if field in event:
                title_field = field
                title_value = event[field]
                break

        if not title_field:
            self.errors.append(
                f"{prefix}: Missing required 'title' field "
                f"(or alternative: 'name', 'subject_line_a')"
            )
            return

        if not isinstance(title_value, str):
            self.errors.append(f"{prefix}: '{title_field}' must be a string")
            return

        if not title_value.strip():
            self.errors.append(f"{prefix}: '{title_field}' cannot be empty")
            return

        if len(title_value) > self.MAX_TITLE_LENGTH:
            self.errors.append(
                f"{prefix}: '{title_field}' exceeds maximum length "
                f"{self.MAX_TITLE_LENGTH} characters (current: {len(title_value)})"
            )

    def _validate_type(self, event: Dict[str, Any], prefix: str) -> None:
        """Validate type field."""
        if "type" not in event:
            self.errors.append(f"{prefix}: Missing required 'type' field")
            return

        type_value = event["type"]

        if not isinstance(type_value, str):
            self.errors.append(f"{prefix}: 'type' must be a string")
            return

        if type_value not in self.VALID_TYPES:
            self.errors.append(
                f"{prefix}: Unknown campaign type '{type_value}'. "
                f"Valid types: {', '.join(sorted(self.VALID_TYPES))}"
            )

    def _validate_description(self, description: Any, prefix: str) -> None:
        """Validate description field."""
        if not isinstance(description, str):
            self.warnings.append(f"{prefix}: 'description' should be a string")
            return

        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            self.warnings.append(
                f"{prefix}: 'description' exceeds recommended length "
                f"{self.MAX_DESCRIPTION_LENGTH} characters (current: {len(description)})"
            )

    def _validate_week_number(self, week_number: Any, prefix: str) -> None:
        """Validate week_number field."""
        if not isinstance(week_number, int):
            self.warnings.append(f"{prefix}: 'week_number' should be an integer")
            return

        if not (1 <= week_number <= 53):
            self.warnings.append(
                f"{prefix}: 'week_number' {week_number} outside typical range 1-53"
            )

    def _validate_send_time(self, send_time: Any, prefix: str) -> None:
        """Validate send_time field (HH:MM format)."""
        if not isinstance(send_time, str):
            self.warnings.append(f"{prefix}: 'send_time' should be a string")
            return

        try:
            datetime.strptime(send_time, "%H:%M")
        except ValueError:
            self.warnings.append(
                f"{prefix}: Invalid 'send_time' format '{send_time}'. "
                "Should be HH:MM (24-hour format)"
            )


def validate_calendar_json(file_path: str) -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate a calendar JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = CalendarFormatValidator()
    return validator.validate_json_file(file_path)


def validate_calendar_data(data: Any) -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate calendar JSON data.

    Args:
        data: Parsed JSON data (dict or list)

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = CalendarFormatValidator()
    return validator.validate_json_data(data)
