"""
Firestore Client for Client Metadata

Fetches client configuration and metadata from Google Cloud Firestore,
including revenue goals, send caps, and other client-specific settings.
"""

from typing import Dict, Optional, Any
import logging
from google.cloud import firestore
from google.api_core.exceptions import NotFound

logger = logging.getLogger(__name__)


class FirestoreClient:
    """
    Client for fetching client metadata from Firestore.

    Firestore stores client configuration including:
    - Revenue goals (monthly and annual targets)
    - Send capacity limits (email and SMS)
    - Timezone information
    - Custom client settings
    """

    def __init__(self, project_id: str):
        """
        Initialize Firestore client.

        Args:
            project_id: Google Cloud project ID
        """
        self.project_id = project_id
        self.db = firestore.Client(project=project_id)
        self.collection_name = "clients"

    def _get_firestore_doc_id(self, client_name: str) -> str:
        """
        Return client name as Firestore document ID.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            Firestore document ID (same as client_name)
        """
        # Use client name as-is for Firestore doc ID
        return client_name

    def get_client_metadata(self, client_name: str) -> Optional[Dict[str, Any]]:
        """
        Get all metadata for a specific client.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            Client metadata dictionary, or None if not found
        """
        doc_id = self._get_firestore_doc_id(client_name)

        try:
            doc_ref = self.db.collection(self.collection_name).document(doc_id)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                logger.info(f"Retrieved Firestore metadata for {client_name}")
                return data
            else:
                logger.warning(f"No Firestore document found for {client_name} (doc_id: {doc_id})")
                return None

        except NotFound:
            logger.warning(f"Firestore document not found: {doc_id}")
            return None

        except Exception as e:
            logger.error(f"Error fetching Firestore data for {client_name}: {str(e)}")
            return None

    def get_revenue_goals(self, client_name: str) -> Optional[Dict[str, float]]:
        """
        Get revenue goals for a client.

        Args:
            client_name: Client slug

        Returns:
            Revenue goals dictionary:
            {
                "monthly": float,
                "annual": float
            }
            or None if not found
        """
        metadata = self.get_client_metadata(client_name)

        if not metadata:
            return None

        return {
            "monthly": metadata.get("revenue_goal_monthly", 0.0),
            "annual": metadata.get("revenue_goal_annual", 0.0)
        }

    def get_send_caps(self, client_name: str) -> Optional[Dict[str, int]]:
        """
        Get send capacity limits for a client.

        Args:
            client_name: Client slug

        Returns:
            Send caps dictionary:
            {
                "email": int,
                "sms": int
            }
            or None if not found
        """
        metadata = self.get_client_metadata(client_name)

        if not metadata:
            return None

        return {
            "email": metadata.get("send_cap_email", 0),
            "sms": metadata.get("send_cap_sms", 0)
        }

    def get_timezone(self, client_name: str) -> Optional[str]:
        """
        Get timezone for a client.

        Args:
            client_name: Client slug

        Returns:
            Timezone string (e.g., "America/Los_Angeles"), or None if not found
        """
        metadata = self.get_client_metadata(client_name)

        if not metadata:
            return None

        return metadata.get("timezone")

    def get_display_name(self, client_name: str) -> Optional[str]:
        """
        Get display name for a client.

        Args:
            client_name: Client slug

        Returns:
            Display name (e.g., "Rogue Creamery"), or None if not found
        """
        metadata = self.get_client_metadata(client_name)

        if not metadata:
            return None

        return metadata.get("display_name")

    def get_all_data(self, client_name: str) -> Dict[str, Any]:
        """
        Get all Firestore data for a client.

        This is the main method used in Stage 1 (Planning) to fetch
        all client configuration data.

        Args:
            client_name: Client slug

        Returns:
            Dictionary containing all Firestore data:
            {
                "metadata": dict,
                "revenue_goals": dict,
                "send_caps": dict,
                "timezone": str,
                "display_name": str
            }
        """
        logger.info(f"Fetching all Firestore data for {client_name}")

        metadata = self.get_client_metadata(client_name)

        if not metadata:
            logger.warning(f"No Firestore data available for {client_name}")
            return {
                "metadata": None,
                "revenue_goals": None,
                "send_caps": None,
                "timezone": None,
                "display_name": None
            }

        result = {
            "metadata": metadata,
            "revenue_goals": self.get_revenue_goals(client_name),
            "send_caps": self.get_send_caps(client_name),
            "timezone": self.get_timezone(client_name),
            "display_name": self.get_display_name(client_name)
        }

        logger.info(f"Firestore data fetch complete for {client_name}")

        return result

    def format_for_prompt(self, client_name: str) -> str:
        """
        Format Firestore data as a text block for inclusion in AI prompts.

        Args:
            client_name: Client slug

        Returns:
            Formatted text block with client metadata
        """
        data = self.get_all_data(client_name)

        if not data["metadata"]:
            return f"# Client Configuration for {client_name}\n\nNo configuration data available."

        sections = []

        if data["display_name"]:
            sections.append(f"**Client Name:** {data['display_name']}")

        if data["revenue_goals"]:
            sections.append(
                f"**Revenue Goals:**\n"
                f"- Monthly: ${data['revenue_goals']['monthly']:,.2f}\n"
                f"- Annual: ${data['revenue_goals']['annual']:,.2f}"
            )

        if data["send_caps"]:
            sections.append(
                f"**Send Capacity:**\n"
                f"- Email: {data['send_caps']['email']:,} sends/month\n"
                f"- SMS: {data['send_caps']['sms']:,} sends/month"
            )

        if data["timezone"]:
            sections.append(f"**Timezone:** {data['timezone']}")

        # Include any additional metadata fields
        if data["metadata"]:
            other_fields = {
                k: v for k, v in data["metadata"].items()
                if k not in ["display_name", "revenue_goal_monthly", "revenue_goal_annual",
                           "send_cap_email", "send_cap_sms", "timezone", "firestore_doc_id"]
            }

            if other_fields:
                sections.append(f"**Additional Settings:**\n" +
                              "\n".join([f"- {k}: {v}" for k, v in other_fields.items()]))

        formatted = f"# Client Configuration for {client_name}\n\n" + "\n\n".join(sections)

        logger.info(f"Formatted Firestore data for prompt: {len(formatted)} characters")

        return formatted

    def update_client_metadata(
        self,
        client_name: str,
        updates: Dict[str, Any],
        merge: bool = True
    ) -> bool:
        """
        Update client metadata in Firestore.

        Args:
            client_name: Client slug
            updates: Dictionary of fields to update
            merge: If True, merge with existing data. If False, replace entire document.

        Returns:
            True if successful, False otherwise
        """
        doc_id = self._get_firestore_doc_id(client_name)

        try:
            doc_ref = self.db.collection(self.collection_name).document(doc_id)

            if merge:
                doc_ref.set(updates, merge=True)
            else:
                doc_ref.set(updates)

            logger.info(f"Updated Firestore metadata for {client_name}")
            return True

        except Exception as e:
            logger.error(f"Error updating Firestore data for {client_name}: {str(e)}")
            return False
