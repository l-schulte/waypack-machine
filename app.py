from flask import Flask, Response, redirect, send_from_directory
import logging
from datetime import datetime, timezone
from endpoints.npm_compatible_apis import NpmCompatibleAPI
from endpoints.pip_apis import PipAPI
import json
import os
import requests
import hashlib
import csv
from threading import Lock

inventory_lock = Lock()

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

npm_registry = os.getenv("NPM_REGISTRY_URL") or "http://registry.npmjs.org/"
yarn_registry = os.getenv("YARN_REGISTRY_URL") or "http://registry.yarnpkg.com/"
pip_index = os.getenv("PIP_INDEX_URL") or "https://pypi.org/simple/"

npm_api = NpmCompatibleAPI(npm_registry)
yarn_api = NpmCompatibleAPI(yarn_registry)
pip_api = PipAPI(pip_index)

local_packages_config = (
    json.load(open("local_packages.config.json", "r"))
    if os.path.exists("local_packages.config.json")
    else None
)

# Log startup info
logger.info("Configured registries:")
logger.info("  NPM_REGISTRY_URL \t%s", npm_registry)
logger.info("  YARN_REGISTRY_URL \t%s", yarn_registry)
logger.info("  PIP_INDEX_URL \t%s", pip_index)

if local_packages_config:
    files = local_packages_config.get("files", {})
    versions = local_packages_config.get("versions", {})
    logger.info(
        "Local packages configuration loaded from %s", os.path.abspath("local_packages.config.json")
    )
    logger.info("  local files entries: %d", len(files))
    if files:
        logger.info("    sample files: %s", ", ".join(list(files.keys())[:10]))
    logger.info("  local versions entries: %d", len(versions))
    if versions:
        logger.info("    sample versions: %s", ", ".join(list(versions.keys())[:10]))
    logger.info("Local files directory: %s", os.path.abspath("local_files"))
else:
    logger.info("No local packages configuration found (local_packages.config.json missing).")


@app.route("/npm/<timestamp>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def handle_npm_request(timestamp, subpath):
    """
    Handle NPM package requests with timestamp filtering.

    Args:
        timestamp (str): Unix timestamp to filter package versions.
        subpath (str): Package path (e.g., 'lodash' or '@scope/package').

    Returns:
        Flask response with filtered package metadata or redirect.
    """
    return handle_request_with_api(npm_api, timestamp, subpath)


@app.route("/yarn/<timestamp>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def handle_yarn_request(timestamp, subpath):
    """
    Handle Yarn package requests with timestamp filtering.

    Args:
        timestamp (str): Unix timestamp to filter package versions.
        subpath (str): Package path (e.g., 'lodash' or '@scope/package').

    Returns:
        Flask response with filtered package metadata or redirect.
    """
    return handle_request_with_api(yarn_api, timestamp, subpath)


@app.route("/pip/<timestamp>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def handle_pip_request(timestamp, subpath):
    """
    Handle pip package requests with timestamp filtering.

    Args:
        timestamp (str): Unix timestamp to filter package versions.
        subpath (str): Package path (e.g., 'lodash' or '@scope/package').

    Returns:
        Flask response with filtered package metadata or redirect.
    """
    return handle_request_with_api(pip_api, timestamp, subpath)


@app.route("/local_config")
def get_local_packages_config():
    """
    Endpoint to retrieve the local packages configuration.

    Returns:
        Flask response with the local packages configuration JSON.
    """
    if local_packages_config:
        return local_packages_config, 200, {"Content-Type": "application/json"}
    else:
        return "Local packages configuration not found", 404


@app.route("/request/<path:original_url>")
def proxy_request(original_url):
    cache_dir = "local_cache"
    os.makedirs(cache_dir, exist_ok=True)
    url_hash = hashlib.sha256(original_url.encode()).hexdigest()
    cache_file_path = os.path.join(cache_dir, url_hash)
    inventory_file_path = os.path.join(cache_dir, "cache_inventory.csv")

    if os.path.exists(cache_file_path):
        with open(cache_file_path, "rb") as cache_file:
            cached_content = cache_file.read()
        return Response(cached_content, status=200, content_type="application/octet-stream")

    response = requests.get(original_url)
    if response.status_code == 200:
        with open(cache_file_path, "wb") as cache_file:
            cache_file.write(response.content)

        with inventory_lock:  # Ensure thread-safe file access
            with open(inventory_file_path, "a", newline="") as inventory_file:
                writer = csv.writer(inventory_file)
                writer.writerow([url_hash, original_url])

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type", "application/octet-stream"),
    )


@app.route("/local/<path:subpath>")
def serve_local_file(subpath):
    """
    Serve local files from the 'local_files' directory.

    Args:
        subpath (str): Path to the local file to serve.

    Returns:
        Flask response with the local file or 404 if not found.
    """
    try:
        return send_from_directory("local_files", subpath)
    except FileNotFoundError:
        return f"Local file not found: {subpath}", 404


def handle_request_with_api(api: NpmCompatibleAPI | PipAPI, timestamp, subpath: str):
    """
    Handle package requests using the specified API with timestamp-based filtering.

    This function:
    1. Redirects according to the redirects.json file (to local files or external URLs)
    2. Redirects paths with specific versions directly to the registry
    3. Fetches and filters package metadata for simple package names
    4. Returns filtered package data with versions available before the timestamp

    Args:
        api (NpmCompatibleAPI): The package registry API to use.
        timestamp (str): Unix timestamp for version filtering.
        subpath (str): Package path or name.

    Returns:
        Flask response: Either a redirect or filtered package metadata JSON.
    """

    # Redirect paths (local or external)
    if local_packages_config and subpath in local_packages_config.get("files", {}):
        redirect_path = local_packages_config["files"][subpath]

        if redirect_path.startswith("http"):
            return redirect(redirect_path, code=302)

        if os.path.exists(f"./local_files/{redirect_path}"):
            return serve_local_file(redirect_path)

    if local_packages_config and subpath in local_packages_config.get("versions", {}):
        return local_packages_config["versions"][subpath], 200, {"Content-Type": "application/json"}

    if api.should_redirect(subpath):
        return redirect(f"{api.base_url}{subpath}", code=302)

    try:
        timestamp = int(timestamp)
    except ValueError:
        return "Invalid timestamp format", 400

    package_name = subpath
    package_response = api.fetch_package_metadata(package_name)
    if package_response.status_code != 200:
        return (
            package_response.content,
            package_response.status_code,
            dict(package_response.headers),
        )

    filtered_data = api.filter_versions_by_timestamp(package_response.json(), timestamp)

    return filtered_data, 200, {"Content-Type": api.content_type}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
