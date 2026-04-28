import logging
import os
import requests
from flask import Blueprint, redirect, send_from_directory
from registries import RegistryAPI
from config import ConfigStore

logger = logging.getLogger(__name__)


def create_package_blueprint(
    npm_api: RegistryAPI,
    yarn_api: RegistryAPI,
    pip_api: RegistryAPI,
    config: ConfigStore,
) -> Blueprint:
    bp = Blueprint("package", __name__)

    @bp.route("/npm/<timestamp>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
    def handle_npm_request(timestamp, subpath):
        return _handle(npm_api, timestamp, subpath)

    @bp.route("/yarn/<timestamp>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
    def handle_yarn_request(timestamp, subpath):
        return _handle(yarn_api, timestamp, subpath)

    @bp.route("/pip/<timestamp>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
    def handle_pip_request(timestamp, subpath):
        return _handle(pip_api, timestamp, subpath)

    def _handle(api: RegistryAPI, timestamp, subpath: str):
        logger.debug("Handling request for %s with timestamp %s", subpath, timestamp)

        if subpath in config.files:
            redirect_path = config.files[subpath]
            if redirect_path.startswith("http"):
                return redirect(redirect_path, code=302)
            if os.path.exists(f"./local_files/{redirect_path}"):
                return send_from_directory("local_files", redirect_path)

        if subpath in config.versions:
            return config.versions[subpath], 200, {"Content-Type": "application/json"}

        if api.should_redirect(subpath):
            return redirect(f"{api.base_url}{subpath}", code=302)

        try:
            timestamp = int(timestamp)
        except ValueError:
            return "Invalid timestamp format", 400

        package_response = api.fetch_package_metadata(subpath)
        if package_response.status_code != 200:
            return (
                package_response.content,
                package_response.status_code,
                dict(package_response.headers),
            )

        filtered_data = api.filter_versions_by_timestamp(package_response.json(), timestamp)
        return filtered_data, 200, {"Content-Type": api.content_type}

    return bp
