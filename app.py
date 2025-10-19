from flask import Flask, request, redirect
import logging
from datetime import datetime, timezone
from endpoints.npm_compatible_apis import NpmCompatibleAPI

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

npm_api = NpmCompatibleAPI("https://registry.npmjs.org/")
yarn_api = NpmCompatibleAPI("https://registry.yarnpkg.com/")


@app.route("/npm/<timestamp>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def handle_npm_request(timestamp, subpath):
    return handle_request_with_api(npm_api, timestamp, subpath)


@app.route("/yarn/<timestamp>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def handle_yarn_request(timestamp, subpath):
    return handle_request_with_api(yarn_api, timestamp, subpath)

 
def handle_request_with_api(api: NpmCompatibleAPI, timestamp, subpath: str):
    if (subpath[0] == "@" and len(subpath.split("/")) > 2 or subpath[0] != "@" and len(subpath.split("/")) > 1):
        return redirect(f"{api.registry_url}{subpath}", code=302)

    # Convert timestamp to integer
    try:
        timestamp = int(timestamp)
    except ValueError:
        return "Invalid timestamp format", 400

    # Fetch package metadata
    package_name = subpath
    package_response = api.fetch_package_metadata(package_name)
    if package_response.status_code != 200:
        return (
            package_response.content,
            package_response.status_code,
            dict(package_response.headers),
        )

    # Filter versions by timestamp
    filtered_data = api.filter_versions_by_timestamp(package_response.json(), timestamp)

    # Return the modified JSON response
    return filtered_data, 200, {"Content-Type": "application/json"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
