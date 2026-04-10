#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate a Zotero-exported batch into the reading-note template."""

from __future__ import annotations

import argparse
import re
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

try:
    import fitz
except ImportError:  # pragma: no cover - optional dependency
    fitz = None


NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "z": "http://www.zotero.org/namespaces/export#",
    "dcterms": "http://purl.org/dc/terms/",
    "bib": "http://purl.org/net/biblio#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "link": "http://purl.org/rss/1.0/modules/link/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "prism": "http://prismstandard.org/namespaces/1.2/basic/",
}

FIELD_SQL = """
SELECT v.value
FROM itemData d
JOIN fields f ON d.fieldID = f.fieldID
JOIN itemDataValues v ON d.valueID = v.valueID
WHERE d.itemID = ? AND f.fieldName = ?
"""

INVALID_FILENAME = re.compile(r'[<>:"/\\|?*]')
TITLE_TOKEN_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+", re.IGNORECASE)
ELLIPSIS_RE = re.compile(r"(…|\.\.\.)")
ENUM_RE = re.compile(r"^[（(]?\d+[）)]")
COUNT_PATTERNS = [
    r"(\d+个(?:地级及以上城市|城市|企业|园区|样本园区|样本城市|样本|案例|科技园区|城市群|网格|专利|地区|县|区))",
    r"(\d+\s+(?:Chinese|U\.S\.|US|European|global|prefecture-level|metropolitan|urban)?[A-Za-z\-\s]*?"
    r"(?:cities|firms|regions|counties|parks|universities|grid cells|grids|patents|papers|areas|clusters))",
]
TIME_PATTERNS = [
    r"((?:19|20)\d{2}\s*[—–-]\s*(?:19|20)\d{2}年?)",
    r"((?:19|20)\d{2}年\s*[—–-]\s*(?:19|20)\d{2}年)",
    r"(from\s+(?:19|20)\d{2}\s+to\s+(?:19|20)\d{2})",
]
LIGATURE_MAP = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\xa0": " ",
    "\u2002": " ",
    "\u2003": " ",
    "\u2009": " ",
    "\u202f": " ",
    "\u3000": " ",
}

FORMULA_CORE_CHARS = "=∑βαγλμρσδ"
STANDARD_FORMULA_NOTE = "注：受限于 PDF 纯文本提取，此为标准模型公式，若需原文精准公式请提供截图进行 OCR。"
MISSING_DATA_SOURCE_NOTE = "缓存文本未包含具体数据来源，需查阅完整正文"
MISSING_METHOD_NOTE = "缓存文本未包含可直接整理的具体步骤，需查阅完整正文"
ACADEMIC_GARBAGE_PATTERNS = [
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    r"\b\d{6}\b",
    r"(基金项目|基金资助|国家自然科学基金|项目编号|Grant\s*No\.?|资助项目)[^。；;]{0,120}",
    r"(作者简介|作者单位|通讯作者|通讯地址|收稿日期|修回日期|投稿须知|稿件内容应符合|责任编辑)[^。；;]{0,120}",
    r"(?:大学|University)[^。；;]{0,30}(?:学院|School|College|Department|研究院|研究所|Institute|Laboratory|实验室)",
    r"(?:学院|School|College|Department|研究院|研究所|Institute|Laboratory|实验室)[^。；;]{0,30}(?:大学|University)",
]


@dataclass
class ExportPaper:
    title: str
    year: str
    url: str
    abstract: str
    authors: List[str]
    tags: List[str]
    attachment_relpath: str
    journal: str
    volume: str
    issue: str
    pages: str


@dataclass
class Attachment:
    key: str
    path: str


@dataclass
class ZoteroItem:
    key: str
    title: str
    date: str
    publication_title: str
    doi: str
    url: str
    abstract: str
    volume: str
    issue: str
    pages: str
    creators: List[str]
    tags: List[str]
    attachments: List[Attachment]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-root", default=r"D:\research\zotero_batch")
    parser.add_argument("--vault-root", default=r"D:\ResearchVault\note")
    parser.add_argument("--folder", default="创新经济地理")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def normalize_text(text: str) -> str:
    value = str(text or "")
    for src, dst in LIGATURE_MAP.items():
        value = value.replace(src, dst)
    value = value.replace("－", "-").replace("–", "—")
    return re.sub(r"\s+", " ", value).strip()


def canonical_title(text: str) -> str:
    value = normalize_text(text).lower()
    value = value.replace("“", "").replace("”", "").replace('"', "")
    value = value.replace("‘", "").replace("’", "").replace("'", "")
    return TITLE_TOKEN_RE.sub("", value)


def split_sentences(text: str) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []
    raw_parts = re.split(r"(?<=[。！？；.!?;])\s*", text)
    parts: List[str] = []
    for part in raw_parts:
        cleaned = clean_candidate(part)
        if cleaned:
            parts.append(cleaned)
    return parts


def clean_candidate(text: str) -> str:
    cleaned = normalize_text(text)
    cleaned = re.sub(r"^(摘要|ABSTRACT|Abstract)[:：]\s*", "", cleaned)
    return cleaned.strip(" ;；")


def is_truncated(text: str) -> bool:
    candidate = clean_candidate(text)
    if not candidate:
        return True
    return bool(ELLIPSIS_RE.search(candidate))


def year_only(text: str) -> str:
    match = re.search(r"(19|20)\d{2}", text or "")
    return match.group(0) if match else ""


def yaml_quote(text: str) -> str:
    return "'" + (text or "").replace("'", "''") + "'"


