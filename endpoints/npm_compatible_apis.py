import requests
from datetime import datetime, timezone
import logging
from packaging.version import parse as parse_version

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
            requests.Response: The response object from the registry request.
        """
        response = requests.get(f"{self.registry_url}{package_name}")
        if response.status_code != 200:
            logger.error(f"Failed to fetch package metadata for {package_name}")
        return response

    def filter_versions_by_timestamp(self, package_data: dict, timestamp: int) -> dict:
        """
        Filter package versions by a given Unix timestamp and update package metadata.

        Args:
            package_data (dict): The package metadata to filter.
            timestamp (int): The Unix timestamp to filter against.

        Returns:
            dict: Modified package data with filtered versions, updated time metadata,
                  and dist-tags containing the latest available version.
        """
        target_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        versions: dict[str, dict] = {}
        time: dict[str, str] = {}
        latest_time = None

        for version, publish_time in package_data.get("time", {}).items():
            publish_time = self.fromisoformat(publish_time)

            if version == "modified" or version == "created":
                continue
            if publish_time <= target_time and version in package_data.get("versions", {}):
                versions[version] = package_data["versions"][version]
                time[version] = self.toisoformat(publish_time)
                if latest_time is None or publish_time > latest_time:
                    latest_time = publish_time

        time["modified"] = self.toisoformat(latest_time) if latest_time else ""
        time["created"] = time.get("created", "")
        latest = max(versions.keys(), key=parse_version, default=None)

        package_data["versions"] = versions
        package_data["time"] = time
        package_data["dist-tags"] = {"latest": latest} if latest else {}

        return package_data
