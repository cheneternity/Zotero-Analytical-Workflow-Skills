from __future__ import annotations

import os
import re
import contextlib
import hashlib
import io
import json
import sqlite3
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "skills/research-vault-knowledge-maintainer/scripts"))

from init_vault import initialize
from validate_research_vault_knowledge import validate as validate_knowledge
from validate_research_vault_literature_links import validate as validate_links


class PortabilityTests(unittest.TestCase):
    def test_config_example_loads_and_requires_no_packages(self):
        import tomllib
        with (ROOT / "config.example.toml").open("rb") as stream:
            data = tomllib.load(stream)
        self.assertEqual(set(data["paths"]), {"vault_root", "zotero_data_dir", "mineru_executable", "archive_root"})

    def test_initializer_is_idempotent_and_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault, config = base / "custom-vault", base / "local-config.toml"
            (vault / "模板").mkdir(parents=True)
            existing = vault / "模板/论文精读模板.md"
            existing.write_text("user template", encoding="utf-8")
            first = initialize(vault, config)
            self.assertEqual(existing.read_text(encoding="utf-8"), "user template")
            self.assertTrue((vault / "01knowledge/.meta/claims").is_dir())
            self.assertTrue((vault / "02vault/_index").is_dir())
            self.assertTrue((vault / "03fulltext").is_dir())
            self.assertTrue(config.is_file())
            import tomllib
            with config.open("rb") as stream:
                saved_config = tomllib.load(stream)
            self.assertEqual(Path(saved_config["paths"]["vault_root"]).resolve(), vault.resolve())
            self.assertTrue(first)
            self.assertEqual(initialize(vault, config), [])

    def test_environment_checker_cli_on_initialized_arbitrary_root(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault, config = base / "portable-root", base / "config.toml"
            initialize(vault, config)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/check_environment.py"), "--config", str(config)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS: vault_root", result.stdout)
            self.assertIn("WARN: MinerU", result.stdout)

    def test_knowledge_templates_follow_page_schema(self):
        directory = ROOT / "templates/知识库模板"
        files = list(directory.glob("*模板.md"))
        self.assertEqual(len(files), 6)
        allowed_page = {"fulltext_verified", "note_only", "mixed"}
        for path in files:
            text = path.read_text(encoding="utf-8")
            front = re.search(r"\A---\s*\n(.*?)\n---", text, re.S).group(1)
            match = re.search(r"(?m)^evidence_status:\s*[\"']?([^\s\"']+)", front)
            self.assertIsNotNone(match, path.name)
            self.assertIn(match.group(1), allowed_page, path.name)
            self.assertNotIn("mechanistic", text)
            self.assertNotRegex(text, r"\bcounter\b")
        synthesis = (directory / "综合模板.md").read_text(encoding="utf-8")
        self.assertNotIn("gap_provenance:", synthesis)

    def test_knowledge_validator_enforces_frozen_claim_and_gap_enums(self):
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp)
            (vault / "01knowledge/.meta/claims").mkdir(parents=True)
            (vault / "01knowledge/.meta/gaps").mkdir(parents=True)
            claim = vault / "01knowledge/.meta/claims/REL-URBAN-HEAT-01.json"
            gap = vault / "01knowledge/.meta/gaps/GAP-01.json"
            claim.write_text(json.dumps({
                "claim_id": "REL-URBAN-HEAT-01", "page_path": "01knowledge/page.md",
                "section_heading": "Findings", "normalized_statement": "Test", "statement_hash": "abc",
                "evidence_role": "mechanistic", "verification_state": "note_supported", "source_notes": [],
            }), encoding="utf-8")
            gap.write_text(json.dumps({"gap_provenance": "evidence_backed"}), encoding="utf-8")
            issues, summary = validate_knowledge(vault)
            self.assertEqual(summary["errors"], 2, issues)
            self.assertEqual({item["code"] for item in issues if item["level"] == "ERROR"}, {"EVIDENCE_ROLE", "GAP_PROVENANCE"})

    def test_required_repository_paths_exist(self):
        required = (
            "tools/run_mineru_production.py", "tools/zotero_readonly_fetch.py",
            "tools/validate_research_vault_literature_links.py", "tools/check_environment.py",
            "tools/init_vault.py", "skills/research-vault-knowledge-maintainer/scripts/validate_research_vault_knowledge.py",
            "templates/知识库模板/综合模板.md",
        )
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_no_machine_specific_paths_in_runtime_or_skills(self):
        forbidden = re.compile(r"(?i)(?:D:|C:)\\(?:ResearchVault(?:_Archive)?|research|MinerU)(?:\\|\b)")
        paths = list(ROOT.rglob("*.py")) + list((ROOT / "skills").rglob("SKILL.md"))
        paths = [p for p in paths if ".git" not in p.parts and "__pycache__" not in p.parts]
        for path in paths:
            self.assertIsNone(forbidden.search(path.read_text(encoding="utf-8")), str(path))

    def test_internal_markdown_file_links_resolve(self):
        link_re = re.compile(r"\]\(([^)]+)\)")
        for path in list(ROOT.rglob("*.md")):
            if ".git" in path.parts:
                continue
            for target in link_re.findall(path.read_text(encoding="utf-8")):
                if re.match(r"^[a-z]+://", target, re.I) or target.startswith("#"):
                    continue
                clean = target.split("#", 1)[0]
                if not clean:
                    continue
                resolved = (path.parent / clean).resolve()
                self.assertTrue(resolved.exists(), f"{path.relative_to(ROOT)} -> {target}")

    def test_skill_reference_paths_exist(self):
        file_ref = re.compile(r"(?:references|scripts|tools|templates)/[A-Za-z0-9_./\-\u4e00-\u9fff]+(?:\.md|\.py|\.yaml|\.yml|/)")
        for path in list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.yaml")) + list(ROOT.rglob("*.yml")):
            if ".git" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for found in file_ref.findall(text):
                relative = found.rstrip("/")
                if "<" in relative or relative.endswith("..."):
                    continue
                resolved = (path.parent / relative).resolve()
                root_resolved = (ROOT / relative).resolve()
                nested_match = next(ROOT.rglob(relative), None)
                if not (resolved.exists() or root_resolved.exists() or nested_match) and relative.startswith(("tools/", "scripts/", "references/", "templates/")):
                    self.fail(f"missing referenced file: {path.relative_to(ROOT)} -> {relative}")

    def test_knowledge_and_link_validators_on_clean_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp)
            note = vault / "02vault/urban/paper.md"
            fulltext = vault / "03fulltext/urban/ABCD1234.md"
            page = vault / "01knowledge/b概念/concept.md"
            for path in (note, fulltext, page):
                path.parent.mkdir(parents=True, exist_ok=True)
            note.write_text('---\ntype: literature-note\nzotero_key: ABCD1234\npdf_key: PDF12345\nfulltext_path: 03fulltext/urban/ABCD1234.md\n---\n', encoding="utf-8")
            fulltext.write_text('---\ntype: literature-fulltext\nzotero_key: ABCD1234\npdf_key: PDF12345\nnote_path: 02vault/urban/paper.md\n---\nOriginal text.\n', encoding="utf-8")
            page.write_text('---\ntype: knowledge-concept\ntitle: Test\naliases: []\nstatus: developing\nevidence_count: 1\nsource_notes:\n  - "[[02vault/urban/paper|Paper]]"\nrelated: []\nlast_updated: 2026-01-01\nevidence_status: note_only\n---\n\nContent.\n', encoding="utf-8")
            link_issues, link_summary = validate_links(vault)
            knowledge_issues, knowledge_summary = validate_knowledge(vault)
            self.assertEqual(link_summary["errors"], 0, link_issues)
            self.assertEqual(knowledge_summary["errors"], 0, knowledge_issues)
            python = Path(sys.executable)
            for script in (
                ROOT / "tools/validate_research_vault_literature_links.py",
                ROOT / "skills/research-vault-knowledge-maintainer/scripts/validate_research_vault_knowledge.py",
            ):
                result = __import__("subprocess").run([str(python), str(script), "--vault", str(vault)], capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_note_link_validator_reads_legacy_fulltext_path_with_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp)
            note = vault / "02vault/urban/legacy.md"
            fulltext = vault / "03fulltext/urban/OLDKEY01.md"
            note.parent.mkdir(parents=True)
            fulltext.parent.mkdir(parents=True)
            note.write_text("---\ntype: literature-note\nzotero_key: OLDKEY01\nfulltext_path: fulltext/urban/OLDKEY01.md\n---\n", encoding="utf-8")
            fulltext.write_text("---\ntype: literature-fulltext\nzotero_key: OLDKEY01\nnote_path: 02vault/urban/legacy.md\n---\nText.\n", encoding="utf-8")
            issues, summary = validate_links(vault)
            self.assertEqual(summary["errors"], 0, issues)
            self.assertEqual(summary["warnings"], 1, issues)
            self.assertEqual(issues[0]["code"], "LEGACY_FULLTEXT_PATH")

    def test_retrieval_mirror_matches_when_available(self):
        mirror = Path(os.environ.get("RETRIEVAL_REPO", ROOT.parent / "Research-Vault-Literature-Retrieval"))
        if not mirror.is_dir():
            self.skipTest("standalone Retrieval checkout is not available in this environment")
        from check_retrieval_sync import compare
        errors = compare(ROOT / "skills/research-vault-literature-retrieval", mirror)
        self.assertEqual(errors, [])

    def test_mineru_runner_with_a_fake_backend(self):
        import run_mineru_production as runner
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source, mineru, output = base / "source.pdf", base / "mineru.exe", base / "run"
            source.write_bytes(b"sample PDF bytes")
            mineru.write_bytes(b"fake executable marker")

            def fake_run(command, **kwargs):
                raw = Path(command[command.index("-o") + 1])
                (raw / "paper.md").write_text("converted body", encoding="utf-8")
                return SimpleNamespace(returncode=0)

            capture = io.StringIO()
            with mock.patch.object(sys, "argv", ["runner", "--input", str(source), "--output", str(output), "--mineru", str(mineru)]), mock.patch.object(runner.subprocess, "run", side_effect=fake_run), contextlib.redirect_stdout(capture):
                self.assertEqual(runner.main(), 0)
            self.assertEqual(source.read_bytes(), b"sample PDF bytes")
            self.assertEqual(json.loads((output / "production-status.json").read_text(encoding="utf-8"))["final_status"], "MINERU_COMPLETED_CLEAN")
            self.assertTrue((output / "raw/paper.md").is_file())

    def test_zotero_fetch_helper_reads_fixture_read_only(self):
        import zotero_readonly_fetch as fetcher
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            storage = data / "storage/PDFKEY1"
            storage.mkdir(parents=True)
            (storage / "paper.pdf").write_bytes(b"%PDF-fixture")
            (storage / ".zotero-ft-cache").write_text("cached text", encoding="utf-8")
            db_path = data / "zotero.sqlite"
            db = sqlite3.connect(db_path)
            db.executescript("""
                CREATE TABLE items(itemID INTEGER PRIMARY KEY, key TEXT, itemTypeID INTEGER);
                CREATE TABLE fields(fieldID INTEGER PRIMARY KEY, fieldName TEXT);
                CREATE TABLE itemData(itemID INTEGER, fieldID INTEGER, valueID INTEGER);
                CREATE TABLE itemDataValues(valueID INTEGER PRIMARY KEY, value TEXT);
                CREATE TABLE creators(creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT);
                CREATE TABLE itemCreators(itemID INTEGER, creatorID INTEGER, orderIndex INTEGER);
                CREATE TABLE collections(collectionID INTEGER PRIMARY KEY, collectionName TEXT);
                CREATE TABLE collectionItems(collectionID INTEGER, itemID INTEGER);
                CREATE TABLE itemAttachments(itemID INTEGER, key TEXT, parentItemID INTEGER, path TEXT, contentType TEXT);
                CREATE TABLE itemAnnotations(itemID INTEGER, parentItemID INTEGER, type TEXT, authorName TEXT, comment TEXT, text TEXT, pageLabel TEXT);
                CREATE TABLE itemNotes(itemID INTEGER, parentItemID INTEGER, note TEXT);
            """)
            db.execute("INSERT INTO items VALUES (1, 'PARENT1', 1)")
            db.execute("INSERT INTO items VALUES (2, 'PDFKEY1', 2)")
            db.execute("INSERT INTO fields VALUES (1, 'title')")
            db.execute("INSERT INTO fields VALUES (2, 'date')")
            db.execute("INSERT INTO fields VALUES (3, 'DOI')")
            db.execute("INSERT INTO itemDataValues VALUES (1, 'Portable Research')")
            db.execute("INSERT INTO itemDataValues VALUES (2, '2024-01-01')")
            db.execute("INSERT INTO itemDataValues VALUES (3, '10.1234/example')")
            db.executemany("INSERT INTO itemData VALUES (1, ?, ?)", [(1, 1), (2, 2), (3, 3)])
            db.execute("INSERT INTO creators VALUES (1, 'Ada', 'Lovelace')")
            db.execute("INSERT INTO itemCreators VALUES (1, 1, 0)")
            db.execute("INSERT INTO collections VALUES (1, 'Methods')")
            db.execute("INSERT INTO collectionItems VALUES (1, 1)")
            db.execute("INSERT INTO itemAttachments VALUES (2, 'PDFKEY1', 1, 'storage:paper.pdf', 'application/pdf')")
            db.execute("INSERT INTO itemAnnotations VALUES (3, 2, 'highlight', 'Ada', '', 'verified text', '2')")
            db.execute("INSERT INTO itemNotes VALUES (4, 1, '<p>Research note</p>')")
            db.commit()
            db.close()
            before = hashlib.sha256(db_path.read_bytes()).hexdigest()
            capture = io.StringIO()
            with mock.patch.object(sys, "argv", ["fetch", "--key", "PARENT1", "--data-dir", str(data)]), contextlib.redirect_stdout(capture):
                self.assertEqual(fetcher.main(), 0)
            result = json.loads(capture.getvalue())
            self.assertEqual(result["zotero_key"], "PARENT1")
            self.assertEqual(result["pdf_key"], "PDFKEY1")
            self.assertEqual(result["title"], "Portable Research")
            self.assertEqual(result["annotations"][0]["text"], "verified text")
            self.assertEqual(result["notes"], ["<p>Research note</p>"])
            self.assertEqual(Path(result["pdf_path"]).resolve(), (storage / "paper.pdf").resolve())
            self.assertTrue(result["fulltext_cache"].endswith(".zotero-ft-cache"))
            self.assertEqual(before, hashlib.sha256(db_path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
