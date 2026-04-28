import csv
import hashlib
import os
from threading import Lock


class FileCache:
    def __init__(self, directory: str = "local_cache"):
        self._directory = directory
        self._inventory_path = os.path.join(directory, "cache_inventory.csv")
        self._lock = Lock()
        os.makedirs(directory, exist_ok=True)

    def _cache_path(self, url: str) -> str:
        return os.path.join(self._directory, hashlib.sha256(url.encode()).hexdigest())

    def get(self, url: str) -> bytes | None:
        path = self._cache_path(url)
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    def put(self, url: str, content: bytes) -> None:
        path = self._cache_path(url)
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        with open(path, "wb") as f:
            f.write(content)
        with self._lock:
            with open(self._inventory_path, "a", newline="") as f:
                csv.writer(f).writerow([url_hash, url])
