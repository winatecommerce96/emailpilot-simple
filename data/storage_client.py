"""
Storage Client - Google Cloud Storage Integration

Provides persistent storage for workflow outputs in Cloud Run production.
Handles upload and retrieval of planning, calendar, and brief outputs.
"""

import logging
from google.cloud import storage
from google.cloud.exceptions import NotFound
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

logger = logging.getLogger(__name__)


class StorageClient:
    """
    Client for Google Cloud Storage operations.

    Manages workflow output persistence in production Cloud Run environment
    where local file storage is ephemeral.
    """

    def __init__(self, project_id: str, bucket_name: Optional[str] = None):
        """
        Initialize Storage Client.

        Args:
            project_id: Google Cloud project ID
            bucket_name: GCS bucket name (defaults to {project_id}-emailpilot-outputs)
        """
        self.client = storage.Client(project=project_id)
        self.bucket_name = bucket_name or f"{project_id}-emailpilot-outputs"
        self.bucket = self._get_or_create_bucket()
        logger.info(f"StorageClient initialized with bucket: {self.bucket_name}")

    def _get_or_create_bucket(self) -> storage.Bucket:
        """Get existing bucket or create new one."""
        try:
            bucket = self.client.get_bucket(self.bucket_name)
            logger.info(f"Using existing bucket: {self.bucket_name}")
            return bucket
        except NotFound:
            logger.info(f"Creating new bucket: {self.bucket_name}")
            bucket = self.client.create_bucket(
                self.bucket_name,
                location="us-central1"
            )
            return bucket

    def save_output(
        self,
        filename: str,
        content: str,
        content_type: str = "text/plain"
    ) -> str:
        """
        Save workflow output to GCS.

        Args:
            filename: Name for the blob (e.g., "rogue-creamery_2025-01-01_briefs.txt")
            content: Content to save
            content_type: MIME type (default: text/plain)

        Returns:
            GCS URI (gs://bucket/filename)
        """
        try:
            blob = self.bucket.blob(filename)
            blob.upload_from_string(content, content_type=content_type)
            logger.info(f"Saved output to GCS: gs://{self.bucket_name}/{filename}")
            return f"gs://{self.bucket_name}/{filename}"
        except Exception as e:
            logger.error(f"Failed to save output to GCS: {str(e)}")
            raise

    def get_output(self, filename: str) -> Optional[str]:
        """
        Retrieve output from GCS.

        Args:
            filename: Blob name

        Returns:
            Content as string, or None if not found
        """
        try:
            blob = self.bucket.blob(filename)
            if not blob.exists():
                logger.warning(f"Output not found in GCS: {filename}")
                return None
            content = blob.download_as_text()
            logger.info(f"Retrieved output from GCS: {filename}")
            return content
        except Exception as e:
            logger.error(f"Failed to retrieve output from GCS: {str(e)}")
            return None

    def get_latest_output(
        self,
        output_type: str,
        client_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve latest output of given type.

        Args:
            output_type: Type of output (planning, calendar, briefs)
            client_name: Optional client filter

        Returns:
            Dict with 'filename', 'content', 'modified', or None if not found
        """
        try:
            # Build prefix for filtering
            prefix = f"{client_name}_" if client_name else ""

            # List blobs matching pattern
            blobs = list(self.bucket.list_blobs(prefix=prefix))

            # Filter by output type
            extension = ".txt" if output_type in ["planning", "briefs"] else ".json"
            matching_blobs = [
                b for b in blobs
                if f"_{output_type}{extension}" in b.name
            ]

            if not matching_blobs:
                logger.info(f"No {output_type} outputs found in GCS")
                return None

            # Get most recent
            latest_blob = max(matching_blobs, key=lambda b: b.time_created)

            content = latest_blob.download_as_text()

            return {
                "filename": latest_blob.name,
                "content": content,
                "modified": latest_blob.time_created.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get latest output: {str(e)}")
            return None

    def list_outputs(
        self,
        prefix: Optional[str] = None,
        output_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List available outputs.

        Args:
            prefix: Optional prefix filter (e.g., client name)
            output_type: Optional type filter (planning, calendar, briefs)

        Returns:
            List of output metadata dicts
        """
        try:
            blobs = list(self.bucket.list_blobs(prefix=prefix))

            # Filter by output type if specified
            if output_type:
                extension = ".txt" if output_type in ["planning", "briefs"] else ".json"
                blobs = [b for b in blobs if f"_{output_type}{extension}" in b.name]

            outputs = [
                {
                    "filename": blob.name,
                    "size": blob.size,
                    "modified": blob.time_created.isoformat(),
                    "content_type": blob.content_type
                }
                for blob in blobs
            ]

            logger.info(f"Listed {len(outputs)} outputs from GCS")
            return outputs
        except Exception as e:
            logger.error(f"Failed to list outputs: {str(e)}")
            return []
