"""
Google Secret Manager Client

Fetches per-client Klaviyo API keys from Google Cloud Secret Manager.
"""

import logging
import os
from typing import Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class SecretManagerClient:
    """
    Client for fetching secrets from Google Cloud Secret Manager.

    Retrieves per-client Klaviyo API keys stored with pattern:
    klaviyo-api-{client-slug}
    """

    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize Secret Manager client.

        Args:
            project_id: Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")

        if not self.project_id:
            raise ValueError(
                "Google Cloud project ID not found. Set GOOGLE_CLOUD_PROJECT environment variable."
            )

        self.client = secretmanager.SecretManagerServiceClient()
        logger.info(f"SecretManagerClient initialized for project: {self.project_id}")

    def _get_secret_name(self, client_name: str) -> str:
        """
        Convert client slug to Secret Manager secret name.

        Handles variations in client naming:
        - rogue-creamery → klaviyo-api-rogue-creamery
        - vlasic → klaviyo-api-vlasic-labs
        - milagro → klaviyo-api-milagro-mushrooms
        - chris-bean → klaviyo-api-christopher-bean-coffee
        - colorado-hemp-honey → klaviyo-api-colorado-hemp-honey
        - wheelchair-getaways → klaviyo-api-wheelchair-getaways
        - faso → klaviyo-api-faso

        Args:
            client_name: Client slug (e.g., "rogue-creamery")

        Returns:
            Secret name (e.g., "klaviyo-api-rogue-creamery")
        """
        # Handle special cases where secret name differs from client slug
        secret_name_mapping = {
            "vlasic": "klaviyo-api-vlasic-labs",
            "milagro": "klaviyo-api-milagro-mushrooms",
            "chris-bean": "klaviyo-api-christopher-bean-coffee"
        }

        # Check if client has special mapping
        if client_name in secret_name_mapping:
            return secret_name_mapping[client_name]

        # Default pattern: klaviyo-api-{client-slug}
        return f"klaviyo-api-{client_name}"

    def get_api_key(self, client_name: str, version: str = "latest") -> str:
        """
        Fetch Klaviyo API key for a client from Secret Manager.

        Args:
            client_name: Client slug (e.g., "rogue-creamery")
            version: Secret version (default: "latest")

        Returns:
            Klaviyo API key

        Raises:
            Exception: If secret cannot be accessed
        """
        secret_name = self._get_secret_name(client_name)

        # Build the secret version path
        secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"

        logger.info(f"Fetching API key for {client_name} from Secret Manager: {secret_name}")

        try:
            # Access the secret version
            response = self.client.access_secret_version(request={"name": secret_path})

            # Decode the secret payload
            api_key = response.payload.data.decode("UTF-8")

            logger.info(f"Successfully fetched API key for {client_name}")

            return api_key

        except Exception as e:
            logger.error(
                f"Failed to fetch API key for {client_name} from secret {secret_name}: {str(e)}"
            )
            raise

    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        """
        Generic method to fetch any secret from Secret Manager.

        Args:
            secret_name: Full secret name (not a client slug)
            version: Secret version (default: "latest")

        Returns:
            Secret value

        Raises:
            Exception: If secret cannot be accessed
        """
        secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"

        logger.info(f"Fetching secret: {secret_name}")

        try:
            response = self.client.access_secret_version(request={"name": secret_path})
            secret_value = response.payload.data.decode("UTF-8")

            logger.info(f"Successfully fetched secret: {secret_name}")

            return secret_value

        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_name}: {str(e)}")
            raise
