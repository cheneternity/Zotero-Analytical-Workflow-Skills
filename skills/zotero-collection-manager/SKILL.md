---
name: zotero-collection-manager
description: "按 Zotero Collection 增量调度 Fetcher、Fulltext Archiver、Analytical Writer 和一致性校验，使用可重试状态而不是以“存在笔记”或临时跳过判断完成；默认单篇/小批量运行，支持断点续传。"
---

# Zotero Collection Manager

## 调度链

```text
Fetcher
  ↓
Fulltext Archiver
  ↓
Analytical Writer
  ↓
Link Validation
  ↓
Dataview Refresh（仅需要时）
  ↓
Process Log
```

各环节保持职责边界，不在 Manager 中重写全文或中文笔记。

## 增量与安全规则

- 以 Zotero `zotero_key` 而不是标题作为主键。
- 先读取现有日志；成功条目只在所有核心条件满足时跳过。
- 默认只处理用户指定的 Collection、单篇或小批量；不得自动批量重跑全库、迁移所有旧笔记或移动 Zotero PDF。
- 已有 analytical note 但没有全文时，只补 Fulltext 与链接，不重新生成整篇笔记。
- 当批次请求包含 Knowledge 整理或“全部论文”时，批次调度必须先读取 `D:\ResearchVault\模板\知识库模板\README_知识库模板说明.md` 和对应的主题/概念/方法/关系/争议模板，并建立逐篇 coverage ledger；不能以“已有笔记”或“已生成综合页”代替 Knowledge 覆盖。
- Knowledge 写作必须同时解析 Analytical Note 的结构化字段和对应 `D:\ResearchVault\03fulltext` 原文。Fulltext 可用时，精确结论、公式、阈值、机制和引语必须回到原文核验；Fulltext 缺失时只能保留 `note_supported` / `FULLTEXT_DEFERRED`，不得补写页码或反向生成引语。
- 批次完成条件包括：每篇论文至少进入一个真实 `source_notes`，页面使用当前知识库模板的完整可见章节，覆盖账本无未解释遗漏，且 Knowledge validator 与模板审查均通过。
- `MinerU_batch` 只作为可复用历史来源；发现标题对应多个 Item Key 时暂停该条目并报告冲突。
- `⚠️ 跳过` 不是永久完成。只有用户明确确认永久忽略才可终止；临时错误必须可重试。

## 每篇论文的状态模型

至少记录：

```json
{
  "item_key": "Q22PFLNV",
  "pdf_found": true,
  "fulltext": true,
  "images_valid": true,
  "note": true,
  "linked": true,
  "page_mapping": "unknown",
  "indexes_refreshed": false
}
```

核心状态：

- `COMPLETE`：`pdf_found && fulltext && images_valid && note && linked` 全部为真。
- `PARTIAL_FULLTEXT_MISSING`：Note 存在但 Fulltext 未建立。
- `PARTIAL_NOTE_MISSING`：Fulltext 存在但 Note 未建立。
- `IMAGES_INVALID`：全文存在但有图片缺失或错误引用。
- `PDF_NOT_FOUND`：找不到父条目 PDF，可重试。
- `MINERU_FAILED`：MinerU 失败，可重试。
- `KEY_CONFLICT`：主键或标题映射冲突，需要人工确认。
- `PERMANENTLY_IGNORED`：仅用户明确确认后使用。

## 日志

每篇论文完成一个阶段后立即记录 Item Key、标题、时间、状态、原因和路径；不要只记录“存在笔记”。Collection Manager 的报告应区分新增成功、部分完成、失败和待人工确认。
