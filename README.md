# Waypack Machine

A wayback machine for the package managers npm and Yarn. Minimal Flask-based web server that allows you to fetch and redirect to specific versions of npm and Yarn packages based on a given timestamp.

> **⚠️ Disclaimer:** This project is a work in progress and may be untested. Use at your own risk.

## Features

- Accepts requests at `/npm/<timestamp>/<path>` and `/yarn/<timestamp>/<path>`.
- Filters npm and Yarn package versions available before the given timestamp.
- Redirects to the closest valid version or returns modified metadata.

## Requirements

- Python
- Flask
- Requests

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd npm-waypackmachine
   ```
2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the server:
   ```bash
   python app.py
   ```
2. Change the npm/yarn registry URL:
   ```bash
   npm set registry http://localhost:3000/npm/<timestamp>/
   yarn config set registry http://localhost:3000/yarn/<timestamp>/
   ```
3. Get your packages from the past! (Fails if newer versions are requested)
   ```bash
   npm install <package-name>
   ```

## License

MIT