def safe_filename(title: str, key: str) -> str:
    cleaned = INVALID_FILENAME.sub("", title).strip().rstrip(".")
    cleaned = cleaned.replace("“", "").replace("”", "").replace('"', "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if len(cleaned) > 120:
        cleaned = f"{cleaned[:100].rstrip()}_{key}"
    return cleaned + ".md"


def unique_preserve_order(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    for value in values:
        cleaned = normalize_text(value)
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out


def select_batch_dir(root: Path, folder_name: str) -> Path:
    target = root / folder_name
    if not target.is_dir():
        raise FileNotFoundError(f"Batch folder not found: {target}")
    return target


def locate_zotero_data_dir() -> Path:
    parent = Path(r"D:\Program Files (x86)\Zotero")
    for child in parent.iterdir():
        if child.is_dir() and ((child / "zotero.sqlite.bak").exists() or (child / "zotero.sqlite").exists()):
            return child
    raise FileNotFoundError("Could not locate Zotero data directory")


def open_db(data_dir: Path) -> sqlite3.Connection:
    for name in ["zotero.sqlite.bak", "zotero.sqlite"]:
        db = data_dir / name
        if db.exists():
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            con.execute("SELECT 1").fetchone()
            return con
    raise FileNotFoundError("Could not open Zotero database")


def parse_rdf(path: Path) -> List[ExportPaper]:
    root = ET.parse(path).getroot()
    journal_map: dict[str, dict[str, str]] = {}
    attachment_map: dict[str, str] = {}
    papers: List[ExportPaper] = []

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[1] if "}" in tag else tag

    for child in root:
        tag = local(child.tag)
        about = child.attrib.get(f"{{{NS['rdf']}}}about", "")
        if tag == "Journal":
            journal_map[about] = {
                "title": normalize_text(child.findtext("dc:title", default="", namespaces=NS)),
                "volume": normalize_text(child.findtext("prism:volume", default="", namespaces=NS)),
                "issue": normalize_text(child.findtext("prism:number", default="", namespaces=NS)),
            }
        elif tag == "Attachment":
            node = child.find("z:path", NS)
            if node is not None:
                attachment_map[about] = node.attrib.get(f"{{{NS['rdf']}}}resource", "")

    for child in root:
        tag = local(child.tag)
        if tag in {"Journal", "Attachment"}:
            continue
        if normalize_text(child.findtext("z:itemType", default="", namespaces=NS)) != "journalArticle":
            continue

        title = normalize_text(child.findtext("dc:title", default="", namespaces=NS))
        if not title:
            continue

        authors: List[str] = []
        for person in child.findall("bib:authors/rdf:Seq/rdf:li/foaf:Person", NS):
            surname = normalize_text(person.findtext("foaf:surname", default="", namespaces=NS))
            given = normalize_text(person.findtext("foaf:givenName", default="", namespaces=NS))
            authors.append(normalize_text(f"{given} {surname}".strip()) if given else surname)

        tags: List[str] = []
        for subject in child.findall("dc:subject", NS):
            value = normalize_text(subject.text or "")
            auto = subject.find("z:AutomaticTag/rdf:value", NS)
            if not value and auto is not None and auto.text:
                value = normalize_text(auto.text)
            if value:
                tags.append(value)

        ref = child.find("dcterms:isPartOf", NS)
        journal = journal_map.get(ref.attrib.get(f"{{{NS['rdf']}}}resource", "") if ref is not None else "", {})
        link = child.find("link:link", NS)
        rel = attachment_map.get(link.attrib.get(f"{{{NS['rdf']}}}resource", ""), "") if link is not None else ""

        papers.append(
            ExportPaper(
                title=title,
                year=normalize_text(child.findtext("dc:date", default="", namespaces=NS)),
                url=normalize_text(child.findtext("dc:identifier/dcterms:URI/rdf:value", default="", namespaces=NS))
                or normalize_text(child.attrib.get(f"{{{NS['rdf']}}}about", "")),
                abstract=normalize_text(child.findtext("dcterms:abstract", default="", namespaces=NS)),
                authors=authors,
                tags=tags,
                attachment_relpath=rel,
                journal=journal.get("title", ""),
                volume=journal.get("volume", ""),
                issue=journal.get("issue", ""),
                pages=normalize_text(child.findtext("bib:pages", default="", namespaces=NS)),
            )
        )
    return papers


def get_field(cur: sqlite3.Cursor, item_id: int, field_name: str) -> str:
    row = cur.execute(FIELD_SQL, (item_id, field_name)).fetchone()
    return normalize_text(str(row[0])) if row and row[0] is not None else ""


def title_variants(title: str) -> List[str]:
    variants = [normalize_text(title)]
    stripped = variants[0].replace("“", "").replace("”", "").replace('"', "")
    variants.append(stripped)
    if ":" in stripped:
        variants.append(stripped.split(":", 1)[0])
    if "：" in stripped:
        variants.append(stripped.split("：", 1)[0])
    return unique_preserve_order([value for value in variants if value])


def load_item_by_title(cur: sqlite3.Cursor, title: str) -> Optional[ZoteroItem]:
    candidates: List[tuple[int, str, str]] = []
    for variant in title_variants(title):
        exact_rows = cur.execute(
            """
            SELECT i.itemID, i.key, v.value
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            JOIN itemData d ON i.itemID = d.itemID
            JOIN fields f ON d.fieldID = f.fieldID
            JOIN itemDataValues v ON d.valueID = v.valueID
            WHERE it.typeName = 'journalArticle'
              AND f.fieldName = 'title'
              AND v.value = ?
            ORDER BY i.dateModified DESC
            """,
            (variant,),
        ).fetchall()
        candidates.extend(exact_rows)
        if exact_rows:
            break

        like_rows = cur.execute(
            """
            SELECT i.itemID, i.key, v.value
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            JOIN itemData d ON i.itemID = d.itemID
            JOIN fields f ON d.fieldID = f.fieldID
            JOIN itemDataValues v ON d.valueID = v.valueID
            WHERE it.typeName = 'journalArticle'
              AND f.fieldName = 'title'
              AND v.value LIKE ?
            ORDER BY i.dateModified DESC
            """,
            (f"%{variant[:32]}%",),
        ).fetchall()
        candidates.extend(like_rows)
        if like_rows:
            break

    if not candidates:
        title_key = canonical_title(title)
        rows = cur.execute(
            """
            SELECT i.itemID, i.key, v.value
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            JOIN itemData d ON i.itemID = d.itemID
            JOIN fields f ON d.fieldID = f.fieldID
            JOIN itemDataValues v ON d.valueID = v.valueID
            WHERE it.typeName = 'journalArticle'
              AND f.fieldName = 'title'
            ORDER BY i.dateModified DESC
            """
        ).fetchall()
        for row in rows:
            if canonical_title(str(row[2])) == title_key:
                candidates.append(row)
                break
        if not candidates:
            for row in rows:
                row_key = canonical_title(str(row[2]))
                if title_key and (title_key in row_key or row_key in title_key):
                    candidates.append(row)
                    break

    if not candidates:
        return None

    title_key = canonical_title(title)
    item_id, key, found_title = min(
        candidates,
        key=lambda row: (
            0 if canonical_title(str(row[2])) == title_key else 1,
            abs(len(canonical_title(str(row[2]))) - len(title_key)),
            abs(len(normalize_text(str(row[2]))) - len(normalize_text(title))),
        ),
    )

    creators: List[str] = []
    for first, last in cur.execute(
        """
        SELECT c.firstName, c.lastName
        FROM itemCreators ic
        JOIN creators c ON ic.creatorID = c.creatorID
        WHERE ic.itemID = ?
        ORDER BY ic.orderIndex
        """,
        (item_id,),
    ).fetchall():
        first_s = normalize_text(str(first or ""))
        last_s = normalize_text(str(last or ""))
        creators.append(normalize_text(f"{first_s} {last_s}".strip()) if first_s else last_s)

    tags = [
        normalize_text(str(row[0]))
        for row in cur.execute(
            """
            SELECT t.name
            FROM itemTags it
            JOIN tags t ON it.tagID = t.tagID
            WHERE it.itemID = ?
            ORDER BY t.name
            """,
            (item_id,),
        ).fetchall()
        if normalize_text(str(row[0]))
    ]

    attachments: List[Attachment] = []
    for _, a_key, a_path in cur.execute(
        """
        SELECT i2.itemID, i2.key, ia.path
        FROM itemAttachments ia
        JOIN items i2 ON ia.itemID = i2.itemID
        WHERE ia.parentItemID = ?
        ORDER BY i2.itemID
        """,
        (item_id,),
    ).fetchall():
        attachments.append(Attachment(key=str(a_key), path=str(a_path or "")))

    return ZoteroItem(
        key=str(key),
        title=normalize_text(str(found_title)),
        date=get_field(cur, item_id, "date"),
        publication_title=get_field(cur, item_id, "publicationTitle"),
        doi=get_field(cur, item_id, "DOI"),
        url=get_field(cur, item_id, "url"),
        abstract=get_field(cur, item_id, "abstractNote"),
        volume=get_field(cur, item_id, "volume"),
        issue=get_field(cur, item_id, "issue"),
        pages=get_field(cur, item_id, "pages"),
        creators=creators,
        tags=tags,
        attachments=attachments,
    )


def choose_attachment(item: ZoteroItem, expected_relpath: str) -> Optional[Attachment]:
    expected_name = Path(expected_relpath).name if expected_relpath else ""
    for attachment in item.attachments:
        actual_name = Path(attachment.path.replace("storage:", "")).name
        if expected_name and actual_name == expected_name:
            return attachment
    for attachment in item.attachments:
        if "pdf" in attachment.path.lower():
            return attachment
    return item.attachments[0] if item.attachments else None


def load_fulltext(data_dir: Path, attachment: Attachment) -> str:
    ft_cache = data_dir / "storage" / attachment.key / ".zotero-ft-cache"
    if not ft_cache.exists():
        return ""
    return normalize_text(ft_cache.read_text(encoding="utf-8", errors="ignore"))


def find_abstract_text(item_abstract: str, fulltext: str) -> str:
    item_abstract = normalize_text(item_abstract)
    if item_abstract:
        return item_abstract
    fulltext = normalize_text(fulltext)
    if not fulltext:
        return ""

    for start_marker, end_markers in [
        ("摘要:", ["关键词", "引言", "1 "]),
        ("摘要", ["关键词", "引言", "1 "]),
        ("ABSTRACT", ["KEYWORDS", "INTRODUCTION", "1. "]),
        ("Abstract", ["Keywords", "Introduction", "1. "]),
    ]:
        start = fulltext.find(start_marker)
        if start < 0:
            continue
        body = fulltext[start + len(start_marker) :]
        end = len(body)
        for marker in end_markers:
            marker_index = body.find(marker)
            if marker_index >= 0:
                end = min(end, marker_index)
        candidate = clean_candidate(body[:end])
        if candidate and not is_truncated(candidate):
            return candidate
    return ""


def first_complete_sentence(sentences: Sequence[str]) -> str:
    for sentence in sentences:
        if not is_truncated(sentence):
            return clean_candidate(sentence)
    return clean_candidate(sentences[0]) if sentences else ""


def sentence_with_keywords(sentences_groups: Sequence[Sequence[str]], keywords: Iterable[str]) -> str:
    keys = [keyword.lower() for keyword in keywords]
    for sentences in sentences_groups:
        for sentence in sentences:
            candidate = clean_candidate(sentence)
            if not candidate or is_truncated(candidate):
                continue
            lower = candidate.lower()
            if any(keyword in candidate or keyword in lower for keyword in keys):
                return candidate
    return ""


def contains_academic_garbage(text: str) -> bool:
    value = normalize_text(text)
    if not value:
        return False
    if any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in ACADEMIC_GARBAGE_PATTERNS):
        return True
    if has_citation_noise(value):
        return True
    if re.search(r"(?:[\u4e00-\u9fff]{2,4}[,，、]){1,5}[\u4e00-\u9fff]{2,4}", value) and any(
        token in value for token in ["摘要", "大学", "学院", "研究院", "通讯", "作者"]
    ):
        return True
    return False


def sanitize_analysis_text(text: str) -> str:
    value = normalize_text(text)
    if not value:
        return ""

    value = re.sub(r"^\d+\s*", "", value)
    value = re.sub(r"^(摘要|ABSTRACT|Abstract)[:：]\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"[（(][^()（）]{0,120}(?:学院|School|College|Department|研究院|研究所|Institute|Laboratory|实验室|邮编|邮政编码|E-mail|email|@)[^()（）]{0,120}[)）]", "", value)
    value = re.sub(r"(基金项目|基金资助|国家自然科学基金|项目编号|Grant\s*No\.?|资助项目)[^。；;]{0,120}", "", value, flags=re.IGNORECASE)
    value = re.sub(r"(作者简介|作者单位|通讯作者|通讯地址|收稿日期|修回日期|投稿须知|稿件内容应符合|责任编辑)[^。；;]{0,120}", "", value)
    value = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "", value)
    value = re.sub(r"\b\d{6}\b", "", value)
    value = re.sub(r"^(?:[\u4e00-\u9fff]{2,4}[,，、]){1,5}[\u4e00-\u9fff]{2,4}\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ，。；;:：,")


def has_required_keyword(text: str, keywords: Iterable[str]) -> bool:
    candidate = normalize_text(text).lower()
    if not candidate:
        return False
    for keyword in keywords:
        lowered = keyword.lower()
        if keyword in text or lowered in candidate:
            return True
    return False


def has_citation_noise(text: str) -> bool:
    value = normalize_text(text)
    if not value:
        return False
    if re.search(r"\[[0-9,\-\s]+\]", value):
        return True
    if re.search(r"(?:等|et al\.?)\s*\[[0-9,\-\s]+\]", value, flags=re.IGNORECASE):
        return True
    return False


def title_focus_conflicts(title: str, text: str) -> bool:
    normalized_title = normalize_text(title)
    candidate = normalize_text(text)
    focus_checks = [
        ("南京", "南京"),
        ("波士顿肯德尔广场", "肯德尔广场"),
        ("粤港澳大湾区", "粤港澳大湾区"),
        ("长三角", "长三角"),
    ]
    for title_token, required_token in focus_checks:
        if title_token in normalized_title and required_token not in candidate:
            return True
    return False


def sentence_with_keywords_clean(
    sentences_groups: Sequence[Sequence[str]],
    keywords: Iterable[str],
) -> str:
    for sentences in sentences_groups:
        for sentence in sentences:
            original = clean_candidate(sentence)
            if not original or is_truncated(original):
                continue
            cleaned = sanitize_analysis_text(original)
            if not cleaned or is_truncated(cleaned):
                continue
            if contains_academic_garbage(cleaned):
                continue
            if not has_required_keyword(cleaned, keywords):
                continue
            return cleaned
    return ""


def clean_sample_phrase(text: str, title: str = "") -> str:
    cleaned = sanitize_analysis_text(text)
    if not cleaned or contains_academic_garbage(cleaned):
        return ""
    if title and title_focus_conflicts(title, cleaned):
        return ""
    return cleaned


def extract_concise_match(texts: Sequence[str], patterns: Sequence[str], max_len: int = 80) -> str:
    for text in texts:
        cleaned = sanitize_analysis_text(text)
        if not cleaned or contains_academic_garbage(cleaned):
            continue
        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if not match:
                continue
            phrase = sanitize_analysis_text(match.group(1))
            if phrase and len(phrase) <= max_len and not contains_academic_garbage(phrase):
                return phrase
    return ""


def extract_data_source_phrase(texts: Sequence[str]) -> str:
    patterns = [
        r"((?:基于|利用|使用|采用)[^。；]{0,60}?(?:面板数据|专利数据|统计数据|调查数据|问卷数据|遥感数据|影像数据|数据库|数据集|样本数据))",
        r"([^。；]{2,50}?(?:面板数据|专利数据|统计数据|调查数据|问卷数据|遥感数据|影像数据|数据库|数据集))",
        r"((?:panel data set|panel data|patent data|survey data|remote sensing data|grid data|database)[^.;]{0,60})",
        r"((?:\d+\s+Chinese cities[^.;]{0,40}))",
    ]
    phrase = extract_concise_match(texts, patterns, max_len=90)
    if "表 1" in phrase or "figure" in phrase.lower():
        return ""
    return phrase


def extract_method_phrase(texts: Sequence[str]) -> str:
    patterns = [
        r"((?:采用|利用|使用|构建|运用|基于)[^。；]{0,60}?(?:模型|方法|分析|回归|识别策略|指标体系|工具变量|固定效应|GIS|空间杜宾))",
        r"((?:using|employing|based on)[^.;]{0,70}?(?:approach|model|analysis|regression|framework))",
        r"((?:instrumental variables approach|fixed effects model|spatial durbin model|difference-in-differences)[^.;]{0,30})",
    ]
    return extract_concise_match(texts, patterns, max_len=90)


def extract_sample_source_phrase(texts: Sequence[str], title: str) -> str:
    patterns = [
        r"((?:以|选取)[^。；，]{2,40}?为(?:研究对象|研究样本|样本|案例))",
        r"((?:\d+个)?[^。；，]{2,40}?(?:城市|企业|园区|样本|案例|地区|县|区))",
        r"((?:\d+\s+Chinese cities[^.;]{0,50}))",
        r"((?:sample of[^.;]{0,60}|case study of[^.;]{0,60}|panel data set[^.;]{0,60}))",
    ]
    phrase = extract_concise_match(texts, patterns, max_len=90)
    if phrase and not title_focus_conflicts(title, phrase):
        return phrase
    return ""


def strip_finding_prefix(text: str) -> str:
    cleaned = clean_candidate(text)
    patterns = [
        r"^(研究发现|结果表明|结果显示|本文发现|实证结果表明)[:：]\s*",
        r"^(Our findings show that|We find that|Results show that|The results show that|This study reveals that)\s*",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned


def extract_findings(sentences: Sequence[str]) -> List[str]:
    findings: List[str] = []
    in_result_block = False
    for sentence in sentences:
        candidate = clean_candidate(sentence)
        if not candidate or is_truncated(candidate):
            continue
        lower = candidate.lower()
        if any(token in candidate for token in ["研究发现", "结果表明", "结果显示", "本文发现", "实证结果表明"]) or any(
            token in lower for token in ["we find", "find that", "our findings show", "results show", "reveal", "reveals", "suggests", "indicate", "negative causal relationship", "positive causal relationship"]
        ):
            findings.append(strip_finding_prefix(candidate))
            in_result_block = True
            continue
        if in_result_block and ENUM_RE.match(candidate):
            findings.append(candidate)
            continue
        in_result_block = False

    if findings:
        return unique_preserve_order(findings)[:3]

    fallbacks = [clean_candidate(sentence) for sentence in sentences if clean_candidate(sentence) and not is_truncated(sentence)]
    return unique_preserve_order(fallbacks[:2])


def extract_pattern(texts: Sequence[str], patterns: Sequence[str]) -> str:
    for text in texts:
        candidate = clean_candidate(text)
        if not candidate or is_truncated(candidate):
            continue
        for pattern in patterns:
            match = re.search(pattern, candidate, flags=re.IGNORECASE)
            if match:
                return normalize_text(match.group(1))
    return ""


def extract_sample_phrase(sentences_groups: Sequence[Sequence[str]]) -> str:
    cn_patterns = [
        r"(以[^。；，]{4,100}?为研究(?:对象|样本|案例))",
        r"(选取[^。；，]{4,100}?为研究(?:对象|样本|案例))",
        r"(以[^。；，]{4,100}?为样本)",
        r"(基于[^。；，]{4,100}?(?:样本|数据))",
    ]
    en_patterns = [
        r"(\d+\s+(?:Chinese|U\.S\.|US|European|global|prefecture-level|metropolitan|urban)?[A-Za-z\-\s]*?"
        r"(?:cities|firms|regions|counties|parks|universities|grid cells|grids|patents|areas|clusters)"
        r"[^.;]{0,80}?(?:from\s+(?:19|20)\d{2}\s+to\s+(?:19|20)\d{2})?)",
        r"(panel data set[^.;]{0,140})",
        r"(sample of[^.;]{0,140})",
        r"(case study of[^.;]{0,140})",
    ]
    flat_sentences = [sentence for group in sentences_groups for sentence in group]
    phrase = extract_pattern(flat_sentences, cn_patterns)
    if phrase:
        return phrase
    return extract_pattern(flat_sentences, en_patterns)


def extract_time_range(texts: Sequence[str], fallback_year: str) -> str:
    value = extract_pattern(texts, TIME_PATTERNS)
    if not value:
        return fallback_year
    value = value.replace("from ", "").replace(" to ", "-")
    value = re.sub(r"\s+", "", value)
    return value


def extract_sample_size(texts: Sequence[str]) -> str:
    value = extract_pattern(texts, COUNT_PATTERNS)
    return value or "摘要或正文未明确给出统一样本量表述"


def detect_method_types(text: str) -> List[str]:
    text_lower = normalize_text(text).lower()
    mapping = [
        ("工具变量", ["instrumental variable", "iv ", "工具变量"]),
        ("面板计量", ["panel", "面板"]),
        ("空间计量", ["spatial", "空间计量", "空间杜宾"]),
        ("网络分析", ["network", "创新网络", "合作网络"]),
        ("问卷调查", ["survey", "问卷"]),
        ("文本分析", ["nlp", "文本", "text analysis"]),
        ("案例研究", ["case study", "案例", "为例"]),
        ("指标测度", ["measure", "测度", "构建", "指数", "评价"]),
        ("综述研究", ["review", "述评", "展望", "special issue"]),
    ]
    found: List[str] = []
    for label, keywords in mapping:
        if any(keyword in text_lower or keyword in text for keyword in keywords):
            found.append(label)
    return found or ["实证研究"]


def infer_data_types(text: str) -> str:
    text_lower = normalize_text(text).lower()
    mapping = [
        ("面板数据", ["panel", "面板"]),
        ("专利数据", ["patent", "专利"]),
        ("空间/遥感数据", ["grid", "landscan", "建筑", "building", "空间", "gis", "遥感"]),
        ("问卷数据", ["survey", "问卷"]),
        ("访谈资料", ["interview", "访谈"]),
        ("网络关系数据", ["network", "联系", "网络"]),
        ("政策文本", ["policy", "政策", "official documents", "文本"]),
        ("案例资料", ["case study", "案例"]),
    ]
    found = [label for label, keywords in mapping if any(keyword in text_lower or keyword in text for keyword in keywords)]
    return "、".join(found[:4]) if found else "论文摘要与正文所述数据"


def guess_analysis_unit(title: str, sample_phrase: str, data_sentence: str, method_sentence: str) -> str:
    text = " ".join([title, sample_phrase, data_sentence, method_sentence]).lower()
    mapping = [
        ("专利/技术类别层面", ["patent", "专利", "ipc"]),
        ("园区层面", ["园区", "park"]),
        ("网格单元层面", ["grid", "网格"]),
        ("企业层面", ["firm", "企业"]),
        ("城市层面", ["city", "cities", "城市"]),
        ("区域层面", ["region", "regions", "区域", "城市群", "metropolitan", "cluster"]),
    ]
    for label, keywords in mapping:
        if any(keyword in text for keyword in keywords):
            return label
    return "摘要与正文所述分析层面"


def clean_tags(tags: Iterable[str], folder_tag: str) -> List[str]:
    out: List[str] = []
    for value in [folder_tag, *tags]:
        cleaned = normalize_text(value).strip("/#")
        if not cleaned or cleaned.lower() in {"done", "reading", "unread"}:
            continue
        if cleaned not in out:
            out.append(cleaned)
    return out


def build_method_rationale(method_types: Sequence[str]) -> str:
    reasons: List[str] = []
    if "工具变量" in method_types:
        reasons.append("缓解内生性问题并更接近因果识别")
    if "面板计量" in method_types:
        reasons.append("利用个体与时间维度的变化")
    if "空间计量" in method_types:
        reasons.append("刻画空间结构与空间溢出")
    if "网络分析" in method_types:
        reasons.append("识别关系结构与节点连接差异")
    if "案例研究" in method_types:
        reasons.append("深入解释具体空间与规划机制")
    if not reasons:
        return "这种方法有助于把研究对象、变量关系和经验发现放进同一个分析框架里。"
    return "这种方法主要用于" + "、".join(reasons) + "。"


def build_summary(study_phrase: str, method_sentence: str, findings: Sequence[str], fallback: str) -> str:
    parts: List[str] = []
    if study_phrase:
        parts.append(study_phrase)
    if method_sentence and method_sentence not in parts:
        parts.append(method_sentence)
    if findings:
        lead = strip_finding_prefix(findings[0])
        if lead and lead not in parts:
            parts.append(lead)
    summary = "；".join(parts[:3])
    return summary or fallback


def clean_alias(title: str) -> str:
    alias = re.split(r"[:：]", title, maxsplit=1)[0].strip()
    alias = alias.replace("“", "").replace("”", "").replace('"', "")
    return alias or title


def guess_study_object_from_title(title: str) -> str:
    normalized = normalize_text(title)
    patterns = [
        r"以([^，。；:：]{2,40})为例",
        r"(粤港澳大湾区)",
        r"(长三角(?:城市群)?)",
        r"(\d+个中国城市)",
        r"(中国城市)",
        r"(Chinese cities)",
        r"(中国高校搬迁样本)",
        r"(波士顿肯德尔广场)",
        r"(南京市)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return sanitize_analysis_text(match.group(1))
    return sanitize_analysis_text(clean_alias(title))


def normalize_formula_block(text: str) -> str:
    parts = []
    for raw_line in str(text or "").splitlines():
        normalized = normalize_text(raw_line)
        if not normalized:
            continue
        printable = "".join(ch for ch in normalized if ch.isprintable())
        if printable:
            parts.append(printable)
    parts = [part for part in parts if not re.fullmatch(r"[（(]?\d+[）)]", part)]
    return " ".join(parts).strip()


def is_formula_block(text: str) -> bool:
    candidate = normalize_formula_block(text)
    if not candidate or len(candidate) > 220:
        return False
    if not any(char in candidate for char in FORMULA_CORE_CHARS):
        return False
    lower = candidate.lower()
    if "r2 =" in lower or lower.startswith("by about ") or "% (=" in lower:
        return False
    if "=" in candidate:
        lhs = candidate.split("=", 1)[0].strip()
        if "%" in lhs:
            return False
        if len(lhs.split()) > 8 and "ln(" not in lower and "poly" not in lower and "innov" not in lower and "hhi" not in lower:
            return False
    return True


def is_formula_continuation(text: str) -> bool:
    candidate = normalize_formula_block(text)
    if not candidate or len(candidate) > 120 or candidate.endswith("."):
        return False
    if any(char in candidate for char in FORMULA_CORE_CHARS):
        return True
    if re.search(r"\bln\s*\(", candidate, flags=re.IGNORECASE):
        return True
    return bool(re.search(r"[()/^]", candidate) and re.search(r"\d|[A-Za-z]", candidate))


def formula_score(text: str) -> int:
    candidate = normalize_formula_block(text)
    lower = candidate.lower()
    score = 0
    if "=" in candidate:
        score += 6
    if "∑" in candidate:
        score += 4
    if any(char in candidate for char in "βαγλμρσδ"):
        score += 3
    if re.search(r"\bln\s*\(", candidate, flags=re.IGNORECASE):
        score += 2
    if re.search(r"[A-Za-z]+_[A-Za-z0-9]", candidate) or "," in candidate:
        score += 1
    if lower.startswith("by about ") or "% (=" in lower or "r2 =" in lower:
        score -= 6
    if len(candidate.split()) > 20:
        score -= 3
    if candidate.strip().endswith("=") or candidate in {"= =", "− =", "- =", "= ＝"}:
        score -= 10
    if "=" in candidate:
        rhs = candidate.split("=", 1)[1].strip()
        compact_rhs = re.sub(r"[^0-9A-Za-z\u4e00-\u9fffβαγλμρσδ∑]+", "", rhs)
        if len(compact_rhs) < 2:
            score -= 10
    return score


def describe_formula(formula: str) -> tuple[str, str, str]:
    lower = formula.lower()
    if any(token in lower for token in ["innov", "patent", "emission", "productivity", "ln(", "pm", "co2", "gdp"]):
        return (
            "用于估计核心结果变量与关键解释变量关系的基准模型。",
            "左侧通常是创新、绩效、排放或增长等结果变量，右侧是核心解释变量、控制变量与固定效应。",
            "对应方法中的基准回归或主方程设定。",
        )
    if any(token in lower for token in ["poly", "hhi", "moran", "relatedness", "similarity", "index", "share"]):
        return (
            "用于构造论文中的核心结构指标或空间测度指标。",
            "公式左侧是待构造指标，右侧是加权项、份额项或空间结构项。",
            "对应方法中的指标构造步骤。",
        )
    if "∑" in formula:
        return (
            "用于把多个观测值加权汇总为综合指标。",
            "求和项表示不同城市、区域或对象对综合指标的贡献。",
            "对应方法中的加权聚合步骤。",
        )
    return (
        "用于表示论文中的核心公式或计量设定。",
        "左侧是被解释对象或待构造指标，右侧是解释变量、参数或权重结构。",
        "对应方法中的关键模型设定。",
    )


def looks_garbled_formula(text: str) -> bool:
    candidate = normalize_formula_block(text)
    if not candidate:
        return True

    lower = candidate.lower()
    chinese_char_count = len(re.findall(r"[\u4e00-\u9fff]", candidate))
    operator_count = sum(candidate.count(op) for op in "=+−-*/^_\\")
    compact_letters = re.sub(r"[^A-Za-z]", "", candidate)

    if re.search(r"(?:^|\s)ic\s*\\?sum", lower) or re.search(r"\\sum\s*$", lower):
        return True
    if re.fullmatch(r"\\sum", candidate.strip()):
        return True
    if re.fullmatch(r"[A-Za-z]{1,3}(?:\s+[A-Za-z]{1,3}){0,2}", candidate.strip()) and len(compact_letters) <= 6:
        return True
    if any(token in candidate for token in ["式中", "其中", "公式", "模型", "变量", "评价网格单元", "通过变异系数法"]):
        return True
    if chinese_char_count >= 8:
        return True
    if operator_count == 0 and "∑" not in candidate and not re.search(r"\bln\s*\(", candidate, flags=re.IGNORECASE):
        return True
    if len(candidate.split()) > 28 and chinese_char_count > 0:
        return True
    return False


def sanitize_formula_entries(entries: Sequence[dict[str, object]], max_items: int = 2) -> List[dict[str, object]]:
    cleaned: List[dict[str, object]] = []
    seen: set[str] = set()
    for entry in entries:
        formula = normalize_formula_block(str(entry.get("formula", "")))
        if looks_garbled_formula(formula):
            continue
        key = re.sub(r"\s+", "", formula)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(
            {
                **entry,
                "formula": formula,
            }
        )
        if len(cleaned) >= max_items:
            break
    return cleaned


def detect_standard_formula(text: str) -> Optional[dict[str, object]]:
    lower = normalize_text(text).lower()
    original = normalize_text(text)
    specs = [
        {
            "name": "空间杜宾模型",
            "patterns": [r"\bspatial durbin\b", r"\bsdm\b"],
            "cn_patterns": ["空间杜宾", "空间杜宾模型"],
            "formula": r"Y_{it} = \rho W Y_{it} + \beta X_{it} + \theta W X_{it} + \mu_i + \lambda_t + \varepsilon_{it}",
            "description": "用于估计空间溢出与本地效应的空间杜宾模型。",
            "symbol_text": "左侧是结果变量，$WY_{it}$ 表示空间滞后项，$X_{it}$ 与 $WX_{it}$ 分别表示本地解释变量与空间滞后解释变量。",
            "step_text": "对应方法中的主回归设定，用于同时识别本地效应与邻近地区溢出效应。",
        },
        {
            "name": "双重差分模型",
            "patterns": [r"\bdid\b", r"difference[\s-]*in[\s-]*differences?"],
            "cn_patterns": ["双重差分"],
            "formula": r"Y_{it} = \alpha + \beta (\mathrm{Treat}_i \times \mathrm{Post}_t) + \gamma X_{it} + \mu_i + \lambda_t + \varepsilon_{it}",
            "description": "用于识别处理组与对照组在政策前后差异变化的双重差分模型。",
            "symbol_text": "$\\mathrm{Treat}_i \\times \\mathrm{Post}_t$ 是核心处理效应项，$X_{it}$ 是控制变量，$\\mu_i$ 与 $\\lambda_t$ 分别表示个体和时间固定效应。",
            "step_text": "对应方法中的因果识别主方程，用于估计政策或冲击的净效应。",
        },
        {
            "name": "工具变量模型",
            "patterns": [r"\biv\b", r"\b2sls\b", r"instrumental variable", r"two-stage least squares"],
            "cn_patterns": ["工具变量", "两阶段最小二乘"],
            "formula": r"Y_{it} = \alpha + \beta \hat{X}_{it} + \gamma Z_{it} + \mu_i + \lambda_t + \varepsilon_{it}",
            "description": "用于缓解内生性问题的工具变量回归模型。",
            "symbol_text": "$\\hat{X}_{it}$ 表示由工具变量预测得到的核心解释变量，$Z_{it}$ 表示其他控制变量，$\\mu_i$ 与 $\\lambda_t$ 表示固定效应。",
            "step_text": "对应方法中的第二阶段回归设定，用于识别更接近因果关系的估计结果。",
        },
        {
            "name": "固定效应模型",
            "patterns": [r"fixed effects?", r"two-way fixed effects?", r"panel regression"],
            "cn_patterns": ["固定效应", "双向固定效应", "面板回归"],
            "formula": r"Y_{it} = \alpha + \beta X_{it} + \gamma Z_{it} + \mu_i + \lambda_t + \varepsilon_{it}",
            "description": "用于控制个体异质性与时间冲击的固定效应模型。",
            "symbol_text": "$Y_{it}$ 是结果变量，$X_{it}$ 是核心解释变量，$Z_{it}$ 是控制变量，$\\mu_i$ 与 $\\lambda_t$ 分别表示个体和时间固定效应。",
            "step_text": "对应方法中的基准回归设定，用于估计核心变量与结果变量之间的稳健关系。",
        },
    ]

    for spec in specs:
        if any(re.search(pattern, lower) for pattern in spec["patterns"]) or any(pattern in original for pattern in spec["cn_patterns"]):
            return {
                "page": None,
                "formula": spec["formula"],
                "description": spec["description"],
                "symbol_text": spec["symbol_text"],
                "step_text": spec["step_text"],
                "note": STANDARD_FORMULA_NOTE,
                "source": "standard",
                "model_name": spec["name"],
            }
    return None


def extract_formula_entries(pdf_path: Path, max_items: int = 2) -> List[dict[str, object]]:
    if fitz is None or not pdf_path.exists():
        return []

    doc = fitz.open(pdf_path)
    candidates: List[tuple[int, int, str]] = []
    try:
        for page_no in range(min(15, doc.page_count)):
            blocks = sorted(doc.load_page(page_no).get_text("blocks"), key=lambda block: (round(block[1], 1), round(block[0], 1)))
            i = 0
            while i < len(blocks):
                text = normalize_formula_block(blocks[i][4])
                if not is_formula_block(text):
                    i += 1
                    continue

                merged = text
                current_bottom = blocks[i][3]
                j = i + 1
                while j < len(blocks):
                    next_text = normalize_formula_block(blocks[j][4])
                    vertical_gap = blocks[j][1] - current_bottom
                    if vertical_gap > 40:
                        break
                    if (merged.endswith(("=", "−", "+", "/", "(")) or len(merged) < 80) and is_formula_continuation(next_text):
                        merged = normalize_formula_block(f"{merged} {next_text}")
                        current_bottom = blocks[j][3]
                        j += 1
                        continue
                    break

                score = formula_score(merged)
                if score > 0:
                    candidates.append((score, page_no + 1, merged))
                i = j
    finally:
        doc.close()

    picked: List[dict[str, object]] = []
    seen: set[str] = set()
    for _, page, formula in sorted(candidates, key=lambda item: (-item[0], item[1], len(item[2]))):
        key = re.sub(r"\s+", "", formula)
        if key in seen:
            continue
        seen.add(key)
        description, symbol_text, step_text = describe_formula(formula)
        picked.append(
            {
                "page": page,
                "formula": formula,
                "description": description,
                "symbol_text": symbol_text,
                "step_text": step_text,
            }
        )
        if len(picked) >= max_items:
            break
    return sanitize_formula_entries(picked, max_items=max_items)


def render_formula_section(
    attachment: Attachment,
    text_for_detection: str,
    formula_entries: Sequence[dict[str, object]],
) -> List[str]:
    lines: List[str] = []
    standard_formula = detect_standard_formula(text_for_detection)
    cleaned_entries = sanitize_formula_entries(formula_entries)

    if standard_formula is not None:
        lines.extend(
            [
                "- **核心公式/指标 1**：" + str(standard_formula["description"]),
                "$$",
                str(standard_formula["formula"]),
                "$$",
                "",
                f"- *{standard_formula['note']}*",
                "",
                "- **公式拆解 1**：",
                f"  - 这条公式表示什么：{standard_formula['description']}",
                f"  - 其中关键符号分别代表什么：{standard_formula['symbol_text']}",
                f"  - 这条公式对应方法中的哪一步：{standard_formula['step_text']}",
            ]
        )
        return lines

    if cleaned_entries:
        for idx, entry in enumerate(cleaned_entries, start=1):
            page = entry.get("page")
            step_text = str(entry["step_text"])
            if page:
                step_text = (
                    f"{step_text} [Zotero PDF 第{page}页]"
                    f"(zotero://open-pdf/library/items/{attachment.key}?page={page})"
                )
            lines.extend(
                [
                    f"- **核心公式/指标 {idx}**：{entry['description']}",
                    "$$",
                    str(entry["formula"]),
                    "$$",
                    "",
                    f"- **公式拆解 {idx}**：",
                    f"  - 这条公式表示什么：{entry['description']}",
                    f"  - 其中关键符号分别代表什么：{entry['symbol_text']}",
                    f"  - 这条公式对应方法中的哪一步：{step_text}",
                ]
            )
        return lines

    lines.extend(
        [
            "- **核心公式/指标**：",
            r"$$\text{【公式复杂/乱码，如需精准提取请截图至 samples 目录并调用 formula_ocr】}$$",
        ]
    )
    return lines


def build_note(
    folder_tag: str,
    paper: ExportPaper,
    item: ZoteroItem,
    attachment: Attachment,
    fulltext: str,
    formula_entries: Sequence[dict[str, object]],
) -> str:
    title = item.title or paper.title
    abstract = find_abstract_text(item.abstract or paper.abstract, fulltext) or item.abstract or paper.abstract or paper.title
    abstract_sentences = split_sentences(abstract)
    fulltext_sentences = split_sentences(fulltext[:12000])
    sentence_groups = [abstract_sentences, fulltext_sentences]

    theme = first_complete_sentence(abstract_sentences) or first_complete_sentence(fulltext_sentences) or paper.title
    study_sentence = sentence_with_keywords_clean(
        sentence_groups,
        ["为研究对象", "为研究样本", "为样本", "为例", "sample", "case study", "panel data set", "城市", "园区", "grid"],
    )
    data_sentence = sentence_with_keywords_clean(
        sentence_groups,
        ["数据", "样本", "数据库", "问卷", "专利", "建筑", "patent", "data", "sample", "survey", "database", "grid"],
    )
    method_sentence = sentence_with_keywords_clean(
        sentence_groups,
        ["采用", "利用", "构建", "基于", "运用", "使用", "using", "based on", "estimate", "measure", "approach"],
    )
    findings = extract_findings(abstract_sentences or fulltext_sentences)
    sample_phrase = clean_sample_phrase(extract_sample_phrase(sentence_groups), title=title)
    sample_source_phrase = extract_sample_source_phrase([study_sentence, abstract, fulltext[:4000], sample_phrase], title=title)
    data_source_phrase = extract_data_source_phrase([data_sentence, abstract, fulltext[:5000]])
    method_phrase = extract_method_phrase([method_sentence, abstract, fulltext[:5000]])
    time_range = extract_time_range(
        [abstract, item.abstract, paper.abstract, study_sentence, data_sentence, method_sentence, fulltext[:4000]],
        year_only(item.date) or year_only(paper.year) or "年份待补",
    )
    sample_size = extract_sample_size([study_sentence, data_sentence, abstract, fulltext[:4000]])
    method_types = detect_method_types(" ".join([paper.title, abstract, fulltext[:4000]]))
    data_type = infer_data_types(" ".join([paper.title, abstract, data_sentence, method_sentence]))
    analysis_unit = guess_analysis_unit(paper.title, sample_phrase, data_sentence, method_sentence)

    clean_topic_tags = clean_tags([*item.tags, *paper.tags], folder_tag)
    core_variable = "、".join(clean_topic_tags[:8]) if clean_topic_tags else folder_tag
    key_finding = strip_finding_prefix(findings[0]) if findings else theme
    relevance = (
        f"这篇论文可用于补充“{folder_tag}”主题下关于{core_variable}的文献脉络，"
        "适合拿来搭建概念框架、变量设计或案例比较。"
    )

    authors = item.creators or paper.authors or ["作者待补"]
    year = year_only(item.date) or year_only(paper.year) or "年份待补"
    source = item.publication_title or paper.journal or "来源待补"
    source_detail = ", ".join([part for part in [item.volume or paper.volume, item.issue or paper.issue, item.pages or paper.pages] if part])
    source_table = source if not source_detail else f"{source}, {source_detail}"
    alias = clean_alias(title)

    title_study_object = guess_study_object_from_title(title)
    study_object = title_study_object or sample_phrase or study_sentence or "研究对象需查阅完整正文"
    data_source_text = data_source_phrase or MISSING_DATA_SOURCE_NOTE
    method_overview = method_phrase or MISSING_METHOD_NOTE
    sample_source_text = sample_source_phrase or "缓存文本未包含明确样本来源，需查阅完整正文"
    context_range = study_object if time_range in study_object else f"{study_object}；时间范围：{time_range}"
    summary = build_summary(study_object, method_sentence or "", findings, theme)
    if data_source_phrase and method_phrase:
        if re.search(r"[A-Za-z]", data_source_text + method_overview):
            steps_text = f"先界定{study_object}，再基于{data_source_text}，并采用{method_overview}进行识别分析。"
        else:
            steps_text = f"先界定{study_object}，再基于{data_source_text}构建或选取指标，随后使用{method_overview}展开分析并归纳结论。"
    elif method_phrase:
        steps_text = f"缓存文本仅能确认作者采用{method_overview}展开分析，更细的识别步骤需查阅完整正文。"
    elif data_source_phrase:
        steps_text = f"缓存文本仅能确认研究使用{data_source_text}，但具体识别步骤需查阅完整正文。"
    else:
        steps_text = MISSING_METHOD_NOTE
    formula_context = " ".join(
        part
        for part in [paper.title, item.title, abstract, method_sentence, data_sentence, fulltext[:6000]]
        if part
    )

    link_bits = []
    if item.doi:
        link_bits.append(f"[DOI](https://doi.org/{item.doi})")
    if item.key:
        link_bits.append(f"[Zotero 条目](zotero://select/library/items/{item.key})")
    if attachment.key:
        link_bits.append(f"[Zotero PDF](zotero://open-pdf/library/items/{attachment.key})")
    links = " 路 ".join(link_bits)

    lines = [
        "---",
        f"title: {yaml_quote(title)}",
        "aliases:",
        f"  - {yaml_quote(alias)}",
        "tags:",
        "  - literature-note",
        "  - reading-note",
        f"  - {folder_tag}",
        f"created: {date.today().isoformat()}",
        f"source: {yaml_quote(source)}",
        "author:",
    ]
    lines.extend(f"  - {yaml_quote(author)}" for author in authors)
    lines.extend(
        [
            f"year: {year}",
            f"theme: {yaml_quote(theme)}",
            f"study_area: {yaml_quote(study_object)}",
            f"data_source: {yaml_quote(data_source_text)}",
            f"methodology: {yaml_quote(method_overview)}",
            f"core_variable: {yaml_quote(core_variable)}",
            f"key_finding: {yaml_quote(key_finding)}",
            f"relevance: {yaml_quote(relevance)}",
            f"doi: {yaml_quote(item.doi)}",
            f"url: {yaml_quote(item.url or paper.url)}",
            f"zotero_key: {yaml_quote(item.key)}",
            f"pdf_key: {yaml_quote(attachment.key)}",
            "---",
            "",
            f"# {title}",
            "",
            "## 基本信息",
            "",
            "| 项目 | 内容 |",
            "| --- | --- |",
            f"| 作者 | {'; '.join(authors)} |",
            f"| 年份 | {year} |",
            f"| 来源 | {source_table} |",
            f"| 主题 | {core_variable} |",
            f"| 链接 | {links} |",
            "",
            "## 一句话摘要",
            "",
            f"> {summary}",
            "",
            "## 研究对象",
            "",
            f"- **研究对象**：{study_object}",
            f"- **核心问题**：{theme}",
            f"- **研究情境/范围**：{context_range}",
            "",
            "## 研究方法",
            "",
            "### 方法概述",
            "",
            f"- **方法类型**：{' + '.join(method_types)}",
            f"- **总体思路**：{method_overview}",
            f"- **为什么用这种方法**：{build_method_rationale(method_types)}",
            "",
            "### 方法分析",
            "",
            f"- **分析单位**：{analysis_unit}",
            f"- **关键变量/概念**：{core_variable}",
            f"- **识别/推断逻辑**：作者围绕“{theme}”组织样本、方法和经验检验，并据此解释主要发现。",
            f"- **具体步骤**：{steps_text}",
        ]
    )

    lines.extend(render_formula_section(attachment, formula_context, formula_entries))

    lines.extend(
        [
            "- **方法优势**：能把研究对象、空间结构或网络关系放进相对统一的分析框架中。",
            "- **方法局限**：仍会受到数据口径、指标构造、识别策略和外部效度的约束。",
            "",
            "## 数据来源",
            "",
            f"- **数据类型**：{data_type}",
            f"- **样本来源**：{sample_source_text}",
            f"- **时间范围**：{time_range}",
            f"- **样本量/案例数**：{sample_size}",
            "- **数据局限**：摘要通常只给出核心样本与变量信息，若要进一步核对口径仍需回到正文与附录。",
            "",
            "## 研究结论",
            "",
            f"> 本篇整理了 {len(findings) if findings else 1} 组“主要发现 + 原文引用”。",
            "",
        ]
    )

    if not findings:
        findings = [theme]

    for index, finding in enumerate(findings, start=1):
        quote = strip_finding_prefix(finding) or finding
        lines.extend(
            [
                f"- **主要发现 {index}**：{quote}",
                f"- **原文引用 {index}**：",
                f'> “{quote}” ({authors[0]} 等, {year}, p. 1)',
                f"> [Zotero PDF 第1页](zotero://open-pdf/library/items/{attachment.key}?page=1)",
                "",
            ]
        )

    lines.extend(
        [
            "## 我的判断",
            "",
            f"- **最有启发的点**：这篇论文把{core_variable}和具体研究对象连到了一起，便于放进同一组主题阅读里比较。",
            f"- **可借鉴的方法**：{'、'.join(method_types)}的组合方式值得后续继续参考。",
            "- **可继续追问的问题**：如果更换研究区域、样本尺度或指标定义，结论是否仍然稳健，值得继续检验。",
            f"- **与我的研究关联**：{relevance}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    batch_dir = select_batch_dir(Path(args.batch_root), args.folder)
    rdf_files = list(batch_dir.glob("*.rdf"))
    if not rdf_files:
        raise FileNotFoundError(f"No RDF file found in {batch_dir}")
    rdf_path = rdf_files[0]

    output_dir = Path(args.vault_root) / args.folder
    output_dir.mkdir(parents=True, exist_ok=True)

    data_dir = locate_zotero_data_dir()
    con = open_db(data_dir)
    papers = parse_rdf(rdf_path)
    if args.limit and args.limit > 0:
        papers = papers[: args.limit]

    created = 0
    updated = 0
    failed: List[str] = []
    written_files: List[str] = []
    try:
        cur = con.cursor()
        for paper in papers:
            item = load_item_by_title(cur, paper.title)
            if item is None:
                failed.append(f"{paper.title}\tmissing_zotero_item")
                continue

            attachment = choose_attachment(item, paper.attachment_relpath)
            if attachment is None:
                failed.append(f"{paper.title}\tmissing_attachment")
                continue

            target = output_dir / safe_filename(item.title or paper.title, item.key)
            if target.exists():
                updated += 1
            else:
                created += 1

            pdf_path = batch_dir / paper.attachment_relpath if paper.attachment_relpath else Path()
            formula_entries = extract_formula_entries(pdf_path)
            note = build_note(
                args.folder,
                paper,
                item,
                attachment,
                load_fulltext(data_dir, attachment),
                formula_entries,
            )
            target.write_text(note, encoding="utf-8", newline="\n")
            written_files.append(target.name)
    finally:
        con.close()

    log_path = output_dir / "_batch_process_log.txt"
    written_files = sorted(unique_preserve_order(written_files))
    lines = [
        f"batch={args.folder}",
        "status=completed",
        f"note_count={len(written_files)}",
        f"created={created}",
        f"updated={updated}",
        f"failed={len(failed)}",
        f"notes_dir={output_dir}",
        "",
    ]
    if failed:
        lines.extend(["failed_items:"] + failed + [""])
    lines.extend(["files:"] + written_files)
    log_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"created={created} updated={updated} failed={len(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
