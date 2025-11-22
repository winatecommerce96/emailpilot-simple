"""
Review State Manager for Calendar Workflow

Manages manual review checkpoints and workflow state in Firestore.
Enables workflow split: Stage 1-2 → Review → Stage 3
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum

try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    firestore = None

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Review status states."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"


class ReviewStateManager:
    """
    Manages workflow review state in Firestore.

    Stores workflow outputs after Stage 2 and tracks review/approval status.
    Enables manual review gate before proceeding to Stage 3.
    """

    COLLECTION_NAME = "workflow_reviews"

    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize review state manager.

        Args:
            project_id: Google Cloud project ID (optional, uses default if not provided)
        """
        if not FIRESTORE_AVAILABLE:
            logger.warning("Firestore not available. Review state will not persist.")
            self.db = None
            return

        try:
            if project_id:
                self.db = firestore.Client(project=project_id)
            else:
                self.db = firestore.Client()
            logger.info(f"ReviewStateManager initialized with Firestore")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            self.db = None

    def is_available(self) -> bool:
        """Check if Firestore is available."""
        return self.db is not None

    def save_review_state(
        self,
        workflow_id: str,
        client_name: str,
        start_date: str,
        end_date: str,
        planning_output: str,
        detailed_calendar: Dict[str, Any],
        simplified_calendar: Dict[str, Any],
        validation_results: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save workflow state for review after Stage 2.

        Args:
            workflow_id: Unique workflow identifier
            client_name: Client slug
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            planning_output: Stage 1 planning text
            detailed_calendar: Stage 2 detailed calendar JSON
            simplified_calendar: Stage 2 simplified calendar JSON
            validation_results: Stage 2 validation results
            metadata: Optional additional metadata

        Returns:
            True if saved successfully, False otherwise
        """
        if not self.is_available():
            logger.warning("Firestore not available. Cannot save review state.")
            return False

        try:
            doc_ref = self.db.collection(self.COLLECTION_NAME).document(workflow_id)

            review_state = {
                "workflow_id": workflow_id,
                "client_name": client_name,
                "start_date": start_date,
                "end_date": end_date,
                "planning_output": planning_output,
                "detailed_calendar": detailed_calendar,
                "simplified_calendar": simplified_calendar,
                "validation_results": validation_results,
                "review_status": ReviewStatus.PENDING.value,
                "submitted_at": datetime.utcnow().isoformat(),
                "reviewed_at": None,
                "reviewed_by": None,
                "review_notes": None,
                "metadata": metadata or {}
            }

            doc_ref.set(review_state)
            logger.info(f"Saved review state for workflow: {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save review state: {e}", exc_info=True)
            return False

    def get_review_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve review state for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Review state dictionary or None if not found
        """
        if not self.is_available():
            logger.warning("Firestore not available. Cannot retrieve review state.")
            return None

        try:
            doc_ref = self.db.collection(self.COLLECTION_NAME).document(workflow_id)
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            else:
                logger.info(f"No review state found for workflow: {workflow_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to retrieve review state: {e}", exc_info=True)
            return None

    def update_review_status(
        self,
        workflow_id: str,
        status: ReviewStatus,
        reviewed_by: Optional[str] = None,
        review_notes: Optional[str] = None
    ) -> bool:
        """
        Update review status for a workflow.

        Args:
            workflow_id: Workflow identifier
            status: New review status
            reviewed_by: Email/ID of reviewer (optional)
            review_notes: Review feedback/notes (optional)

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.is_available():
            logger.warning("Firestore not available. Cannot update review status.")
            return False

        try:
            doc_ref = self.db.collection(self.COLLECTION_NAME).document(workflow_id)

            update_data = {
                "review_status": status.value,
                "reviewed_at": datetime.utcnow().isoformat()
            }

            if reviewed_by:
                update_data["reviewed_by"] = reviewed_by

            if review_notes:
                update_data["review_notes"] = review_notes

            doc_ref.update(update_data)
            logger.info(f"Updated review status to {status.value} for workflow: {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update review status: {e}", exc_info=True)
            return False

    def update_review_data(
        self,
        workflow_id: str,
        detailed_calendar: Optional[Dict[str, Any]] = None,
        simplified_calendar: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update the calendar data for a workflow review.

        Allows the external app to push back edited calendar data.

        Args:
            workflow_id: Workflow identifier
            detailed_calendar: Updated detailed calendar JSON (optional)
            simplified_calendar: Updated simplified calendar JSON (optional)

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.is_available():
            logger.warning("Firestore not available. Cannot update review data.")
            return False

        try:
            doc_ref = self.db.collection(self.COLLECTION_NAME).document(workflow_id)

            # Check if document exists first
            doc = doc_ref.get()
            if not doc.exists:
                logger.warning(f"Cannot update data: Review state not found for {workflow_id}")
                return False

            update_data = {
                "updated_at": datetime.utcnow().isoformat()
            }

            if detailed_calendar:
                update_data["detailed_calendar"] = detailed_calendar

            if simplified_calendar:
                update_data["simplified_calendar"] = simplified_calendar

            # Add metadata about the update
            current_metadata = doc.to_dict().get("metadata", {})
            current_metadata["has_external_edits"] = True
            current_metadata["last_external_edit_at"] = datetime.utcnow().isoformat()
            update_data["metadata"] = current_metadata

            doc_ref.update(update_data)
            logger.info(f"Updated review data for workflow: {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update review data: {e}", exc_info=True)
            return False

    def list_pending_reviews(
        self,
        client_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List workflows pending review.

        Args:
            client_name: Filter by client (optional)
            limit: Maximum number of results

        Returns:
            List of review state dictionaries
        """
        if not self.is_available():
            logger.warning("Firestore not available. Cannot list pending reviews.")
            return []

        try:
            query = self.db.collection(self.COLLECTION_NAME).where(
                "review_status", "==", ReviewStatus.PENDING.value
            )

            if client_name:
                query = query.where("client_name", "==", client_name)

            query = query.order_by("submitted_at", direction=firestore.Query.DESCENDING).limit(limit)

            docs = query.stream()
            return [doc.to_dict() for doc in docs]

        except Exception as e:
            logger.error(f"Failed to list pending reviews: {e}", exc_info=True)
            return []

    def list_all_reviews(
        self,
        status: Optional[ReviewStatus] = None,
        client_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all reviews with optional filters.

        Args:
            status: Filter by review status (optional)
            client_name: Filter by client (optional)
            limit: Maximum number of results

        Returns:
            List of review state dictionaries
        """
        if not self.is_available():
            logger.warning("Firestore not available. Cannot list reviews.")
            return []

        try:
            query = self.db.collection(self.COLLECTION_NAME)

            if status:
                query = query.where("review_status", "==", status.value)

            if client_name:
                query = query.where("client_name", "==", client_name)

            query = query.order_by("submitted_at", direction=firestore.Query.DESCENDING).limit(limit)

            docs = query.stream()
            return [doc.to_dict() for doc in docs]

        except Exception as e:
            logger.error(f"Failed to list reviews: {e}", exc_info=True)
            return []

    def delete_review_state(self, workflow_id: str) -> bool:
        """
        Delete review state for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_available():
            logger.warning("Firestore not available. Cannot delete review state.")
            return False

        try:
            doc_ref = self.db.collection(self.COLLECTION_NAME).document(workflow_id)
            doc_ref.delete()
            logger.info(f"Deleted review state for workflow: {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete review state: {e}", exc_info=True)
            return False

    def cleanup_old_reviews(self, days_old: int = 90) -> int:
        """
        Delete review states older than specified days.

        Args:
            days_old: Age threshold in days

        Returns:
            Number of review states deleted
        """
        if not self.is_available():
            logger.warning("Firestore not available. Cannot cleanup reviews.")
            return 0

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()

            query = self.db.collection(self.COLLECTION_NAME).where(
                "submitted_at", "<", cutoff_iso
            )

            docs = query.stream()
            deleted_count = 0

            for doc in docs:
                doc.reference.delete()
                deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old review states")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old reviews: {e}", exc_info=True)
            return 0


# Singleton instance
_review_manager: Optional[ReviewStateManager] = None


def get_review_manager(project_id: Optional[str] = None) -> ReviewStateManager:
    """Get or create singleton review state manager."""
    global _review_manager
    if _review_manager is None:
        _review_manager = ReviewStateManager(project_id)
    return _review_manager
