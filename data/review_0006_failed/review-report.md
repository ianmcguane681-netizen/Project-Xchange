# RBE-001 Review Report

> **ADVISORY DRY RUN:** RBM-001 is RELEASE_CANDIDATE. This report is non-binding and does not permit merge.

## Decision Summary

- Review: `RBE-GSCF001-0006`
- Process status: **READY**
- Machine outcome: **FAIL**
- Binding: **false**
- Merge permitted: **false**
- Decision candidate: `DCA-A0CD3DC8B527302F5AEC5F59`
- Frozen snapshot: `sha256:9504d7fd2e8ad22b271c8c8d86730782bfe08837d06cdf00e66884d46b63b9db`

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

### `EVI-3F565FB74EBB8DA54D64B21B`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/test_results.txt`
- SHA-256: `sha256:8ea9e2f7663f5582085d10e28e09f78cc41afb2c2132750d11b6d4635b234202`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file test_results.txt

### `EVI-3FA42256C21407708C77B395`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/proof_gate_results.json`
- SHA-256: `sha256:82b43c62a049efa964a281f8888c44337a40c6963c7aeb2b238da7721f41cdaa`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file proof_gate_results.json

### `EVI-51727D4B08CBBB89552F195D`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/normalised_candidates_redacted.json`
- SHA-256: `sha256:2a2404eb91ebc0f1e9f25e8093230b99b222a929b8b2d0b7c64eba40835340eb`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file normalised_candidates_redacted.json

### `EVI-6053E72BD29FF79BCED1E1E1`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/report.md`
- SHA-256: `sha256:ea7a61469938d5c220b5c8c9bb959e0b0f2ff20b9462760543ac208e487cf813`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file report.md

### `EVI-766410B2208CA50E16FF4EEC`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/verification_artifacts.json`
- SHA-256: `sha256:de1236092f73482d1af448988b11f384fb8d87c852c9e4aca2dcda1604d17278`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file verification_artifacts.json

### `EVI-862FFC03D0490525AF441A20`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/source_reliability_assessment.json`
- SHA-256: `sha256:32bd37a955b253bfe9871751cc53ac3d740382f8d3fe49227f2fc5142b33769e`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file source_reliability_assessment.json

### `EVI-AAF210DD81702D55FE32EAA7`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/raw_records_redacted.json`
- SHA-256: `sha256:7498e716004402a98d0058f45fc10a01db2cdf84ec553bd2b88c4e58c1ce93d9`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file raw_records_redacted.json

### `EVI-AE0D502CFCD4F164FB813FA8`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/access_diagnostics.json`
- SHA-256: `sha256:f7851c417f5335ad2c3b9ad877d590fb78bc44d9665a2b1c951577aa14490886`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file access_diagnostics.json

### `EVI-B05D188B428E2C702EC8CDBD`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/adjudication_coverage.json`
- SHA-256: `sha256:499901ab110425ab53b6fbf275cab361eae1593d3b139f1f1015772b5b9965c5`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file adjudication_coverage.json

### `EVI-BA71348D51A92649B7AAEE67`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/report.json`
- SHA-256: `sha256:9967cae69e4c1c0e927d13774096028ba5d6aaafe6895079cf7d1975628f63d9`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file report.json

### `EVI-C66C7F8E803987965C747B8C`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/README.md`
- SHA-256: `sha256:d5cab74043cd41942ea50266f7389e4a683a063b78458dca6e89a1eb64ec6177`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file README.md

### `EVI-F400A0B5920ABC1F8AF24EB7`

- Locator: `GS-CF001-C/RUN-C1BEC4A07CED/run_manifest.json`
- SHA-256: `sha256:67e6788c38636661a0eb9a9db78c0dee0cb094048dc3eddcc9c4b766b04c2381`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file run_manifest.json

## Reviewer Reports

### `RPT-RBE-GSCF001-0006-BCA`

