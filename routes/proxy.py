import requests
from flask import Blueprint, Response, request
from cache import FileCache


def create_proxy_blueprint(file_cache: FileCache) -> Blueprint:
    bp = Blueprint("proxy", __name__)

    @bp.route("/request/<path:original_url>")
    def proxy_request(original_url):
        # Split at "http" and use the last part to avoid processing prefixed URLs
        target_url = "http" + original_url.split("http")[-1]
        target_headers = {"Accept": request.headers.get("Accept", "application/octet-stream")}

        cached = file_cache.get(target_url)
        if cached is not None:
            return Response(cached, status=200, content_type="application/octet-stream")

        response = requests.get(target_url, headers=target_headers)
        if response.status_code == 200:
            file_cache.put(target_url, response.content)

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type", "application/octet-stream"),
        )

    return bp
