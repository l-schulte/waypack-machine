import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigStore:
    def __init__(self, directory: str = "."):
        self.files: dict = {}
        self.versions: dict = {}
        self.loaded_paths: list[str] = []

        for path in sorted(Path(directory).rglob("*.config.json")):
            with open(path) as f:
                data = json.load(f)
            self.files.update(data.get("files", {}))
            self.versions.update(data.get("versions", {}))
            self.loaded_paths.append(str(path))

    @property
    def is_loaded(self) -> bool:
        return bool(self.loaded_paths)
