#!/usr/bin/env python3
"""
Process all Git tags from the consensys-vertical-apps/metamask-institutional monorepo,
repackage each workspace package as an npm-ready tarball, and output
local_packages_output.json for the WayPack Machine local registry.

Usage:
    python raw_packages/process_mmi_tags.py /path/to/metamask-institutional-clone
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

WAYPACK_ROOT = Path(__file__).parent.parent
OUTPUT_JSON = WAYPACK_ROOT / "local_packages_output.json"
REGISTRY_URL_BASE = "http://localhost:3000/local"

# Packages whose directory name cannot be derived by simple kebab→camelCase conversion.
CAMEL_OVERRIDES: dict[str, str] = {
    "simplecache": "simpleCache",
    "websocket-client": "websocketClient",
}


def kebab_to_camel(name: str) -> str:
    if name in CAMEL_OVERRIDES:
        return CAMEL_OVERRIDES[name]
    parts = name.split("-")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def parse_tag(tag: str) -> tuple[str, str] | None:
    """
    Return (kebab_package_name, version) for a valid release tag, else None.

    Supported formats:
      New: custody-controller-v0.2.22
      Old: @metamask-institutional/custody-controller@0.1.4
    """
    # Old format: @metamask-institutional/<name>@<version>
    m = re.match(r"^@metamask-institutional/(.+)@(\d+\.\d+\.\d+.*)$", tag)
    if m:
        return m.group(1), m.group(2)

    # New format: <name>-v<version>
    m = re.match(r"^(.+)-v(\d+\.\d+\.\d+.*)$", tag)
    if m:
        return m.group(1), m.group(2)

    return None


def get_commit_date(repo_path: Path, ref: str) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI", ref],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"Could not read date for '{ref}': {result.stderr.strip()}")
    date = result.stdout.strip()
    date = re.sub(r"\+00:00$", "Z", date)
    return date


def get_commit_packages(repo_path: Path) -> list[tuple[str, str, Path]]:
    """
    Return (npm_package_name, version, package_dir) for every workspace package at the
    currently checked-out commit that has a name and version in its package.json.
    """
    packages_root = repo_path / "packages"
    if not packages_root.exists():
        return []
    results = []
    for pkg_dir in sorted(packages_root.iterdir()):
        pkg_json = pkg_dir / "package.json"
        if not pkg_json.exists():
            continue
        with open(pkg_json) as f:
            data = json.load(f)
        name = data.get("name", "")
        version = data.get("version", "")
        if name and version:
            results.append((name, version, pkg_dir))
    return results


def get_all_tags(repo_path: Path) -> list[str]:
    result = subprocess.run(
        ["git", "tag"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git tag failed: {result.stderr.strip()}")
    return [t.strip() for t in result.stdout.splitlines() if t.strip()]


def get_tag_date(repo_path: Path, tag: str) -> str:
    """
    Return the ISO-8601 creation date of a tag (tagger date for annotated tags,
    commit date for lightweight tags), always ending in 'Z'.
    """
    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(creatordate:iso-strict)", f"refs/tags/{tag}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"Could not read date for tag '{tag}': {result.stderr.strip()}")
    date = result.stdout.strip()
    # Normalise timezone suffix → Z
    date = re.sub(r"\+00:00$", "Z", date)
    return date


def checkout_tag(repo_path: Path, tag: str) -> None:
    result = subprocess.run(
        ["git", "checkout", "--quiet", tag],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git checkout '{tag}' failed: {result.stderr.strip()}")


def run_npm_pack(package_dir: Path) -> Path:
    """
    Run `npm pack --ignore-scripts` in package_dir and return the path to the
    produced tarball (inside package_dir).
    """
    result = subprocess.run(
        ["npm", "pack", "--ignore-scripts"],
        cwd=package_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"npm pack failed in {package_dir}:\n"
            f"  stdout: {result.stdout.strip()}\n"
            f"  stderr: {result.stderr.strip()}"
        )
    # npm pack prints the tarball filename on the last line of stdout
    tarball_name = result.stdout.strip().splitlines()[-1].strip()
    tarball_path = package_dir / tarball_name
    if not tarball_path.exists():
        raise RuntimeError(
            f"npm pack claimed to produce '{tarball_name}' but it was not found in {package_dir}"
        )
    return tarball_path


def expected_tarball_name(npm_package_name: str, version: str) -> str:
    """
    Compute the canonical tarball filename for a scoped package.
    @metamask-institutional/custody-controller 0.2.22
      → metamask-institutional-custody-controller-0.2.22.tgz
    """
    bare = npm_package_name.split("/")[-1]
    return f"{bare}-{version}.tgz"


def record_version(
    output: dict,
    npm_package_name: str,
    version: str,
    tarball_name: str,
    dest_path: str,
    tag_date: str,
) -> None:
    """Insert or update a version entry in the output dict (mutates in place)."""
    pkg = output["versions"].setdefault(
        npm_package_name,
        {
            "_id": npm_package_name,
            "name": npm_package_name,
            "versions": {},
            "time": {"created": tag_date, "modified": tag_date},
        },
    )

    pkg["versions"][version] = {
        "version": version,
        "name": npm_package_name,
        "dist": {"tarball": f"{REGISTRY_URL_BASE}/{dest_path}"},
    }
    pkg["time"][version] = tag_date
    if tag_date > pkg["time"].get("modified", ""):
        pkg["time"]["modified"] = tag_date

    files = output["files"]
    file_tag = f"{npm_package_name}/-/{tarball_name}"
    files[file_tag] = dest_path


def load_output() -> dict:
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON) as f:
            data = json.load(f)
        if "versions" not in data:
            data["versions"] = {}
        if "files" not in data:
            data["files"] = {}
        return data
    return {"versions": {}, "files": {}}


def save_output(output: dict) -> None:
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=4)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repackage metamask-institutional monorepo tags as npm tarballs."
    )
    parser.add_argument(
        "repo_path",
        help="Path to the local clone of consensys-vertical-apps/metamask-institutional",
    )
    parser.add_argument(
        "--commit",
        nargs="?",
        const="HEAD",
        default=None,
        metavar="SHA",
        help="Also pack workspace packages at this commit (default: HEAD when flag is present).",
    )
    parser.add_argument(
        "--commit-only",
        nargs="?",
        const="HEAD",
        default=None,
        metavar="SHA",
        help="Only pack packages at this commit; skip all tag processing.",
    )
    args = parser.parse_args()

    commit_ref = args.commit_only if args.commit_only is not None else args.commit
    skip_tags = args.commit_only is not None

    repo_path = Path(args.repo_path).resolve()
    if not (repo_path / ".git").exists():
        print(f"ERROR: {repo_path} is not a git repository", file=sys.stderr)
        sys.exit(1)

    repo_name = str(repo_path).split("/")[-1]

    local_packages_dir = WAYPACK_ROOT / repo_name
    if not local_packages_dir.exists():
        os.makedirs(local_packages_dir)

    output = load_output()

    processed = skipped = errors = 0

    if not skip_tags:
        tags = get_all_tags(repo_path)
        release_tags = [(tag, parse_tag(tag)) for tag in tags]
        release_tags = [(tag, parsed) for tag, parsed in release_tags if parsed is not None]
        print(f"Found {len(tags)} tags total, {len(release_tags)} are package release tags.")

        for tag, (kebab_name, version) in release_tags:
            npm_package_name = f"@metamask-institutional/{kebab_name}"
            camel_name = kebab_to_camel(kebab_name)
            tarball_name = expected_tarball_name(npm_package_name, version)
            dest_path = local_packages_dir / tarball_name

            if dest_path.exists():
                # Tarball already present — make sure the JSON entry exists.
                if version not in output["versions"].get(npm_package_name, {}).get("versions", {}):
                    try:
                        tag_date = get_tag_date(repo_path, tag)
                        record_version(
                            output,
                            npm_package_name,
                            version,
                            tarball_name,
                            str(dest_path.relative_to(WAYPACK_ROOT)),
                            tag_date,
                        )
                    except Exception as exc:
                        print(
                            f"  WARN  {tag}: tarball exists but could not record JSON entry: {exc}",
                            file=sys.stderr,
                        )
                else:
                    print(f"  SKIP  {tag} — already done")
                skipped += 1
                continue

            print(f"  PACK  {tag} → {tarball_name}")
            try:
                package_dir = repo_path / "packages" / camel_name

                checkout_tag(repo_path, tag)

                if not package_dir.exists():
                    raise RuntimeError(
                        f"Package directory 'packages/{camel_name}' not found after checkout of '{tag}'. "
                        f"You may need to add '{kebab_name}' to CAMEL_OVERRIDES."
                    )

                tag_date = get_tag_date(repo_path, tag)
                tarball_path = run_npm_pack(package_dir)
                shutil.move(str(tarball_path), str(dest_path))
                record_version(
                    output,
                    npm_package_name,
                    version,
                    tarball_name,
                    str(dest_path.relative_to(WAYPACK_ROOT)),
                    tag_date,
                )
                processed += 1

            except Exception as exc:
                print(f"  ERROR {tag}: {exc}", file=sys.stderr)
                errors += 1

    if commit_ref is not None:
        print(f"\nChecking out '{commit_ref}' to process commit packages…")
        checkout_tag(repo_path, commit_ref)

        commit_date = get_commit_date(repo_path, commit_ref)
        commit_packages = get_commit_packages(repo_path)
        print(f"Found {len(commit_packages)} workspace packages at '{commit_ref}'.")

        for npm_package_name, version, package_dir in commit_packages:
            tarball_name = expected_tarball_name(npm_package_name, version)
            dest_path = local_packages_dir / tarball_name

            if version in output["versions"].get(npm_package_name, {}).get("versions", {}):
                print(f"  SKIP  {npm_package_name}@{version} — already recorded")
                skipped += 1
                continue

            if dest_path.exists():
                record_version(
                    output,
                    npm_package_name,
                    version,
                    tarball_name,
                    str(dest_path.relative_to(WAYPACK_ROOT)),
                    commit_date,
                )
                print(f"  SKIP  {npm_package_name}@{version} — tarball exists, recorded")
                skipped += 1
                continue

            print(f"  PACK  {npm_package_name}@{version} → {tarball_name}")
            try:
                tarball_path = run_npm_pack(package_dir)
                shutil.move(str(tarball_path), str(dest_path))
                record_version(
                    output,
                    npm_package_name,
                    version,
                    tarball_name,
                    str(dest_path.relative_to(WAYPACK_ROOT)),
                    commit_date,
                )
                processed += 1
            except Exception as exc:
                print(f"  ERROR {npm_package_name}@{version}: {exc}", file=sys.stderr)
                errors += 1

    save_output(output)
    print(
        f"\nDone — processed: {processed}, skipped: {skipped}, errors: {errors}\n"
        f"Output: {OUTPUT_JSON}"
    )
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
