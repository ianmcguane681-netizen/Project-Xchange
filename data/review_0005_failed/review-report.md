# RBE-001 Review Report

> **ADVISORY DRY RUN:** RBM-001 is RELEASE_CANDIDATE. This report is non-binding and does not permit merge.

## Decision Summary

- Review: `RBE-GSCF001-0005`
- Process status: **READY**
- Machine outcome: **FAIL**
- Binding: **false**
- Merge permitted: **false**
- Decision candidate: `DCA-B117666DA887727C5246B83A`
- Frozen snapshot: `sha256:4ce2dd1723dd25fccde52e6cea300c3c9c5aff48bfd7774a04f2cfe9b05459f9`

The machine outcome is deterministic but is not itself governance authority.

## Target And Authority

- Target repository: `ianmcguane681-netizen/GS-CF001`
- Target artefact: `ed243479a1b4c7e2f6d8a3b5c9e1f4a7d2b6c8e0`
- Architecture authority: RBE-001 v1.1.0
- Methodology: `RBM-001` v2.2.0
- Methodology status: **RELEASE_CANDIDATE**
- Profile checksum: `sha256:9d6cd7cf305b3a415d664ec61ebe691e06439591257a2e86617880c39b7f8461`

## Decision Basis

FAIL was selected by RBM-DEC-002 from the frozen finding counts and substantive-evidence assessment.

Rules applied: `RBM-DEC-001`, `RBM-DEC-002`

Reason codes: `RBM-DEC-002`

## Evidence Register

### `EVI-047DB0EF258948D86DBABC7F`

- Locator: `GS-CF001-C/RUN-AE1038287921/run_manifest.json`
- SHA-256: `sha256:23860b1982c9566dbeb6bb9a59d26d04422b7734a7fe735a9a00579cec23dee1`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file run_manifest.json

### `EVI-1DBBEB531D04C596824E1569`

- Locator: `GS-CF001-C/RUN-AE1038287921/proof_gate_results.json`
- SHA-256: `sha256:879e92f07aa92443d815971117847078611bc6fa9230d217f5dfdf0afd9fc057`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file proof_gate_results.json

### `EVI-6D1D4D0175474456C014127E`

- Locator: `GS-CF001-C/RUN-AE1038287921/verification_artifacts.json`
- SHA-256: `sha256:23c9c06ab389dbb751fa7dd5022b972b8f1b8f6d5e279004654d5d48f68e1c93`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file verification_artifacts.json

### `EVI-831456CA9324D9886D789837`

- Locator: `GS-CF001-C/RUN-AE1038287921/source_reliability_assessment.json`
- SHA-256: `sha256:f99804612cb36b20e4f0142624605b9e88b07eddb90609dd7c7730a0b5f4f15d`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file source_reliability_assessment.json

### `EVI-89CF53FAEFD7BD3FFF931613`

- Locator: `GS-CF001-C/RUN-AE1038287921/normalised_candidates_redacted.json`
- SHA-256: `sha256:965c7d4485ce0dd68fbc2ed15f06917fd6c7df45406685d46685c58547066b5a`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file normalised_candidates_redacted.json

### `EVI-9FFAF3BA38CDE6ADB32BCB0E`

- Locator: `GS-CF001-C/RUN-AE1038287921/report.md`
- SHA-256: `sha256:caf42ed0e65bfbaa862cb3791192318d3b7dd7578922583c72c496d89269c292`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file report.md

### `EVI-A546EFDE84F713A6CD0EDE23`

- Locator: `GS-CF001-C/RUN-AE1038287921/test_results.txt`
- SHA-256: `sha256:c112fa7b5b3b6890ff4383b79500551d2f4f4691f101ab5e8bfe8c97fd82963f`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file test_results.txt

### `EVI-B2FB9B1DBA27B6CBC336FDC1`

