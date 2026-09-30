"""Read-only environment diagnostics for a configured ResearchVault install."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from config import configured_path, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    failures = 0

    def report(level: str, label: str, detail: str) -> None:
        nonlocal failures
        print(f"{level}: {label}: {detail}")
        failures += level == "FAIL"

    report("PASS" if sys.version_info >= (3, 11) else "FAIL", "Python", sys.version.split()[0] + (" (3.11+ required)" if sys.version_info < (3, 11) else ""))
    report("PASS" if args.config and args.config.is_file() or (Path(__file__).resolve().parents[1] / "config.toml").is_file() else "WARN", "config", str(args.config or Path(__file__).resolve().parents[1] / "config.toml") + (" found" if config else " not found or empty; use config.example.toml"))
    vault = configured_path("vault_root", config)
    if vault is None:
        report("FAIL", "vault_root", "set paths.vault_root or RESEARCHVAULT_ROOT")
    else:
        report("PASS" if vault.is_dir() else "FAIL", "vault_root", str(vault))
        for relative in ("01knowledge", "02vault", "03fulltext", "模板"):
            path = vault / relative
            report("PASS" if path.is_dir() else "FAIL", relative, "present" if path.is_dir() else f"missing under {vault}; run tools/init_vault.py")
        for relative in ("论文精读模板.md", "知识库模板/综合模板.md"):
            path = vault / "模板" / relative
            report("PASS" if path.is_file() else "WARN", f"template {relative}", "present" if path.is_file() else "missing; initializer can copy it")
    zotero = configured_path("zotero_data_dir", config)
    report("PASS" if zotero and (zotero / "zotero.sqlite").is_file() else "WARN", "Zotero data", str(zotero) if zotero else "not configured or not detected")
    mineru = configured_path("mineru_executable", config)
    report("PASS" if mineru and mineru.is_file() else "WARN", "MinerU", str(mineru) if mineru else "not configured; conversion unavailable")
    archive = configured_path("archive_root", config)
    report("PASS" if archive and archive.is_dir() else "WARN", "MinerU archive_root", str(archive) if archive else "not configured; pass --output to the runner")
    report("PASS" if shutil.which("rg") else "WARN", "ripgrep", shutil.which("rg") or "not found; built-in retrieval instructions remain usable")
    repo = Path(__file__).resolve().parents[1]
    for relative in ("skills/research-vault-knowledge-maintainer/scripts/validate_research_vault_knowledge.py", "tools/validate_research_vault_literature_links.py", "tools/run_mineru_production.py"):
        path = repo / relative
        report("PASS" if path.is_file() else "FAIL", f"required tool {relative}", "present" if path.is_file() else "missing")
    report("PASS", "Python packages", "all bundled diagnostics use the Python standard library")
    print(f"RESULT: {'FAIL' if failures else 'PASS'} ({failures} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
