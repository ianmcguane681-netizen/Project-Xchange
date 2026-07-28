# RBE-001 Review Report

> **ADVISORY DRY RUN:** RBM-001 is RELEASE_CANDIDATE. This report is non-binding and does not permit merge.

## Decision Summary

- Review: `RBE-GSCF001-0007`
- Process status: **READY**
- Machine outcome: **FAIL**
- Binding: **false**
- Merge permitted: **false**
- Decision candidate: `DCA-F71B8C5E03DC02B2578FC55C`
- Frozen snapshot: `sha256:4497dcbe3f81d2d2729c8755d018560a06986fb022efcce651376e5358e7f9fb`

The machine outcome is deterministic but is not itself governance authority.

## Target And Authority

- Target repository: `ianmcguane681-netizen/GS-CF001`
- Target artefact: `df776460a2b5c8e3f7d9a4b6c1e2f5a8d3b7c9e1`
- Architecture authority: RBE-001 v1.1.0
- Methodology: `RBM-001` v2.2.0
- Methodology status: **RELEASE_CANDIDATE**
- Profile checksum: `sha256:9d6cd7cf305b3a415d664ec61ebe691e06439591257a2e86617880c39b7f8461`

## Decision Basis

FAIL was selected by RBM-DEC-002 from the frozen finding counts and substantive-evidence assessment.

Rules applied: `RBM-DEC-001`, `RBM-DEC-002`

Reason codes: `RBM-DEC-002`

## Evidence Register

### `EVI-11D466897FA4D5A887C08019`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/adjudication_coverage.json`
- SHA-256: `sha256:499901ab110425ab53b6fbf275cab361eae1593d3b139f1f1015772b5b9965c5`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file adjudication_coverage.json

### `EVI-3718C21C68CD9AD7309E15D5`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/access_diagnostics.json`
- SHA-256: `sha256:f7851c417f5335ad2c3b9ad877d590fb78bc44d9665a2b1c951577aa14490886`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file access_diagnostics.json

### `EVI-45D82E21B5C835CA923F417A`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/README.md`
- SHA-256: `sha256:d5cab74043cd41942ea50266f7389e4a683a063b78458dca6e89a1eb64ec6177`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file README.md

### `EVI-4B189E3A7C2CED8834906C42`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/test_results.txt`
- SHA-256: `sha256:8ea9e2f7663f5582085d10e28e09f78cc41afb2c2132750d11b6d4635b234202`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file test_results.txt

### `EVI-6A538E7345AC11FF79B52A29`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/proof_gate_results.json`
- SHA-256: `sha256:82b43c62a049efa964a281f8888c44337a40c6963c7aeb2b238da7721f41cdaa`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file proof_gate_results.json

### `EVI-6BB7B07F4585B61B021ED882`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/source_reliability_assessment.json`
- SHA-256: `sha256:32bd37a955b253bfe9871751cc53ac3d740382f8d3fe49227f2fc5142b33769e`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file source_reliability_assessment.json

### `EVI-7865B4567629911FFB795A19`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/normalised_candidates_redacted.json`
- SHA-256: `sha256:2a2404eb91ebc0f1e9f25e8093230b99b222a929b8b2d0b7c64eba40835340eb`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file normalised_candidates_redacted.json

### `EVI-78D4429887DD46E2C4915036`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/report.json`
- SHA-256: `sha256:9967cae69e4c1c0e927d13774096028ba5d6aaafe6895079cf7d1975628f63d9`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file report.json

### `EVI-7A47EDE0A1422CF928BB3F9C`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/raw_records_redacted.json`
- SHA-256: `sha256:7498e716004402a98d0058f45fc10a01db2cdf84ec553bd2b88c4e58c1ce93d9`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file raw_records_redacted.json

### `EVI-7C2412A2FBF59BEE675391BA`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/verification_artifacts.json`
- SHA-256: `sha256:de1236092f73482d1af448988b11f384fb8d87c852c9e4aca2dcda1604d17278`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file verification_artifacts.json

### `EVI-B2A4711D7518172B265C42B5`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/report.md`
- SHA-256: `sha256:ea7a61469938d5c220b5c8c9bb959e0b0f2ff20b9462760543ac208e487cf813`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file report.md

### `EVI-E8CD55B621FCB4BF0EB8D6F5`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/run_manifest.json`
- SHA-256: `sha256:67e6788c38636661a0eb9a9db78c0dee0cb094048dc3eddcc9c4b766b04c2381`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file run_manifest.json

## Reviewer Reports

### `RPT-RBE-GSCF001-0007-BCA`

