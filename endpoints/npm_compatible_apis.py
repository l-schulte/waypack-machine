import requests
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class NpmCompatibleAPI:
    def __init__(self, registry_url):
        self.registry_url = registry_url

    def fetch_package_metadata(self, package_name):
        """
        Fetch package metadata from the registry.

        Args:
            package_name (str): The name of the package.

        Returns:
            dict: The package metadata, or None if the request fails.
        """
        response = requests.get(f"{self.registry_url}{package_name}")
        if response.status_code != 200:
            logger.error(f"Failed to fetch package metadata for {package_name}")
            return None
        return response.json()

    def filter_versions_by_timestamp(self, package_data, timestamp):
        """
        Filter package versions by a given Unix timestamp.

        Args:
            package_data (dict): The package metadata.
            timestamp (int): The Unix timestamp.

        Returns:
            dict: Filtered package data with versions and time.
        """
        target_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        new_package_data = {"versions": {}, "time": {}}
        new_modified_time = None

        time = package_data.get("time", {})
        for version, publish_time in time.items():
            publish_time = datetime.fromisoformat(publish_time.replace("Z", "+00:00"))
            if version == "modified":
                continue
            if publish_time <= target_time:
                new_package_data["versions"][version] = package_data["versions"][
                    version
                ]
                new_package_data["time"][version] = publish_time.isoformat()
                if new_modified_time is None or publish_time > new_modified_time:
                    new_modified_time = publish_time
        new_package_data["time"]["modified"] = (
            new_modified_time.isoformat() if new_modified_time else None
        )

        return new_package_data
