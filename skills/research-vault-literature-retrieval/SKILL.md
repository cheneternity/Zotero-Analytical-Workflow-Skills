---
name: research-vault-literature-retrieval
description: "ResearchVault 文献知识问题的默认检索技能。先从 02vault/_index 和 D:\\ResearchVault\\02vault 的 Analytical Notes 定位相关论文，再按需要定向进入对应 D:\\ResearchVault\\03fulltext MinerU Markdown，必要时回到 Zotero PDF 验证。若用户消息以‘基于当前 ResearchVault 项目文件检索’（或明确要求基于当前 ResearchVault 项目文件作答）开头，必须优先执行严格的项目文件检索后再回答。纯 Skill/Python/Git/文件整理/MinerU 调试等操作任务不自动触发文献检索。"
---

# Research Vault Literature Retrieval

## 核心定位

本技能固定执行：

NOTE-FIRST RETRIEVAL.
TARGETED FULLTEXT FOLLOW-UP.

Analytical Notes 负责定位和理解论文；MinerU Fulltext 负责补充、核验、细化、追溯和引用原文；Original Zotero PDF 负责最后一级页面、公式、表格、图像和 OCR 验证。

不要把论文库和全文库作为两个平级数据库并行搜索，也不要把 Fulltext 当作默认论文发现层。

## 目录与身份规则

- D:\ResearchVault\02vault 是 PRIMARY RETRIEVAL LAYER 和 SEMANTIC RETRIEVAL LAYER。
- D:\ResearchVault\03fulltext 是 SUPPLEMENTARY ORIGINAL-TEXT LAYER 和 SOURCE DETAIL LAYER。
- 两个目录必须物理分离；不得把 Fulltext 放入 02vault，也不得把 Analytical Note 放入 03fulltext。
- 两层属于同一篇论文时，统一使用 zotero_key。
- Note → Fulltext 优先通过 fulltext_path，其次通过 zotero_key，最后才允许唯一的 title fallback。
- Fulltext → Note 通过 note_path，并同时核对 zotero_key 和 pdf_key。
- 标题多重匹配、主键冲突或路径指向不一致时，停止该条目并报告冲突，不得猜测。
- Fulltext 不进入普通 Dataview 文献索引，但 Retrieval 必须能够跨目录访问它。

## Activation Policy

默认使用本技能处理：

- 论文、概念、理论、方法、变量、数据、结论和文献证据
- 多论文比较、研究方向、文献综述
- 某个说法是否被当前 Vault 支持

以下纯操作任务不先执行文献检索：

- 修改 Skill、Python 或 Git
- 文件移动、目录整理和 Obsidian 配置
- MinerU 调试、环境检查或辅助脚本维护

默认只读。只有用户明确要求时才修改 Vault 文件。

### High-priority project-file trigger

如果用户消息以以下固定短语开头：

`基于当前 ResearchVault 项目文件检索`

立即进入 `STRICT_RESEARCHVAULT_RETRIEVAL`。以下近似表达也触发同一模式：

- `基于 ResearchVault 项目文件检索`
- `基于当前 ResearchVault 检索`
- `从当前 ResearchVault 项目文件中检索`
- `先检索 ResearchVault 再回答`

固定短语是最高优先级触发词。严格模式只改变检索启动顺序，不改变本技能已有的 canonical identity、Note/Fulltext 证据链、证据强度、引用追踪、Zotero 验证和只读保护规则。

## Strict project-file retrieval mode

严格模式必须遵守 `PROJECT_FILE_RETRIEVAL_FIRST`：先检索当前 ResearchVault 项目文件，再分析和回答。模型记忆、之前会话结论、Knowledge 概括、缓存回答或文件名印象只能帮助生成搜索词，不能作为本轮 ResearchVault 证据。

执行顺序固定为：