- Locator: `GS-CF001-C/RUN-AE1038287921/raw_records_redacted.json`
- SHA-256: `sha256:bf4ef53e4def41fd374dc512aaf68c8a6751c91ba141adc326b85e74d098b758`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file raw_records_redacted.json

### `EVI-EB230E8F60DF797209D48600`

- Locator: `GS-CF001-C/RUN-AE1038287921/access_diagnostics.json`
- SHA-256: `sha256:8f569433b2fcb80430dcc50e23a3c536aab2a1a85a9a5d6dc117ec59e018e0d8`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file access_diagnostics.json

### `EVI-EE6313D2F59B0772119646C1`

- Locator: `GS-CF001-C/RUN-AE1038287921/report.json`
- SHA-256: `sha256:c83697f6e7dc3cb109dd1418b92353e3505858f9032d5cec0861e351d9e4769c`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file report.json

### `EVI-EFC8602A88CB39980D984379`

- Locator: `GS-CF001-C/RUN-AE1038287921/README.md`
- SHA-256: `sha256:d5cab74043cd41942ea50266f7389e4a683a063b78458dca6e89a1eb64ec6177`
- Source tier: `GOLDEN_STUDY_PROOF_BUNDLE`
- Description: GS-CF001-C proof bundle file README.md

## Reviewer Reports

### `RPT-RBE-GSCF001-0005-BCA`

- Assignment: `ASN-30AA51CB659AAB2F166C2F79`
- Summary: Commercial position is unchanged and remains correctly unproven; this run does not bear on it.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`, `EVI-1DBBEB531D04C596824E1569`, `EVI-6D1D4D0175474456C014127E`, `EVI-831456CA9324D9886D789837`, `EVI-89CF53FAEFD7BD3FFF931613`, `EVI-9FFAF3BA38CDE6ADB32BCB0E`, `EVI-A546EFDE84F713A6CD0EDE23`, `EVI-B2FB9B1DBA27B6CBC336FDC1`, `EVI-EB230E8F60DF797209D48600`, `EVI-EE6313D2F59B0772119646C1`, `EVI-EFC8602A88CB39980D984379`
- Human signature: `SIG-VERIFY-BCA`

### `RPT-RBE-GSCF001-0005-DEA`

- Assignment: `ASN-4B8B98BC3FBB5EC65EE669AA`
- Summary: Source handling is sound and the exclusions are well reasoned. A recurring failure mode -- gates passing on placeholder values -- has now appeared twice.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`, `EVI-1DBBEB531D04C596824E1569`, `EVI-6D1D4D0175474456C014127E`, `EVI-831456CA9324D9886D789837`, `EVI-89CF53FAEFD7BD3FFF931613`, `EVI-9FFAF3BA38CDE6ADB32BCB0E`, `EVI-A546EFDE84F713A6CD0EDE23`, `EVI-B2FB9B1DBA27B6CBC336FDC1`, `EVI-EB230E8F60DF797209D48600`, `EVI-EE6313D2F59B0772119646C1`, `EVI-EFC8602A88CB39980D984379`
- Human signature: `SIG-VERIFY-DEA`

### `RPT-RBE-GSCF001-0005-MA`

- Assignment: `ASN-980D0D68D0A52DB88B7F8F1E`
- Summary: The control is correctly built and enforced at the right layer. The prior SEV-3 on run manifest provenance remains open.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`, `EVI-1DBBEB531D04C596824E1569`, `EVI-6D1D4D0175474456C014127E`, `EVI-831456CA9324D9886D789837`, `EVI-89CF53FAEFD7BD3FFF931613`, `EVI-9FFAF3BA38CDE6ADB32BCB0E`, `EVI-A546EFDE84F713A6CD0EDE23`, `EVI-B2FB9B1DBA27B6CBC336FDC1`, `EVI-EB230E8F60DF797209D48600`, `EVI-EE6313D2F59B0772119646C1`, `EVI-EFC8602A88CB39980D984379`
- Human signature: `SIG-VERIFY-MA`

### `RPT-RBE-GSCF001-0005-QRA`

- Assignment: `ASN-FE6BF58C46E71E0441840F10`
- Summary: Risk controls behaved correctly under live conditions and caught a real off-mechanism admission. Join key reconstruction is under-tested.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`, `EVI-1DBBEB531D04C596824E1569`, `EVI-6D1D4D0175474456C014127E`, `EVI-831456CA9324D9886D789837`, `EVI-89CF53FAEFD7BD3FFF931613`, `EVI-9FFAF3BA38CDE6ADB32BCB0E`, `EVI-A546EFDE84F713A6CD0EDE23`, `EVI-B2FB9B1DBA27B6CBC336FDC1`, `EVI-EB230E8F60DF797209D48600`, `EVI-EE6313D2F59B0772119646C1`, `EVI-EFC8602A88CB39980D984379`
- Human signature: `SIG-VERIFY-QRA`

