# Waypack Machine

A wayback machine for npm and Yarn package managers. This Flask-based web server filters package versions by timestamp, allowing you to fetch packages as they existed at any point in time.

> **⚠️ Disclaimer:** This project is a work in progress and may be untested. Use at your own risk.

## Features

- **Timestamp filtering**: Get package versions that existed before a specific Unix timestamp
- **NPM & Yarn support**: Can be set as a registry for both NPM and Yarn
- **Fallback for unavailable packages**: Optional fallback to local files

## Requirements

- Python 3.10+
- Flask
- Requests
- packaging (for version parsing)

## Installation

1. Build the Docker image:

   ```bash
   docker build -t waypack-machine .
   ```

2. Run the container:
   ```bash
   docker run -p 3000:3000 waypack-machine
   ```

## Usage

1. Start the server:

   ```bash
   python app.py
   ```

2. Configure your package manager with a Unix timestamp:

   ```bash
   # Example: October 17, 2015 timestamp
   npm set registry http://localhost:3000/npm/1445062501/
   yarn config set registry http://localhost:3000/yarn/1445062501/
   ```

3. Install packages as they existed at that time:
   ```bash
   npm install lodash  # Gets lodash version available on Oct 17, 2015
   ```

## Endpoints

- `/npm/<timestamp>/<package-path>` - NPM packages with timestamp filtering
- `/yarn/<timestamp>/<package-path>` - Yarn packages with timestamp filtering
- `/local/<path>` - Serve local files from `local_files/` directory

## Fallback for Unavailable Packages (Optional)

Override package metadata requests:

1. Configure `local_packages.config` to replace metadata requests:
   ```json
   {
     "versions": {
       "package-name": {
         "_id": "package-name",
         "name": "package-name",
         "versions": {
           "0.5.0": {
             "version": "0.5.0",
             "dist": {
               // tarball URL pointing to your server, date set to 2000-01-01
               "tarball": "http://localhost:3000/npm/946684800/package-name-0.5.0.tgz",
               // shasum waypack/packages/package-name-0.5.0.tgz
               "shasum": "YOUR_HEX_ENCODED_SHASUM",
               // shasum -b -a 512 waypack/packages/package-name-0.5.0.tgz | awk '{ print $1 }' | xxd -r -p | base64
               "integrity": "YOUR_BASE64_ENCODED_INTEGRITY"
             }
           }
         },
         "time": {
           "modified": "1999-12-31T23:59:59.000Z",
           "0.5.0": "1999-12-31T23:59:59.000Z",
           "created": "1999-12-31T23:59:59.000Z"
         }
       }
     }
   }
   ```

Override package tarball requests with local files:

1. Put files in `local_packages/` directory.
2. Configure `redirects.config`:
   ```json
   {
     "files": {
       "package-name/-/package-name-0.5.0.tgz": "package-name-0.5.0.tgz"
     }
   }
   ```

Local files have priority over remote registry requests and bypass timestamp filtering.

## License

MIT
