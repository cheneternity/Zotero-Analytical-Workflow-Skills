---
name: research-vault-ingest-orchestrator
description: "Orchestrate the verified ResearchVault single-paper ingest workflow from Zotero identity through Fulltext, Analytical Note, Knowledge decision, validation, and append-only logging. Use only when the user explicitly identifies paper(s) to add or asks to assess the ingest state of specified paper(s)."
---

# ResearchVault Ingest Orchestrator

## Purpose and boundary

This is the production control plane for a **specified** paper. It orchestrates existing specialist Skills; it does not reimplement Zotero extraction, MinerU conversion, Analytical Note writing, Knowledge synthesis, or retrieval.

It never performs discovery, searches Zotero for interesting papers, or downloads new papers unless the user explicitly requests that work. It never restarts an already complete pipeline merely because a new ingest request arrived.

Current production layout:

- Knowledge Wiki: `D:\ResearchVault\01knowledge`
- Analytical Notes: `D:\ResearchVault\02vault`
- Formal Fulltext: `D:\ResearchVault\03fulltext`
- Knowledge machine metadata: `D:\ResearchVault\01knowledge\.meta`
- Knowledge page templates: `D:\ResearchVault\模板\知识库模板`
- MinerU production runner: `D:\ResearchVault\tools\run_mineru_production.py`
- Canonical Analytical Note template: `D:\ResearchVault\模板\论文精读模板.md`

The stable identity is `zotero_key` (parent item); `pdf_key` identifies its PDF attachment. A title is display-only and may be used for human sanity checks, never as the primary key.

## Required specialist Skills

Read the current instructions before each delegated stage:

1. `zotero-data-fetcher` — resolve the parent item and attached PDF identity.
2. `zotero-fulltext-archiver` — obtain or validate formal Fulltext.
3. `zotero-analytical-writer` — create or minimally complete the single-paper Analytical Note.
4. `research-vault-knowledge-maintainer` — decide and perform a justified cross-paper Knowledge update.
5. `research-vault-literature-retrieval` — answer later evidence questions; it is not an ingest stage.

The collection manager remains a compatible batch/small-batch scheduler. This orchestrator applies the same identity and incremental rules to a specified paper.

## Workflow

Use the gates in [references/ingest-gates.md](references/ingest-gates.md), the stage contract in [references/pipeline.md](references/pipeline.md), and the acceptance checks in [references/validation-contract.md](references/validation-contract.md).

```text
SPECIFIED PAPER
  -> STATE INSPECTION
  -> ZOTERO IDENTITY
  -> FULLTEXT GATE
  -> ANALYTICAL NOTE GATE
  -> NOTE/FULLTEXT PAIR VALIDATION
  -> KNOWLEDGE INGEST DECISION
  -> KNOWLEDGE UPDATE OR NO_KNOWLEDGE_CHANGE
  -> FINAL VALIDATION
  -> APPEND-ONLY LOG
```

At every gate, stop downstream writes on failure. Record a retryable or review state from [references/workflow-states.md](references/workflow-states.md); never label a partial result as success.

For any Knowledge update, the Knowledge gate is a two-layer evidence pass: parse the Analytical Note's structured fields and sections, then search the linked `03fulltext` Markdown or original PDF for the exact result, mechanism, threshold, formula, limitation, and qualifier. The Note is the structured map; the original text is the primary evidence. A missing Fulltext produces `note_supported` or a deferred state, never an invented quotation or page number.

## Workflow modes

Use exactly one mode for each request:

- `NORMAL_INGEST` is the default for a normal request to add a specified Zotero paper. Run state inspection, Zotero identity, only the necessary Fulltext and Analytical Note stages, the Knowledge decision, any necessary Knowledge update, standard validation, and append-only logging. Do not run the acceptance suite (hard retrieval tests, cross-topic retrieval, autonomous theme testing, or an extended audit report) unless the user explicitly asks for it.
- `ACCEPTANCE_TEST` is selected only when the user explicitly requests a Skill test, new-topic autonomous creation test, retrieval test, or system acceptance. Run the requested ingest path plus hard retrieval tests, cross-topic tests, and the extended audit required by the acceptance scope.

`NORMAL_INGEST` must retain standard safety validation: identity, Note/Fulltext pairing, Knowledge links, claim sidecars, statement-drift checks, and the Knowledge validator exit code. The mode split removes repeated acceptance-test overhead; it never disables safety checks or lowers a Knowledge page-creation gate.