`USER QUESTION → PARSE RESEARCH QUESTION → SEARCH CURRENT RESEARCHVAULT PROJECT FILES → IDENTIFY CANDIDATE PAPERS → RESOLVE CANONICAL SOURCE IDENTITY → LOCATE REAL ANALYTICAL NOTES → LOCATE MATCHING FULLTEXTS → VERIFY IMPORTANT CLAIMS WHEN REQUIRED → CLASSIFY EVIDENCE → SYNTHESIZE ANSWER`

严格模式下，优先使用当前项目环境实际返回的文件检索结果。开始检索时不要要求用户提供 Windows absolute path、精确 Note/Fulltext 文件名、Zotero key 或 DOI；只有项目文件结果不足以解决 source identity 时，才进一步使用这些定位信息。

对核心来源尽量建立并核验：`Canonical paper ↔ actual Analytical Note ↔ matching Fulltext`。Analytical Note 用于理解研究设计、数据、方法、主要发现、局限和主题关系；Fulltext 用于核验重要结论、数值、模型结果、显著性、因果性、变量定义、阈值和作者原始解释。沿用本技能已有证据 schema，不另建第二套 evidence taxonomy。

如果项目文件检索已返回实际的 Analytical Note 或 Fulltext 文件结果，继续沿用这些实际结果作为回答来源，并保留两者的对应关系。不要把正常的项目文件检索改造成等待客户端内部绑定状态的诊断流程；项目文件是否可由客户端直接打开属于交付层验证，不是启动检索的前置条件。路径只能作为调试、文件定位或项目文件结果不可用时的 fallback，不能覆盖已经获得的实际文件结果，也不能成为默认科研来源交付形式。

严格模式的普通回答默认采用：

1. `## 结论`：直接回答问题；
2. `## 关键证据`：综合本轮实际检索到的文献，并在必要处标明已有证据等级；
3. `## 来源文件`：列出本轮实际使用的 Analytical Note 和对应 Fulltext 文件结果，尽量保持项目环境可打开的实际文件引用。

用户未使用上述固定或近似触发语时，保留本技能原有的普通触发逻辑；不要把闲聊、简单改写或非文献操作任务强制升级为严格 ResearchVault 全库检索。

## Knowledge-aware routing

Keep NOTE-FIRST RETRIEVAL. Knowledge (`D:\ResearchVault\01knowledge`) is an optional derived-synthesis routing layer for concepts, methods, relationships, controversies, and research-direction/gap questions. It never replaces the Analytical Note or original-text evidence chain.

Classify each question with [references/retrieval-routing.md](references/retrieval-routing.md) before retrieval. For paper-specific and exact-source questions, begin directly with the Analytical Note. For broad synthesis, start from Knowledge only to identify the relevant claims/pages, then return to their supporting Notes; use targeted Fulltext only for the precise point that needs verification.

Knowledge-assisted routing does not authorize a default fulltext-wide scan, raw-key-heavy user output, or treating a Knowledge sentence as an original-paper conclusion.

## 默认 Retrieval Workflow

### STEP 1 — Understand Question

判断用户主要是在问主题、相关论文、方法、变量、结论、定义、原文、页码，还是研究方向。

### STEP 2 — Analytical-note Index

