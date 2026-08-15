---
name: research-vault-knowledge-maintainer
description: "Maintain the persistent Research Knowledge Wiki in D:\\ResearchVault\\knowledge from existing analytical literature notes. Use when creating or incrementally updating cross-paper themes, concepts, methods, relationships, controversies, syntheses, the knowledge index or append-only log; or when linting traceability, duplicates, conflicts, and stale claims. Preserve note-first retrieval and use linked MinerU fulltexts only for targeted verification of precise claims."
---

# Research Vault Knowledge Maintainer

Maintain a small, evidence-traceable Markdown knowledge layer. Treat it as navigation and persistent synthesis, never as primary evidence.

## Current Vault Layout

- Knowledge Wiki: `D:\ResearchVault\01knowledge`
- Analytical Notes: `D:\ResearchVault\02vault`
- MinerU Fulltext: `D:\ResearchVault\03fulltext`

These paths take precedence over legacy folder names appearing in historical notes or examples.

## Guardrails

- Read the analytical-note indexes in `02vault/_index/` first: `文献索引.md`, `研究主题索引.md`, `研究方法索引.md`, and `字段补全检查.md` when present.
- Compile from Analytical Notes. Do not begin discovery from `fulltext/`.
- Resolve every scientific claim to one or more `zotero_key` values and Analytical Notes. For exact wording, definitions, model details, coefficients, formulas, or mechanisms, follow the note's `fulltext_path` and make a targeted search there.
- Treat a Knowledge Page as a derived artifact. It may link to pages for navigation, but never use a Knowledge Page as evidence for another scientific claim.
- On incremental ingestion, re-evaluate the prior synthesis against the new Analytical Note; do not treat prior knowledge text as supporting evidence.
- A same-path Analytical Note template repair is a presentation/traceability maintenance action, not by itself a new scientific contribution. Re-check source-note resolution and validator coverage, but do not create or revise a Knowledge Page solely because the Note was normalized to `D:\ResearchVault\模板\论文精读模板.md`.
- Prefer updating an existing canonical page over creating a synonym. Use `aliases` for Chinese/English names and common variants.
- Preserve disagreement. Use `agreement: mixed`, `conflicting`, or `insufficient` where the current Vault evidence does not support a single conclusion. Label explanations not stated by papers as `interpretation`.
- Create a page only for a durable theme, recurrent method, shared relationship, real controversy, or clearly important emerging concept. Do not create one-node-per-term pages.
- Do not alter Zotero, MinerU Fulltext, existing analytical notes, or normal paper-oriented indexes unless explicitly requested.

## Frozen schema

Follow [references/knowledge-schema.md](references/knowledge-schema.md) and select the matching template in `references/` before creating or materially restructuring a Knowledge Page. The six listed page types, common frontmatter, status values, agreement values, evidence roles, verification states, gap provenances, Claim ID format, and metadata location are frozen.

Do not invent a page type, status, agreement, evidence role, verification state, gap provenance, or top-level machine-metadata location. If current evidence cannot be expressed by the frozen schema, preserve the evidence and report `SCHEMA_REVIEW_REQUIRED` rather than creating an ad hoc field or value.

## Formal Knowledge Page Discovery Rule

A Markdown file is a formal Knowledge Page only when it is outside
`01knowledge/.meta/`, is in the human-facing Knowledge tree, and its
frontmatter `type` is one of the frozen Knowledge Page types. `index.md` and
`log.md` are human-facing navigation exceptions. Machine reports, sidecars and
all other files under `.meta/**` must never be interpreted as Knowledge Pages
by validation or template-compliance checks.

## Knowledge Template Rule

All user-facing Knowledge Pages must follow the current template stored at `D:\ResearchVault\模板\知识库模板`. Before creating or structurally refreshing Knowledge Pages, read and follow the current template. Do not invent an alternative visible page structure when a valid workspace template exists.

If a template change is only presentational, update the human-readable layer while preserving the frozen schema. If it would change the semantic schema, report `SCHEMA_REVIEW_REQUIRED` rather than changing fields, enums, IDs, or metadata locations automatically.

### Strict local template contract

The actual template authority is the directory `D:\ResearchVault\模板\知识库模板`, not a remembered outline or a simplified evidence-list pattern. Before every Knowledge Page creation or material rewrite, read:

1. `README_知识库模板说明.md`;
2. the matching page template: `主题模板.md`, `概念模板.md`, `方法模板.md`, `关系模板.md`, or `争议模板.md`;
3. the current page and its canonical aliases in `01knowledge/index.md`.

Preserve the template's visible section order, heading levels, summary callout, evidence tables, boundary sections, research-gap sections, usage/implication sections, and source-tracking sections. Do not replace a template page with a short “summary + source list”, a paper-by-paper abstract dump, or a generic “来源与边界” stub. A page is not template-compliant merely because its frontmatter validates.

