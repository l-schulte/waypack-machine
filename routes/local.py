from flask import Blueprint, send_from_directory
from config import ConfigStore


def create_local_blueprint(config: ConfigStore) -> Blueprint:
    bp = Blueprint("local", __name__)

    @bp.route("/local_config")
    def get_local_packages_config():
        if config.is_loaded:
            return {"files": config.files, "versions": config.versions}, 200, {"Content-Type": "application/json"}
        return "Local packages configuration not found", 404

    @bp.route("/local/<path:subpath>")
    def serve_local_file(subpath):
        try:
            return send_from_directory("local_files", subpath)
        except FileNotFoundError:
            return f"Local file not found: {subpath}", 404

    return bp
