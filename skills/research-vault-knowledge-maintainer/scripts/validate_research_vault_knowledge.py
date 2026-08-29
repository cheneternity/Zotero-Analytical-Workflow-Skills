#!/usr/bin/env python3
"""Validate a ResearchVault Knowledge Wiki against the frozen schema.

Read-only lint. Exits 0 when no ERROR-level problems are found and 1 otherwise.
WARNING-level findings are reported but do not fail the run.

The Knowledge Wiki layout is discovered under ``--vault`` with support for both
the original author layout (``01knowledge`` / ``02vault`` / ``03fulltext``) and
the user layout (``wiki`` / ``Research/Papers`` / ``Research/Fulltext``).
Override any directory with the explicit flags when auto-detection guesses
wrong.

Usage:
    validate_research_vault_knowledge.py --vault PATH [--knowledge DIR]
        [--notes DIR] [--fulltext DIR] [--stale-days N] [--strict]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# --------------------------------------------------------------------------- #
# Frozen schema (kept in sync with references/knowledge-schema.md)
# --------------------------------------------------------------------------- #

PAGE_TYPES = {
    "knowledge-theme",
    "knowledge-concept",
    "knowledge-method",
    "knowledge-relation",
    "knowledge-controversy",
    "knowledge-synthesis",
}

STATUS_VALUES = {"emerging", "developing", "established", "conditional", "contested"}
AGREEMENT_VALUES = {"strong", "mixed", "conflicting", "insufficient"}
EVIDENCE_STATUS_VALUES = {"fulltext_verified", "note_only", "mixed"}
EVIDENCE_ROLE_VALUES = {"direct", "mechanism", "conditional", "contextual", "related"}
VERIFICATION_STATE_VALUES = {"fulltext_verified", "note_supported", "interpretation"}
GAP_PROVENANCE_VALUES = {"evidence-backed", "interpretive"}

REQUIRED_FIELDS = {
    "type",
    "title",
    "aliases",
    "status",
    "evidence_count",
    "source_notes",
    "related",
    "last_updated",
    "evidence_status",
}

# Relation pages additionally require subject/relation/object/agreement.
# Controversy pages additionally require agreement.
RELATION_EXTRA = {"subject", "relation", "object", "agreement"}
CONTROVERSY_EXTRA = {"agreement"}

# Claim ID format: (REL|CON|SYN)-TOKEN(-TOKEN)+-NN
CLAIM_ID_RE = re.compile(r"^(REL|CON|SYN)-[A-Z0-9]+(?:-[A-Z0-9]+)+-\d{2}$")

# A Zotero key is 8 uppercase alphanumerics (matches items.key in Zotero).
ZOTERO_KEY_RE = re.compile(r"^[A-Z0-9]{8}$")

# Navigation files that are human-facing but not Knowledge pages.
NAV_FILES = {"index.md", "log.md"}

# Claim sidecar required fields (from knowledge-schema.md).
CLAIM_SIDECAR_FIELDS = {
    "claim_id",
    "page_path",
    "section_heading",
    "normalized_statement",
    "statement_hash",
    "evidence_role",
    "verification_state",
    "source_notes",
}

# Literal-8-key lookalike that flags a likely raw Zotero key leaking into prose.
RAW_KEY_LEAK_RE = re.compile(r"\b[A-Z0-9]{8}\b")

WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


# --------------------------------------------------------------------------- #
# Frontmatter parsing (dependency-free YAML-lite)
# --------------------------------------------------------------------------- #

def _parse_scalar(s: str):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if s == "[]":
        return []
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x.strip()) for x in inner.split(",")]
    try:
        return int(s)
    except ValueError:
        return s


def parse_frontmatter_text(fm_text: str):
    """Parse the YAML-lite frontmatter body into a dict.

    Handles ``key: scalar``, ``key: []``, inline lists, and block lists of the
    form ``key:\\n  - item``. Values are str, int, or list.
    """
    result = {}
    current_key = None
    for raw in fm_text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key is not None:
            result.setdefault(current_key, []).append(
                _parse_scalar(stripped[2:].strip())
            )
            continue
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                current_key = key
                result.setdefault(key, [])
            else:
                result[key] = _parse_scalar(val)
                current_key = None
    return result


def read_frontmatter(path: Path):
    """Return (frontmatter_dict, body_str). Empty dict when no frontmatter."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"<unreadable: {exc}>"
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    close = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close = i
            break
    if close is None:
        return {}, text
    fm_text = "\n".join(lines[1:close])
    body = "\n".join(lines[close + 1:])
    return parse_frontmatter_text(fm_text), body


