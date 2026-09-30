# Zotero Analytical Workflow Skills

A portable set of agent Skills and local tools for the workflow:

```text
Zotero → MinerU Fulltext → Analytical Notes → Knowledge → Literature Retrieval
```

The repository is the canonical source for the complete workflow and for the Literature Retrieval Skill. New Vault content uses one layout: `01knowledge/`, `02vault/`, `03fulltext/`, and `模板/`. No tool requires the author's drive letters or private scripts.

## Requirements

- Python 3.11 or newer. The bundled tools use only the Python standard library.
- Zotero Desktop if reading the local Zotero database or attachments.
- MinerU is optional; install it separately if PDF conversion is required. The conversion runner accepts the executable path in configuration.
- Obsidian is optional for editing and navigating Markdown. Dataview is optional for users whose own index pages use Dataview.
- `rg` (ripgrep) is optional. The Skills can use the agent's available project search tools when it is absent.

No Zotero database, PDF, private Vault content, API package, or credential is included.

## Installation

```powershell
git clone https://github.com/cheneternity/Zotero-Analytical-Workflow-Skills.git
cd Zotero-Analytical-Workflow-Skills
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python tools/init_vault.py --vault-root "E:\ResearchVault"
```

On macOS/Linux, use:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python tools/init_vault.py --vault-root "$HOME/ResearchVault"
```

`init_vault.py` creates only missing directories, copies only missing bundled templates, and creates a local `config.toml` only if it does not exist. It does not modify existing research files or Zotero data.

Set the Zotero and MinerU locations in the generated, git-ignored `config.toml` (format shown below), then check the setup:

```powershell
python tools/check_environment.py
```

The checker is read-only. Zotero, MinerU and `rg` are optional capabilities and show `WARN` when not configured; missing Python, Vault folders or bundled tools show `FAIL`.

## Configuration

Copy [`config.example.toml`](config.example.toml) or let the initializer create `config.toml`. Paths are local filesystem paths; use TOML strings and forward slashes for portable examples:

```toml
[paths]
vault_root = "E:/ResearchVault"
zotero_data_dir = "C:/Users/alex/Zotero"
mineru_executable = "C:/Tools/MinerU/mineru.exe"
archive_root = "E:/ResearchVault/_staging/mineru"
```

Any value can be overridden per process with `RESEARCHVAULT_ROOT`, `ZOTERO_DATA_DIR`, `MINERU_EXECUTABLE`, or `RESEARCHVAULT_ARCHIVE_ROOT`. `RESEARCHVAULT_CONFIG` selects another TOML config file. CLI flags override configuration where offered. Do not commit your local `config.toml`.

## Canonical Vault layout

```text
<VAULT_ROOT>/
├── 01knowledge/
│   ├── index.md
│   ├── log.md
│   ├── _index/
│   └── .meta/                 # claims and gaps; machine metadata only
├── 02vault/
│   ├── _index/                 # four literature indexes
│   └── <collection>/<paper>.md
├── 03fulltext/
│   └── <collection>/<zotero_key>.md
└── 模板/
    ├── 论文精读模板.md
    └── 知识库模板/             # six canonical Knowledge templates
