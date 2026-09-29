#!/usr/bin/env python3
"""Read one Zotero item, its PDF attachment, annotations and full-text cache."""
from __future__ import annotations

import argparse
import json
import os
import platform
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

from config import configured_path, load_config


def discover_data_dir() -> Path | None:
    candidates = [Path.home() / "Zotero"]
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            profiles = Path(appdata) / "Zotero" / "Zotero" / "Profiles"
            if profiles.is_dir():
                candidates.extend(path / "zotero" for path in profiles.iterdir() if path.is_dir())
    return next((p.resolve() for p in candidates if (p / "zotero.sqlite").is_file()), None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--key", help="parent Zotero item key")
    group.add_argument("--title", help="exact title; must match one item")
    parser.add_argument("--data-dir", type=Path, help="Zotero data directory; defaults to platform discovery")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    data_dir = args.data_dir.expanduser().resolve() if args.data_dir else configured_path("zotero_data_dir", config) or discover_data_dir()
    if data_dir is None or not (data_dir / "zotero.sqlite").is_file():
        print("FAIL: zotero.sqlite not found; pass --data-dir or set ZOTERO_DATA_DIR", file=sys.stderr)
        return 2
    db_uri = quote(str(data_dir / "zotero.sqlite").replace("\\", "/"), safe=":/")
    uri = f"file:{db_uri}?mode=ro"
    try:
        db = sqlite3.connect(uri, uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        db.execute("PRAGMA busy_timeout = 5000")
        item_rows = db.execute("SELECT itemID, key, itemTypeID FROM items WHERE key = ?", (args.key,)).fetchall() if args.key else db.execute(
            "SELECT i.itemID, i.key, i.itemTypeID FROM items i JOIN itemData d ON d.itemID=i.itemID JOIN fields f ON f.fieldID=d.fieldID JOIN itemDataValues v ON v.valueID=d.valueID WHERE f.fieldName='title' AND v.value=?", (args.title,)
        ).fetchall()
        if not item_rows:
            print("FAIL: no matching Zotero parent item", file=sys.stderr)
            return 1
        if len(item_rows) != 1:
            print(f"FAIL: {len(item_rows)} items matched; use --key to disambiguate", file=sys.stderr)
            return 1
        item = item_rows[0]
        item_id, key = item["itemID"], item["key"]
        values = {r["fieldName"]: r["value"] for r in db.execute("SELECT f.fieldName, v.value FROM itemData d JOIN fields f ON f.fieldID=d.fieldID JOIN itemDataValues v ON v.valueID=d.valueID WHERE d.itemID=?", (item_id,))}
        creators = []
        try:
            creator_query = "SELECT c.firstName, c.lastName FROM itemCreators ic JOIN creators c ON c.creatorID=ic.creatorID JOIN creatorTypes ct ON ct.creatorTypeID=ic.creatorTypeID WHERE ic.itemID=? AND ct.creatorType='author' ORDER BY ic.orderIndex"
            creators = [" ".join(filter(None, (r["firstName"], r["lastName"]))) for r in db.execute(creator_query, (item_id,))]
        except sqlite3.OperationalError:
            try:
                creator_query = "SELECT c.firstName, c.lastName FROM itemCreators ic JOIN creators c ON c.creatorID=ic.creatorID WHERE ic.itemID=? ORDER BY ic.orderIndex"
                creators = [" ".join(filter(None, (r["firstName"], r["lastName"]))) for r in db.execute(creator_query, (item_id,))]
            except sqlite3.OperationalError:
                creators = []
        collections = [r[0] for r in db.execute("SELECT c.collectionName FROM collectionItems ci JOIN collections c ON c.collectionID=ci.collectionID WHERE ci.itemID=?", (item_id,))]
        attachments = db.execute("SELECT a.itemID, a.key, a.path, a.contentType FROM items i JOIN itemAttachments a USING(itemID) WHERE a.parentItemID=?", (item_id,)).fetchall()
        pdfs = []
        for attachment in attachments:
            path_value = attachment["path"] or ""
            pdf_path = data_dir / "storage" / attachment["key"] / path_value.split(":", 1)[-1] if path_value.startswith("storage:") else None
            if attachment["contentType"] == "application/pdf":
                cache_dir = data_dir / "storage" / attachment["key"]
                cache = next((str(p) for p in cache_dir.glob(".zotero-ft-cache*")), None) if cache_dir.is_dir() else None
                pdfs.append({"pdf_key": attachment["key"], "pdf_path": str(pdf_path) if pdf_path and pdf_path.is_file() else None, "attachment_path_field": path_value, "fulltext_cache": cache})
        annotations = []
        try:
            annotation_columns = [r["name"] for r in db.execute("PRAGMA table_info(itemAnnotations)")]
            selected = [name for name in ("type", "authorName", "comment", "text", "pageLabel") if name in annotation_columns]
            attachment_ids = [row["itemID"] for row in attachments]
            if selected and attachment_ids:
                placeholders = ",".join("?" for _ in attachment_ids)
                annotations = [dict(r) for r in db.execute(
                    f"SELECT {', '.join(selected)} FROM itemAnnotations WHERE parentItemID IN ({placeholders})",
                    attachment_ids,
                )]
        except sqlite3.OperationalError:
            annotations = []
        notes = []
        try:
            note_columns = [r["name"] for r in db.execute("PRAGMA table_info(itemNotes)")]
            if "note" in note_columns:
                notes = [r[0] for r in db.execute("SELECT note FROM itemNotes WHERE parentItemID=?", (item_id,))]
        except sqlite3.OperationalError:
            pass
        primary_pdf = pdfs[0] if pdfs else {}
        pdf_key = primary_pdf.get("pdf_key")
        output = {
            "zotero_key": key,
            "pdf_key": pdf_key,
            "title": values.get("title"),
            "author": "; ".join(creators),
            "year": (values.get("date", "")[:4] or None),
            "doi": values.get("DOI"),
            "collection": collections,
            "annotations": annotations,
            "notes": notes,
            "pdf_path": primary_pdf.get("pdf_path"),
            "fulltext_cache": primary_pdf.get("fulltext_cache"),
            "zotero_item": f"zotero://select/library/items/{key}",
            "zotero_pdf": f"zotero://open-pdf/library/items/{pdf_key}" if pdf_key else None,
            "pdf_attachments": pdfs,
            "database_access": "read-only SQLite; no writes performed",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except sqlite3.OperationalError as exc:
        print(f"FAIL: Zotero database could not be read (it may be locked or mid-upgrade): {exc}; close Zotero or retry after sync settles", file=sys.stderr)
        return 2
    finally:
        try:
            db.close()
        except UnboundLocalError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
