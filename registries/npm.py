import requests
from datetime import datetime, timezone
import logging
import semver
from registries.utils import parse_version, get_version_dict, fromisoformat, toisoformat

logger = logging.getLogger(__name__)


class NpmCompatibleAPI:
    def __init__(self, base_url):
        self.base_url = base_url

    content_type: str = "application/json"

    def should_redirect(self, subpath: str) -> bool:
        return (
            subpath[0] == "@"
            and len(subpath.split("/")) > 2
            or subpath[0] != "@"
            and len(subpath.split("/")) > 1
        )

    def fetch_package_metadata(self, package_name: str) -> requests.Response:
        response = requests.get(f"{self.base_url}{package_name}")
        if response.status_code != 200:
            logger.error(f"Failed to fetch package metadata for {package_name}")
        return response

    def build_dist_tags(
        self, original_dist_tags: dict[str, str], parsed_versions: list[semver.VersionInfo]
    ) -> dict[str, str]:
        new_dist_tags = {}

        common_prerelease_keywords = ["beta", "alpha", "rc", "esm"]

        def get_versions_by_keyword(keyword: str) -> list[semver.VersionInfo]:
            return [v for v in parsed_versions if v.prerelease and keyword in v.prerelease]

        prerelease_versions = [v for v in parsed_versions if v.prerelease != None]
        release_versions = [v for v in parsed_versions if v.prerelease == None]

        next: semver.VersionInfo | None = max(prerelease_versions, default=None)
        if next:
            new_dist_tags["next"] = next.__str__()
        latest: semver.VersionInfo | None = max(release_versions, default=next)
        if latest:
            new_dist_tags["latest"] = latest.__str__()

        for keyword in common_prerelease_keywords:
            versions_by_keyword = get_versions_by_keyword(keyword)
            if versions_by_keyword:
                new_dist_tags[keyword] = max(versions_by_keyword).__str__()

        for tag, version in original_dist_tags.items():
            if tag in ["latest", "next"] or tag in common_prerelease_keywords:
                continue

            tag_version = parse_version(version)
            if tag_version not in parsed_versions:
                tag_version = get_versions_by_keyword(tag)
                if tag_version:
                    tag_version = max(tag_version)
                else:
                    tag_version = latest if latest else next
            new_dist_tags[tag] = tag_version.__str__()

        return new_dist_tags

    def filter_versions_by_timestamp(self, package_data: dict, timestamp: int) -> dict:
        target_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        versions: dict[str, dict] = {}
        time: dict[str, str] = {}
        latest_time = None

        for version, publish_time in package_data.get("time", {}).items():
            if version not in package_data.get("versions", {}) or not isinstance(publish_time, str):
                continue

            publish_time = fromisoformat(publish_time)

            if publish_time <= target_time:
                versions[version] = get_version_dict(package_data, version)
                time[version] = toisoformat(publish_time)
                if latest_time is None or publish_time > latest_time:
                    latest_time = publish_time

        time["modified"] = toisoformat(latest_time) if latest_time else ""
        time["created"] = package_data.get("time", {"created": ""}).get("created", "")
        parsed_versions = [parse_version(v) for v in versions.keys()]

        logger.debug(
            "Filtered versions for package %s: %s",
            package_data.get("name", "unknown"),
            list(versions.keys()),
        )

        package_data["versions"] = versions
        package_data["time"] = time
        package_data["dist-tags"] = self.build_dist_tags(
            package_data.get("dist-tags", {}), parsed_versions
        )

        return package_data
