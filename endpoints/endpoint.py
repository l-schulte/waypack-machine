from datetime import datetime, timezone
import logging
from packaging.version import parse, InvalidVersion, Version
import requests


logger = logging.getLogger(__name__)


def is_valid_version(version_string: str) -> bool:
    """Check if the version string is a valid version."""
    try:
        parse(version_string)
        return True
    except InvalidVersion:
        return False


def parse_version(version_string: str) -> Version:
    """Parse version string using packaging.version.parse."""
    try:
        return parse(version_string)
    except InvalidVersion as e:
        logger.error(f"Invalid version string: {version_string}")
        return Version("0.0.0")


def get_version_dict(package_data: dict[str, dict], version: str) -> dict[str, dict | str]:
    """Returns the version dictionary if possible. Otherwise returns a dummy dict."""
    if version in package_data.get("versions", {}):
        return package_data["versions"][version]
    dummy_name = package_data.get("name", "dummy-package")
    return {
        "version": version,
        "name": dummy_name,
        "_id": f"{dummy_name}@{version}",
        "main": dummy_name,
    }


def fromisoformat(date_string: str) -> datetime:
    """Parse ISO 8601 date string to datetime object."""
    return datetime.fromisoformat(date_string.replace("Z", "+00:00"))


def toisoformat(dt: datetime) -> str:
    """Convert datetime object to ISO 8601 string."""
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z") if dt else ""