### `RPT-RBE-GSCF001-0005-SAA`

- Assignment: `ASN-0E1885B887A62B54D5474EF6`
- Summary: The two-axis model is the right abstraction and is enforced where it matters.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`, `EVI-1DBBEB531D04C596824E1569`, `EVI-6D1D4D0175474456C014127E`, `EVI-831456CA9324D9886D789837`, `EVI-89CF53FAEFD7BD3FFF931613`, `EVI-9FFAF3BA38CDE6ADB32BCB0E`, `EVI-A546EFDE84F713A6CD0EDE23`, `EVI-B2FB9B1DBA27B6CBC336FDC1`, `EVI-EB230E8F60DF797209D48600`, `EVI-EE6313D2F59B0772119646C1`, `EVI-EFC8602A88CB39980D984379`
- Human signature: `SIG-VERIFY-SAA`

### `RPT-RBE-GSCF001-0005-SR`

- Assignment: `ASN-77594100AD4C8F1376D09726`
- Summary: An adjudicated tier exists and is correctly conservative, but it does not yet establish this study's mechanism, and the sources integrated cannot be made to.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`, `EVI-1DBBEB531D04C596824E1569`, `EVI-6D1D4D0175474456C014127E`, `EVI-831456CA9324D9886D789837`, `EVI-89CF53FAEFD7BD3FFF931613`, `EVI-9FFAF3BA38CDE6ADB32BCB0E`, `EVI-A546EFDE84F713A6CD0EDE23`, `EVI-B2FB9B1DBA27B6CBC336FDC1`, `EVI-EB230E8F60DF797209D48600`, `EVI-EE6313D2F59B0772119646C1`, `EVI-EFC8602A88CB39980D984379`
- Human signature: `SIG-VERIFY-SR`

## Findings

### SEV-2: Control built, requirement not met

- Finding ID: `FND5-SR-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0005-SR`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: The remediation for FND3-SR-001 built the control but did not satisfy it. An adjudicated tier now exists and 67 qualifying merits judgments are retrievable, yet zero records in this run establish occurrence for the study's mechanism. PG-09 fails. The finding it was raised against is therefore not remediated on the evidence, only on the process.

### SEV-2: Mechanism unreachable from integrated sources

