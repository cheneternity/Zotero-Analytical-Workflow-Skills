# Installation

See [README.md](README.md#installation) for the full install, configuration, migration, troubleshooting, and quick-start instructions.

Shortest Windows setup:

```powershell
git clone https://github.com/cheneternity/Zotero-Analytical-Workflow-Skills.git
cd Zotero-Analytical-Workflow-Skills
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python tools/init_vault.py --vault-root "E:\ResearchVault"
```

Edit the generated `config.toml`, then run `python tools/check_environment.py`. The bundled helpers use only Python 3.11+ standard-library modules.
