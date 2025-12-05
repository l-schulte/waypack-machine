import requests
from datetime import datetime, timezone
import logging
import json
import re

logger = logging.getLogger(__name__)


class PipAPI:
    def __init__(self, base_url):
        self.base_url = base_url

    content_type: str = "application/vnd.pypi.simple.v1+json"

    def should_redirect(self, subpath: str) -> bool:
        return False

    def fetch_package_metadata(self, package_name: str) -> requests.Response:
        """
        Fetch package metadata from the registry.

        Args:
            package_name (str): The name of the package.

        Returns:
            requests.Response: The response object from the registry request.
        """
        headers = {"Accept": self.content_type}
        url = f"{self.base_url}{package_name}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch package metadata for {url}")
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

        json.dump(package_data, fp=open("tmp/package_data_before_filter.json", "w"), indent=2)

        versions: list[str] = []
        files: list[dict] = []

        for file in package_data.get("files", []):
            upload_time_str = file.get("upload-time")
            upload_time = datetime.fromisoformat(upload_time_str.replace("Z", "+00:00"))

            if upload_time <= target_time:
                filename = file.get("filename")
                version_match = re.search(r"^(?:[^-]+-)?([0-9]+(?:\.[0-9]+)*)", filename)
                if version_match:
                    version = version_match.group(1)
                    if version not in versions:
                        versions.append(version)
                    files.append(file)

        return package_data | {
            "versions": versions,
            "files": files,
        }
