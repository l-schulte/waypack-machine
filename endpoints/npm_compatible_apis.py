import requests
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class NpmCompatibleAPI:
    def __init__(self, registry_url):
        self.registry_url = registry_url

    def fromisoformat(self, date_string):
        """Parse ISO 8601 date string to datetime object."""
        return datetime.fromisoformat(date_string.replace("Z", "+00:00"))

    def toisoformat(self, dt: datetime) -> str:
        """Convert datetime object to ISO 8601 string."""
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z") if dt else ""

    def fetch_package_metadata(self, package_name) -> requests.Response:
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
        return response

    def filter_versions_by_timestamp(self, package_data: dict, timestamp: int) -> dict:
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
            publish_time = self.fromisoformat(publish_time)
            if version == "modified" or version == "created":
                continue
            if publish_time <= target_time and version in package_data.get("versions", {}):
                new_package_data["versions"][version] = package_data["versions"][version]
                new_package_data["time"][version] = self.toisoformat(publish_time)
                if new_modified_time is None or publish_time > new_modified_time:
                    new_modified_time = publish_time
        new_package_data["time"]["modified"] = (
            self.toisoformat(new_modified_time) if new_modified_time else None
        )
        new_package_data["time"]["created"] = time.get("created", None)

        package_data["versions"] = new_package_data["versions"]
        package_data["time"] = new_package_data["time"]

        return package_data