The template frontmatter is a writing contract; the frozen Knowledge schema is a machine contract. Where the template uses a presentation field such as `knowledge_type`, map it to the frozen `type` value and preserve only schema-approved fields in the page frontmatter. Never add an unvalidated field just to imitate a template example.

### Two-source-layer synthesis contract

For every paper used in a Knowledge Page, parse both layers before writing a claim:

- **Structural library layer:** the Analytical Note frontmatter and structured sections (`study_area`, `data_source`, `methodology`, `core_variable`, `key_finding`, `relevance`, limitations, formulas, quotes, `zotero_key`, and `fulltext_path`).
- **Original-text layer:** the linked `03fulltext` Markdown, or the original PDF when Fulltext is absent or a page-level detail needs verification. Search the original text for the exact result, definition, mechanism, threshold, formula, limitation, and qualifying condition being written.

The Note supplies the structured map; the Fulltext supplies the primary evidence. Do not write a precise coefficient, threshold, formula, mechanism, or quotation from the Note alone when a linked Fulltext exists. If Fulltext is unavailable, mark the claim `note_supported`, record the missing-verification boundary, and do not invent a page number or quote.

### Comprehensive coverage gate

When the user asks for a collection, folder, research direction, or “all papers” to be organized, build a coverage ledger from the relevant Analytical Note index before editing pages. Every paper must be classified as one of: direct evidence, mechanism evidence, conditional evidence, contextual evidence, related evidence, or explicitly out of scope with a reason. Every in-scope paper must appear in at least one real-path `source_notes` list and in the appropriate template evidence/source section; a small representative subset is not sufficient without an explicit coverage statement. Report the total, Fulltext-available count, Note-only count, and any unresolved items.

### Template compliance acceptance

Do not declare the Knowledge update complete until all of the following are true:

- the page uses the matching template's visible section structure;
- every precise claim has an adjacent evidence link, evidence role, and verification state;
- the page distinguishes definitions, proxies, mechanisms, outcomes, and policy implications;
- conditions, heterogeneity, limitations, and research gaps are explicit;
- all in-scope papers are covered by real Analytical Note links;
- Fulltext-backed claims have been targeted back to `fulltext_path` and no unverified quote/page number is present;
- the Knowledge validator exits 0 and the coverage ledger has no unexplained missing paper.

## Chinese-first Knowledge Writing Rule

All user-facing Knowledge titles, headings, synthesis, evidence descriptions, gap descriptions, and navigation text must be written primarily in Chinese. English is allowed only for standard scientific abbreviations, symbols, proper method/model names where needed, and first-use bilingual terminology. Machine metadata under `.meta` remains in the Frozen Schema.

## Workflow

1. Read `02vault/_index/`, then candidate Analytical Notes. Build a coverage ledger recording title, `zotero_key`, note path, Fulltext availability, variables, methods, findings, limitations, and the page(s) to which each paper will be routed.
2. Read `D:\ResearchVault\模板\知识库模板\README_知识库模板说明.md` and the matching page template before drafting. Read `01knowledge/index.md` and find canonical pages by title and aliases. Decide explicitly which pages to update, create, or leave unchanged.
3. For each precise claim, inspect the structured Note first and then search the linked Fulltext or PDF for the exact result and its qualifiers. Record the verification state; do not treat a Note-only summary as Fulltext evidence.
4. Update evidence lists and cross-links. Keep `evidence_count` equal to the distinct Analytical Notes in `source_notes`; add a real-path source link for every supporting paper. It is a page-coverage count, never a claim-support count.
5. Use the six page classes only: `knowledge-theme`, `knowledge-concept`, `knowledge-method`, `knowledge-relation`, `knowledge-controversy`, and `knowledge-synthesis`. A relation page must set `subject`, `relation`, `object`, and `agreement`.
6. For each precise claim, record `fulltext_verified` only after targeted verification through the linked Fulltext. Otherwise use `note_supported`; use `interpretation` for a clearly labelled cross-paper inference. Page-level `evidence_status` remains a summary and may be `mixed`; never recreate English quotations from Chinese notes.
7. Refresh the knowledge-oriented `01knowledge/index.md`, append (never rewrite) an entry in `01knowledge/log.md`, and record created/updated/unchanged pages, coverage counts, Fulltext counts, and unresolved items.
8. Run the Knowledge validator and a template/coverage audit. Fix only conservative structural issues; never delete a knowledge page automatically.

The lint reports page classes, orphan pages, missing evidence, broken note links, invalid Zotero keys, evidence-count mismatches, duplicate titles, alias conflicts, invalid relations, note-only versus Fulltext-verified states, possible relationship contradictions, and stale pages.

## Required frontmatter

