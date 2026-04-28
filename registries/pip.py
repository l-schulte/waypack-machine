import requests
from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)


class PipAPI:
    def __init__(self, base_url):
        self.base_url = base_url

    content_type: str = "application/vnd.pypi.simple.v1+json"

    def should_redirect(self, subpath: str) -> bool:
        return False

    def fetch_package_metadata(self, package_name: str) -> requests.Response:
        headers = {"Accept": self.content_type}
        url = f"{self.base_url}{package_name}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch package metadata for {url}")
        return response

    def filter_versions_by_timestamp(self, package_data: dict, timestamp: int) -> dict:
        target_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

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
