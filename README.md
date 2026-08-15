# Zotero Analytical Workflow Skills

这不是单个“论文精读 skill”，而是一整条 Zotero 文献处理工作流的打包仓库。

仓库当前包含 5 个核心 skill 和 1 个精读模板，用来覆盖：

- 论文分类批处理与断点续跑
- 论文元数据、批注、全文缓存提取
- 中文精读笔记生成与模板套用
- 研究知识库的模板化维护与跨论文综合
- Zotero、Fulltext、精读笔记和 Knowledge 的端到端编排

## 目录结构

```text
Zotero-analytical-writer/
├── README.md
├── skills/
│   ├── zotero-collection-manager/
│   │   └── SKILL.md
│   ├── zotero-data-fetcher/
│   │   └── SKILL.md
│   └── zotero-analytical-writer/
│       └── SKILL.md
│   ├── research-vault-knowledge-maintainer/
│   │   └── SKILL.md
│   └── research-vault-ingest-orchestrator/
│       └── SKILL.md
├── templates/
│   └── 论文精读模板.md
```

## 工作流关系

推荐按下面顺序使用：

1. `zotero-collection-manager`
   负责读取某个 Zotero 分类、比对处理日志、筛出未完成文献并串行调度。
2. `zotero-data-fetcher`
   负责抓取单篇论文的元数据、批注、全文缓存和附件信息。
3. `zotero-analytical-writer`
   负责中文逻辑重构、Frontmatter 提炼、模板套用和 Obsidian 笔记写入。
4. `research-vault-ingest-orchestrator`
   负责按单篇论文编排 Zotero 身份、Fulltext、精读笔记、Knowledge 决策和校验。
5. `research-vault-knowledge-maintainer`
   负责按知识库模板维护主题、概念、方法、关系、争议和综合页，并执行跨论文覆盖与证据审查。

其中：

- `templates/论文精读模板.md` 是精读模板

## 仓库内容说明

### `skills/zotero-collection-manager`

适用于整批处理 Zotero 分类。它强调：

- 读取并维护 `_ProcessLog_进度记录.md`
- 自动跳过已成功或已跳过条目
- 按篇串行执行，处理完一篇立即写入日志
- 将抓取与写作拆给下游 skill

### `skills/zotero-data-fetcher`

适用于单篇论文语料准备。它强调：

- 先读 Zotero 数据目录和数据库
- 优先取批注，其次取全文缓存，再考虑本地 PDF
- 保持原始语言，不在此步骤翻译或总结

### `skills/zotero-analytical-writer`

适用于最终精读笔记生成。它强调：

- Frontmatter 字段必须高度提炼，不能机械复制摘要
- 研究区、数据来源、方法、核心变量要精准提取
- 公式提取要防乱码、防胡编，并支持 OCR 兜底
- 正文区要过滤作者单位、基金号、投稿规范等学术噪音

### `skills/research-vault-ingest-orchestrator`

适用于指定论文的端到端入库。它强调：

- 先确认 Zotero 稳定身份，再复用或归档可追踪的 Fulltext
- Analytical Note 与原文证据分层处理，精确结论、公式、阈值和引语必须回到原文核验
- Knowledge 写入前必须读取当前知识库模板，并建立逐篇覆盖账本
- 以可重试状态、重复检查和最终校验作为完成条件

### `skills/research-vault-knowledge-maintainer`

适用于从已有精读笔记和 Fulltext 维护 Research Knowledge Wiki。它强调：

- 严格使用 `D:\ResearchVault\模板\知识库模板` 的 README 和对应页面模板
- 区分结构化库字段与原文证据，保留真实 `source_notes`、证据表、边界、缺口和争议
- “全部论文”任务必须建立逐篇 coverage ledger，不能只生成综合页
- 精确结论、公式、阈值、机制和引语需要 Fulltext 支持；缺全文时明确标注延后核验

## 使用建议

- 如果你是把这些 skill 用于 Codex 或类似代理系统，建议保持当前目录结构不变。
- `skills/zotero-analytical-writer/SKILL.md` 已经改为使用仓库内相对模板路径：`../../templates/论文精读模板.md`。

## 环境说明

仓库内容目前默认基于 Windows 路径习惯编写，并保留了你当前环境中的默认目录，例如：

- `D:\ResearchVault\note`

如果在别的机器或仓库环境中使用，建议通过命令行参数覆盖这些默认路径，而不是直接依赖硬编码默认值。

## 后续可继续补充

- 增加示例输入与输出
- 增加安装说明或依赖说明
- 为每个 skill 单独补充测试样例或演示数据
