---
name: zotero-data-fetcher
description: "根据 Zotero Item Key 或标题提取元数据、父条目与 PDF 附件、批注、Notes、.zotero-ft-cache 和本地 PDF 路径，并为全文归档或分析写作提供可追踪的原始数据。此技能不翻译、不总结、不替代全文证据。"
---

# Zotero Data Fetcher

## 职责

只负责找到 Zotero 数据、父条目和 PDF；不负责 MinerU 转换、中文分析笔记或用户检索。

## 统一输出字段

尽可能输出以下字段，并保持同名：

`zotero_key`、`pdf_key`、`title`、`author`、`year`、`doi`、`collection`、`note_path`、`fulltext_path`、`pdf_path`、`annotations`、`zotero_item`、`zotero_pdf`。

其中 `zotero_key` 是父条目唯一主键，`pdf_key` 是 PDF 附件键；标题只作为人工核对或唯一 fallback。

## 模式 A：首次论文处理

1. 读取 Zotero `prefs.js`，确认生效的数据目录；按当前可用的 Zotero connector/API 或现有提取脚本查询父条目。
2. 获取标题、作者、年份、DOI、所属 Collection、父条目 Key。
3. 在子附件中锁定 PDF，记录附件 Key 和真实本地路径；不存在 PDF 时明确失败原因。
4. 提取批注、Notes 和 `.zotero-ft-cache`（若存在），但保持原始语言和原始内容。
5. 将 `PDF path + metadata` 交给 `zotero-fulltext-archiver`；将原始语料交给 `zotero-analytical-writer`。

## 模式 B：已有论文证据查询

- 若分析笔记存在 `fulltext_path`，先返回并使用该全文路径。
- 精确正文证据优先级为：**MinerU Fulltext → Original PDF verification → `.zotero-ft-cache` fallback**。
- 批注可用于理解阅读重点，但不能替代正文原文。
- 缓存或批注缺失不等于 PDF 缺失；分别记录 `cache_found`、`pdf_found` 和 `annotations_found`。

## 约束

- 不根据标题猜 Item Key；同名或多条候选必须报告冲突。
- 不修改 Zotero 数据库，不移动原 PDF，不覆盖无关文件。
- 不在 Fetcher 阶段翻译、总结或套用中文模板。