- Assignment: `ASN-8A78C1FB518E78508B787822`
- Summary: Commercial gates unchanged; the pricing lane is correctly barred from moving them.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`, `EVI-3FA42256C21407708C77B395`, `EVI-51727D4B08CBBB89552F195D`, `EVI-6053E72BD29FF79BCED1E1E1`, `EVI-766410B2208CA50E16FF4EEC`, `EVI-862FFC03D0490525AF441A20`, `EVI-AAF210DD81702D55FE32EAA7`, `EVI-AE0D502CFCD4F164FB813FA8`, `EVI-B05D188B428E2C702EC8CDBD`, `EVI-BA71348D51A92649B7AAEE67`, `EVI-C66C7F8E803987965C747B8C`, `EVI-F400A0B5920ABC1F8AF24EB7`
- Human signature: `SIG-VERIFY-BCA`

### `RPT-RBE-GSCF001-0006-DEA`

- Assignment: `ASN-ADAA2AE60558F6856ABC0346`
- Summary: Coverage is now measured rather than estimated, and the measuring tool failed the same way the gates did.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`, `EVI-3FA42256C21407708C77B395`, `EVI-51727D4B08CBBB89552F195D`, `EVI-6053E72BD29FF79BCED1E1E1`, `EVI-766410B2208CA50E16FF4EEC`, `EVI-862FFC03D0490525AF441A20`, `EVI-AAF210DD81702D55FE32EAA7`, `EVI-AE0D502CFCD4F164FB813FA8`, `EVI-B05D188B428E2C702EC8CDBD`, `EVI-BA71348D51A92649B7AAEE67`, `EVI-C66C7F8E803987965C747B8C`, `EVI-F400A0B5920ABC1F8AF24EB7`
- Human signature: `SIG-VERIFY-DEA`

### `RPT-RBE-GSCF001-0006-MA`

- Assignment: `ASN-A0EFFCED9C53D54B7FEEF39E`
- Summary: The prior review's structural finding was falsified by evidence and the correction is properly recorded. Process held.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`, `EVI-3FA42256C21407708C77B395`, `EVI-51727D4B08CBBB89552F195D`, `EVI-6053E72BD29FF79BCED1E1E1`, `EVI-766410B2208CA50E16FF4EEC`, `EVI-862FFC03D0490525AF441A20`, `EVI-AAF210DD81702D55FE32EAA7`, `EVI-AE0D502CFCD4F164FB813FA8`, `EVI-B05D188B428E2C702EC8CDBD`, `EVI-BA71348D51A92649B7AAEE67`, `EVI-C66C7F8E803987965C747B8C`, `EVI-F400A0B5920ABC1F8AF24EB7`
- Human signature: `SIG-VERIFY-MA`

### `RPT-RBE-GSCF001-0006-QRA`

- Assignment: `ASN-04E67D9F0BDDF89A9519CDB5`
- Summary: Controls held under live conditions; one systemic weakness recurs across unrelated components.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`, `EVI-3FA42256C21407708C77B395`, `EVI-51727D4B08CBBB89552F195D`, `EVI-6053E72BD29FF79BCED1E1E1`, `EVI-766410B2208CA50E16FF4EEC`, `EVI-862FFC03D0490525AF441A20`, `EVI-AAF210DD81702D55FE32EAA7`, `EVI-AE0D502CFCD4F164FB813FA8`, `EVI-B05D188B428E2C702EC8CDBD`, `EVI-BA71348D51A92649B7AAEE67`, `EVI-C66C7F8E803987965C747B8C`, `EVI-F400A0B5920ABC1F8AF24EB7`
- Human signature: `SIG-VERIFY-QRA`

### `RPT-RBE-GSCF001-0006-SAA`

- Assignment: `ASN-227E34FA3B1FF2C69B450A43`
- Summary: The evidentiary architecture absorbed the change without needing to be reshaped.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`, `EVI-3FA42256C21407708C77B395`, `EVI-51727D4B08CBBB89552F195D`, `EVI-6053E72BD29FF79BCED1E1E1`, `EVI-766410B2208CA50E16FF4EEC`, `EVI-862FFC03D0490525AF441A20`, `EVI-AAF210DD81702D55FE32EAA7`, `EVI-AE0D502CFCD4F164FB813FA8`, `EVI-B05D188B428E2C702EC8CDBD`, `EVI-BA71348D51A92649B7AAEE67`, `EVI-C66C7F8E803987965C747B8C`, `EVI-F400A0B5920ABC1F8AF24EB7`
- Human signature: `SIG-VERIFY-SAA`

### `RPT-RBE-GSCF001-0006-SR`

