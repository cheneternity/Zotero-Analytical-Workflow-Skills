---
name: zotero-fulltext-archiver
description: "将当前环境可访问的 Zotero PDF 或已提供的转换结果归档为可追踪的 Fulltext Markdown，保留原文、图片、稳定身份和 Note 关联。此技能不做中文总结、不改写论文正文、不负责用户检索。"
---

# Zotero Fulltext Archiver

## 职责边界

执行：`可访问的 Zotero PDF → 可用的 PDF 文本转换 → Fulltext Markdown → 图片整理 → metadata → Note 关联 → 校验`。

不执行中文翻译、分析笔记写作、批量文献发现或 Zotero 数据库改写。

## 1. 解析当前环境

1. 从用户指定的 Vault 或当前 agent 工作区确认 `vault_root`；从其中发现现有 Fulltext 目录、Note 目录和相关索引。常见的相对结构是 `03fulltext/<collection>/`、`02vault/<collection>/`，但必须保留项目实际采用的结构。
2. 先按 `zotero_key` 检查是否已有正式 Fulltext。若其 `zotero_key`、`pdf_key`、frontmatter、正文和图片链接均有效，则复用并执行定向校验；修整 Note 模板不是重新转换全文的理由。
3. 检查当前 agent 实际可用的 Zotero 附件访问和 PDF 转换能力。优先复用用户提供的合格转换结果；需要转换时，只使用当前环境确实可调用的兼容工具。不要假设 MinerU、特定版本、runner、命令、后端、操作系统或个人历史目录已安装/存在，也不要为满足本技能安装软件或个人代码。
4. 若 PDF 或转换工具不可访问，返回 `FULLTEXT_DEFERRED` 并说明缺少的文件或能力。不得以空壳、摘要或模型生成正文冒充 Formal Fulltext。

## 2. 转换与来源完整性

- 原始 Zotero PDF 只读。若转换器需要可写输入，先在当前运行环境提供的临时目录中建立工作副本；不要改动原附件。
- 当当前环境能计算校验和时，记录原 PDF 与工作副本的 SHA-256，并在转换前确认一致；若无法计算，记录该项未执行，不要声称已核对。
- 一次只处理当前请求范围内的论文。保留当前转换器可提供的诊断信息；只清理能够确认由本次调用启动的进程和临时文件。
- 对转换结果检查正文前、中、后是否存在，来源身份是否匹配，图片目标是否存在。任何缺页、截断、乱码或图片缺失都应如实记录并阻止标记为完成。
- 除 frontmatter、可验证的机器定位标记和必要的安全图片路径修复外，保持抽取正文原样；不翻译、总结、润色、重写或插入模型生成内容。

## 3. 正式归档位置与图片

Fulltext 使用当前 Vault 已有的目录和命名规则；若项目尚未建立规则，采用相对 `vault_root` 的 `03fulltext/<collection>/<zotero_key>.md`，图片放在同目录下 `images/<zotero_key>/`。所有写入路径必须先确认位于活动 Vault 中。

- Vault 内链接使用相对路径和 `/` 分隔符，不写机器绝对路径。
- 图片引用应相对于 Fulltext Markdown，且不得跳出其图片目录或活动 Vault。
- 只有确认每个图片文件真实存在且引用可解析时，才报告 `images_valid: true`。
- 已有可复用 Markdown/图片仅在用户提供或当前 Vault 可访问且身份唯一时迁移；不假定存在某个历史暂存目录。

## 4. Fulltext Frontmatter

每个正式全文至少保留以下可确认字段；按当前 Vault 既有 schema 增补其他必要字段。路径均为 Vault-relative：

```yaml
---
type: literature-fulltext
title: "..."
zotero_key: "..."
pdf_key: "..."
doi: "..."
collection: "..."
note_path: "<relative path to analytical note>"
fulltext_path: "<relative path to this file>"
zotero_item: "zotero://select/library/items/<zotero_key>"
zotero_pdf: "zotero://open-pdf/library/items/<pdf_key>"
source_type: "<actual source or converter>"
page_mapping: unknown
---
```

缺失 DOI 可留空。不要猜 DOI、collection、Key 或页码。若 Zotero URI 目标信息不足，不要生成不完整 URI。

## 5. 原文与页码规则

- 页码映射只有在转换器提供的数据与实际 PDF 经核验可靠对应时，才标记为可靠或插入页码标记。
- 记录转换器使用的页码基准和验证方法；无法验证时保留 `page_mapping: unknown`，不得推算页码。
- `page_mapping: unknown` 不阻止分析写作者直接访问 PDF 做页面核验；它只禁止从 Markdown 推断页码。

## 6. 关联与完成状态

1. Fulltext 的 `note_path` 与 Note 的 `fulltext_path` 必须指向活动 Vault 内真实存在的目标。
2. 两侧 `zotero_key`、`pdf_key` 应一致；图片引用和正文完整性应通过检查。
3. 如果当前项目提供验证工具，可运行相关检查并报告实际结果。没有项目验证器时，执行文件存在性、frontmatter、双向路径、身份字段、正文和图片的人工/可用工具检查，并明确说明自动校验未运行；未做的检查不能记为通过。
4. 只有附件访问、Fulltext 正文、必要图片、身份和链接检查均通过时，才向 Collection Manager 报告 `COMPLETE`；否则给出准确的可重试部分状态。
