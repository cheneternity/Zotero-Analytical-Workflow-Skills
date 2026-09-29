#!/usr/bin/env python3
"""Run a guarded, single-PDF MinerU conversion into a new output directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from config import configured_path, load_config


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="source PDF (read only)")
    parser.add_argument("--output", type=Path, help="new output/run directory; defaults to a unique folder under configured archive_root")
    parser.add_argument("--mineru", type=Path, help="MinerU executable; overrides config and MINERU_EXECUTABLE")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--method", choices=("auto", "txt", "ocr"), default="auto")
    parser.add_argument("--timeout", type=int, default=3600, help="hard timeout in seconds (default: 3600)")
    args = parser.parse_args()
    source = args.input.expanduser().resolve()
    settings = load_config(args.config)
    archive_root = configured_path("archive_root", settings)
    if args.output:
        output = args.output.expanduser().resolve()
    elif archive_root:
        output = archive_root / f"{args.input.stem}-{time.strftime('%Y%m%d-%H%M%S')}"
    else:
        parser.error("pass --output or configure paths.archive_root / RESEARCHVAULT_ARCHIVE_ROOT")
    executable = args.mineru.expanduser().resolve() if args.mineru else configured_path("mineru_executable", settings)
    if not source.is_file() or source.suffix.lower() != ".pdf":
        parser.error(f"input must be an existing PDF: {source}")
    if executable is None or not executable.is_file():
        parser.error("MinerU executable not found; set --mineru, MINERU_EXECUTABLE or paths.mineru_executable")
    if output.exists():
        parser.error(f"output already exists; refusing to overwrite: {output}")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    output.mkdir(parents=True)
    input_dir, raw_dir = output / "input", output / "raw"
    input_dir.mkdir()
    raw_dir.mkdir()
    work_pdf = input_dir / "input.pdf"
    shutil.copyfile(source, work_pdf)
    source_hash, working_hash = digest(source), digest(work_pdf)
    if source_hash != working_hash:
        parser.error("read-only source and working copy SHA-256 differ")
    command = [str(executable), "-p", str(work_pdf), "-o", str(raw_dir), "-b", "pipeline", "-m", args.method, "-l", "ch"]
    status = {"started_at": timestamp(), "source_pdf": str(source), "working_pdf": str(work_pdf), "source_read_only": True, "sha256": source_hash, "command": command, "returncode": None, "final_status": "RUNNING"}
    status_path = output / "production-status.json"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    timed_out = False
    with (output / "mineru.stdout.log").open("w", encoding="utf-8") as stdout, (output / "mineru.stderr.log").open("w", encoding="utf-8") as stderr:
        try:
            result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=args.timeout, check=False)
            return_code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            return_code = 124
    markdown = [p for p in raw_dir.rglob("*.md") if p.is_file() and p.stat().st_size]
    status.update({"finished_at": timestamp(), "returncode": return_code, "output_markdown_files": len(markdown), "final_status": "MINERU_TIMEOUT" if timed_out else "MINERU_COMPLETED_CLEAN" if return_code == 0 and markdown else "MINERU_FAILED"})
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "status": status["final_status"], "markdown_files": len(markdown)}, ensure_ascii=False))
    return 0 if status["final_status"] == "MINERU_COMPLETED_CLEAN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
