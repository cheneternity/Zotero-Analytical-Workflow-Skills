#!/usr/bin/env python3
"""Serially run MinerU over a small list of PDFs into a staging directory.

This is the batch front-end to ``run_mineru_production.py``. It does NOT write
into the formal Fulltext directory: per the zotero-fulltext-archiver contract,
batch output is only external staging; each paper must be individually
finalized (frontmatter, image paths, note link) and validated before being
copied into ``Research/Fulltext/<collection>/``.

One paper runs at a time. Each paper gets its own scoped run directory so a
failure never contaminates another paper's output.

Usage:
    mineru_batch_runner.py --manifest papers.json [--staging DIR]
        [--mineru PATH] [--backend pipeline] [--dry-run]

Manifest format (JSON array):
    [
      {"zotero_key": "Q22PFLNV", "pdf": "C:/path/to/paper.pdf"},
      ...
    ]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SINGLE_RUNNER = HERE / "run_mineru_production.py"


def log(msg: str):
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def run_one(entry, staging: Path, mineru, backend, dry_run):
    key = entry.get("zotero_key")
    pdf = entry.get("pdf")
    if not key or not pdf:
        log(f"SKIP invalid entry {entry!r}")
        return "INVALID_ENTRY"
    src = Path(pdf).expanduser()
    if not src.exists():
        log(f"SKIP missing pdf for {key}: {src}")
        return "PDF_NOT_FOUND"

    cmd = [
        sys.executable, str(SINGLE_RUNNER),
        "--pdf", str(src.resolve()),
        "--zotero-key", key,
        "--output", str(staging / key),
        "--mineru", mineru,
        "--backend", backend,
    ]
    if dry_run:
        cmd.append("--dry-run")

    log(f"RUN {key} <- {src}")
    try:
        rc = subprocess.run(cmd, timeout=7200).returncode
    except subprocess.TimeoutExpired:
        log(f"FAIL {key} timeout")
        return "TIMEOUT"
    if rc == 0:
        log(f"OK   {key}")
        return "COMPLETE"
    log(f"FAIL {key} rc={rc}")
    return "FAILED"


def main(argv=None):
    p = argparse.ArgumentParser(description="Serially run MinerU over a manifest of PDFs.")
    p.add_argument("--manifest", required=True, help="JSON array of {zotero_key, pdf}")
    p.add_argument("--staging", default="mineru-staging", help="staging output directory")
    p.add_argument("--mineru", default="mineru", help="MinerU executable (default: mineru on PATH)")
    p.add_argument("--backend", default="pipeline", help="MinerU backend (default: pipeline)")
    p.add_argument("--dry-run", action="store_true", help="preflight only, stub conversion")
    args = p.parse_args(argv)

    manifest_path = Path(args.manifest).expanduser().resolve()
    if not manifest_path.exists():
        print(f"[ERROR] manifest not found: {manifest_path}")
        return 1
    try:
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] invalid manifest JSON: {exc}")
        return 1
    if not isinstance(entries, list):
        print("[ERROR] manifest must be a JSON array")
        return 1

    staging = Path(args.staging).expanduser().resolve()
    staging.mkdir(parents=True, exist_ok=True)

    results = {}
    for entry in entries:
        status = run_one(entry, staging, args.mineru, args.backend, args.dry_run)
        key = entry.get("zotero_key", "?")
        results[key] = status

    log("-" * 60)
    for key, status in results.items():
        log(f"{key}: {status}")
    ok = sum(1 for s in results.values() if s == "COMPLETE")
    log(f"summary: {ok}/{len(results)} complete")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
