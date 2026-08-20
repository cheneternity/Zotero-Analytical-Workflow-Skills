---
name: zotero-fulltext-archiver
description: "将已有 Zotero PDF 或历史 MinerU 输出归档为可追踪的 ResearchVault Fulltext Markdown：先复用已成功的 MinerU 链路，再写入统一 frontmatter、整理安全图片路径、保留页面映射并执行只读校验。此技能不做中文总结、不改写论文正文、不负责用户检索。"
---

# Zotero Fulltext Archiver

## 职责边界

执行：`Zotero PDF → MinerU → Fulltext Markdown → 图片整理 → metadata → Note 关联 → validation`。

不执行中文翻译、分析笔记写作、批量检索或 Zotero 数据库改写。

## 1. 先确认实际 MinerU 环境

不要重新安装 MinerU。先搜索 `D:\ResearchVault`、`D:\research` 和相关项目中的 `MinerU`、`mineru`、`magic-pdf`、批处理脚本、配置和历史输出。

当前已发现的可复用调用链是：

`D:\research\mineru_batch_runner.py` → `D:\MinerU\.venv\Scripts\mineru.exe` → 临时输出目录 → 选择最新的 `*.md` → 复制 Markdown 与 `images/` → `D:\ResearchVault\MinerU_batch`。

现有 `D:\ResearchVault\MinerU_test\output\...` 中的 `content_list.json`、`middle.json`、`model.json` 和 `page_idx` 信息用于判断页码映射，不足以证明所有论文都可可靠映射。

## 2. 归档路径

正式全文：

```text
D:\ResearchVault\fulltext\<collection>\<zotero_key>.md
D:\ResearchVault\fulltext\<collection>\images\<zotero_key>\<image-file>
```

旧的 `MinerU_batch` 保留为历史迁移来源，不继续作为正式全文检索目录。当前 Vault 的分析笔记仍位于 `论文库/` 时，不移动它们；仅在全文 frontmatter 中写准确的 `note_path`。

## 3. 优先迁移旧结果

若 `MinerU_batch` 已有与 `zotero_key` 唯一对应的 Markdown 和图片：

1. 确认 Zotero 主键、PDF 键、标题和 Collection。
2. 将旧 Markdown 复制到正式 `fulltext/<collection>/<zotero_key>.md`。
3. 将图片复制到 `images/<zotero_key>/`，不得使用完整论文标题作为目录名。
4. 将原有图片引用改为相对于 Fulltext Markdown 的安全路径，例如 `![](<images/Q22PFLNV/image.jpg>)`。
5. 逐一检查每个本地图片引用真实存在；有缺失时不能报告成功。

若没有可复用结果，才调用已确认的 MinerU 可执行文件处理单篇 PDF；不得批量重跑整个库。

## 4. Fulltext Frontmatter

每个正式全文顶部至少包含：

```yaml
---
type: literature-fulltext
title: "..."
zotero_key: "Q22PFLNV"
pdf_key: "4RMSR7ZR"
doi: "..."
collection: "创新经济地理"
note_path: "论文库/创新经济地理/论文标题.md"
fulltext_path: "fulltext/创新经济地理/Q22PFLNV.md"
zotero_item: "zotero://select/library/items/Q22PFLNV"
zotero_pdf: "zotero://open-pdf/library/items/4RMSR7ZR"
source_type: mineru
page_mapping: unknown
---
```

Vault 内部路径统一使用 `/`。缺失的 DOI 可留空，但不得伪造。

## 5. 原文与页码规则

- MinerU Markdown 是证据档案：不翻译、总结、润色、重写、删减或插入模型生成内容。
- 允许的后处理仅包括 frontmatter、机器定位标记和安全图片路径修复。
- 只有当 `content_list.json`/`middle.json` 等信息与真实 PDF 通过单篇测试可靠对应时，才写 `page_mapping: reliable` 或 `<!-- pdf_page: N -->`。
- 0-based/1-based 转换必须记录并用真实 PDF 验证；无法可靠映射时写 `page_mapping: unknown`，不要猜 page。

## 6. 关联与校验

归档完成后：

1. 分析笔记补 `fulltext_path`，并可增加 `[[fulltext/<collection>/<zotero_key>]]` 入口；不重写整篇笔记。
2. Fulltext 补 `note_path`，确认双方 `zotero_key`、`pdf_key` 一致。
3. 运行 `D:\research\zotero_batch\validate_research_vault_literature_links.py`，只报告，不自动删除。
4. 只有 PDF、Fulltext、图片、Note、链接均有效时，才向 Collection Manager 报告 COMPLETE。
