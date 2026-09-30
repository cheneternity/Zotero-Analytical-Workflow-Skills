#!/usr/bin/env python3
"""Validate ResearchVault Knowledge pages against the bundled frozen schema."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PAGE_TYPES = {"knowledge-theme", "knowledge-concept", "knowledge-method", "knowledge-relation", "knowledge-controversy", "knowledge-synthesis"}
STATUSES = {"emerging", "developing", "established", "conditional", "contested"}
EVIDENCE = {"fulltext_verified", "note_only", "mixed"}
AGREEMENT = {"strong", "mixed", "conflicting", "insufficient"}
EVIDENCE_ROLE = {"direct", "mechanism", "conditional", "contextual", "related"}
VERIFICATION = {"fulltext_verified", "note_supported", "interpretation"}
GAP_PROVENANCE = {"evidence-backed", "interpretive"}
CLAIM_ID = re.compile(r"^(REL|CON|SYN)-[A-Z0-9]+(?:-[A-Z0-9]+)+-\d{2}$")
REQUIRED = {"type", "title", "aliases", "status", "evidence_count", "source_notes", "related", "last_updated", "evidence_status"}
SCALAR = re.compile(r"(?m)^([A-Za-z_][\w-]*):\s*(.*?)\s*$")
LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


def frontmatter(text: str) -> dict[str, str] | None:
    match = re.match(r"\A---\s*\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.DOTALL)
    if not match:
        return None
    return {key: value.strip().strip("\"'") for key, value in SCALAR.findall(match.group(1))}


def validate(vault: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    issues: list[dict[str, str]] = []

    def add(level: str, code: str, path: Path, detail: str) -> None:
        issues.append({"level": level, "code": code, "path": str(path), "detail": detail})

    knowledge = vault / "01knowledge"
    if not knowledge.is_dir():
        add("ERROR", "KNOWLEDGE_ROOT", knowledge, "missing 01knowledge directory")
        return issues, {"pages": 0, "errors": 1, "warnings": 0}
    pages = 0
    for path in knowledge.rglob("*.md"):
        if ".meta" in path.relative_to(knowledge).parts:
            continue
        text = path.read_text(encoding="utf-8-sig")
        data = frontmatter(text)
        if not data or data.get("type") not in PAGE_TYPES:
            continue
        pages += 1
        missing = REQUIRED - data.keys()
        if missing:
            add("ERROR", "SCHEMA_REQUIRED", path, "missing: " + ", ".join(sorted(missing)))
        if data.get("status") not in STATUSES:
            add("ERROR", "SCHEMA_STATUS", path, f"unsupported status: {data.get('status')!r}")
        if data.get("evidence_status") not in EVIDENCE:
            add("ERROR", "SCHEMA_EVIDENCE_STATUS", path, f"page evidence_status must be one of {sorted(EVIDENCE)}")
        if data.get("evidence_count", "").isdigit() is False:
            add("ERROR", "EVIDENCE_COUNT", path, "evidence_count must be a non-negative integer")
        if data["type"] in {"knowledge-relation", "knowledge-controversy"}:
            if data["type"] == "knowledge-relation" and not {"subject", "relation", "object", "agreement"} <= data.keys():
                add("ERROR", "RELATION_REQUIRED", path, "relation pages require subject, relation, object and agreement")
            if data.get("agreement") not in AGREEMENT:
                add("ERROR", "AGREEMENT", path, f"unsupported agreement: {data.get('agreement')!r}")
        if "note_supported" in data.get("evidence_status", "") or re.search(r"(?m)^\s*-\s*(?:mechanistic|counter)\s*(?:/|$)", text):
            add("ERROR", "LEGACY_ENUM", path, "claim verification/role enum used as page status or unsupported role")
        if "{{" in text or "[[]]" in text or "待填写" in text:
            add("ERROR", "UNFILLED_TEMPLATE", path, "template placeholder remains in a formal page")
        if re.search(r"(?is)<!--\s*(?:claim_id|evidence_role|verification_state|gap_provenance)\s*:", text):
            add("ERROR", "EMBEDDED_MACHINE_METADATA", path, "claim and gap machine metadata belongs in .meta/ JSON sidecars")
        source_block = re.search(r"(?ms)^source_notes:\s*\r?\n(.*?)(?=^[A-Za-z_][\w-]*:|\Z)", (re.match(r"\A---\s*\r?\n(.*?)\r?\n---", text, re.DOTALL) or [None, ""])[1])
        source_links = LINK.findall(source_block.group(1)) if source_block else []
        if data.get("evidence_count", "").isdigit() and len(set(source_links)) != int(data["evidence_count"]):
            add("WARN", "SOURCE_COUNT", path, f"evidence_count={data['evidence_count']}, source_notes links={len(set(source_links))}")
        for target in source_links:
            relative = target.replace("\\", "/").split("|", 1)[0]
            source = vault / (relative if relative.lower().endswith(".md") else relative + ".md")
            if not source.is_file():
                add("ERROR", "SOURCE_LINK", path, f"missing Analytical Note: {relative}")
    meta = knowledge / ".meta"
    for path in (meta / "claims").glob("*.json") if (meta / "claims").is_dir() else ():
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            add("ERROR", "CLAIM_JSON", path, str(exc))
            continue
        required = {"claim_id", "page_path", "section_heading", "normalized_statement", "statement_hash", "evidence_role", "verification_state", "source_notes"}
        if not required <= record.keys():
            add("ERROR", "CLAIM_REQUIRED", path, "missing: " + ", ".join(sorted(required - record.keys())))
        if not CLAIM_ID.fullmatch(str(record.get("claim_id", ""))):
            add("ERROR", "CLAIM_ID", path, "claim_id does not match the frozen format")
        if record.get("evidence_role") not in EVIDENCE_ROLE:
            add("ERROR", "EVIDENCE_ROLE", path, f"unsupported evidence_role: {record.get('evidence_role')!r}")
        if record.get("verification_state") not in VERIFICATION:
            add("ERROR", "VERIFICATION_STATE", path, f"unsupported verification_state: {record.get('verification_state')!r}")
    for path in (meta / "gaps").glob("*.json") if (meta / "gaps").is_dir() else ():
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            add("ERROR", "GAP_JSON", path, str(exc))
            continue
        if record.get("gap_provenance") not in GAP_PROVENANCE:
            add("ERROR", "GAP_PROVENANCE", path, f"unsupported gap_provenance: {record.get('gap_provenance')!r}")
    if pages == 0:
        add("WARN", "NO_PAGES", knowledge, "no formal Knowledge pages found; structure-only validation completed")
    summary = {"pages": pages, "errors": sum(i["level"] == "ERROR" for i in issues), "warnings": sum(i["level"] == "WARN" for i in issues)}
    return issues, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True, help="ResearchVault root")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()
    issues, summary = validate(args.vault.expanduser().resolve())
    if args.json:
        print(json.dumps({"summary": summary, "issues": issues}, ensure_ascii=False, indent=2))
    else:
        for issue in issues:
            print(f"{issue['level']} {issue['code']} | {issue['path']} | {issue['detail']}")
        print(f"RESULT: {'FAIL' if summary['errors'] else 'PASS'} ({summary['pages']} pages, {summary['errors']} errors, {summary['warnings']} warnings)")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
