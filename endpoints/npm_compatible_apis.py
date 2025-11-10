import requests
from datetime import datetime, timezone
import logging
from endpoints.endpoint import parse_version, get_version_dict, fromisoformat, toisoformat

logger = logging.getLogger(__name__)


class NpmCompatibleAPI:
    def __init__(self, registry_url):
        self.registry_url = registry_url

    content_type: str = "application/json"

    def should_redirect(self, subpath: str) -> bool:
        return (
            subpath[0] == "@"
            and len(subpath.split("/")) > 2
            or subpath[0] != "@"
            and len(subpath.split("/")) > 1
        )

    def fetch_package_metadata(self, package_name: str) -> requests.Response:
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

            if version not in package_data.get("versions", {}) or not isinstance(publish_time, str):
                # Skip non-version entries like "modified" and "created", or unpublished versions without timestamps.
                continue

            publish_time = fromisoformat(publish_time)

            if publish_time <= target_time:
                versions[version] = get_version_dict(package_data, version)
                time[version] = toisoformat(publish_time)
                if latest_time is None or publish_time > latest_time:
                    latest_time = publish_time

        time["modified"] = toisoformat(latest_time) if latest_time else ""
        time["created"] = package_data.get("time", {"created": ""}).get("created", "")
        latest = max(versions.keys(), key=parse_version, default=None)

        package_data["versions"] = versions
        package_data["time"] = time
        package_data["dist-tags"] = {"latest": latest} if latest else {}

        return package_data
