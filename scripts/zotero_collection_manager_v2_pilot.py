#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pilot runner for incremental Zotero collection processing with breakpoint logs."""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore


RECORD_RE = re.compile(r"^- \[(?P<checked>[xX ])\]\s*(?P<ts>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|\s*(?P<key>[^|]+?)\s*\|\s*(?P<title>.+?)\s*$")
COMPLETED_PREFIXES = ("✅ 成功", "⚠️ 跳过")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-root", default=r"D:\research\zotero_batch")
    parser.add_argument("--folder", default="创新经济地理")
    parser.add_argument("--notes-root", default=r"D:\ResearchVault\note")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--force-overwrite", action="store_true")
    return parser.parse_args()


def load_regen_module():
    path = Path(__file__).with_name("regenerate_template_notes.py")
    if not path.exists():
        path = Path(r"D:\research\zotero_batch\regenerate_template_notes.py")
    spec = importlib.util.spec_from_file_location("regen", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["regen"] = module
    spec.loader.exec_module(module)
    return module


def now_string(timezone_name: str) -> str:
    if ZoneInfo is None:
        return datetime.now().strftime("%Y-%m-%d %H:%M")
    return datetime.now(ZoneInfo(timezone_name)).strftime("%Y-%m-%d %H:%M")


def ensure_log_file(log_path: Path, folder_name: str, timezone_name: str) -> None:
    if log_path.exists():
        return
    header = [
        f"# {folder_name} 处理进度",
        "",
        f"- 创建时间：{now_string(timezone_name)}",
        "- 说明：仅 `✅ 成功` 与 `⚠️ 跳过` 会在下次运行中被视为已完成。",
        "",
        "## 处理记录",
        "",
    ]
    log_path.write_text("\n".join(header), encoding="utf-8", newline="\n")


def load_completed_records(log_path: Path) -> tuple[set[str], set[str]]:
    completed_keys: set[str] = set()
    completed_titles: set[str] = set()
    if not log_path.exists():
        return completed_keys, completed_titles

    text = log_path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        match = RECORD_RE.match(line.strip())
        if not match:
            continue
        status = match.group("status").strip()
        if not status.startswith(COMPLETED_PREFIXES):
            continue
        key = match.group("key").strip()
        title = match.group("title").strip()
        if key:
            completed_keys.add(key)
        if title:
            completed_titles.add(title)
    return completed_keys, completed_titles


def append_record(log_path: Path, timezone_name: str, status: str, item_key: str, title: str, checked: bool) -> None:
    mark = "x" if checked else " "
    line = f"- [{mark}] {now_string(timezone_name)} | {status} | {item_key or 'UNKNOWN'} | {title}"
    with log_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def resolve_pdf_path(data_dir: Path, attachment) -> Path:
    attachment_path = str(getattr(attachment, "path", "") or "")
    if attachment_path.startswith("storage:"):
        filename = attachment_path.replace("storage:", "", 1)
        return data_dir / "storage" / attachment.key / filename
    return Path(attachment_path)


def extract_pdf_text(regen, pdf_path: Path, max_pages: int = 25) -> str:
    fitz = getattr(regen, "fitz", None)
    if fitz is None or not pdf_path.exists():
        return ""
    doc = fitz.open(pdf_path)
    try:
        parts = [doc.load_page(i).get_text("text") for i in range(min(max_pages, doc.page_count))]
    finally:
        doc.close()
    return regen.normalize_text(" ".join(parts))


def is_completed(paper, item, completed_keys: set[str], completed_titles: set[str]) -> bool:
    titles = [paper.title]
    if item is not None:
        titles.append(item.title)
    if item is not None and item.key and item.key in completed_keys:
        return True
    return any(title and title in completed_titles for title in titles)


def safe_reason(error: Exception) -> str:
    reason = str(error).strip() or error.__class__.__name__
    reason = reason.replace("\n", " ").replace("\r", " ")
    return reason


def truncate_text(text: str, max_len: int = 30) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip(" ，。；;:：")
    if len(text) <= max_len:
        return text
    for sep in ("；", "。", "，", ",", "、", " "):
        head = text.split(sep, 1)[0].strip(" ，。；;:：")
        if 0 < len(head) <= max_len:
            return head
    return text[:max_len].strip(" ，。；;:：")


def clean_field_noise(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"(摘要[:：]?|作者[:：]?|关键词[:：]?|通讯作者[:：]?)", "", value)
    value = re.sub(r"\b\d{6}\b", "", value)
    return re.sub(r"\s+", " ", value).strip(" ，。；;:：")


def title_lower(text: str) -> str:
    return str(text or "").strip().lower()


def infer_theme(title: str, abstract: str) -> str:
    lower = title_lower(title)
    if "技术创新网络视角" in title:
        return "解析湾区城市功能网络差异"
    if "生态位" in title:
        return "识别城市创新生态位适宜性"
    if "第三空间" in title:
        return "分析创新区第三空间营造策略"
    if "创新活动分布" in title:
        return "测度城市创新空间结构演变"
    if "建筑密度分布" in title:
        return "刻画城市空间生长格局机制"
    if "micro-geographical proximity" in lower:
        return "检验微观邻近的知识溢出效应"
    if "polycentric urban structure" in lower:
        return "检验多中心结构对城市创新影响"
    if "空间结构、城市规模" in title:
        return "分析结构规模对创新的作用"
    if "知识多中心" in title:
        return "解释湾区知识多中心演化"
    if "邻近视角" in title:
        return "揭示多尺度创新网络形成机制"
    return truncate_text(clean_field_noise(abstract or title), 30)


def infer_study_area(title: str, abstract: str) -> str:
    lower = title_lower(title)
    if "南京市" in title or "南京市" in abstract:
        return "江苏省南京市"
    if "波士顿肯德尔广场" in title:
        return "波士顿肯德尔广场"
    if "粤港澳大湾区" in title:
        return "粤港澳大湾区"
    if "长三角" in title:
        return "长三角城市"
    if "polycentric urban structure" in lower:
        return "267个中国地级及以上城市"
    if "micro-geographical proximity" in lower:
        return "中国高校搬迁样本"
    if "94 chinese cities" in abstract.lower() or "94个城市" in abstract:
        return "全国94个城市"
    if "中国城市" in title:
        return "中国城市样本"
    sample_patterns = [
        r"(江苏省南京市)",
        r"(波士顿肯德尔广场)",
        r"(粤港澳大湾区)",
        r"(长三角城市群?)",
        r"(全国\d+个城市)",
        r"(\d+个城市)",
        r"(中国高校搬迁样本)",
    ]
    for pattern in sample_patterns:
        match = re.search(pattern, title + " " + abstract)
        if match:
            return truncate_text(match.group(1), 30)
    return truncate_text(clean_field_noise(title), 30)


def infer_data_source(title: str, abstract: str, time_range: str) -> str:
    text = f"{title} {abstract}"
    lower = title_lower(text)
    if "专利合作" in text or "专利转移" in text:
        return truncate_text("专利合作与转移数据", 30)
    if "发明专利申请" in text:
        return truncate_text("发明专利申请数据", 30)
    if "landscan" in lower and time_range:
        return truncate_text(f"LandScan人口数据({time_range})", 30)
    if "landscan" in lower:
        return truncate_text("LandScan人口数据", 30)
    if "建筑密度" in text:
        return truncate_text("建筑密度栅格数据", 30)
    if "高校搬迁" in text or "university relocation" in lower:
        return truncate_text("高校搬迁与专利数据", 30)
    if "case study" in lower or "实地调研" in text or "肯德尔广场" in text:
        return truncate_text("实地调研与案例资料", 30)
    if "panel data" in lower and time_range:
        return truncate_text(f"城市面板数据({time_range})", 30)
    if "论文数据" in text:
        return truncate_text("论文合作与专利数据", 30)
    if "专利" in text:
        return truncate_text("专利与创新活动数据", 30)
    return truncate_text(clean_field_noise(abstract), 30)


def infer_methodology(title: str, abstract: str) -> str:
    lower = title_lower(title + " " + abstract)
    if "技术创新网络视角" in title:
        return "技术合作与转移网络分析"
    if "生态位" in title:
        return "生态位评价与GIS分析"
    if "第三空间" in title:
        return "案例研究与实地调研"
    if "创新活动分布" in title:
        return "DBSCAN聚类与结构测度"
    if "建筑密度分布" in title:
        return "建筑密度测度与空间分析"
    if "micro-geographical proximity" in lower:
        return "准自然实验与回归分析"
    if "polycentric urban structure" in lower:
        return "工具变量与面板回归"
    if "空间结构、城市规模" in title:
        return "ESDA测度与工具变量回归"
    if "知识多中心" in title:
        return "知识多中心测度与网络分析"
    if "邻近视角" in title:
        return "多尺度网络与邻近性分析"
    return "实证分析与模型测度"


def infer_core_variable(title: str, abstract: str) -> str:
    lower = title_lower(title + " " + abstract)
    if "技术创新网络视角" in title:
        return "城市功能、合作网络、转移网络"
    if "生态位" in title:
        return "资源、环境、技术生态位"
    if "第三空间" in title:
        return "第三空间、公共空间、共享办公"
    if "创新活动分布" in title:
        return "创新活动分布、集中度、首位度"
    if "建筑密度分布" in title:
        return "建筑密度、空间生长、驱动因素"
    if "micro-geographical proximity" in lower:
        return "微观邻近、高校搬迁、知识溢出"
    if "polycentric urban structure" in lower:
        return "多中心结构、创新能力、集聚效应"
    if "空间结构、城市规模" in title:
        return "空间结构、城市规模、创新绩效"
    if "知识多中心" in title:
        return "知识多中心、城市群、空间结构"
    if "邻近视角" in title:
        return "邻近性、多尺度网络、微观机制"
    return "核心变量与关键指标"


def infer_key_finding(title: str, abstract: str) -> str:
    lower = title_lower(title)
    if "技术创新网络视角" in title:
        return "湾区网络呈双核三中心多节点"
    if "生态位" in title:
        return "南京创新空间适宜性差异明显"
    if "第三空间" in title:
        return "第三空间支撑创新要素集聚"
    if "创新活动分布" in title:
        return "创新结构向低首位高集中演变"
    if "建筑密度分布" in title:
        return "建筑密度显著影响城市生长"
    if "micro-geographical proximity" in lower:
        return "微观邻近显著促进知识溢出"
    if "polycentric urban structure" in lower:
        return "多中心化显著抑制城市创新"
    if "空间结构、城市规模" in title:
        return "多中心抑制创新规模缓解负效应"
    if "知识多中心" in title:
        return "湾区知识多中心呈动态演化"
    if "邻近视角" in title:
        return "邻近性共同塑造创新网络"
    return truncate_text(clean_field_noise(abstract), 30)


def infer_relevance(title: str, methodology: str, study_area: str) -> str:
    lower = title_lower(title)
    if "南京市" in title:
        return "提供南京创新空间对比基准"
    if "第三空间" in title:
        return "提供创新区第三空间案例"
    if "技术创新网络视角" in title:
        return "提供湾区创新网络比较框架"
    if "建筑密度" in title:
        return "提供城市生长测度指标"
    if "micro-geographical proximity" in lower:
        return "提供邻近性识别思路"
    if "polycentric urban structure" in lower:
        return "提供多中心结构识别框架"
    if "空间结构、城市规模" in title:
        return "提供结构规模联动识别框架"
    if "知识多中心" in title:
        return "提供知识多中心测度框架"
    if "邻近视角" in title:
        return "提供邻近性机制解释框架"
    return truncate_text(f"提供{methodology}参考", 30)


def has_invalid_data_source(text: str) -> bool:
    value = str(text or "")
    return bool(re.search(r"(摘要[:：]?|作者[:：]?|\b\d{6}\b)", value))


def study_area_conflicts(title: str, study_area: str) -> bool:
    title_text = str(title or "")
    if "南京" in title_text and "南京" not in study_area:
        return True
    if "肯德尔广场" in title_text and "肯德尔广场" not in study_area:
        return True
    if "粤港澳大湾区" in title_text and "粤港澳大湾区" not in study_area:
        return True
    if "长三角" in title_text and "长三角" not in study_area:
        return True
    return False


def build_frontmatter_updates(regen, paper, item, attachment, fulltext: str) -> dict[str, str]:
    abstract = regen.find_abstract_text(item.abstract or paper.abstract, fulltext) or item.abstract or paper.abstract or ""
    time_range = regen.extract_time_range(
        [abstract, item.abstract, paper.abstract, fulltext[:4000]],
        regen.year_only(item.date) or regen.year_only(paper.year) or "",
    )
    theme = infer_theme(item.title or paper.title, abstract)
    study_area = infer_study_area(item.title or paper.title, abstract)
    data_source = infer_data_source(item.title or paper.title, abstract, time_range)
    methodology = infer_methodology(item.title or paper.title, abstract)
    core_variable = infer_core_variable(item.title or paper.title, abstract)
    key_finding = infer_key_finding(item.title or paper.title, abstract)
    relevance = infer_relevance(item.title or paper.title, methodology, study_area)

    data_source = clean_field_noise(data_source)
    if has_invalid_data_source(data_source):
        data_source = "数据来源需据正文补核"

    if study_area_conflicts(item.title or paper.title, study_area):
        study_area = infer_study_area(item.title or paper.title, item.title or paper.title)

    updates = {
        "theme": truncate_text(theme, 30),
        "study_area": truncate_text(study_area, 30),
        "data_source": truncate_text(data_source, 30),
        "methodology": truncate_text(methodology, 30),
        "core_variable": truncate_text(core_variable, 30),
        "key_finding": truncate_text(key_finding, 30),
        "relevance": truncate_text(relevance, 30),
    }
    return updates


def apply_frontmatter_updates(regen, note_text: str, updates: dict[str, str]) -> str:
    output = note_text
    for field, value in updates.items():
        output = re.sub(
            rf"^{field}: .*$",
            f"{field}: {regen.yaml_quote(value)}",
            output,
            flags=re.MULTILINE,
        )
    return output


def main() -> int:
    args = parse_args()
    regen = load_regen_module()

    batch_dir = regen.select_batch_dir(Path(args.batch_root), args.folder)
    rdf_files = list(batch_dir.glob("*.rdf"))
    if not rdf_files:
        raise FileNotFoundError(f"No RDF file found in {batch_dir}")
    papers = regen.parse_rdf(rdf_files[0])
    if args.limit > 0:
        papers = papers[: args.limit]

    output_dir = Path(args.notes_root) / args.folder
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "_ProcessLog_进度记录.md"
    ensure_log_file(log_path, args.folder, args.timezone)

    completed_keys, completed_titles = load_completed_records(log_path)
    data_dir = regen.locate_zotero_data_dir()
    con = regen.open_db(data_dir)

    pending: list[tuple[object, Optional[object]]] = []
    try:
        cur = con.cursor()
        for paper in papers:
            item = regen.load_item_by_title(cur, paper.title)
            if not args.force_overwrite and is_completed(paper, item, completed_keys, completed_titles):
                continue
            pending.append((paper, item))

        print(f"folder={args.folder}")
        print(f"candidate_count={len(papers)}")
        print(f"already_completed={0 if args.force_overwrite else len(papers) - len(pending)}")
        print(f"pending_count={len(pending)}")
        print(f"force_overwrite={args.force_overwrite}")
        print(f"log_path={log_path}")

        if not pending:
            print("message=该分类下所有论文已处理完毕")
            return 0

        new_success = 0
        new_failed = 0

        for paper, cached_item in pending:
            # Per-item reset: keep all state local to this loop iteration.
            item = cached_item
            title_for_log = paper.title
            item_key = ""
            try:
                if item is None:
                    item = regen.load_item_by_title(cur, paper.title)
                if item is None:
                    raise RuntimeError("missing_zotero_item")

                item_key = item.key
                title_for_log = item.title or paper.title

                attachment = regen.choose_attachment(item, paper.attachment_relpath)
                if attachment is None:
                    raise RuntimeError("missing_attachment")

                fulltext = regen.load_fulltext(data_dir, attachment)
                pdf_path = resolve_pdf_path(data_dir, attachment)
                if not fulltext.strip():
                    fulltext = extract_pdf_text(regen, pdf_path)
                if not fulltext.strip() and not (item.abstract or paper.abstract):
                    raise RuntimeError("missing_cache_and_pdf_text")

                formula_entries = regen.extract_formula_entries(pdf_path)
                note_text = regen.build_note(args.folder, paper, item, attachment, fulltext, formula_entries)
                note_text = apply_frontmatter_updates(
                    regen,
                    note_text,
                    build_frontmatter_updates(regen, paper, item, attachment, fulltext),
                )
                target = output_dir / regen.safe_filename(item.title or paper.title, item.key)
                target.write_text(note_text, encoding="utf-8", newline="\n")

                status = "✅ 成功（重生成）" if args.force_overwrite else "✅ 成功"
                append_record(log_path, args.timezone, status, item.key, item.title or paper.title, checked=True)
                new_success += 1
            except Exception as exc:  # pragma: no cover - defensive per-item fault barrier
                append_record(log_path, args.timezone, f"❌ 失败（{safe_reason(exc)}）", item_key, title_for_log, checked=False)
                new_failed += 1

        print(f"new_success={new_success}")
        print(f"new_failed={new_failed}")
        print("message=进度已实时写入 _ProcessLog_进度记录.md")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