- Assignment: `ASN-E127E8DCE9B0576A59E8AD15`
- Summary: Commercial position unchanged and untouched by this review.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-11D466897FA4D5A887C08019`, `EVI-3718C21C68CD9AD7309E15D5`, `EVI-45D82E21B5C835CA923F417A`, `EVI-4B189E3A7C2CED8834906C42`, `EVI-6A538E7345AC11FF79B52A29`, `EVI-6BB7B07F4585B61B021ED882`, `EVI-7865B4567629911FFB795A19`, `EVI-78D4429887DD46E2C4915036`, `EVI-7A47EDE0A1422CF928BB3F9C`, `EVI-7C2412A2FBF59BEE675391BA`, `EVI-B2A4711D7518172B265C42B5`, `EVI-E8CD55B621FCB4BF0EB8D6F5`
- Human signature: `SIG-VERIFY-BCA`

### `RPT-RBE-GSCF001-0007-DEA`

- Assignment: `ASN-96B7D977B88306D5FB74E3E7`
- Summary: Evidence unchanged from 0006; this review judges plans, not new data.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-11D466897FA4D5A887C08019`, `EVI-3718C21C68CD9AD7309E15D5`, `EVI-45D82E21B5C835CA923F417A`, `EVI-4B189E3A7C2CED8834906C42`, `EVI-6A538E7345AC11FF79B52A29`, `EVI-6BB7B07F4585B61B021ED882`, `EVI-7865B4567629911FFB795A19`, `EVI-78D4429887DD46E2C4915036`, `EVI-7A47EDE0A1422CF928BB3F9C`, `EVI-7C2412A2FBF59BEE675391BA`, `EVI-B2A4711D7518172B265C42B5`, `EVI-E8CD55B621FCB4BF0EB8D6F5`
- Human signature: `SIG-VERIFY-DEA`

### `RPT-RBE-GSCF001-0007-MA`

- Assignment: `ASN-826566F221060DE3ABD3B3CC`
- Summary: Both findings are carried forward intact and answered with plans; one plan concedes the finding cannot be closed.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-11D466897FA4D5A887C08019`, `EVI-3718C21C68CD9AD7309E15D5`, `EVI-45D82E21B5C835CA923F417A`, `EVI-4B189E3A7C2CED8834906C42`, `EVI-6A538E7345AC11FF79B52A29`, `EVI-6BB7B07F4585B61B021ED882`, `EVI-7865B4567629911FFB795A19`, `EVI-78D4429887DD46E2C4915036`, `EVI-7A47EDE0A1422CF928BB3F9C`, `EVI-7C2412A2FBF59BEE675391BA`, `EVI-B2A4711D7518172B265C42B5`, `EVI-E8CD55B621FCB4BF0EB8D6F5`
- Human signature: `SIG-VERIFY-MA`

### `RPT-RBE-GSCF001-0007-QRA`

- Assignment: `ASN-27D0AD230D5E08242CE139C2`
- Summary: The remediation route itself is now controlled.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-11D466897FA4D5A887C08019`, `EVI-3718C21C68CD9AD7309E15D5`, `EVI-45D82E21B5C835CA923F417A`, `EVI-4B189E3A7C2CED8834906C42`, `EVI-6A538E7345AC11FF79B52A29`, `EVI-6BB7B07F4585B61B021ED882`, `EVI-7865B4567629911FFB795A19`, `EVI-78D4429887DD46E2C4915036`, `EVI-7A47EDE0A1422CF928BB3F9C`, `EVI-7C2412A2FBF59BEE675391BA`, `EVI-B2A4711D7518172B265C42B5`, `EVI-E8CD55B621FCB4BF0EB8D6F5`
- Human signature: `SIG-VERIFY-QRA`

### `RPT-RBE-GSCF001-0007-SAA`

