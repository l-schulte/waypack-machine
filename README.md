# NPM Wayback Machine

A minimal Flask-based web server that allows you to fetch and redirect to specific versions of npm packages based on a given timestamp.

## Features

- Accepts requests at `/npm/<timestamp>/<path>`.
- Filters npm package versions available before the given timestamp.
- Redirects to the closest valid version or returns modified metadata.

## Requirements

- Python 3.10+
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
2. Change the npm registry URL:
   ```bash
   npm set registry http://172.17.0.1:3000/npm/<timestamp>/
   ```
3. Get your packages from the past! (Fails if newer versions are requested)
   ```bash
   npm install <package-name>
   ```

## License

MIT
