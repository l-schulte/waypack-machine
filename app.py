from flask import Flask, request, redirect, send_from_directory
import logging
from datetime import datetime, timezone
from endpoints.npm_compatible_apis import NpmCompatibleAPI
import json
import os

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

npm_api = NpmCompatibleAPI("https://registry.npmjs.org/")
yarn_api = NpmCompatibleAPI("https://registry.yarnpkg.com/")

requests_dict = {}
requests_counter = 0

redirects = json.load(open("redirects.config", "r")) if os.path.exists("redirects.config") else None


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


@app.route("/local/<path:subpath>")
def serve_local_file(subpath):
    """
    Serve local files from the 'local_packages' directory.

    Args:
        subpath (str): Path to the local file to serve.

    Returns:
        Flask response with the local file or 404 if not found.
    """
    try:
        return send_from_directory("local_packages", subpath)
    except FileNotFoundError:
        return f"Local file not found: {subpath}", 404


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
    global requests_counter

    if subpath not in requests_dict:
        requests_dict[subpath] = 0
    requests_dict[subpath] += 1

    requests_counter += 1
    if requests_counter % 100 == 0:
        with open("requests.json", "w") as f:
            json.dump(requests_dict, f)

    # Redirect paths (local or external)
    if redirects and subpath in redirects.get("files", {}):
        redirect_path = redirects["files"][subpath]

        if redirect_path.startswith("http"):
            return redirect(redirect_path, code=302)

        if os.path.exists(f"/local/{redirect_path}"):
            return redirect(f"/local/{redirect_path}", code=302)

    if redirects and subpath in redirects.get("versions", {}):
        return redirects["versions"][subpath], 200, {"Content-Type": "application/json"}

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
