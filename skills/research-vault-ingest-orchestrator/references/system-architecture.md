# ResearchVault production architecture

```text
Zotero parent item (zotero_key)
  + PDF attachment (pdf_key)
        |
        v
03fulltext/<collection>/<zotero_key>.md
  - original-language MinerU archive
  - image assets and reciprocal note link
        |
        v
02vault/<collection>/<paper>.md
  - Chinese structured single-paper Analytical Note
  - Zotero identity and fulltext_path
        |
        v
01knowledge/
  - Chinese human-facing derived synthesis
01knowledge/.meta/
  - claims, gaps, indexes and machine traceability
```

`01knowledge` is a navigation and synthesis layer, not primary scientific evidence. Evidence must remain traceable as Knowledge → Analytical Note → Fulltext → optional original PDF.

| Layer | Responsibility | Stable identity |
| --- | --- | --- |
| Zotero | Parent metadata and attached source PDF | `zotero_key`, `pdf_key` |
| `03fulltext` | Verbatim source archive and images | `zotero_key`, `pdf_key` |
| `02vault` | Structured single-paper interpretation | `zotero_key` |
| `01knowledge` | Cross-paper Chinese synthesis and navigation | source Note links |
| `01knowledge/.meta` | Claims, gaps and machine-only traceability | claim/gap IDs plus Note-derived identity |
