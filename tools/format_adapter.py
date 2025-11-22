"""
Format Adapter for EmailPilot App Integration

Transforms v4.0.0 calendar JSON to EmailPilot app-compatible format.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CalendarFormatAdapter:
    """
    Adapter that transforms v4.0.0 calendar JSON to EmailPilot app format.

    Handles field mapping, emoji prefixes, and data transformation for
    integration with EmailPilot app at http://127.0.0.1:8000
    """

    # Channel to emoji mapping
    CHANNEL_EMOJIS = {
        'email': '✉️',
        'sms': '💬',
        'push': '📱',
        'mobile_push': '📱'
    }

    # Campaign type normalization
    TYPE_MAPPING = {
        'promotional': 'promotional',
        'product_spotlight': 'promotional',
        'educational': 'content',
        'lifecycle': 'engagement',
        'win_back': 'engagement',
        'nurture': 'engagement',
        'seasonal': 'seasonal',
        'resend': 'promotional'
    }

    def __init__(self):
        """Initialize the format adapter."""
        self.logger = logging.getLogger(__name__)

    def transform_to_app_format(
        self,
        v4_calendar: Dict[str, Any],
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transform v4.0.0 calendar JSON to EmailPilot app format.

        Args:
            v4_calendar: Calendar in v4.0.0 format
            client_id: Optional client ID for app import

        Returns:
            Calendar in EmailPilot app format

        Example v4.0.0 input:
            {
                "calendar_variants": [{
                    "events": [{
                        "event_id": 1,
                        "send_date": "2025-01-05",
                        "send_time": "10:17 AM",
                        "subject_lines": {"variant_a": "New Year Sale"},
                        "segments": {"primary": "engaged_subscribers"},
                        "campaign_type": "promotional",
                        "preview_text": "50% off...",
                        "hero_h1": "Start 2025 Right"
                    }]
                }]
            }

        Example app output:
            {
                "client_id": "rogue_creamery",
                "events": [{
                    "date": "2025-01-05",
                    "title": "✉️ New Year Sale",
                    "type": "promotional",
                    "description": "50% off...",
                    "segment": "engaged_subscribers",
                    "send_time": "10:17"
                }]
            }
        """
        self.logger.info("Transforming v4.0.0 calendar to app format")

        # Extract events from v4.0.0 structure
        events_v4 = self._extract_events_from_v4(v4_calendar)

        # Transform each event
        events_app = []
        for event in events_v4:
            app_event = self._transform_event(event)
            if app_event:
                events_app.append(app_event)

        # Build app-compatible structure
        app_calendar = {
            "events": events_app
        }

        # Add client_id if provided
        if client_id:
            app_calendar["client_id"] = client_id

        self.logger.info(f"Transformed {len(events_app)} events to app format")

        return app_calendar

    def _extract_events_from_v4(self, v4_calendar: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract events array from v4.0.0 calendar structure.

        Handles nested structure: calendar_variants[0].events
        """
        # Check for calendar_variants structure
        if "calendar_variants" in v4_calendar:
            variants = v4_calendar["calendar_variants"]
            if variants and isinstance(variants, list) and len(variants) > 0:
                first_variant = variants[0]
                if "events" in first_variant:
                    return first_variant["events"]

        # Fallback: check for direct events array
        if "events" in v4_calendar:
            return v4_calendar["events"]

        # Fallback: check for campaigns array (alternative naming)
        if "campaigns" in v4_calendar:
            return v4_calendar["campaigns"]

        self.logger.warning("No events found in v4.0.0 calendar")
        return []

    def _transform_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a single event from v4.0.0 to app format.

        Field mappings:
            send_date → date
            subject_lines.variant_a/hero_h1 → title (with emoji prefix)
            campaign_type → type
            preview_text/sub_headline → description
            segments.primary → segment
            send_time → send_time (normalized to HH:MM format)
        """
        try:
            # Required field: date
            date = self._extract_date(event)
            if not date:
                self.logger.warning(f"Event missing date, skipping: {event.get('event_id', 'unknown')}")
                return None

            # Required field: title
            title = self._extract_title(event)
            if not title:
                self.logger.warning(f"Event missing title, skipping: {event.get('event_id', 'unknown')}")
                return None

            # Add emoji prefix based on channel
            channel = self._extract_channel(event)
            title = self._add_emoji_prefix(title, channel)

            # Required field: type
            event_type = self._extract_type(event)

            # Optional fields
            description = self._extract_description(event)
            segment = self._extract_segment(event)
            send_time = self._extract_send_time(event)

            # Build app event
            app_event = {
                "date": date,
                "title": title,
                "type": event_type
            }

            # Add optional fields if present
            if description:
                app_event["description"] = description

            if segment:
                app_event["segment"] = segment

            if send_time:
                app_event["send_time"] = send_time

            return app_event

        except Exception as e:
            self.logger.error(f"Error transforming event: {str(e)}", exc_info=True)
            return None

    def _extract_date(self, event: Dict[str, Any]) -> Optional[str]:
        """Extract date in YYYY-MM-DD format."""
        # Try multiple field names
        for field in ['send_date', 'date', 'event_date', 'planned_send_date']:
            if field in event:
                date_value = event[field]
                if isinstance(date_value, str):
                    # Already a string, validate format
                    if len(date_value) >= 10:  # YYYY-MM-DD is 10 chars
                        return date_value[:10]
                    return date_value
        return None

    def _extract_title(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Extract campaign title from various sources.

        Priority:
        1. subject_lines.variant_a
        2. hero_h1
        3. name
        4. title
        """
        # Try subject_lines.variant_a (highest priority)
        if "subject_lines" in event:
            subject_lines = event["subject_lines"]
            if isinstance(subject_lines, dict):
                if "variant_a" in subject_lines:
                    return str(subject_lines["variant_a"])[:100]  # Max 100 chars

        # Try hero_h1
        if "hero_h1" in event:
            return str(event["hero_h1"])[:100]

        # Try name
        if "name" in event:
            return str(event["name"])[:100]

        # Try title
        if "title" in event:
            return str(event["title"])[:100]

        return None

    def _extract_channel(self, event: Dict[str, Any]) -> str:
        """Extract channel (defaults to email)."""
        return event.get('channel', 'email').lower()

    def _add_emoji_prefix(self, title: str, channel: str) -> str:
        """Add emoji prefix based on channel type."""
        # Don't add emoji if already present
        if any(emoji in title for emoji in self.CHANNEL_EMOJIS.values()):
            return title

        # Get emoji for channel
        emoji = self.CHANNEL_EMOJIS.get(channel, self.CHANNEL_EMOJIS['email'])

        return f"{emoji} {title}"

    def _extract_type(self, event: Dict[str, Any]) -> str:
        """
        Extract and normalize campaign type.

        Maps v4.0.0 types to app-compatible types.
        """
        v4_type = event.get('campaign_type', event.get('type', 'email'))

        # Normalize using mapping
        normalized_type = self.TYPE_MAPPING.get(v4_type.lower(), v4_type.lower())

        return normalized_type

    def _extract_description(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Extract campaign description from various sources.

        Priority:
        1. preview_text
        2. sub_headline
        3. description
        4. content_theme
        """
        for field in ['preview_text', 'sub_headline', 'description', 'content_theme']:
            if field in event and event[field]:
                desc = str(event[field])
                # Truncate if too long
                return desc[:500] if len(desc) > 500 else desc

        return None

    def _extract_segment(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Extract primary segment name.

        Handles both nested (segments.primary) and flat (segment) structures.
        """
        # Try nested structure first
        if "segments" in event:
            segments = event["segments"]
            if isinstance(segments, dict):
                if "primary" in segments:
                    return str(segments["primary"])

        # Try flat structure
        if "segment" in event:
            return str(event["segment"])

        # Try audience field
        if "audience" in event:
            audience = event["audience"]
            if isinstance(audience, dict):
                if "segment_id" in audience:
                    return str(audience["segment_id"])
                if "name" in audience:
                    return str(audience["name"])
            elif isinstance(audience, str):
                return audience

        return None

    def _extract_send_time(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Extract send time in HH:MM format.

        Converts from "10:17 AM" format to "10:17" format.
        """
        send_time = event.get('send_time')
        if not send_time:
            return None

        send_time = str(send_time).strip()

        # Remove AM/PM if present
        send_time = send_time.replace(' AM', '').replace(' PM', '').replace('AM', '').replace('PM', '')

        # Validate format (should be HH:MM)
        if ':' in send_time:
            parts = send_time.split(':')
            if len(parts) == 2:
                try:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        return f"{hour:02d}:{minute:02d}"
                except ValueError:
                    pass

        return None

    def validate_app_format(self, app_calendar: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate calendar is in correct app format.

        Returns:
            (is_valid, errors)
        """
        errors = []

        # Check required top-level fields
        if "events" not in app_calendar:
            errors.append("Missing required field: events")
            return False, errors

        events = app_calendar["events"]

        # Validate events is a list
        if not isinstance(events, list):
            errors.append("Field 'events' must be an array")
            return False, errors

        # Validate each event
        for i, event in enumerate(events):
            event_errors = self._validate_app_event(event, i)
            errors.extend(event_errors)

        is_valid = len(errors) == 0

        return is_valid, errors

    def _validate_app_event(self, event: Dict[str, Any], index: int) -> List[str]:
        """Validate a single app event."""
        errors = []

        # Required fields
        required_fields = ['date', 'title', 'type']
        for field in required_fields:
            if field not in event:
                errors.append(f"Event {index}: Missing required field '{field}'")

        # Validate date format
        if 'date' in event:
            date = event['date']
            if not isinstance(date, str) or len(date) < 10:
                errors.append(f"Event {index}: Invalid date format (expected YYYY-MM-DD)")

        # Validate title length
        if 'title' in event:
            if len(event['title']) > 100:
                errors.append(f"Event {index}: Title exceeds 100 characters")

        # Validate type
        if 'type' in event:
            # Type should be lowercase
            if event['type'] != event['type'].lower():
                errors.append(f"Event {index}: Type must be lowercase")

        return errors