- Assignment: `ASN-CC4EF7059CF8563BE17C14B2`
- Summary: The prior structural claim is falsified and corroboration is demonstrated once. One case is not a mechanism.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`, `EVI-3FA42256C21407708C77B395`, `EVI-51727D4B08CBBB89552F195D`, `EVI-6053E72BD29FF79BCED1E1E1`, `EVI-766410B2208CA50E16FF4EEC`, `EVI-862FFC03D0490525AF441A20`, `EVI-AAF210DD81702D55FE32EAA7`, `EVI-AE0D502CFCD4F164FB813FA8`, `EVI-B05D188B428E2C702EC8CDBD`, `EVI-BA71348D51A92649B7AAEE67`, `EVI-C66C7F8E803987965C747B8C`, `EVI-F400A0B5920ABC1F8AF24EB7`
- Human signature: `SIG-VERIFY-SR`

## Findings

### SEV-2: Corroboration rests on a single case

- Finding ID: `FND6-SR-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-SR`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: The remediation is now demonstrated rather than asserted: Sandmeier v. Collection Consultants of California is a merits judgment for the plaintiff, on a consumer credit case, whose complaint classifies to the mechanism CFPB records independently allege. That is one case, in one district, against one collection agency. A gate passing on it would assert a market-wide operational mechanism from a single California dispute. The finding should not close on n=1.

### SEV-2: The binding constraint is an archive, not the courts

- Finding ID: `FND6-SR-002`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-SR`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: 43 of 67 occurrence-establishing records fail solely because RECAP holds no complaint. Coverage is contributed by volunteers, so the sample of adjudications this study can ever reach is shaped by who chose to upload documents, not by which cases were decided. That is a selection effect on the corroborating evidence itself and it is not correctable by further retrieval.

### SEV-3: PG-12 unmoved and unmovable by retrieval

- Finding ID: `FND6-BCA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-BCA`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: PG-11 is WEAK on five identified but unassessed incumbents and PG-12 remains FAIL with zero buyer records. The pricing lane is structurally prevented from touching the buyer gates, which is correct: a published list price is what a vendor charges and cannot evidence what a buyer would pay. No retrieval closes PG-12.

### SEV-3: The coverage tool reported a completed summary over an unenumerated pool

- Finding ID: `FND6-DEA-002`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-DEA`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: Its first two runs wrote a summary while pagination had failed on the first page having retrieved nothing, so a run with no denominator read as finished. This is the fourth instance in this system of a partial or placeholder state presenting as a completed one, and the first inside a tool built to investigate that very failure. It was corrected, but the recurrence rate is the finding.

### SEV-3: Rate limiting silently degraded results before backoff was added

- Finding ID: `FND6-QRA-002`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-QRA`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: A 429 during the docket join left every record unjoined, making the study's output depend on API load at the time of the run. Reproducibility is a stated property of this system and it did not hold. Backoff is now present; the class of defect -- an infrastructure failure changing a substantive result quietly -- warrants a standing check.

### SEV-4: Coverage measured across the full pool

- Finding ID: `FND6-DEA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-DEA`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: All 67 occurrence-establishing records were walked with the stop point recorded for each: 43 no complaint text, 11 off-study suit nature, 10 not an original proceeding, 2 join failed, 1 reached a mechanism. The denominator is established and the artefact is in the bundle, so the board is ruling on a measurement it can re-run.

### SEV-4: A prior board finding was overturned on evidence, and recorded as such

- Finding ID: `FND6-MA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-MA`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: Review 0005 accepted FND5-SR-002, that mechanism corroboration was structurally unreachable. That is now disproven and the disproof is documented in the source evaluation with the original claim retained rather than deleted. A board that silently revised its own history would be worthless; this one did not.

### SEV-4: Run manifest provenance closed

- Finding ID: `FND6-MA-002`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-MA`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: FND3-MA-001 is remediated. The run manifest names RBM-001 as the governing regime and declines to assert an assessment version it cannot know, which is the correct split.

### SEV-4: Origin check prevented misattribution

- Finding ID: `FND6-QRA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-QRA`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: 10 of 67 records were excluded because the case was not an original proceeding, so document 1 is a notice of removal or transfer papers rather than the plaintiff's account. Without that check those documents would have been classified as complaints and given the case a mechanism it never pleaded.

### SEV-4: Complaint text entered through the existing classifier unchanged

- Finding ID: `FND6-SAA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0006-SAA`
- Evidence references: `EVI-3F565FB74EBB8DA54D64B21B`
- Detail: No new inference mechanism was introduced. A complaint is the plaintiff's own account, the same evidentiary class as a CFPB narrative, so the study's classifier applied as-is. A design needing a new interpretive step for each source would not have survived this.

## Remediation

No remediation plans were recorded.

## Governance And Publication

- Decision status: **SIGNED**
- Publication: **RECORDED**

## Audit Verification

- Entries verified: 39
- Audit root hash: `sha256:57a17a5b4663277beb5e7f02ebaeb8e52d275bb8b239faeca502f1dc7e90f89f`
- Audit chain valid: **true**

## Limitations

- RBM-001 v2.0.0 remains RELEASE_CANDIDATE and cannot issue binding authority.
- Reviewer recommendations are non-binding and do not determine the machine outcome.
- This report contains only statements derived from the exported structured records.