def parse_wikilink_target(entry: str):
    """Extract a real (vault-relative) target path from a source_notes entry.

    Returns (target, alias). ``target`` has any ``#heading`` anchor removed.
    """
    s = entry.strip()
    m = WIKILINK_RE.search(s)
    if m:
        inner = m.group(1)
    else:
        inner = s
    if "|" in inner:
        target, alias = inner.split("|", 1)
    else:
        target, alias = inner, None
    target = target.strip().split("#")[0].rstrip()
    return target, (alias.strip() if alias else None)


# --------------------------------------------------------------------------- #
# Directory discovery
# --------------------------------------------------------------------------- #

def resolve_dir(vault: Path, explicit, *candidates):
    if explicit:
        p = Path(explicit)
        return p if p.is_absolute() else vault / p
    for c in candidates:
        p = vault / c
        if p.is_dir():
            return p
    return None


# --------------------------------------------------------------------------- #
# Report collector
# --------------------------------------------------------------------------- #

class Reporter:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, msg):
        self.errors.append(f"[ERROR] {path}: {msg}")

    def warning(self, path, msg):
        self.warnings.append(f"[WARNING] {path}: {msg}")

    def summarize(self):
        for line in self.errors:
            print(line)
        for line in self.warnings:
            print(line)
        print("-" * 60)
        print(f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return 1 if self.errors else 0


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

def validate(vault: Path, knowledge_dir, notes_dir, fulltext_dir, stale_days, strict):
    rep = Reporter()
    kdir = resolve_dir(vault, knowledge_dir, "wiki", "01knowledge", "knowledge")
    ndir = resolve_dir(vault, notes_dir, "Research/Papers", "02vault", "note", "论文库")
    fdir = resolve_dir(vault, fulltext_dir, "Research/Fulltext", "03fulltext", "fulltext")

    if kdir is None:
        rep.error(vault, "knowledge directory not found (tried wiki/01knowledge/knowledge)")
        return rep
    if ndir is None:
        rep.error(vault, "analytical notes directory not found (tried Research/Papers/02vault)")
        return rep

    pages = discover_pages(kdir, rep)
    index = collect_index_titles(kdir)
    note_index = collect_note_map(ndir, rep)

    for page_path, fm, body in pages:
        check_page(page_path, fm, body, rep, vault, kdir, ndir, fdir, index, note_index, stale_days, strict)

    check_claim_sidecars(kdir, rep)
    check_gap_sidecars(kdir, rep)

    return rep


def discover_pages(kdir: Path, rep: Reporter):
    """Yield (path, frontmatter, body) for formal Knowledge pages only."""
    out = []
    for md in sorted(kdir.rglob("*.md")):
        rel = md.relative_to(kdir)
        # Exclude .meta entirely; it is machine metadata, not pages.
        if ".meta" in rel.parts:
            continue
        if rel.name.lower() in NAV_FILES:
            continue
        fm, body = read_frontmatter(md)
        if fm is None:
            rep.error(md, "unreadable file")
            continue
        if not fm:
            rep.error(md, "missing frontmatter")
            continue
        ptype = fm.get("type")
        if ptype not in PAGE_TYPES:
            # Not a formal Knowledge page; ignore silently.
            continue
        out.append((md, fm, body))
    return out


def collect_index_titles(kdir: Path):
    """Return the set of page titles/filenames referenced from index.md."""
    idx = kdir / "index.md"
    if not idx.exists():
        return set()
    text = idx.read_text(encoding="utf-8", errors="replace")
    # Collect wikilink targets and any quoted titles.
    targets = set()
    for m in WIKILINK_RE.finditer(text):
        inner = m.group(1)
        targets.add(inner.split("|")[0].strip())
    return targets


def collect_note_map(ndir: Path, rep: Reporter):
    """Map vault-relative note path (posix, no .md) -> note frontmatter."""
    note_map = {}
    for md in sorted(ndir.rglob("*.md")):
        if md.name.startswith("_"):
            continue
        fm, _ = read_frontmatter(md)
        if fm is None:
            continue
        # Only literature notes participate in the evidence chain.
        if fm.get("type") not in ("literature-note", None):
            continue
        for key in _note_relative_keys(md, ndir):
            note_map[key] = fm
    return note_map


def _note_relative_keys(md: Path, ndir: Path):
    """Possible vault-relative keys for a note file (posix, with/without .md)."""
    rel = md.relative_to(ndir).as_posix()
    keys = {rel, rel[:-3] if rel.endswith(".md") else rel + ".md"}
    return keys


def check_page(page_path, fm, body, rep, vault, kdir, ndir, fdir, index, note_index, stale_days, strict):
    rel = page_path.relative_to(kdir).as_posix()
    ptype = fm.get("type")

    # --- required fields ----------------------------------------------------
    missing = REQUIRED_FIELDS - set(fm)
    if missing:
        rep.error(rel, f"missing required field(s): {', '.join(sorted(missing))}")

    # --- enum checks --------------------------------------------------------
    if fm.get("status") not in STATUS_VALUES:
        rep.error(rel, f"invalid status {fm.get('status')!r} (allowed: {sorted(STATUS_VALUES)})")
    if fm.get("evidence_status") not in EVIDENCE_STATUS_VALUES:
        rep.error(rel, f"invalid evidence_status {fm.get('evidence_status')!r}")

    if ptype == "knowledge-relation":
        miss = RELATION_EXTRA - set(fm)
        if miss:
            rep.error(rel, f"relation page missing field(s): {', '.join(sorted(miss))}")
    if ptype in ("knowledge-relation", "knowledge-controversy", "knowledge-synthesis"):
        if "agreement" in fm and fm.get("agreement") not in AGREEMENT_VALUES:
            rep.error(rel, f"invalid agreement {fm.get('agreement')!r}")

    # --- evidence_count vs source_notes ------------------------------------
    source_notes = fm.get("source_notes", [])
    if isinstance(source_notes, list):
        ec = fm.get("evidence_count")
        if isinstance(ec, int) and ec != len(source_notes):
            rep.error(rel, f"evidence_count {ec} != len(source_notes) {len(source_notes)}")

    # --- source_notes link resolution --------------------------------------
    if isinstance(source_notes, list):
        seen = set()
        for entry in source_notes:
            target, _alias = parse_wikilink_target(str(entry))
            if not target:
                rep.error(rel, f"unparseable source_notes entry: {entry!r}")
                continue
            key = target[:-3] if target.endswith(".md") else target
            if key in seen:
                rep.warning(rel, f"duplicate source link {target}")
            seen.add(key)
            resolved = resolve_note(key, note_index, ndir)
            if resolved is None:
                rep.error(rel, f"source_notes link target not found: {target}")
            else:
                nfm = note_index.get(resolved)
                if nfm and nfm.get("type") not in (None, "literature-note"):
                    rep.warning(rel, f"source link {target} is not a literature-note")

    # --- raw key / machine-metadata leak -----------------------------------
    if "zotero_key" in fm:
        rep.error(rel, "raw zotero_key must not appear in a Knowledge page frontmatter")
    # HTML comments are reserved for machine metadata and must not appear.
    if "<!--" in body:
        rep.error(rel, "HTML comment found in visible Markdown body (machine metadata must live in .meta)")

    # --- index coverage ------------------------------------------------------
    if index:
        title = str(fm.get("title", ""))
        basename = page_path.stem
        if not any(t in index for t in (title, basename)) and title and basename not in index:
            rep.warning(rel, f"page not listed in index.md (title={title!r})")

    # --- stale pages --------------------------------------------------------
    if stale_days and stale_days > 0:
        lu = fm.get("last_updated")
        if isinstance(lu, str):
            if _days_old(lu) is not None and _days_old(lu) > stale_days:
                rep.warning(rel, f"stale page: last_updated {lu} older than {stale_days} days")


def resolve_note(key, note_index, ndir):
    """Resolve a vault-relative note key to a key present in note_index."""
    # Try exact matches against all known keys.
    cand = {key, key + ".md", key[:-3] if key.endswith(".md") else key}
    for c in cand:
        if c in note_index:
            return c
    # Also allow a target that already starts with a notes-dir alias.
    for alias in ("Research/Papers/", "02vault/", "note/", "论文库/"):
        if key.startswith(alias):
            suffix = key[len(alias):]
            for c in (suffix, suffix + ".md"):
                if c in note_index:
                    return c
    return None


def _days_old(s: str):
    try:
        d = date.fromisoformat(s[:10])
        return (date.today() - d).days
    except ValueError:
        return None


def check_claim_sidecars(kdir: Path, rep: Reporter):
    claims_dir = kdir / ".meta" / "claims"
    if not claims_dir.exists():
        return
    for f in sorted(claims_dir.glob("*.json")):
        rel = f.relative_to(kdir).as_posix()
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            rep.error(rel, f"unreadable/invalid JSON: {exc}")
            continue
        missing = CLAIM_SIDECAR_FIELDS - set(data)
        if missing:
            rep.error(rel, f"claim sidecar missing field(s): {', '.join(sorted(missing))}")
        cid = data.get("claim_id", "")
        if cid and not CLAIM_ID_RE.match(str(cid)):
            rep.error(rel, f"invalid claim_id {cid!r} (expected REL|CON|SYN-...-NN)")
        if data.get("evidence_role") not in EVIDENCE_ROLE_VALUES:
            rep.error(rel, f"invalid evidence_role {data.get('evidence_role')!r}")
        if data.get("verification_state") not in VERIFICATION_STATE_VALUES:
            rep.error(rel, f"invalid verification_state {data.get('verification_state')!r}")


def check_gap_sidecars(kdir: Path, rep: Reporter):
    gaps_dir = kdir / ".meta" / "gaps"
    if not gaps_dir.exists():
        return
    for f in sorted(gaps_dir.glob("*.json")):
        rel = f.relative_to(kdir).as_posix()
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            rep.error(rel, f"unreadable/invalid JSON: {exc}")
            continue
        if data.get("gap_provenance") not in GAP_PROVENANCE_VALUES:
            rep.error(rel, f"invalid gap_provenance {data.get('gap_provenance')!r}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    p = argparse.ArgumentParser(description="Validate a ResearchVault Knowledge Wiki.")
    p.add_argument("--vault", required=True, help="vault root directory")
    p.add_argument("--knowledge", help="knowledge dir (default: auto-detect)")
    p.add_argument("--notes", help="analytical notes dir (default: auto-detect)")
    p.add_argument("--fulltext", help="fulltext dir (default: auto-detect)")
    p.add_argument("--stale-days", type=int, default=0, help="warn if last_updated older than N days")
    p.add_argument("--strict", action="store_true", help="reserved; currently no-op")
    args = p.parse_args(argv)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"[ERROR] vault not found: {vault}")
        return 1

    rep = validate(vault, args.knowledge, args.notes, args.fulltext, args.stale_days, args.strict)
    return rep.summarize()


if __name__ == "__main__":
    sys.exit(main())
