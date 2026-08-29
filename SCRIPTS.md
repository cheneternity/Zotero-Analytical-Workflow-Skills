# 脚本说明（Scripts）

本仓库的 skill 文件中引用了若干辅助脚本，但原仓库只包含 `SKILL.md`、`references/` 和
`templates/`，脚本本体未随仓库提供。本目录补齐了这些脚本，全部为**只依赖 Python 3 标准库**、
无第三方依赖的独立脚本。

## 脚本清单

| 脚本 | 位置 | 用途 |
| --- | --- | --- |
| `validate_research_vault_knowledge.py` | `skills/research-vault-knowledge-maintainer/scripts/` | Knowledge Wiki 校验器（`validation-contract.md` 中要求 exit code 0 的硬性门槛） |
| `validate_research_vault_literature_links.py` | `skills/zotero-fulltext-archiver/scripts/` | Note ↔ Fulltext 双向链接、图片、身份字段校验 |
| `run_mineru_production.py` | `skills/zotero-fulltext-archiver/scripts/` | 单篇 PDF 的 MinerU 生产转换（含 Batch 6D 安全护栏） |
| `mineru_batch_runner.py` | `skills/zotero-fulltext-archiver/scripts/` | 串行批量调度单篇转换到 staging 目录 |

## 环境要求

- **Python 3.8+**（全部脚本仅用标准库，无 pip 依赖）
- MinerU 相关脚本需要本机已安装 **MinerU**，否则可用 `--dry-run` 做预检。

---

## 1. validate_research_vault_knowledge.py

Knowledge Wiki 的只读校验器。`research-vault-ingest-orchestrator/references/validation-contract.md`
中明确要求执行并检查 exit code 0，否则整条 Knowledge 入库流程判 `VALIDATION_FAILED`。

### 校验内容

- 页面 `type` 是否为冻结的 6 类（`knowledge-theme/concept/method/relation/controversy/synthesis`）
- 必需 frontmatter 字段是否齐全（`type/title/aliases/status/evidence_count/source_notes/related/last_updated/evidence_status`）
- `status`、`agreement`、`evidence_status` 是否在冻结枚举内
- `evidence_count` 是否等于 `source_notes` 的数量
- `source_notes` 里的每个链接是否真实指向存在的 Analytical Note
- 关系页是否具备 `subject/relation/object/agreement`；争议页是否具备 `agreement`
- 可见 Markdown 正文是否泄漏 HTML 注释或裸 `zotero_key`（应只存在于 `.meta`）
- `wiki/.meta/claims/*.json` 的 Claim ID 格式（`^(REL|CON|SYN)-[A-Z0-9]+(?:-[A-Z0-9]+)+-\d{2}$`）、`evidence_role`、`verification_state`
- `wiki/.meta/gaps/*.json` 的 `gap_provenance` 枚举
- 页面是否登记在 `index.md`（warning 级）

### 用法

```bash
python skills/research-vault-knowledge-maintainer/scripts/validate_research_vault_knowledge.py \
  --vault /path/to/Science_Research_Vault
```

可选参数：

- `--knowledge DIR` / `--notes DIR` / `--fulltext DIR`：手动指定各层目录（默认自动识别 `wiki`/`Research/Papers`/`Research/Fulltext` 及作者原始 `01knowledge`/`02vault`/`03fulltext` 布局）
- `--stale-days N`：`last_updated` 超过 N 天给出 warning

退出码：0 = 无 ERROR；1 = 存在 ERROR（warning 不导致失败）。

---

## 2. validate_research_vault_literature_links.py

Note ↔ Fulltext 双向关联与全文完整性的只读校验器。对应 `zotero-fulltext-archiver` 中
“只有 PDF、Fulltext、图片、Note、链接均有效时，才报告 COMPLETE”的要求。

### 校验内容

- Fulltext frontmatter 必需字段齐全（`type/title/zotero_key/pdf_key/doi/collection/note_path/fulltext_path/zotero_item/zotero_pdf/source_type/page_mapping`）
- `zotero_key` / `pdf_key` 是否为 8 位 Zotero key 格式
- Fulltext 内每个本地图片引用是否真实存在（缺失记为 `MISSING_IMAGES=N`，必须为 0）
- Note 的 `fulltext_path` 是否指向真实存在的 Fulltext 文件，且双方 `zotero_key`/`pdf_key` 一致
- Fulltext 的 `note_path` 是否指向真实存在的 Note 文件，且身份一致

