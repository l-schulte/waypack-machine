from flask import Flask, request, redirect
import logging
import requests
from datetime import datetime, timezone

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

NPM_REGISTRY_URL = "https://registry.npmjs.org/"


@app.route("/npm/<timestamp>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def handle_request(timestamp, subpath: str):
    # Log the request details
    data = request.get_data()
    logger.info(
        f"⏯️ Request received: timestamp={timestamp}, subpath={subpath}, method={request.method}"
    )

    npm_url = f"{NPM_REGISTRY_URL}{subpath}"

    if not subpath.replace("/", "").isalnum():
        logger.info(f"✅ Redirecting to npm registry for metadata files: {npm_url}")
        return redirect(npm_url, code=302)

    target_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)

    response = requests.get(npm_url)
    if response.status_code != 200:
        logger.error(f"❌ Failed to fetch package metadata for {subpath}")
        return f"Error: Unable to fetch package metadata for {subpath}", 404

    package_data = response.json()

    # Replace the JSON in the response from npm with filtered data
    new_package_data = {"versions": {}, "time": {}}
    new_modified_time = None  # Initialize outside the loop

    time = package_data.get("time", {})
    for version, publish_time in time.items():
        publish_time = datetime.fromisoformat(publish_time.replace("Z", "+00:00"))
        if version == "modified" or version == "created":
            continue
        if publish_time <= target_time:
            new_package_data["versions"][version] = package_data["versions"][version]
            new_package_data["time"][version] = publish_time.isoformat()
            if new_modified_time is None or publish_time > new_modified_time:
                new_modified_time = publish_time

    new_package_data["time"]["modified"] = (
        new_modified_time.isoformat() if new_modified_time else None
    )

    # Return the modified JSON response
    logger.info(
        f"✅ Returning filtered package data with {len(new_package_data['versions'])} out of {len(package_data['versions'])} versions"
    )
    return new_package_data, 200, {"Content-Type": "application/json"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
