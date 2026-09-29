#!/usr/bin/env python3
"""Check Note-to-Fulltext links and stable Zotero identity without changing files."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

FIELD = re.compile(r"(?m)^([A-Za-z_][\w-]*):\s*[\"']?([^\r\n\"']*)")
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def fields(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\r?\n(.*?)\r?\n---", text, re.DOTALL)
    return dict(FIELD.findall(match.group(1))) if match else {}


def resolve(root: Path, value: str) -> Path:
    rel = value.strip().replace("\\", "/")
    target = (root / rel).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Vault-relative path escapes the Vault: {value}")
    if target.suffix.lower() != ".md":
        target = target.with_suffix(".md")
    return target


def validate(vault: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    issues: list[dict[str, str]] = []
    notes = [p for p in (vault / "02vault").rglob("*.md") if p.is_file()] if (vault / "02vault").is_dir() else []
    fulltexts = [p for p in (vault / "03fulltext").rglob("*.md") if p.is_file()] if (vault / "03fulltext").is_dir() else []
    by_key: dict[str, list[Path]] = {}
    for path in fulltexts:
        key = fields(path).get("zotero_key", "").strip()
        if key:
            by_key.setdefault(key, []).append(path)
    for note in notes:
        data = fields(note)
        if data.get("type", "").strip() != "literature-note" and "#literature-note" not in note.read_text(encoding="utf-8-sig"):
            continue
        key = data.get("zotero_key", "").strip()
        fulltext_value = data.get("fulltext_path", "").strip()
        if not key:
            issues.append({"level": "ERROR", "code": "NOTE_KEY", "path": str(note), "detail": "Analytical Note has no zotero_key"})
            continue
        candidate = None
        if fulltext_value:
            try:
                candidate = resolve(vault, fulltext_value)
            except ValueError as exc:
                issues.append({"level": "ERROR", "code": "PATH_ESCAPE", "path": str(note), "detail": str(exc)})
                continue
            if not candidate.is_file() and fulltext_value.replace("\\", "/").startswith("fulltext/"):
                legacy = resolve(vault, "03" + fulltext_value.replace("\\", "/"))
                if legacy.is_file():
                    candidate = legacy
                    issues.append({"level": "WARN", "code": "LEGACY_FULLTEXT_PATH", "path": str(note), "detail": f"read fallback resolved to {legacy.relative_to(vault.resolve()).as_posix()}; new writes must use 03fulltext/"})
            if not candidate.is_file():
                issues.append({"level": "ERROR", "code": "FULLTEXT_MISSING", "path": str(note), "detail": f"fulltext_path does not resolve: {fulltext_value}"})
                continue
        else:
            matches = by_key.get(key, [])
            if len(matches) == 1:
                candidate = matches[0]
            elif len(matches) > 1:
                issues.append({"level": "ERROR", "code": "FULLTEXT_AMBIGUOUS", "path": str(note), "detail": f"{len(matches)} Fulltexts share zotero_key {key}"})
                continue
        if candidate:
            if not candidate.is_relative_to((vault / "03fulltext").resolve()):
                issues.append({"level": "ERROR", "code": "NONCANONICAL_FULLTEXT", "path": str(note), "detail": f"resolved Fulltext is outside 03fulltext/: {candidate}"})
            full_fields = fields(candidate)
            if full_fields.get("zotero_key", "").strip() != key:
                issues.append({"level": "ERROR", "code": "KEY_MISMATCH", "path": str(candidate), "detail": f"note zotero_key={key!r}, fulltext zotero_key={full_fields.get('zotero_key')!r}"})
            for field in ("pdf_key",):
                if data.get(field) and full_fields.get(field) and data[field].strip() != full_fields[field].strip():
                    issues.append({"level": "ERROR", "code": "PDF_KEY_MISMATCH", "path": str(candidate), "detail": f"note and Fulltext {field} differ"})
            back = full_fields.get("note_path", "").strip()
            if back:
                try:
                    if resolve(vault, back) != note.resolve():
                        issues.append({"level": "ERROR", "code": "NOTE_PATH_MISMATCH", "path": str(candidate), "detail": f"note_path points to {back}"})
                except ValueError as exc:
                    issues.append({"level": "ERROR", "code": "PATH_ESCAPE", "path": str(candidate), "detail": str(exc)})
    errors = sum(i["level"] == "ERROR" for i in issues)
    summary = {"notes_scanned": len(notes), "fulltexts_scanned": len(fulltexts), "errors": errors, "warnings": sum(i["level"] == "WARN" for i in issues)}
    return issues, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    issues, summary = validate(args.vault.expanduser().resolve())
    if args.json:
        print(json.dumps({"summary": summary, "issues": issues}, ensure_ascii=False, indent=2))
    else:
        for item in issues:
            print(f"{item['level']} {item['code']} | {item['path']} | {item['detail']}")
        print(f"RESULT: {'FAIL' if summary['errors'] else 'PASS'} ({summary['notes_scanned']} notes, {summary['fulltexts_scanned']} fulltexts, {summary['errors']} errors)")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