按以下顺序读取 `D:\ResearchVault\02vault\_index\` 中存在的页面，缺失则跳过：

1. 文献索引.md
2. 研究主题索引.md
3. 研究方法索引.md
4. 字段补全检查.md

索引只用于导航和召回，不替代原文证据。

### STEP 3 — Analytical Note Retrieval

正常文献发现只能先搜索 D:\ResearchVault\02vault。搜索 title、theme、methodology、core_variable、key_finding、relevance、中文正文、英文术语、作者和 keywords。

绝不能以 D:\ResearchVault\03fulltext 作为正常检索第一步。

### STEP 4 — Read Candidate Notes

读取与任务规模相称的候选笔记，建立：

paper、theme、method、variable、finding、relevance、zotero_key、fulltext_path。

单篇问题不无意义打开全文；高层综述和方法比较优先基于 Notes 回答。

### STEP 5 — Evidence Decision

只使用以下三种模式：

- NOTE_ONLY：Notes 已足以回答相关论文、主题归纳、高层方法比较、总体结论或研究方向框架。
- NOTE_PLUS_FULLTEXT：先由 Note 确定论文、答案框架和语义上下文，再进入对应 Fulltext 补充定义、变量、方法细节、原始结论或 exact quote。
- PDF_VERIFY_REQUIRED：涉及 PDF 页码、MinerU OCR 疑点、复杂公式、表格结构、图像、图表数值或用户明确要求 PDF 页面。

### STEP 6A — NOTE_ONLY

只基于已读取的 Analytical Notes 回答；如果 Notes 已经足够，不为了形式打开 Fulltext。

### STEP 6B — NOTE_PLUS_FULLTEXT

1. 从已定位的 Note 读取 fulltext_path；缺失时读取 zotero_key。
2. 按 fulltext_path → zotero_key → 唯一 title fallback 解析对应 Fulltext。
3. 只打开已经由 Notes 定位的论文全文，不重新扩大论文集合。
4. 继承 Note 的 theme、methodology、core_variable、key_finding、relevance、关键词和英文术语。
5. 用这些上下文在对应 MinerU Markdown 中做 targeted search。
6. 读取命中位置前后 1–3 个自然段或相邻逻辑 block。
7. 用 Fulltext 补充、核验、细化和追溯 Note，再回答。

### STEP 6C — PDF VERIFY

只有 Fulltext 不足或用户要求最终页面验证时，才进入 Original Zotero PDF。页码只有可靠映射或实际 PDF 验证后才能提供；否则明确写 page unknown，不猜页码。

## 四条强规则

### Primary Retrieval Rule

Analytical Notes are the default and primary source for identifying relevant papers. Never begin normal literature discovery from fulltext/.

### Fulltext Follow-up Rule

Open MinerU Fulltext only after the corresponding paper has been resolved through its Analytical Note，除非用户明确要求 exact-term search 或补充全文召回。

### Context Inheritance Rule

进入 Fulltext 时必须继承 Note 已提供的搜索词、变量、方法、发现、概念和上下文；不得脱离 Note 重新宽泛搜索。

### Evidence Supplement Rule

Use MinerU Fulltext to supplement, verify, refine, trace, and quote Analytical Notes—not to replace Analytical Note retrieval.

## Fulltext 搜索范围

默认只对已定位论文做 targeted search，例如：

D:\ResearchVault\03fulltext\能耗\TTD9LZ5H.md

根据 Note 中的 building height、building volume、building lifespan、random forest、SHAP 或对应英文原句搜索。

禁止默认执行 D:\ResearchVault\03fulltext 的全库扫描。仅以下情况允许例外：

1. 用户明确要求直接在全文中搜索某术语；
2. 用户要求找正文中出现某个确切词组的论文；
3. 用户要核验 Notes 无法判断的具体术语；
4. Notes 明显召回不足，需要明确标记为 supplementary fulltext recall。

即使发生例外，仍应回到对应 Note 获取论文身份和背景。

## 证据与引用规则

- 原文只能来自 MinerU Fulltext 或 Original Zotero PDF，不得由中文 Note 反向生成英文 quote。
- Quote 必须读取上下文，并检查 however、although、not、only when、conditional、hypothesis、limitation 和 robustness 等限定。
- Fulltext 缺失时明确说明“该 analytical note 当前尚未建立 MinerU fulltext”，不得用模型记忆补论文内容。
- 默认 Vault-only。只有用户明确要求外部论文或联网搜索时才切换外部证据模式。
- 保持可追踪链路：问题 → 索引 → Note → zotero_key → fulltext_path → section/context → PDF page（如已验证）→ 回答。

## 研究方向与跨论文比较

研究方向梳理：

Root Index → 大量 Analytical Notes → 主题结构和研究空缺 → 筛选关键论文 → 仅对关键论据进入 Fulltext → 形成判断。

跨论文比较：

先用 Notes 建立方法、变量或结论矩阵，再只对需要确认的定义、指标、参数、模型和原话进入各自 Fulltext。不得重新完整读取所有全文，也不得因为某篇全文出现新概念而自动扩大论文集合。

## Index Isolation Rule

普通文献索引、研究主题索引、研究方法索引和字段补全检查继续只识别 Analytical Notes：

- 现有 #literature-note
- 或 type: literature-note

type: literature-fulltext 不得作为普通文献记录出现。物理隔离不等于检索隔离：Fulltext 仍可被 Retrieval 跨目录定向读取。

## 五个逻辑测试

1. “有哪些论文研究建筑高度与环境绩效？”  
   Root Index → 论文库 → Analytical Notes → 返回相关论文，不扫描 fulltext。
2. “A、B、C 三篇如何定义 building height？”  
   Notes → 确认 A/B/C → 分别 resolve Fulltext → 只搜索三篇全文 → 比较定义。
3. “第二篇作者关于结论的原话？”  
   第二篇 Note → fulltext_path → Fulltext → exact quote → context。
4. “这句话在 PDF 第几页？”  
   Note → Fulltext → page mapping 或 PDF Verify；不可靠时返回 unknown。
5. “根据整个论文库梳理研究方向？”  
   大量 Analytical Notes → 研究框架 → 关键论文 → 选择性 Fulltext 核验，不读取几十篇全文。

最终原则：

SEPARATE STORAGE.
SHARED IDENTITY.
RETRIEVE FROM NOTES.
TRACE INTO FULLTEXT.
VERIFY THE SOURCE.

## 综述型问题的 paper-level retrieval state machine

以下问题必须按 paper-level candidate pool 处理：文献综述、已有研究发现、共识与争议、指标方向比较、方法比较、研究缺口、直接/间接/中介效应。

1. **Topic discovery**：Knowledge Notes 只负责导航同义词、指标、方法和候选研究；正式候选必须回到 `scope=papers` 的 Analytical Note 结果。
2. **Candidate collection**：为每个语义主题维护候选池，并跨所有 query 合并。优先使用 Gateway 返回的 `paper_id`，必要时依次使用 Zotero Key、DOI、唯一规范化标题。Analytical Note、Fulltext 和 Knowledge Note 的文件命中不得直接当作论文数；同一论文多次命中只能计 1 篇。
3. **Per-query accounting**：每次 Search 都记录 `query`、`raw_hits`、`unique_papers_this_query`、`new_unique_papers`、`master_unique_papers`、`page`、`has_more` 和 `next_page`。Gateway 的 `total_unique_papers` 是该 query 跨页的总数，不是跨 query 的候选池总数；跨 query 的池必须由模型继续合并。
4. **Pagination and coverage**：使用 `scope=papers` 和 `page_size=30`（旧客户端可用 `top_k=30`）。只要 `has_more=true` 且候选池未达到最低覆盖，就必须请求 `next_page`；不能把当前页、文件数或核验数当作论文数。综述候选池最低目标为 15 篇，默认目标为 20 篇，一般覆盖范围为 20–30 篇。
5. **Allowed stopping conditions**：候选收集仅可在以下任一条件成立时停止：`master_unique_papers >= 20`（或用户明确指定的目标）；已执行多个语义不同的 query 且每个 query 的所有页面均已到尾部（`has_more=false`）；或连续 2–3 个概念不同的扩展 query 均只产生 `new_unique_papers <= 1`，且没有出现新的指标、机制、方法、尺度或结果类型。单个 zero-new query、结果重叠、已经找到几篇高相关论文或已经核验 5–7 篇，均不是停止理由。若最终少于 15 篇，必须报告 query、页面、`has_more` 和候选统计，并区分数据不足与检索覆盖不足。
6. **Verification and synthesis**：完成候选池和初筛后，才选择 CORE/RELEVANT 论文进入 `Analytical Note → matching Fulltext` 核验；最后再综合一致方向、冲突方向、直接效应和中介机制，并报告检索覆盖块。
