# ResearchVault Knowledge Schema (Frozen)

This reference is the single source of truth for Knowledge Wiki structure. Schema changes require an explicit migration; otherwise mark the need as `SCHEMA_REVIEW_REQUIRED`.

## Scope and page types

The only supported `type` values are `knowledge-theme`, `knowledge-concept`, `knowledge-method`, `knowledge-relation`, `knowledge-controversy`, and `knowledge-synthesis`. Knowledge pages synthesize across papers; do not create paper, author, journal, city, country, dataset, or other page types without a schema migration.

## Common frontmatter

Every page has: `type`, `title`, `aliases`, `status`, `evidence_count`, `source_notes`, `related`, `last_updated`, and `evidence_status`.

- `evidence_count` is a distinct-source coverage count, never a count of support for every claim.
- `source_notes` contains only `[[REAL_ANALYTICAL_NOTE_PATH|HUMAN_READABLE_SHORT_NAME]]` links.
- `related` contains Knowledge navigation links, not paper evidence.
- `evidence_status` is the page-level summary: `fulltext_verified`, `note_only`, or `mixed`.

Relation pages additionally require `subject`, `relation`, `object`, and `agreement`. Controversy pages require `agreement`. Synthesis pages may use `agreement` only when it has a defined meaning.

## Frozen enumerations

| Field | Allowed values |
| --- | --- |
| `status` | `emerging`, `developing`, `established`, `conditional`, `contested` |
| `agreement` | `strong`, `mixed`, `conflicting`, `insufficient` |
| Claim evidence role | `direct`, `mechanism`, `conditional`, `contextual`, `related` |
| Claim verification state | `fulltext_verified`, `note_supported`, `interpretation` |
| Gap provenance | `evidence-backed`, `interpretive` |

`conditional` describes dependence on scale, threshold, climate, season, or setting; it does not itself mean `contested`. `conflicting` requires comparable evidence with genuinely opposing directions.

## Claim record

Use natural section titles in Markdown. Store metadata for important relation, controversy, and synthesis claims in `01knowledge/.meta/claims/<claim_id>.json`; Markdown itself contains only the human-readable claim.

```markdown
**结论**：…

- **证据**：[[02vault/.../完整论文标题|可读短名]]
- **证据类型**：直接证据
- **验证**：全文已核验
```

`direct` tests the target relation; `mechanism` supports a pathway; `conditional` supports a modifier; `contextual` supplies a setting, scale, LCZ, metric, or scenario; and `related` is relevant but not any stronger role. `fulltext_verified` requires the chain Knowledge → Analytical Note → `fulltext_path` → Fulltext. `interpretation` must visibly say `interpretation` or `解释` and cannot be presented as an author-level result.

Claim IDs are unique and permanent. Use `REL-`, `CON-`, or `SYN-`, a readable uppercase topic token, and a two-digit sequence: `^(REL|CON|SYN)-[A-Z0-9]+(?:-[A-Z0-9]+)+-\d{2}$`. Do not reuse retired IDs.

Each claim sidecar contains `claim_id`, `page_path`, `section_heading`, `normalized_statement`, `statement_hash`, `evidence_role`, `verification_state`, and `source_notes`. Claim IDs, role enums, and verification states must not be embedded in Knowledge Markdown. The validator treats embedded HTML and Obsidian comments as errors after migration.

## Gap record

Store each gap in `01knowledge/.meta/gaps/` and its index; do not embed a marker in Markdown.

```markdown
{"gap_provenance": "evidence-backed"}
```

An `evidence-backed` gap explicitly says it is limited to current Vault coverage. An `interpretive` opportunity visibly labels itself `interpretation`; it is a research direction, not a claim that the entire field lacks work.

## Source identity and metadata

A human-readable short name is an alias, not an identity. Resolve source identity through the linked Analytical Note and its `zotero_key`; never display a raw key in normal Knowledge prose or properties. Never create an empty note to satisfy a link.

Machine metadata belongs only in `01knowledge/.meta/`; it must not be linked from ordinary Knowledge pages or listed in the Knowledge Index.

## Templates

Use the six templates in this directory: `knowledge-theme-template.md`, `knowledge-concept-template.md`, `knowledge-method-template.md`, `knowledge-relation-template.md`, `knowledge-controversy-template.md`, and `knowledge-synthesis-template.md`.