```

New Analytical Notes go only to `02vault/`; new Fulltext goes only to `03fulltext/`. Obsidian links use `/` and paths relative to the Vault root. Historical `note/`, `论文库/`, `fulltext/`, `knowledge/`, and root-level indexes are migration inputs, not new-write destinations.

## Quick start

### Read Zotero metadata and attachments

```powershell
python tools/zotero_readonly_fetch.py --key ABCD1234
```

The helper uses Zotero's local SQLite database in read-only mode and emits JSON with parent `zotero_key`, PDF attachment `pdf_key`, title, authors, year, DOI, collections, annotations, PDF path when resolvable, and `.zotero-ft-cache` path when present. It never edits the Zotero database. It discovers common Windows, macOS and Linux data directories; use `--data-dir` or `ZOTERO_DATA_DIR` if the Zotero profile is elsewhere. A locked/upgrading database returns a clear failure; retry after Zotero finishes syncing or use the Zotero API/export route.

### Convert one PDF with MinerU (optional)

```powershell
python tools/run_mineru_production.py --input "E:\Papers\paper.pdf" --output "E:\ResearchVault\_staging\mineru\ABCD1234-run1"
```

The output directory must not already exist. The runner preserves the source PDF, writes a hashed working copy, logs the MinerU command, enforces a timeout, and reports success only when MinerU exits cleanly and produces non-empty Markdown. It does not promote output into the Vault; inspect it and use the Fulltext Archiver Skill to create a canonical `03fulltext/...` file. MinerU's CLI must be installed separately. Conversion should work on Windows, macOS or Linux when the selected MinerU executable supports that platform. On Windows, keep the MinerU executable and staging path accessible to the current account; if a specific MinerU build cannot handle non-ASCII paths, choose an ASCII-only `archive_root`.

### Validate local Vault files

```powershell
python skills/research-vault-knowledge-maintainer/scripts/validate_research_vault_knowledge.py --vault "E:\ResearchVault"
python tools/validate_research_vault_literature_links.py --vault "E:\ResearchVault"
```

Both validators are read-only and accept any Vault root. The Knowledge validator checks the frozen page schema and source links. The link validator checks `zotero_key`, `pdf_key`, Note ↔ Fulltext paths, canonical placement and legacy `fulltext/` read fallback.

### Agent Skills workflow

The repository's Skills guide the agent through paper-level ingestion, analysis, Knowledge decisions, and retrieval. These stages are not one undocumented all-in-one CLI: use the installed Skills from a Codex/compatible agent. A minimal run is: fetch one Zotero parent item → archive/convert its PDF when needed → write its Note from the bundled template → decide whether Knowledge merits an update → run both validators. The Retrieval Skill is Note-first and follows selected evidence through Fulltext to the original Zotero PDF when needed.

Install the standalone Retrieval Skill from [Research-Vault-Literature-Retrieval](https://github.com/cheneternity/Research-Vault-Literature-Retrieval). Its published Skill files mirror the canonical implementation at `skills/research-vault-literature-retrieval/` in this repository; the mirror includes a synchronization check and must be updated with the canonical source.

## Migration from older Vault layouts

The tools never reorganize an existing Vault automatically. Back up the Vault, then move or copy old files only after confirming their identity and links:

- `论文库/<collection>/` and `note/<collection>/` → `02vault/<collection>/`
- `fulltext/<collection>/<zotero_key>.md` → `03fulltext/<collection>/<zotero_key>.md`
- root literature indexes → `02vault/_index/`
- old `knowledge/` → `01knowledge/` after reviewing `.meta/` sidecars and links
- prior absolute Vault paths (including `D:\ResearchVault`) → relative Vault paths

The validators and retrieval instructions can read historical `fulltext/` links during transition. Update `note_path`, `fulltext_path`, reciprocal links, images, and indexes when files are migrated. Do not create new content in both old and canonical directories.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Zotero PDF not found | Confirm the parent `zotero_key`, the attachment's `pdf_key`, `storage/<pdf_key>/`, and whether the attachment is linked externally. The helper reports only files that exist. |
| MinerU missing | Configure `paths.mineru_executable` or `MINERU_EXECUTABLE`; verify that it is an executable supported by your MinerU installation. |
| `rg` missing | Optional dependency; use the agent's built-in file search or install ripgrep using your OS package manager. |
| Vault path error | Check `paths.vault_root` or `RESEARCHVAULT_ROOT`; run `python tools/init_vault.py --vault-root <your-path>` to create missing structure. |
| Template missing | Re-run the initializer; it copies only missing templates and leaves existing versions untouched. |
| Knowledge validator fails | Read each `ERROR` code; page `evidence_status` is `fulltext_verified`, `note_only`, or `mixed`. Claim `note_supported` belongs in claim metadata, not page frontmatter. |
| Note ↔ Fulltext validation fails | Check reciprocal `note_path` and `fulltext_path`, key equality, and `03fulltext/` canonical placement. Legacy `fulltext/` may be read during migration. |
| Chinese path / Windows conversion issue | Confirm Python and MinerU have access to the path. If the installed MinerU backend fails on non-ASCII paths, set an ASCII-only `archive_root`; the source PDF remains unchanged. |
| Zotero database is locked | Let Zotero finish sync/upgrade, close Zotero, then retry. The helper never switches to write access. |

## Tests and CI

Run the dependency-free release smoke tests with `python -m unittest discover -s tests -v`. GitHub Actions runs those tests and Python syntax compilation without requiring a live Zotero profile, MinerU installation, PDF, or private Vault.
