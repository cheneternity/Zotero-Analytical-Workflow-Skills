---
name: research-vault-literature-retrieval
description: "ResearchVault 文献知识问题的默认检索技能。用于论文、概念、理论、方法、变量、数据、证据、文献比较、研究结论和研究方向问题：先从根索引与分析笔记召回论文，再按问题需要解析 MinerU Fulltext，必要时回到 Zotero PDF 验证。纯 Skill/Python/Git/文件整理/MinerU 调试等操作任务不自动触发文献检索。"
---

# Research Vault Literature Retrieval

在 `D:\ResearchVault` 内执行“笔记发现、全文取证、PDF 终检”的渐进式检索。

## 1. 适用范围与路径兼容

- 文献知识问题默认使用本技能：论文、概念、理论、方法、变量、数据、结论、证据、比较和研究方向。
- 纯操作任务不先做文献检索：修改 Skill/Python、Git、文件移动、MinerU 调试、Obsidian 配置和目录整理。
- 依次读取根索引（存在则读取，缺失则跳过）：
  1. `文献索引.md`
  2. `研究主题索引.md`
  3. `研究方法索引.md`
  4. `字段补全检查.md`
- 分析笔记优先使用 `note/`；若该目录不存在，兼容当前 Vault 的 `论文库/`。
- 正式全文目录为 `fulltext/`。`MinerU_batch/` 只作为历史迁移来源，不作为默认检索目录。
- 默认只读。只有用户明确要求时才修改 Vault 文件。

## 2. 三层证据

### LEVEL 1 — Analytical Note

用于召回相关论文、主题归纳、高层方法比较、研究方向梳理和已整理的研究发现。它解释“哪篇论文与问题有关”，不是作者原始全文。

### LEVEL 2 — MinerU Fulltext

用于 definition、exact wording、作者原话、methods、data、variable、equation、model、robustness、mechanism、table/figure caption 和原始结论。全文必须保持论文原文属性。

### LEVEL 3 — Original Zotero PDF

用于可靠页码、公式/表格/图像/数值核对、OCR 异常、MinerU 可疑内容，以及用户明确要求的 PDF 定位。页码无法验证时明确写“页码尚未可靠验证”，不得猜测。

核心原则：**DISCOVER FROM NOTES. VERIFY FROM FULLTEXT. FINAL-CHECK WITH PDF.**

## 3. 证据路由

先判断问题模式：

- `NOTE_ONLY`：相关论文有哪些、主题综述、高层方法/结论比较。
- `FULLTEXT_REQUIRED`：具体定义、变量计算、方法参数、模型方程、精确结论或作者原话。
- `PDF_VERIFY_REQUIRED`：页码、公式、表格、图表数值、OCR 疑点或用户明确要求 PDF。

执行顺序：

1. 读索引，缩小候选范围。
2. 搜索 `note/` 或兼容的 `论文库/`，完整阅读与任务规模相称的分析笔记。
3. 从笔记的 `zotero_key` 解析论文；优先使用 `fulltext_path`。
4. 若缺少 `fulltext_path`，按 `zotero_key` 查找 `fulltext/<collection>/<zotero_key>.md`。
5. 只有主键无法解析且标题匹配唯一时才使用标题 fallback；多条匹配不得猜测。
6. 对指定全文按 section、关键词和同义词检索；精确引用必须读取命中位置前后的自然段或逻辑 block。
7. 需要 PDF 终检时，使用 `pdf_key`；未验证页码不得生成带猜测 page 的 Zotero URI。

不要第一步扫描整个 `fulltext/`。只有用户明确要求全文库搜索、寻找精确英文术语、笔记召回不足，或询问正文出现某术语的论文时，才允许 Vault-wide Fulltext Search；命中后仍回到对应分析笔记获取元数据和背景。

## 4. 精确证据规则

- 原文只能来自 MinerU Fulltext 或 Original PDF；不得从中文笔记反向生成英文 quote。
- 引用至少连同前后适量上下文阅读，并检查 `not`、`however`、`although`、条件句、假设、稳健性限定和局限，避免断章取义。
- Fulltext 缺失时，不得把模型记忆、摘要改写或 `.zotero-ft-cache` 冒充作者原文；应明确说明 Vault 证据不足。
- PDF 页码只在可靠映射或实际打开 PDF 验证后提供。
- 维持可追踪链路：问题 → 命中索引 → 分析笔记 → `zotero_key` → `fulltext_path` → section/context → PDF page（如已验证）→ 回答。

## 5. 回答模式

按任务选择，不机械套用同一结构：

- **Exact Fact / Definition**：定义 → 原文 → 中文解释 → 来源定位。
- **Single Paper Evidence**：结论 → 原文证据 → 方法/上下文 → 来源。
- **Multi-paper Comparison**：逐篇列出证据后再比较，不能只比较中文摘要。
- **Research Synthesis**：结论 → 支持文献 → 差异/争议 → 对研究的启发。
- **Vault Coverage Check**：已有证据 → 缺失证据 → 当前能否支持结论。

按实际任务规模渐进读取：单篇问题读 1 篇；简单比较读 2–5 篇；综述或研究方向梳理覆盖所有明显相关论文，不设置固定的“只读 1–3 篇”上限。

## 6. Vault-only 与索引隔离

- 默认只使用根索引、分析笔记、MinerU Fulltext 和 Zotero PDF。
- 证据不足时先写 `Vault 中未找到足够依据`，并说明是笔记缺失、全文缺失、主键冲突还是页码未验证。
- 只有用户明确要求结合外部论文或联网搜索时才切换外部证据模式。
- 普通文献索引只纳入 `type: literature-note` 或现有 `#literature-note` 笔记；`type: literature-fulltext` 不得进入普通文献索引。
- 不因全文缺失而重写现有笔记；增量任务只补全文链接和验证信息。

## 7. 搜索示例

```powershell
rg -n --glob '*.md' "关键词1|keyword2|method|variable" 'D:\ResearchVault\note'
rg -n --glob '*.md' "关键词1|keyword2|method|variable" 'D:\ResearchVault\论文库'
rg -n "building height|mean building height|BH" 'D:\ResearchVault\fulltext\对应分类\ITEMKEY.md'
```
