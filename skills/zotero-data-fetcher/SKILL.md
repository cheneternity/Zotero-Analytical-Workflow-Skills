---
name: zotero-data-fetcher
description: 根据 Item Key 或标题，从 Zotero 数据库及本地目录快速提取元数据、批注和全文缓存。此步骤严禁翻译和长篇推理。
---

# Zotero Data Fetcher

## 1. 锁定数据源

- 读取 `prefs.js` 确认生效的 `extensions.zotero.dataDir` 路径。
- 调用 `extract_item_json.py` 或同类脚本提取元数据（包含 DOI、作者、摘要、PDF 文件名及 Zotero Item Key）。

## 2. 语料提取优先级

针对该条目，按以下优先级获取核心正文内容：

1. **最高级（批注）**：提取 Zotero 内的高亮（Highlights）和笔记（Notes）。如果批注内容已足够丰富，可跳过后续读取。
2. **次高级（全文缓存）**：读取附件目录中的 `.zotero-ft-cache` 文件，提取包含核心方法、数据和结论的关键段落。
3. **备用级（本地 PDF）**：仅在前两者缺失或需要确认复杂公式时，才读取本地 PDF 对应页码。

## 3. 构建原始语料库（交付标准）

- 将提取到的所有内容整合为一个 `Raw_Data_Buffer`。
- **严格约束**：保持论文的原始语言（通常为英文）。严禁在此步骤进行任何翻译、总结或模板套用动作，确保数据提取过程以最高速度完成，不消耗过多算力。
- 交付数据至 `zotero-analytical-writer`。
