# Validation contract

Run only the checks applicable to the observed state; never convert an omitted stage into a pass.

## Identity and artifact checks

- Parent `zotero_key` is resolved and unique.
- `pdf_key` is resolved when a PDF/Fulltext is required.
- Note exists when the workflow claims a Note result.
- Note uses the canonical structure from `D:\ResearchVault\模板\论文精读模板.md` when the request requires strict template compliance; no stale template placeholders or legacy headings remain.
- Note frontmatter preserves the stable identity and required source fields, including `zotero_key`, `pdf_key`, `fulltext_path`, and `note_path` when available.
- Formal Fulltext exists when the workflow claims a Fulltext result.
- Note → Fulltext and Fulltext → Note paths resolve when both artifacts exist.
- `zotero_key` and `pdf_key` agree across Note and Fulltext.
- All Fulltext image links resolve; no missing image target is accepted.
- Every conclusion that claims a finding has a directly located source quotation; PDF page numbers are present only when verified against the Original PDF or a reliable page mapping.

## Knowledge checks

When Knowledge is updated or re-evaluated, run `research-vault-knowledge-maintainer/scripts/validate_research_vault_knowledge.py --vault D:\ResearchVault` and require exit code 0. Inspect the resulting checks for:

- Knowledge source links, claim/gap sidecars and statement drift;
- source mismatch, embedded machine metadata, raw key leakage and template/schema compliance;
- evidence counts, identity resolution, duplicate/alias conflicts and relation calibration.

`fulltext_verified` remains invalid unless the particular claim has the chain Note → declared `fulltext_path` → targeted Fulltext verification. A failed contract yields `VALIDATION_FAILED`, not success.