## Minimal-action decision table

| Observed state | Required action |
| --- | --- |
| Zotero, Note, Fulltext and Knowledge coverage are valid, and the Note conforms to the canonical template | `ALREADY_COMPLETE`; do not reprocess. |
| Note and Fulltext are valid, but the Note does not conform to the canonical template | Run only the Analytical Note gate in template-repair mode; preserve the same Note path and identity, then revalidate. |
| Note exists but Fulltext is missing/invalid | Run only the Fulltext gate, then reconsider Knowledge. |
| Fulltext exists but Note is missing | Run only the Analytical Note gate. |
| Note and Fulltext are valid but Knowledge has not considered the paper | Run only the Knowledge decision. |
| Required artifacts are absent | Run the necessary stages in order. |

`NO_KNOWLEDGE_CHANGE` is a successful Knowledge-decision outcome: it means that the new, validated paper adds no durable claim, condition, mechanism, boundary, direct evidence, challenge, or justified synthesis change.

## Production rules

- The Zotero fetcher must resolve `zotero_key` and `pdf_key`; do not use fuzzy title-based disk searches as acquisition.
- For a needed new MinerU conversion, use the verified runner and the Fulltext Archiver instructions: an ASCII `input_<zotero_key>.pdf` working copy, matching source/working SHA-256, explicit `pipeline` backend in the current Windows CPU environment, one paper at a time, timestamped stdout/stderr, and scoped process cleanup. This documents `CURRENT_ENVIRONMENT_PIPELINE_PREFERRED`; it does not declare hybrid permanently unsupported.
- Formal Fulltext is `03fulltext/<collection>/<zotero_key>.md`, with resolved image links and `MISSING_IMAGES = 0`. Preserve extracted body text; do not translate, summarize, polish, or Knowledge-ify it.
- Analytical Note writing belongs solely to `zotero-analytical-writer` and represents single-paper structured understanding. For every new or explicitly normalized Note, use `D:\ResearchVault\模板\论文精读模板.md` as the structural authority; do not create a duplicate Note merely because an existing Note needs template repair.
- When the user requires the template strictly, audit the existing Note before declaring `ALREADY_COMPLETE`. Preserve confirmed metadata, identity, links, formulas, and evidence, but reshape headings and conclusion blocks to the canonical template. Each conclusion must pair a finding with a source quotation; add PDF page numbers only after direct PDF verification or a reliable page mapping.
- Knowledge writing belongs solely to `research-vault-knowledge-maintainer`. Before every Knowledge write, read `D:\ResearchVault\模板\知识库模板\README_知识库模板说明.md` and the matching `主题模板.md`, `概念模板.md`, `方法模板.md`, `关系模板.md`, or `争议模板.md`. Preserve the template's visible section order, tables, boundary sections, gaps, implications, and source tracking; do not substitute a short summary/source-list page. It must retain the frozen schema, Chinese-first human layer, claim sidecars, gap sidecars, and page-creation gate. Update an existing canonical page before considering a new page.
- When the user asks for a folder, collection, research direction, or all papers, the Knowledge gate must build a coverage ledger and route every in-scope paper to at least one real-path `source_notes` list and template evidence/source section. Report total papers, Fulltext-available papers, Note-only papers, and unresolved coverage before declaring success.
- Workflow states are not Knowledge evidence enums and must never be inserted into frozen Knowledge schema fields.
- The visible Knowledge log remains human-readable. Keep raw `zotero_key`/`pdf_key` in the orchestrator run record or linked Note/Fulltext identity chain, not in visible Knowledge prose or the human-facing log.

## Logging and completion

After all applicable validation succeeds, append one Chinese-format event to `01knowledge/log.md` through the Knowledge Maintainer workflow. Include date, human-readable source paper, Fulltext status, Analytical Note status, Knowledge action, updated pages/claims (if any), and validation result. Do not rewrite log history.

Completion requires the final validator and the template/coverage audit to pass. A Note-template repair is complete only after Note↔Fulltext identity/path checks, image checks, and the Knowledge validator applicable to the observed state pass. If Fulltext is absent, report the accurate partial state (for example `FULLTEXT_DEFERRED`); do not claim `fulltext_verified` evidence.

## References

- [System architecture](references/system-architecture.md)
- [Pipeline](references/pipeline.md)
- [Ingest gates](references/ingest-gates.md)
- [Workflow states](references/workflow-states.md)
- [Validation contract](references/validation-contract.md)
