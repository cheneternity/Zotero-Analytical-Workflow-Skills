#!/usr/bin/env python3
"""Validate the reciprocal Note <-> Fulltext links in a ResearchVault.

Read-only lint: it reports broken/mismatched links but never moves or deletes
anything. Exits 0 when no ERROR-level problems are found and 1 otherwise.

Checks, per the zotero-fulltext-archiver contract:

- Fulltext frontmatter has the required identity fields.
- Every local image reference inside a Fulltext resolves to a real file
  (``MISSING_IMAGES`` must be 0 for the archiver to report COMPLETE).
- A Note whose frontmatter carries ``fulltext_path`` actually points to an
  existing Fulltext file.
- A Fulltext whose frontmatter carries ``note_path`` actually points to an
  existing Note file.
- The ``zotero_key`` and ``pdf_key`` agree between a Note and its Fulltext.

Usage:
    validate_research_vault_literature_links.py --vault PATH
        [--notes DIR] [--fulltext DIR] [--zotero-db PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FULLTEXT_REQUIRED_FIELDS = {
    "type",
    "title",
    "zotero_key",
    "pdf_key",
    "doi",
    "collection",
    "note_path",
    "fulltext_path",
    "zotero_item",
    "zotero_pdf",
    "source_type",
    "page_mapping",
}

IMAGE_REF_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
ZOTERO_KEY_RE = re.compile(r"^[A-Z0-9]{8}$")


# --------------------------------------------------------------------------- #
# Frontmatter parsing (shared with the knowledge validator)
# --------------------------------------------------------------------------- #

def _parse_scalar(s: str):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if s == "[]":
        return []
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [_parse_scalar(x.strip()) for x in inner.split(",")] if inner else []
    try:
        return int(s)
    except ValueError:
        return s


def parse_frontmatter_text(fm_text: str):
    result = {}
    current_key = None
    for raw in fm_text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key is not None:
            result.setdefault(current_key, []).append(_parse_scalar(stripped[2:].strip()))
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
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, "", str(exc)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, None
    close = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close = i
            break
    if close is None:
        return {}, text, None
    return parse_frontmatter_text("\n".join(lines[1:close])), "\n".join(lines[close + 1:]), None


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
# Scanning
# --------------------------------------------------------------------------- #

def collect_notes(ndir: Path):
    """Return list of (path, frontmatter) for literature notes."""
    out = []
    for md in sorted(ndir.rglob("*.md")):
        if md.name.startswith("_"):
            continue
        fm, _body, err = read_frontmatter(md)
        if fm is None:
            continue
        if fm.get("type") not in ("literature-note", None):
            continue
        out.append((md, fm))
    return out


def collect_fulltexts(fdir: Path):
    out = []
    for md in sorted(fdir.rglob("*.md")):
        fm, _body, err = read_frontmatter(md)
        if fm is None:
            continue
        if fm.get("type") != "literature-fulltext":
            continue
        out.append((md, fm))
    return out


def check_fulltext_frontmatter(fm, rel, rep):
    missing = FULLTEXT_REQUIRED_FIELDS - set(fm)
    if missing:
        rep.error(rel, f"missing fulltext frontmatter field(s): {', '.join(sorted(missing))}")
    for k in ("zotero_key", "pdf_key"):
        v = fm.get(k)
        if v and not ZOTERO_KEY_RE.match(str(v)):
            rep.error(rel, f"invalid {k} {v!r}")
    pm = fm.get("page_mapping")
    if pm and pm not in ("unknown", "reliable"):
        rep.warning(rel, f"unusual page_mapping value {pm!r}")


def check_fulltext_images(md: Path, rel, rep):
    try:
        body = md.read_text(encoding="utf-8")
    except OSError:
        return
    missing = 0
    for m in IMAGE_REF_RE.finditer(body):
        ref = m.group(1).strip()
        # Strip angle brackets and any URL query/fragment; ignore remote URLs.
        ref = ref.strip("<>")
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", ref):
            continue
        ref = ref.split("?")[0].split("#")[0]
        target = (md.parent / ref).resolve()
        if not target.exists():
            missing += 1
            rep.error(rel, f"missing image target: {ref}")
    if missing:
        rep.error(rel, f"MISSING_IMAGES={missing}")


# --------------------------------------------------------------------------- #
# Cross-validation
# --------------------------------------------------------------------------- #

def vault_rel(path: Path, vault: Path):
    try:
        return path.resolve().relative_to(vault.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_note_key(target: str):
    target = target.strip().split("#")[0].strip()
    if target.endswith(".md"):
        target = target[:-3]
    return target.strip("/")


def build_note_path_index(notes, vault: Path):
    """Map several possible note path spellings -> (path, fm)."""
    idx = {}
    for path, fm in notes:
        rel = vault_rel(path, vault)
        keys = {rel, rel[:-3] if rel.endswith(".md") else rel}
        # also keyed by just the filename stem (unique filenames convention)
        keys.add(path.stem)
        for k in keys:
            idx.setdefault(normalize_note_key(k), (path, fm))
    return idx


def main(argv=None):
    p = argparse.ArgumentParser(description="Validate ResearchVault literature links.")
    p.add_argument("--vault", required=True, help="vault root directory")
    p.add_argument("--notes", help="analytical notes dir (default: auto-detect)")
    p.add_argument("--fulltext", help="fulltext dir (default: auto-detect)")
    args = p.parse_args(argv)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"[ERROR] vault not found: {vault}")
        return 1

    ndir = resolve_dir(vault, args.notes, "Research/Papers", "02vault", "note", "论文库")
    fdir = resolve_dir(vault, args.fulltext, "Research/Fulltext", "03fulltext", "fulltext")

    rep = Reporter()
    if ndir is None:
        rep.error(vault, "notes directory not found")
        return rep.summarize()
    if fdir is None:
        rep.error(vault, "fulltext directory not found")
        return rep.summarize()

    notes = collect_notes(ndir)
    fulltexts = collect_fulltexts(fdir)
    note_idx = build_note_path_index(notes, vault)

    # Fulltext integrity.
    for md, fm in fulltexts:
        rel = vault_rel(md, vault)
        check_fulltext_frontmatter(fm, rel, rep)
        check_fulltext_images(md, rel, rep)

    # Note -> Fulltext.
    for md, fm in notes:
        rel = vault_rel(md, vault)
        fp = fm.get("fulltext_path")
        if not fp:
            continue
        target = (vault / str(fp).replace("\\", "/")).resolve()
        if not target.exists():
            rep.error(rel, f"fulltext_path points to missing file: {fp}")
            continue
        ffm, _b, _e = read_frontmatter(target)
        if ffm.get("type") != "literature-fulltext":
            rep.warning(rel, f"fulltext_path target is not a literature-fulltext: {fp}")
            continue
        nk, fk = fm.get("zotero_key"), ffm.get("zotero_key")
        if nk and fk and nk != fk:
            rep.error(rel, f"zotero_key mismatch: note={nk} fulltext={fk}")
        npk, fpk = fm.get("pdf_key"), ffm.get("pdf_key")
        if npk and fpk and npk != fpk:
            rep.error(rel, f"pdf_key mismatch: note={npk} fulltext={fpk}")

    # Fulltext -> Note.
    for md, fm in fulltexts:
        rel = vault_rel(md, vault)
        np_ = fm.get("note_path")
        if not np_:
            rep.error(rel, "fulltext missing note_path")
            continue
        key = normalize_note_key(str(np_))
        # Try progressively shorter suffixes to tolerate a leading notes-dir alias.
        hit = None
        for alias in ("Research/Papers/", "02vault/", "note/", "论文库/"):
            if key.startswith(alias.rstrip("/") + "/"):
                key = key[len(alias):]
        hit = note_idx.get(key) or note_idx.get(Path(key).stem) or note_idx.get(Path(key).name)
        if hit is None:
            rep.error(rel, f"note_path target not found: {np_}")
            continue
        npath, nfm = hit
        nk, fk = nfm.get("zotero_key"), fm.get("zotero_key")
        if nk and fk and nk != fk:
            rep.error(rel, f"zotero_key mismatch (from note {vault_rel(npath, vault)}): note={nk} fulltext={fk}")

    print(f"notes scanned: {len(notes)}, fulltexts scanned: {len(fulltexts)}")
    return rep.summarize()


if __name__ == "__main__":
    sys.exit(main())
