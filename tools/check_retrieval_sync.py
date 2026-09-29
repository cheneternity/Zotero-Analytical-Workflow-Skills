"""Check the standalone Retrieval release against this canonical Skill tree."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REQUIRED = ("SKILL.md", "agents/openai.yaml", "references/retrieval-routing.md")


def compare(canonical: Path, mirror: Path) -> list[str]:
    errors = []
    for relative in REQUIRED:
        source, published = canonical / relative, mirror / relative
        if not source.is_file():
            errors.append(f"canonical file missing: {source}")
        elif not published.is_file():
            errors.append(f"published file missing: {published}")
        elif source.read_bytes() != published.read_bytes():
            errors.append(f"content drift: {relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-dir", type=Path, default=Path(__file__).resolve().parents[1] / "skills/research-vault-literature-retrieval")
    parser.add_argument("--mirror-dir", type=Path, required=True)
    args = parser.parse_args()
    errors = compare(args.canonical_dir.resolve(), args.mirror_dir.resolve())
    for error in errors:
        print(f"FAIL: {error}")
    print("RESULT: " + ("FAIL" if errors else "PASS: standalone Retrieval files match canonical source"))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
