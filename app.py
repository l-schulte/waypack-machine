from flask import Flask, Response, redirect, send_from_directory
import logging
from datetime import datetime, timezone
from endpoints.npm_compatible_apis import NpmCompatibleAPI
import json
import os
import requests
import hashlib


app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

npm_registry = os.getenv("NPM_REGISTRY_URL") or "http://registry.npmjs.org/"
yarn_registry = os.getenv("YARN_REGISTRY_URL") or "http://registry.yarnpkg.com/"

npm_api = NpmCompatibleAPI(npm_registry)
yarn_api = NpmCompatibleAPI(yarn_registry)

local_packages_config = (
    json.load(open("local_packages.config.json", "r"))
    if os.path.exists("local_packages.config.json")
    else None
)


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


@app.route("/custom_cache/<path:baseurl>/resource/<path:subpath>")
def handle_custom_cache(baseurl, subpath):
    """
    Handle custom cache requests.
    Route provides the original URL. Function checks if the requested resource
    (subpath) is available as a local file and serves it. If not found, it gets
    the resource from the original URL (baseurl/subpath), stores it, and serves it.
    Example: https://www.electronjs.org/headers/v13.1.8/node-v13.1.8-headers.tar.gz
    Baseurl: https://www.electronjs.org/headers
    Subpath: v13.1.8/node-v13.1.8-headers.tar.gz
    Example request:
    GET /custom_cache/https://www.electronjs.org/headers/resource/v13.1.8/node-v13.1.8-headers.tar.gz
    """
    full_url = f"{baseurl}/{subpath}"
    cache_path = f"{hashlib.sha256(baseurl.encode()).hexdigest()}/{subpath}"
    if os.path.exists(f"./local_files/{cache_path}"):
        return serve_local_file(cache_path)

    print(f"Fetching resource from: {full_url}")
    response = requests.get(full_url)
    print(f"Response status code: {response.status_code}")

    if response.status_code == 200:
        os.makedirs(os.path.dirname(f"./local_files/{cache_path}"), exist_ok=True)
        with open(f"./local_files/{cache_path}", "wb") as f:
            f.write(response.content)
        return Response(
            response.content,
            content_type=response.headers.get("Content-Type"),
        )
    else:
        return f"Resource not found at {full_url}", response.status_code


def handle_request_with_api(api: NpmCompatibleAPI, timestamp, subpath: str):
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

    if (
        subpath[0] == "@"
        and len(subpath.split("/")) > 2
        or subpath[0] != "@"
        and len(subpath.split("/")) > 1
    ):
        return redirect(f"{api.registry_url}{subpath}", code=302)

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

    return filtered_data, 200, {"Content-Type": "application/json"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
