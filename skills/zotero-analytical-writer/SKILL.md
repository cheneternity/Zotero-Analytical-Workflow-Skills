---
name: zotero-analytical-writer
description: "使用 Zotero metadata、批注和 MinerU Fulltext 生成或增量更新 ResearchVault 中文分析笔记；保留现有 Obsidian 模板、字段、公式和 Zotero 链接，并要求原文引用真实可追溯。"
---

# Zotero Analytical Writer

## 职责与语料顺序

Writer 只负责分析层：`metadata + annotations + MinerU Fulltext + 必要时 PDF → 中文 analytical note`。

- Fulltext 是原文证据，分析笔记是中文理解层；不得把二者混为一谈。
- 仍保留现有的 `theme`、`study_area`、`data_source`、`methodology`、`core_variable`、`key_finding`、`relevance`、中文逻辑重构、学术垃圾过滤、公式防乱码、Zotero URI 和 Dataview 刷新逻辑。
- 不负责 PDF→MinerU；缺全文时交给 `zotero-fulltext-archiver`，不要自行伪造原文。

## Frontmatter 增量字段

新建或明确要求更新的笔记使用：

```yaml
type: literature-note
zotero_key: "Q22PFLNV"
pdf_key: "4RMSR7ZR"
title: "..."
doi: "..."
collection: "创新经济地理"
note_path: "论文库/创新经济地理/论文标题.md"
fulltext_path: "fulltext/创新经济地理/Q22PFLNV.md"
```

旧笔记不批量重写；增量迁移只补可确认的字段和全文入口。正式新笔记优先使用 `note/<collection>/`，当前 Vault 的 `论文库/` 继续兼容。

## 原文引用规则

- “主要发现 + 原文引用”中的原文必须真实出现在 MinerU Fulltext 或 Original PDF。
- 严禁根据中文摘要反向生成英文 quote；定位不到时写“未在当前全文中定位到可核验原句”。
- 引用要保留必要上下文，检查否定、条件、稳健性限定、假设和局限。
- PDF 页码只有在可靠映射或实际 PDF 验证后才写入 `zotero://open-pdf/...?...page=`；否则保留 Fulltext 链接或写“PDF 页码未验证”。

## 既有写作约束

- `theme` 概括研究问题；`study_area`、`data_source`、`methodology`、`core_variable`、`key_finding`、`relevance` 必须来自真实材料，不复制大段摘要。
- 过滤作者地址、单位、邮编、邮箱、基金号和排版垃圾；数据与方法缺失时如实说明。
- 公式仅在原文可靠时保留；乱码或残片不强行解释，也不为占位符生成符号拆解。
- 写入前检查 YAML、美元符号配对、`zotero://select/...` 和 PDF/Fulltext 入口。

## 写入与索引

1. 保留现有笔记正文，优先做最小增量补充。
2. 在基本信息区增加 `全文 Markdown：[[fulltext/<collection>/<zotero_key>]]`（路径存在时）。
3. 新建论文笔记时才刷新四个根 Dataview 索引；不因补全文而批量重写索引或旧笔记。
