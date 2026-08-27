# Ingest gates

| Gate | Pass condition | On failure | Downstream effect |
| --- | --- | --- | --- |
| State inspection | Existing artifacts and coverage are classified by stable identity | `VALIDATION_FAILED` or `MANUAL_REVIEW_REQUIRED` | Do not choose a write action |
| Identity | One parent `zotero_key`; attached PDF has one `pdf_key` and real path when Fulltext is required | `PDF_NOT_FOUND` or `KEY_CONFLICT` | No MinerU, Note or Knowledge claim creation |
| Fulltext | Valid formal Markdown, matching identifiers, images resolved; or an explicitly allowed deferred state | `FULLTEXT_FAILED` / `FULLTEXT_DEFERRED` | Do not call anything fulltext-verified |
| Analytical Note | Formal Note exists or is created with correct identity, source links, and the canonical template structure | `NOTE_FAILED` / `NOTE_DEFERRED` / `NOTE_TEMPLATE_REPAIR_REQUIRED` | Do not ingest a paper into Knowledge |
| Pair validation | Note ↔ Fulltext reciprocal paths and both keys agree when Fulltext exists | `VALIDATION_FAILED` | Stop Knowledge update |
| Knowledge decision | Existing pages considered first; action is justified by the completed Note | `SCHEMA_REVIEW_REQUIRED` / `MANUAL_REVIEW_REQUIRED` | Do not invent a page or schema value |
| Final validation | Applicable link, sidecar, schema, source, drift, Note-template, source-quotation, and image checks pass | `VALIDATION_FAILED` | Do not report success or append completion log |

An unavailable Fulltext may preserve a Note-only result, but it cannot upgrade a claim to `fulltext_verified`.
