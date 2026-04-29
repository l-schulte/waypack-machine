import logging
import os
from flask import Flask
from registries.npm import NpmCompatibleAPI
from registries.pip import PipAPI
from config import ConfigStore
from cache import FileCache
from routes.package import create_package_blueprint
from routes.proxy import create_proxy_blueprint
from routes.local import create_local_blueprint


def _log_startup(logger: logging.Logger, npm: str, yarn: str, pip: str, config: ConfigStore) -> None:
    logger.info("Registries:  npm=%s  yarn=%s  pip=%s", npm, yarn, pip)

    if not config.is_loaded:
        logger.info("No local packages config found (no *.config.json files).")
        return

    logger.info(
        "Local config: %d source file(s), %d file entries, %d version entries",
        len(config.loaded_paths),
        len(config.files),
        len(config.versions),
    )
    for path in config.loaded_paths:
        logger.info("  %s", os.path.abspath(path))


def create_app() -> Flask:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    logger = logging.getLogger(__name__)

    npm_registry = os.getenv("NPM_REGISTRY_URL") or "http://registry.npmjs.org/"
    yarn_registry = os.getenv("YARN_REGISTRY_URL") or "http://registry.yarnpkg.com/"
    pip_index = os.getenv("PIP_INDEX_URL") or "https://pypi.org/simple/"

    npm_api = NpmCompatibleAPI(npm_registry)
    yarn_api = NpmCompatibleAPI(yarn_registry)
    pip_api = PipAPI(pip_index)

    config = ConfigStore("local_files")
    file_cache = FileCache()

    _log_startup(logger, npm_registry, yarn_registry, pip_index, config)

    flask_app = Flask(__name__)
    flask_app.register_blueprint(create_package_blueprint(npm_api, yarn_api, pip_api, config))
    flask_app.register_blueprint(create_proxy_blueprint(file_cache))
    flask_app.register_blueprint(create_local_blueprint(config))

    return flask_app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
