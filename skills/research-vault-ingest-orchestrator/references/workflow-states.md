# Workflow states

These states describe process progress only. They do not replace evidence roles, verification states, Knowledge statuses, agreements, or gap provenance.

| State | Meaning | Next action |
| --- | --- | --- |
| `ALREADY_COMPLETE` | All required artifacts and prior Knowledge decision are valid | No write |
| `FULLTEXT_CREATED` | Formal Fulltext was newly archived and passed its gate | Continue to Note/pair checks |
| `NOTE_CREATED` | Formal Analytical Note was newly created | Continue to pair/Knowledge checks |
| `NOTE_TEMPLATE_REPAIRED` | Existing Analytical Note was normalized to the canonical template without changing its stable identity | Continue to pair/Knowledge checks |
| `KNOWLEDGE_UPDATED` | Existing or gated-new Knowledge was conservatively updated and validated | Final log |
| `NO_KNOWLEDGE_CHANGE` | Paper is complete but adds no durable Knowledge change | Final log; success |
| `FULLTEXT_DEFERRED` | PDF/runner condition prevents Fulltext now | Retain accurate partial evidence state |
| `NOTE_DEFERRED` | Note cannot yet be responsibly created | Retry after source material is available |
| `PDF_NOT_FOUND` | Resolved item has no usable attachment | Retry with Zotero repair/user input |
| `KEY_CONFLICT` | Identity or attachment mapping is ambiguous | Human review required |
| `FULLTEXT_FAILED` | MinerU/archive gate failed | Retry targeted Fulltext work only |
| `VALIDATION_FAILED` | A required contract check failed | Fix only the failing artifact and revalidate |
| `SCHEMA_REVIEW_REQUIRED` | Evidence cannot be represented by frozen schema | Stop Knowledge write pending explicit migration |
| `MANUAL_REVIEW_REQUIRED` | A non-guessable conflict or ambiguity remains | Request clarification |
