# Zotero Analytical Workflow Skills

这不是单个“论文精读 skill”，而是一整条 Zotero 文献处理工作流的打包仓库。

仓库当前包含 7 个核心 skill 和 7 个模板文件，用来覆盖：

- 论文分类批处理与断点续跑
- 论文元数据、批注、全文缓存提取
- PDF/MinerU 全文归档与可追踪链接维护
- 中文精读笔记生成与模板套用
- 研究知识库的模板化维护与跨论文综合
- ResearchVault 内的 Note-first 文献检索与原文核验
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
│   ├── zotero-fulltext-archiver/
│   │   └── SKILL.md
│   ├── zotero-analytical-writer/
│   │   └── SKILL.md
│   ├── research-vault-knowledge-maintainer/
│   │   └── SKILL.md
│   ├── research-vault-ingest-orchestrator/
│       └── SKILL.md
│   └── research-vault-literature-retrieval/
│       └── SKILL.md
├── templates/
│   ├── 论文精读模板.md
│   └── 知识库模板/
│       ├── README_知识库模板说明.md
│       ├── 主题模板.md
│       ├── 概念模板.md
│       ├── 方法模板.md
│       ├── 关系模板.md
│       └── 争议模板.md
```

## 工作流关系

推荐按下面顺序使用：

1. `zotero-collection-manager`
   负责读取某个 Zotero 分类、比对处理日志、筛出未完成文献并串行调度。
2. `zotero-data-fetcher`
   负责抓取单篇论文的元数据、批注、全文缓存和附件信息。
3. `zotero-fulltext-archiver`
   负责归档已处理的 PDF/MinerU 全文，整理图片和元数据，并维护 Note 与 Fulltext 的双向关联。
4. `zotero-analytical-writer`
   负责中文逻辑重构、Frontmatter 提炼、模板套用和 Obsidian 笔记写入。
5. `research-vault-ingest-orchestrator`
   负责按单篇论文编排 Zotero 身份、Fulltext、精读笔记、Knowledge 决策和校验。
6. `research-vault-knowledge-maintainer`
   负责按知识库模板维护主题、概念、方法、关系、争议和综合页，并执行跨论文覆盖与证据审查。
7. `research-vault-literature-retrieval`
   处理 ResearchVault 文献问题时，先从 Analytical Notes 定位论文，再按需进入对应 Fulltext 或 Zotero PDF 核验。

其中：

- `templates/论文精读模板.md` 是精读模板
- `templates/知识库模板/` 包含主题、概念、方法、关系、争议及使用说明模板

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

### `skills/zotero-fulltext-archiver`

用于将 Zotero PDF 或已有 MinerU 结果归档为可追踪的 Fulltext Markdown。它负责保留 stable key、图片路径、前置元数据以及与 Analytical Note 的双向关联。

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

- 先读取当前 Vault 中可访问的模板；若没有项目模板，则使用仓库随附的知识库模板参考
- 区分结构化库字段与原文证据，保留真实 `source_notes`、证据表、边界、缺口和争议
- “全部论文”任务必须建立逐篇 coverage ledger，不能只生成综合页
- 精确结论、公式、阈值、机制和引语需要 Fulltext 支持；缺全文时明确标注延后核验

### `skills/research-vault-literature-retrieval`

用于回答基于当前 ResearchVault 的文献问题。它以 Analytical Notes 为默认检索入口，以相应 Fulltext 或 Zotero PDF 做定向补充与核验，避免无边界扫描全文库。

## 使用建议

- 如果你是把这些 skill 用于 Codex 或类似代理系统，建议保持当前目录结构不变。
- 两种 Writer 优先使用当前 Vault 中已有的模板；模板不可用时使用仓库随附模板。

## 跨环境使用

仓库不要求特定操作系统、用户名、磁盘、Zotero 安装目录、Vault 绝对路径或个人脚本。执行任务时按以下顺序确定工作区：

1. 使用用户在当前任务中明确指定的 Vault/项目目录；
2. 否则使用当前 agent 已打开且确实包含目标文献库的工作区；
3. 如果两者都无法唯一确定，先只读检查当前环境可见的目录标记；仍不明确时再询问用户，不扫描无关的用户目录。

把确定的根目录作为本轮的 `vault_root`，并从中解析现有的论文笔记、全文、知识库和索引目录。目录名可能因项目而异；优先沿用当前 Vault 的真实结构和已有链接，不强制迁移或重命名。路径示例均应使用相对 `vault_root` 的形式。

精读模板和知识模板随仓库提供。若 Vault 内存在其自己的当前模板，先读取并遵循该模板；否则使用仓库内相应模板。不要要求使用者把模板复制到某个固定盘符。

各 skill 会检测当前 agent 实际可用的 Zotero 连接器、PDF 读取、MinerU/文档转换、文件搜索和校验能力。仓库不附带或要求使用者补充私有 runner、验证脚本或机器专用配置。若某一步需要的能力在当前环境不可用，记录准确的部分状态并说明所需输入/能力；不要假装步骤成功，也不要安装或调用个人机器上的代码。

## 后续可继续补充

- 增加示例输入与输出
- 增加安装说明或依赖说明
- 为每个 skill 单独补充测试样例或演示数据
