# Production ingest pipeline

## Entry condition

Accept a paper only when the user identifies it by Zotero item, `zotero_key`, a Zotero URI, collection plus an unambiguous item, or another resolvable explicit reference. This workflow does not discover papers.

## Stages

1. **State inspection** — inspect existing Note, Fulltext, Knowledge source coverage, sidecars, prior log entries, and Note conformance to `D:\ResearchVault\模板\论文精读模板.md` without writing.
2. **Identity resolution** — use `zotero-data-fetcher` to resolve parent `zotero_key`, PDF `pdf_key`, and actual PDF path. A conflict becomes `MANUAL_REVIEW_REQUIRED`.
3. **Fulltext gate** — reuse a valid formal Fulltext first; otherwise use `zotero-fulltext-archiver` and its production MinerU route.
4. **Analytical Note gate** — reuse a valid formal Note only if its identity, source links, and structure conform to the canonical template; otherwise use `zotero-analytical-writer` in create or same-path template-repair mode after sufficient source material is available.
5. **Pair validation** — require reciprocal Note/Fulltext paths and matching `zotero_key` and `pdf_key`; validate image links where Fulltext exists.
6. **Knowledge decision** — call `research-vault-knowledge-maintainer` only with the completed Note and evidence state. It decides whether existing Knowledge is strengthened, conditioned, bounded, challenged, newly supported, or unchanged.
7. **Final validation and log** — validate Note-template conformance, quotation/page evidence, reciprocal links, and images; run the Knowledge validator when Knowledge is touched or re-evaluated, then append the human-readable log event only if the applicable contract passes.

## Delegation map

| Stage | Owner | Must not be duplicated here |
| --- | --- | --- |
| Zotero identity/PDF lookup | `zotero-data-fetcher` | Zotero database queries and attachment discovery |
| PDF to formal Fulltext | `zotero-fulltext-archiver` | MinerU implementation and image migration |
| Structured paper understanding | `zotero-analytical-writer` | Note template and writing logic |
| Cross-paper synthesis | `research-vault-knowledge-maintainer` | Frozen schema, templates, claims and gaps |
| Later user questions | `research-vault-literature-retrieval` | Ingest execution |
