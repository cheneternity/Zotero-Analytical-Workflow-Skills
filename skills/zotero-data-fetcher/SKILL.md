---
name: zotero-data-fetcher
description: "根据 Zotero Item Key 或标题，从当前 agent 可访问的 Zotero 数据源或用户提供的论文材料中提取元数据、批注和正文证据。此技能不翻译、不总结、不替代全文证据。"
---

# Zotero Data Fetcher

## 职责

只负责核实 Zotero 条目与 PDF 附件身份，并提取可访问的原始材料；不负责 MinerU 转换、中文分析笔记或用户检索。

## 数据源发现

1. 优先使用当前 agent 已连接的 Zotero integration/API；它们可提供条目、父条目、附件、集合和批注。
2. 无 connector 时，可运行本仓库的 `python tools/zotero_readonly_fetch.py --key <parent-key>`；按平台自动发现 data directory，或传 `--data-dir` / 设置 `ZOTERO_DATA_DIR`。Windows 默认检查 `%USERPROFILE%/Zotero` 和 `%APPDATA%/Zotero/Zotero/Profiles/*/zotero`；macOS/Linux 检查 `~/Zotero`。也可从 Zotero 设置页定位 data directory。
3. Helper 以 SQLite `mode=ro` 打开 `zotero.sqlite` 并开启 `query_only`，不会修改数据库。按父条目 key 或精确 title 查询，返回 `zotero_key`、PDF attachment `pdf_key`、title、author、year、DOI、collection、批注、可访问的 storage PDF 路径及 `.zotero-ft-cache` 路径。缓存文件只报告位置，不代替原文。
4. PDF 只从 Zotero `storage/<pdf_key>/` attachment 路径解析。外部链接附件或不可访问文件明确返回缺失；不猜路径。如果 SQLite 被锁定或正在升级，先等待同步结束/关闭 Zotero 后重试；若仍失败，改用 Zotero 导出/API 或用户提供的附件。
5. 不得写入 Zotero 数据库、移动或覆盖附件。若以上数据源不可用，请求用户提供可访问的导出或附件。

## 身份核对与输出

尽可能返回以下字段，并保持字段名一致：

`zotero_key`、`pdf_key`、`title`、`author`、`year`、`doi`、`collection`、`note_path`、`fulltext_path`、`pdf_path`、`annotations`、`zotero_item`、`zotero_pdf`。

- `zotero_key` 是父条目唯一主键，`pdf_key` 是 PDF 附件键。标题仅用于人工核对或唯一候选时的 fallback。
- 路径字段只有在当前 agent 确认路径真实存在且可访问时才填写；路径不可访问或仅有远端附件时，返回可用的附件引用/URI，或明确标记不可用，不要构造本机路径。
- 同名条目、多条候选、父子附件关系不清或来源互相冲突时，报告冲突并停止身份相关的后续处理。
- 不根据标题猜 Item Key，不把 PDF 附件 Key 当作父条目 Key。

## 原始材料提取

对确认的条目，按当前数据源实际支持的能力提取：

1. 元数据：标题、作者、年份、DOI、Collection 和父条目 Key。
2. 附件：PDF 附件 Key，以及当前环境可访问的文件路径或远端附件引用。
3. Zotero 高亮、批注和 Notes。
4. 可用的全文索引缓存（例如 `.zotero-ft-cache`）及其来源；此缓存是可选项，不假设所有 Zotero 安装或 connector 都提供它。
5. 只有在批注和缓存不足，或需要核对公式、页码等细节时，才读取当前环境可访问的 PDF。

区分 `annotations_found`、`cache_found` 和 `pdf_found`。某一种材料缺失不能推断其他材料也缺失。

首次论文处理时，将已确认且当前环境可读取的 PDF 文件或附件引用与元数据交给下游全文处理流程；若下游只接受本地文件而当前只有远端附件，明确说明接口限制并请求可访问的文件，不要伪造本地路径。将批注、Notes 和缓存等原始语料交给下游分析写作流程。

已有论文证据查询时，若 `fulltext_path` 指向当前环境中确实可读的全文，优先使用它。正文证据优先级为：Formal Fulltext → 可核对的原始 PDF → 全文缓存。批注可说明阅读重点，但不能代替正文原文。

## 交付约束

- 将可提取内容整理为 `Raw_Data_Buffer`，尽可能保留原始语言、原文和来源信息。
- 此阶段不翻译、不总结、不套用中文模板。
- 不修改 Zotero 数据库，不移动或覆盖 PDF，不创建或改写无关文件。
- 明确记录未访问到的字段和材料；不要把缺失信息表述成已核实不存在。