### 用法

```bash
python skills/zotero-fulltext-archiver/scripts/validate_research_vault_literature_links.py \
  --vault /path/to/Science_Research_Vault
```

可选参数：`--notes DIR`、`--fulltext DIR`。退出码 0/1 同上。

---

## 3. run_mineru_production.py

单篇 PDF 的 MinerU 生产转换，落实 `zotero-fulltext-archiver/SKILL.md` 中的 “Batch 6D”
安全护栏（Windows CPU / MinerU 3.x）：

- 将源 PDF 复制为 **ASCII-only 工作副本** `input_<zotero_key>.pdf`，Zotero 附件保持只读
- 记录源文件与工作副本的 SHA-256，不一致则拒绝启动 MinerU
- 使用已验证的 `pipeline` backend
- 每次调用把带时间戳的 stdout/stderr 与阶段转换写入独立 run 目录
- 硬时限（默认 3600 秒）与无进展停止（默认 900 秒）
- 只清理本次调用派生的 MinerU 进程树
- 转换后执行 raw-Markdown gate（前/中/后段均非空）

### 用法

```bash
python skills/zotero-fulltext-archiver/scripts/run_mineru_production.py \
  --pdf "C:/path/to/paper.pdf" --zotero-key Q22PFLNV \
  --output "C:/path/to/output" \
  --mineru "D:/MinerU/.venv/Scripts/mineru.exe" \
  --backend pipeline
```

关键参数：

- `--pdf`：源 PDF（只读，不会被移动）
- `--zotero-key`：父条目 key
- `--mineru`：MinerU 可执行文件路径（默认 `mineru`，即 PATH 上）
- `--backend`：默认 `pipeline`
- `--dry-run`：执行全部预检 + 桩转换，**不真正调用 MinerU**，用于无 MinerU 环境验证链路

### 重要：代理与模型源

MinerU CLI 会在本地启动一个临时 API 服务，并通过 `127.0.0.1` 做健康检查。如果系统设置了 HTTP 代理但未豁免 loopback，健康检查会被代理劫持并返回 503，导致转换卡在 “Timed out waiting for local mineru-api to become healthy”。

本脚本已自动为子进程注入 `no_proxy=127.0.0.1,localhost,::1`，无需手动处理。但还需要：

- 设置 `MINERU_MODEL_SOURCE=modelscope`（或 `huggingface`），否则可能反复走自动检测；
- 首次运行会下载约 7GB 的 pipeline 模型（`PDF-Extract-Kit-1.0`），可先用 `modelscope` 的 `snapshot_download` 预下载；
- 首次加载模型可能超过默认 5 分钟健康检查窗口，可调大 `MINERU_LOCAL_API_STARTUP_TIMEOUT_SECONDS`（例如 1200）。

---

## 4. mineru_batch_runner.py

`run_mineru_production.py` 的串行批量前端。**不会写入正式 Fulltext 目录**——按
`zotero-fulltext-archiver` 约定，批量输出只是外部 staging，逐篇补齐 frontmatter、图片路径、
Note 关联并验证后，才复制进 `Research/Fulltext/<collection>/`。

### Manifest 格式

```json
[
  {"zotero_key": "Q22PFLNV", "pdf": "C:/path/to/paper.pdf"},
  {"zotero_key": "3M4RAI34", "pdf": "C:/path/to/another.pdf"}
]
```

### 用法

```bash
python skills/zotero-fulltext-archiver/scripts/mineru_batch_runner.py \
  --manifest papers.json --staging C:/path/to/mineru-staging \
  --mineru "D:/MinerU/.venv/Scripts/mineru.exe" --backend pipeline
```

每篇论文独立 run 目录，一篇失败不影响其他。`--dry-run` 用于无 MinerU 环境验证调度逻辑。

---

## 自检方法

无 MinerU 环境下可用 `--dry-run` 验证 MinerU 链路；两个校验器可用带错误样例的 vault 验证：

```bash
# Knowledge 校验器应输出 error 并 exit 1（缺失字段 / 非法枚举 / 坏链接等）
python skills/research-vault-knowledge-maintainer/scripts/validate_research_vault_knowledge.py \
  --vault /path/to/fixture-vault

# 链接校验器应抓出缺失图片与坏 fulltext_path
python skills/zotero-fulltext-archiver/scripts/validate_research_vault_literature_links.py \
  --vault /path/to/fixture-vault
```
