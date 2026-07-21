# GS-P001-DOC-006 — Assumptions Register

**Document version:** 1.0.0  
**Study:** GS-P001  
**Execution mode:** `ADVISORY_DRY_RUN`

This register records assumptions that may shape collection, interpretation or review. Assumptions are not evidence and must not be treated as findings.

| ID | Assumption | Rationale | Risk if wrong | Required control | Status |
|---|---|---|---|---|---|
| A-001 | Public complaints may reflect genuine operational pain. | Public complaints can reveal recurring failures. | Anecdotal or false records could distort prevalence. | Verify source, preserve provenance and avoid treating one complaint as representative. | Accepted with controls |
| A-002 | Multiple genuinely independent sources reduce single-source bias. | Independent corroboration improves confidence. | Apparent independence may mask duplication or common origin. | Record source ownership, underlying incident and duplicate relationships. | Accepted with controls |
| A-003 | Software reviews may reveal workflow pain as well as product defects. | Users often describe operational consequences in reviews. | Product-specific frustration may be misclassified as market pain. | Separate workflow evidence from vendor-specific defects. | Accepted with controls |
| A-004 | Government, regulator, court and housing-authority material can provide authoritative context. | Such records may establish duties, recurring failure modes or measured consequences. | Authority does not automatically prove commercial opportunity. | Use authoritative sources for context and claims they directly support only. | Accepted with controls |
| A-005 | Vendor marketing claims are not independent proof of pain. | Vendors have commercial incentives. | Excluding all vendor material may remove useful contextual information. | Vendor material may be contextual only and must not establish a core finding. | Accepted |
| A-006 | Repeated communication failures may justify a reusable component only when the workflow is sufficiently common and bounded. | Reusability requires recurrence across organizations rather than one-off customization. | Broad pain may still be too heterogeneous for a reusable component. | Require cross-source recurrence and later component-boundary analysis. | Accepted with controls |
| A-007 | Historical evidence can remain relevant when the underlying workflow persists. | Some operational patterns change slowly. | Old evidence may misrepresent present practice. | Record publication date and document continuing relevance. | Accepted with controls |
| A-008 | Absence of evidence is not evidence of absence. | Collection limitations may hide relevant pain. | A weak sample may be overinterpreted as a negative market conclusion. | Distinguish `FURTHER_EVIDENCE_REQUIRED` from `DO_NOT_PROCEED`. | Accepted |
| A-009 | AI and automation can assist preparation and validation without becoming governance actors. | Automation can improve consistency and speed. | Generated content could be mistaken for human judgment or source evidence. | Prohibit AI review seats, signatures, ratification, publication authority and synthetic evidence. | Accepted with controls |

## Review rule

Any assumption found to materially influence a claim must be cited in the claim record and challenged by the review board. Rejected assumptions must remain in the audit trail with their status and reason.