- Assignment: `ASN-8634CBF0B065EF09CC9FB6AC`
- Summary: No architectural change under review.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-11D466897FA4D5A887C08019`, `EVI-3718C21C68CD9AD7309E15D5`, `EVI-45D82E21B5C835CA923F417A`, `EVI-4B189E3A7C2CED8834906C42`, `EVI-6A538E7345AC11FF79B52A29`, `EVI-6BB7B07F4585B61B021ED882`, `EVI-7865B4567629911FFB795A19`, `EVI-78D4429887DD46E2C4915036`, `EVI-7A47EDE0A1422CF928BB3F9C`, `EVI-7C2412A2FBF59BEE675391BA`, `EVI-B2A4711D7518172B265C42B5`, `EVI-E8CD55B621FCB4BF0EB8D6F5`
- Human signature: `SIG-VERIFY-SAA`

### `RPT-RBE-GSCF001-0007-SR`

- Assignment: `ASN-77D4548E8C7D60B80FCBC057`
- Summary: The two blockers from 0006 stand unchanged on the evidence; one of them may not be resolvable.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-11D466897FA4D5A887C08019`, `EVI-3718C21C68CD9AD7309E15D5`, `EVI-45D82E21B5C835CA923F417A`, `EVI-4B189E3A7C2CED8834906C42`, `EVI-6A538E7345AC11FF79B52A29`, `EVI-6BB7B07F4585B61B021ED882`, `EVI-7865B4567629911FFB795A19`, `EVI-78D4429887DD46E2C4915036`, `EVI-7A47EDE0A1422CF928BB3F9C`, `EVI-7C2412A2FBF59BEE675391BA`, `EVI-B2A4711D7518172B265C42B5`, `EVI-E8CD55B621FCB4BF0EB8D6F5`
- Human signature: `SIG-VERIFY-SR`

## Findings

### SEV-2: Corroboration still rests on a single case

- Finding ID: `FND7-SR-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0007-SR`
- Evidence references: `EVI-11D466897FA4D5A887C08019`
- Detail: Carried from FND6-SR-001. Sandmeier remains the only adjudicated finding reaching this study's mechanism, out of 67 occurrence-establishing records. Nothing in the evidence has changed since 0006. One California dispute cannot support a market-wide operational claim.

### SEV-2: Archive selection bias cannot be retrieved away

- Finding ID: `FND7-SR-002`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0007-SR`
- Evidence references: `EVI-11D466897FA4D5A887C08019`
- Detail: Carried from FND6-SR-002. 43 of 67 records fail only because RECAP holds no complaint, and RECAP is volunteer-uploaded. Retrieving more records enlarges the sample without correcting which cases are in it. A remediation that promises more retrieval would not address this finding, and the board should refuse one that does.

### SEV-3: PG-12 remains outside the reach of any plan here

- Finding ID: `FND7-BCA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0007-BCA`
- Evidence references: `EVI-11D466897FA4D5A887C08019`
- Detail: No remediation in this review bears on buyer evidence. PG-12 closes when someone speaks to a budget holder and not before.

### SEV-4: Same artefact, same measurement

- Finding ID: `FND7-DEA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0007-DEA`
- Evidence references: `EVI-11D466897FA4D5A887C08019`
- Detail: The bundle and coverage sweep are identical to 0006. No new retrieval was performed, which is correct for a remediation review: changing the evidence and the plans together would make it impossible to tell which moved the outcome.

### SEV-4: Findings carried forward rather than reset

- Finding ID: `FND7-MA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0007-MA`
- Evidence references: `EVI-11D466897FA4D5A887C08019`
- Detail: 0006 was published and frozen, so its blockers could not be answered in place. They are re-raised here verbatim rather than restated more favourably, and the plans attach to the carried findings.

### SEV-4: Plans cannot be back-fitted to a decision

- Finding ID: `FND7-QRA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0007-QRA`
- Evidence references: `EVI-11D466897FA4D5A887C08019`
- Detail: The remediation command refuses submission once a decision candidate is frozen and accepts only from the Methodology Auditor. Verified against 0006, which refused with RBE_DECISION_INPUTS_FROZEN. A plan written after a verdict is computed is not a plan.

### SEV-4: Remediation exposed through the same front door

- Finding ID: `FND7-SAA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0007-SAA`
- Evidence references: `EVI-11D466897FA4D5A887C08019`
- Detail: The runtime capability existed and was unreachable without writing Python. Exposing it through the CLI keeps the board operable by one person, which is the constraint this system is built under.

## Remediation

- `RMP-1E3528AE3C461E9151E30703` for `FND7-SR-001`: **ACCEPTED**; owner `ian.mcguane`; due `2026-09-30`.
- `RMP-970FB558A46F49D5834613F5` for `FND7-SR-002`: **ACCEPTED**; owner `ian.mcguane`; due `2026-10-31`.

## Governance And Publication

- Decision status: **SIGNED**
- Publication: **RECORDED**

## Audit Verification

- Entries verified: 40
- Audit root hash: `sha256:df31a13b1965d5b3eb96a270160727d37220d204c4488f36d7c745674b619c68`
- Audit chain valid: **true**

## Limitations

- RBM-001 v2.0.0 remains RELEASE_CANDIDATE and cannot issue binding authority.
- Reviewer recommendations are non-binding and do not determine the machine outcome.
- This report contains only statements derived from the exported structured records.
