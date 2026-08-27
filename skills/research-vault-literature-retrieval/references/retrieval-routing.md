# Knowledge-aware retrieval routing

Knowledge is a derived synthesis layer. It may guide discovery, framing and cross-paper synthesis, but it is never substituted for original paper evidence.

Evidence trace: **Knowledge → Analytical Note → targeted Fulltext → optional PDF**.

| Query type | Primary layer | Evidence follow-up | Fulltext required? | PDF required? | Allowed scope |
| --- | --- | --- | --- | --- | --- |
| Paper-specific | Analytical Note | Linked Fulltext | Only for methods, variables, precise result or quote | Only for page/formula/table/figure/OCR | One identified paper |
| Concept | Knowledge concept/theme | Supporting Notes, then targeted Fulltext for a precise definition | Conditional | Conditional | Relevant Knowledge nodes and Notes |
| Method | Knowledge method | Supporting Notes, then targeted Fulltext for parameters/implementation | Conditional | Conditional | Relevant Knowledge nodes and Notes |
| Relationship | Knowledge relation | Claim-linked Notes, then targeted Fulltext for direction/threshold/mechanism | Conditional | Conditional | Relevant relation and evidence chain |
| Controversy | Knowledge controversy plus relation | Competing claim-linked Notes, then targeted Fulltext | Conditional | Conditional | Directly competing/conditional evidence only |
| Research direction / gap | Knowledge synthesis plus gap/claim maturity | Supporting Notes where a recommendation needs grounding | Usually no | No, unless an exact source issue arises | Knowledge structure and linked Notes |
| Exact source | Analytical Note | Targeted Fulltext with surrounding context | Yes | Only for page, formula, table, figure or OCR verification | One resolved paper |

## Non-negotiable rules

- Begin normal paper discovery in `02vault` and its `_index` pages; do not default to a vault-wide `03fulltext` scan.
- Knowledge can identify concepts, relations, controversies, gaps and candidate papers, but paper identity and evidence interpretation must return to the actual Analytical Note.
- A Fulltext search inherits the Note and claim context and is restricted to the resolved paper(s).
- A direct fulltext-wide search is allowed only when the user explicitly requests it or Notes/Knowledge cannot recall sufficient candidates; label it supplementary recall and then resolve each candidate through its Note.
- Never fabricate an original definition, quotation, coefficient, formula, or method parameter from a Note or Knowledge page.
- If the chain lacks evidence, answer that the current Vault evidence is insufficient rather than filling the gap from general model knowledge.