- Finding ID: `FND5-SR-002`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0005-SR`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: Mechanism-level corroboration is structurally unreachable from the sources now integrated. The IDB records section 1681 with subsection empty on every row, and docket metadata carries a statutory cause and a suit-nature category but no consumer narrative. Case-level records establish that an FCRA claim was decided, never which duty was breached. No amount of further retrieval from these two sources closes this.

### SEV-3: Commercial gates unmoved

- Finding ID: `FND5-BCA-001`
- Status: **OPEN**
- Category: `COMMERCIAL`
- Source report: `RPT-RBE-GSCF001-0005-BCA`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: No movement on the commercial gates. PG-10, PG-11 and PG-12 remain unproven and continue to cap the verdict independently of the evidence work in this run. The adjudicated tier does not advance the commercial position at all.

### SEV-3: Run manifest does not name the reviewing board

- Finding ID: `FND5-MA-002`
- Status: **OPEN**
- Category: `METHODOLOGY`
- Source report: `RPT-RBE-GSCF001-0005-MA`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: The run manifest still does not name the reviewing board or the methodology version under which the artefact was assessed. Raised as FND3-MA-001 in the previous review and unaddressed in this run.

### SEV-3: Second gate to pass on placeholder values

- Finding ID: `FND5-DEA-002`
- Status: **OPEN**
- Category: `PROCESS`
- Source report: `RPT-RBE-GSCF001-0005-DEA`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: A false PASS occurred and was caught by inspection of live output rather than by test. The first three-source run passed PG-09 because an adjudication and a complaint matched on both being unclassified. Tests were green throughout. This is the second gate in this system to pass on placeholder values, after G7 on placeholder competitors.

### SEV-3: Join key reconstruction under-tested

- Finding ID: `FND5-QRA-002`
- Status: **OPEN**
- Category: `RISK`
- Source report: `RPT-RBE-GSCF001-0005-QRA`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: The join depends on reconstructing a PACER docket number from coded fields, verified at 4 of 4 live cases. That sample is too small to establish the reconstruction holds across districts and years, and a wrong join would silently attribute an outcome to the wrong case.

### SEV-4: Standing modelled orthogonally to source family

- Finding ID: `FND5-SAA-001`
- Status: **OPEN**
- Category: `ARCHITECTURE`
- Source report: `RPT-RBE-GSCF001-0005-SAA`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: Evidentiary standing is modelled orthogonally to source family, and the FJC source deliberately shares the court records family so it cannot inflate the independence count. That separation is correct and is enforced by test rather than convention.

### SEV-4: Source exclusions are high-volume and correctly reasoned

- Finding ID: `FND5-DEA-001`
- Status: **OPEN**
- Category: `EVIDENCE`
- Source report: `RPT-RBE-GSCF001-0005-DEA`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: The exclusions carry the integrity of this source. 7,683 settled cases, 32 default judgments and 363 ambiguous defence-side pre-trial judgments are all discarded on stated reasoning. Admitting the settled group alone would have produced thousands of false proofs. The discard ratio is high and correct.

### SEV-4: Pinned gate constants replaced by computed controls

- Finding ID: `FND5-MA-001`
- Status: **OPEN**
- Category: `METHODOLOGY`
- Source report: `RPT-RBE-GSCF001-0005-MA`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: PG-09 and PG-13 were pinned FAIL constants before this change and are now computed. That is a genuine control improvement: the gates can now distinguish a study lacking adjudicated evidence from one holding it, which a constant cannot. The remediation is correctly implemented as a requirement rather than a dataset.

### SEV-4: Docket join prevented an off-mechanism admission

- Finding ID: `FND5-QRA-001`
- Status: **OPEN**
- Category: `RISK`
- Source report: `RPT-RBE-GSCF001-0005-QRA`
- Evidence references: `EVI-047DB0EF258948D86DBABC7F`
- Detail: The docket join is a precondition, not enrichment, and prevented a specific concrete error: United States v. Vivint Smart Home is a consent judgment against the respondent on suit nature 890, an enforcement action about misusing consumer reports rather than a reinvestigation failure. It was the study's only occurrence-establishing record and would have proved the mechanism with an unrelated case.

## Remediation

No remediation plans were recorded.

## Governance And Publication

- Decision status: **SIGNED**
- Publication: **RECORDED**

## Audit Verification

- Entries verified: 38
- Audit root hash: `sha256:a4071d1f3ae06989448c0884bf56b80a01122c7ca853bb1ece5b6c587a7719f0`
- Audit chain valid: **true**

## Limitations

- RBM-001 v2.0.0 remains RELEASE_CANDIDATE and cannot issue binding authority.
- Reviewer recommendations are non-binding and do not determine the machine outcome.
- This report contains only statements derived from the exported structured records.
