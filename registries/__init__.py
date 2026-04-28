from typing import Protocol
import requests


class RegistryAPI(Protocol):
    base_url: str
    content_type: str

    def should_redirect(self, subpath: str) -> bool: ...
    def fetch_package_metadata(self, package_name: str) -> requests.Response: ...
    def filter_versions_by_timestamp(self, package_data: dict, timestamp: int) -> dict: ...
