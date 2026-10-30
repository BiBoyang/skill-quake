#!/usr/bin/env python3
"""Write one run's provenance manifest with deterministic content hashes."""
import argparse
import datetime
import hashlib
import json
import os
import sys

VERSION_FIELDS = ("target_version", "host_version", "model", "effort")


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_hash(root):
    if not os.path.isdir(root):
        raise NotADirectoryError(f"fixture is not a directory: {root}")
    entries = []
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        files.sort()
        for name in list(dirs):
            path = os.path.join(current, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.islink(path):
                entries.append(["symlink", rel, os.readlink(path)])
                dirs.remove(name)
            else:
                entries.append(["directory", rel])
        for name in files:
            path = os.path.join(current, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.islink(path):
                entries.append(["symlink", rel, os.readlink(path)])
            elif os.path.isfile(path):
                entries.append(["file", rel, file_hash(path)])
            else:
                entries.append(["other", rel])
    encoded = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--fault", required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--run", required=True, type=int)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--time")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--guard", required=True)
    parser.add_argument("--witness-checker", required=True)
    for name in VERSION_FIELDS:
        parser.add_argument("--" + name.replace("_", "-"))
    parser.add_argument("--strict", action="store_true", help="fail when a version field is missing")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    missing = [name for name in VERSION_FIELDS if not getattr(args, name)]
    if missing and args.strict:
        print("write_meta: missing required metadata: " + ", ".join(missing), file=sys.stderr)
        return 2
    if missing:
        print("write_meta: WARNING incomplete provenance: " + ", ".join(missing), file=sys.stderr)

    with open(args.guard, encoding="utf-8") as handle:
        guard = json.load(handle)
    timestamp = args.time or datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    meta = {
        "schema_version": "1.0",
        "host": args.host,
        "fault": args.fault,
        "cell": args.cell,
        "run": args.run,
        "stage": args.stage,
        "time": timestamp,
        "target_version": args.target_version or "unknown",
        "host_version": args.host_version or "unknown",
        "model": args.model or "unknown",
        "effort": args.effort or "unknown",
        "prompt_sha256": file_hash(args.prompt),
        "fixture_sha256": tree_hash(args.fixture),
        "witness": {
            "verdict": guard.get("verdict", "UNKNOWN"),
            "output_sha256": file_hash(args.guard),
            "checker_sha256": file_hash(args.witness_checker),
        },
        "missing": missing,
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
