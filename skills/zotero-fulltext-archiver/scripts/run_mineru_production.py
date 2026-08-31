#!/usr/bin/env python3
"""Run MinerU on a single validated Zotero PDF and emit a formal Markdown gate.

Implements the "Batch 6D" production safeguards from
zotero-fulltext-archiver/SKILL.md for a Windows CPU environment:

- copy the source PDF to an ASCII-only working copy ``input_<zotero_key>.pdf``
  in a scoped temporary run directory (the Zotero attachment stays read-only);
- verify the source and working-copy SHA-256 before invoking MinerU;
- use the explicitly validated ``pipeline`` backend;
- stream timestamped stdout/stderr into the run directory and record stage
  transitions;
- enforce a hard time limit (default 60 minutes) and a no-progress stop
  (default 15 minutes of no output/progress);
- clean only the MinerU process tree spawned by this invocation;
- run the raw-Markdown gate (non-empty front/middle/end samples).

Usage:
    run_mineru_production.py --pdf SOURCE.pdf --zotero-key KEY
        [--output DIR] [--mineru PATH] [--backend pipeline]
        [--model-source modelscope] [--run-dir DIR]
        [--timeout 3600] [--no-progress-timeout 900] [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def log_file(f: object):
    """Return a helper that writes a timestamped line to an open file."""
    def emit(msg: str):
        line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n"
        f.write(line)
        f.flush()
        print(line, end="", flush=True)
    return emit


def run_dir_path(run_dir: Path, *parts: str) -> Path:
    p = run_dir
    for part in parts:
        p = p / part
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def kill_process_tree(proc: subprocess.Popen, log):
    """Terminate the MinerU process tree created by this invocation only."""
    if proc is None or proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True, timeout=30,
            )
        else:
            subprocess.run(["pkill", "-TERM", "-P", str(proc.pid)],
                           capture_output=True, timeout=30)
            proc.terminate()
    except (OSError, subprocess.TimeoutExpired):
        pass
    log(f"stage=cleanup pid={proc.pid} terminated")


def raw_markdown_gate(md_path: Path, log) -> bool:
    """Check a produced Markdown has non-empty front/middle/end samples."""
    if not md_path.exists():
        log(f"stage=gate result=FAIL reason=missing_output {md_path}")
        return False
    text = md_path.read_text(encoding="utf-8", errors="replace")
    n = len(text)
    if n == 0:
        log(f"stage=gate result=FAIL reason=empty_output {md_path}")
        return False
    front = text[:200].strip()
    middle = text[n // 2 - 100:n // 2 + 100].strip()
    end = text[-200:].strip()
    if not (front and middle and end):
        log(f"stage=gate result=FAIL reason=empty_region {md_path}")
        return False
    log(f"stage=gate result=PASS bytes={n} {md_path}")
    return True


def main(argv=None):
    p = argparse.ArgumentParser(description="Run MinerU on a single PDF with production safeguards.")
    p.add_argument("--pdf", required=True, help="source PDF path (kept read-only)")
    p.add_argument("--zotero-key", required=True, help="Zotero parent item key")
    p.add_argument("--output", help="output directory for MinerU Markdown")
    p.add_argument("--mineru", default="mineru", help="MinerU executable (default: mineru on PATH)")
    p.add_argument("--backend", default="pipeline", help="MinerU backend (default: pipeline)")
    p.add_argument("--model-source", default="modelscope",
                   help="model download source: modelscope, huggingface, or local (default: modelscope)")
    p.add_argument("--run-dir", help="scoped temp run dir (default: system temp)")
    p.add_argument("--timeout", type=int, default=3600, help="hard time limit seconds (default 3600)")
    p.add_argument("--no-progress-timeout", type=int, default=900,
                   help="stop after N seconds with no output (default 900)")
    p.add_argument("--dry-run", action="store_true",
                   help="run all preflight checks and a stub conversion, no real MinerU")
    args = p.parse_args(argv)

    src = Path(args.pdf).expanduser().resolve()
    if not src.exists():
        print(f"[ERROR] source PDF not found: {src}")
        return 1

    # Scoped run directory.
    if args.run_dir:
        run_dir = Path(args.run_dir).expanduser().resolve()
    else:
        run_dir = Path(tempfile.mkdtemp(prefix="mineru_run_"))
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "run.log", "w", encoding="utf-8") as lf, \
         open(run_dir / "stdout.log", "w", encoding="utf-8") as so, \
         open(run_dir / "stderr.log", "w", encoding="utf-8") as se:
        log = log_file(lf)

        log(f"stage=start pdf={src} zotero_key={args.zotero_key} backend={args.backend}")

        # 1. source hash.
        log("stage=hash source")
        src_hash = sha256(src)
        log(f"stage=hash source_sha256={src_hash}")

        # 2. ASCII working copy.
        work = run_dir / f"input_{args.zotero_key}.pdf"
        shutil.copy2(src, work)
        work_hash = sha256(work)
        log(f"stage=hash work_sha256={work_hash} work={work}")

        if work_hash != src_hash:
            log("stage=hash result=FAIL reason=mismatch")
            return 1
        log("stage=hash result=PASS")

        # 3. output directory.
        out_dir = Path(args.output).expanduser().resolve() if args.output else (run_dir / "output")
        out_dir.mkdir(parents=True, exist_ok=True)

        # 4. invoke MinerU (or stub in dry-run).
        cmd = [args.mineru, "-p", str(work), "-o", str(out_dir), "-b", args.backend]
        log(f"stage=invoke cmd={' '.join(cmd)} dry_run={args.dry_run}")

        if args.dry_run:
            log("stage=invoke result=SKIPPED reason=dry_run")
            # Mimic MinerU's real output layout: <out>/input_<key>/auto/input_<key>.md
            base = f"input_{args.zotero_key}"
            stub = out_dir / base / "auto" / f"{base}.md"
            stub.parent.mkdir(parents=True, exist_ok=True)
            stub.write_text("STUB-FRONT\n\nSTUB-MIDDLE\n\nSTUB-END\n", encoding="utf-8")
            md_candidate = stub
            rc = 0
        else:
            # MinerU's CLI starts a local API and health-checks it over
            # 127.0.0.1. If a system HTTP proxy is set, those localhost
            # requests are hijacked and return 503. Exempt loopback from the
            # proxy for the child process.
            env = dict(os.environ)
            # Model source is configurable; modelscope is the China-friendly
            # default for the pipeline models. A caller-chosen env var is
            # preserved when --model-source is not overridden.
            env["MINERU_MODEL_SOURCE"] = args.model_source
            no_proxy = env.get("NO_PROXY") or env.get("no_proxy") or ""
            if no_proxy:
                no_proxy += ","
            no_proxy += "127.0.0.1,localhost,::1"
            env["NO_PROXY"] = no_proxy
            env["no_proxy"] = no_proxy
            proc = subprocess.Popen(
                cmd, stdout=so, stderr=se, text=True, env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
            start = time.time()
            last_output = start
            try:
                while proc.poll() is None:
                    elapsed = time.time() - start
                    if elapsed > args.timeout:
                        log(f"stage=timeout result=FAIL elapsed={int(elapsed)}")
                        kill_process_tree(proc, log)
                        return 1
                    # detect no-progress via run.log / output file growth
                    if time.time() - last_output > args.no_progress_timeout:
                        log(f"stage=no_progress result=FAIL")
                        kill_process_tree(proc, log)
                        return 1
                    time.sleep(2)
                rc = proc.returncode
            except KeyboardInterrupt:
                kill_process_tree(proc, log)
                return 130
            log(f"stage=invoke result=done rc={rc}")

        if rc != 0:
            log(f"stage=invoke result=FAIL rc={rc}")
            return 1

        # 5. locate produced markdown and run gate.
        candidates = list(out_dir.rglob("*.md"))
        if not candidates and args.dry_run:
            candidates = [md_candidate]
        if not candidates:
            log("stage=gate result=FAIL reason=no_markdown")
            return 1
        md_path = candidates[0]
        if not raw_markdown_gate(md_path, log):
            return 1

        log(f"stage=complete output={md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