All pages require `type`, `title`, `aliases`, `status`, `evidence_count`, `source_notes`, `related`, `last_updated`, and `evidence_status`. Relation pages also require `subject`, `relation`, `object`, and `agreement`. Raw-key `supporting_papers` is not a user-facing Knowledge property.

Use statuses `emerging`, `developing`, `established`, `conditional`, or `contested`; use agreements `strong`, `mixed`, `conflicting`, or `insufficient`. `conditional` denotes evidence that changes with scale, setting, measure, or threshold; it does not by itself imply a research conflict. These are Vault-internal evidence states, not meta-analytic estimates.

## Human-readable Citation Rule

Knowledge pages must cite papers through real-path Analytical Note links with concise human-readable aliases, for example `[[02vault/能耗/Urban 3D building morphology and energy consumption empirical evidence from 53 cities in China|53城三维形态—用电]]`. Raw Zotero keys must not appear in normal user-facing Knowledge prose, frontmatter properties, index pages, or maintenance-log entries.

### Human-readable Link Target Rule

A human-readable paper short name is a display alias, not a file identity. Never create `[[short name]]` unless a real Analytical Note with exactly that target already exists. When the Analytical Note filename differs from the short name, always generate `[[real note path|human-readable short name]]`.

### No Phantom Note Rule

Knowledge maintenance must never create empty Markdown files merely to satisfy unresolved source links. Before writing a source link, resolve the target Analytical Note and verify that it exists.

### Stable Source Resolution Rule

Resolve source identity through the actual Analytical Note and its `zotero_key`; use the short name only for display. A link is valid only when its target is a formal Analytical Note (`#literature-note` or official Analytical Note metadata), not merely an existing Markdown file.

## Machine Identity Resolution Rule

The stable paper identity remains the `zotero_key` stored in the linked Analytical Note. Knowledge pages use `source_notes` as their evidence list; when a machine identifier is needed, resolve `source_notes` → Analytical Note → `zotero_key` → `fulltext_path`. Do not store a duplicate `supporting_papers` list of raw keys in a human-readable Knowledge page.

## Claim-level Evidence Rule

For important relationship, controversy, and synthesis pages, attach evidence to specific claims whenever practical. Use an explicit, readable structure: conclusion, linked note evidence, evidence type, and verification status. A page-level `evidence_status` is only a coarse summary and must not imply that every claim received the same verification.

## Evidence Role Rule

Distinguish direct, mechanism, contextual, conditional, and related evidence. In Chinese Knowledge pages, prefer `直接证据`、`机制证据`、`情境证据`、`条件证据`和`相关证据`; do not present all source notes as equally direct support.

### Claim-centered Knowledge Rule

Organize relation, controversy, and synthesis pages around research claims, conditions, mechanisms, and unresolved questions rather than paper-by-paper summaries. Use natural, reader-facing section titles and adjacent hidden metadata when machine traceability is needed.

### Synthesis Maturity Gate

Follow [references/synthesis-maturity-gate.md](references/synthesis-maturity-gate.md). Theme creation and Synthesis creation are separate decisions: never create a Synthesis automatically when a Theme is created. Require multiple stable cross-paper Relations or Claims, sufficient cross-paper synthesis evidence, and at least one worthwhile condition, mechanism, boundary, controversy, or evidence-backed gap. Do not use a rigid paper count as the sole gate.

### Hidden Machine Metadata Rule

Claim IDs, evidence-role enums, verification-state enums, and gap provenance are machine metadata and must not visually pollute Knowledge Markdown. Store claims in `01knowledge/.meta/claims/` and gaps in `01knowledge/.meta/gaps/`, with indexes in `01knowledge/.meta/`; retain only human-readable conclusions, evidence, evidence type, and verification text in pages. Do not use visible prose, HTML comments, or Obsidian comments for schema metadata in newly written Knowledge Markdown.

### Verification State Rule

Use `fulltext_verified` only when the individual claim's linked Analytical Note has been checked against its `fulltext_path`. Use `note_supported` when the claim is supported by the Analytical Note but not specifically checked in Fulltext. Use `interpretation` for labelled cross-paper synthesis; it is not an author-level finding.

### Page Evidence Count Rule

Page-level `evidence_count` is a source-coverage count, not a count of papers supporting every claim. Assess claim strength from its own evidence links, roles, and verification state.

### Gap Provenance Rule

Separate an **Evidence-backed Gap**—explicitly limited to what current Vault coverage shows—from an **Interpretive Gap** or research opportunity. Label the latter as `interpretation`; never state either as an absolute claim about the whole literature without broader evidence.

## Query routing

- For broad synthesis, trends, disputes, or research directions: Knowledge Index -> relevant Knowledge Pages -> supporting Notes -> selective Fulltexts.
- For a paper-specific definition, quotation, method, or result: Analytical Note -> linked Fulltext. Do not route it through Knowledge first.
