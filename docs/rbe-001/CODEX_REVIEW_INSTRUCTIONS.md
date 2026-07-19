# Codex Review Instructions — RBE-001

## Purpose

This directory contains the complete AI-readable Review Board Engine architecture package prepared for Codex review.

The complete package is stored in:

`docs/rbe-001/RBE-001_AI_Reader_Package_v1.0.0.zip`

The archive SHA-256 is:

`6eafdaeb8f77b61a83a589c397f75d7c820786e2f690457734f9bc096b6ca0c1`

## Required first step

From the repository root, extract the archive without modifying it:

```bash
mkdir -p docs/rbe-001/extracted
python - <<'PY'
from pathlib import Path
import zipfile

archive = Path('docs/rbe-001/RBE-001_AI_Reader_Package_v1.0.0.zip')
target = Path('docs/rbe-001/extracted')
target.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive) as zf:
    zf.extractall(target)
print(f'Extracted {len(zf.namelist())} entries to {target}')
PY
```

Then verify the SHA-256:

```bash
python - <<'PY'
from pathlib import Path
import hashlib
p = Path('docs/rbe-001/RBE-001_AI_Reader_Package_v1.0.0.zip')
print(hashlib.sha256(p.read_bytes()).hexdigest())
PY
```

## Review scope

Codex must review all of the following:

1. The complete RBE-001 Reference Architecture v1.0.0.
2. Chapters 1–23 individually.
3. The RBE-001 Engineering Specification.
4. The Architecture Consistency and Principal Review Report.
5. Release notes, change log and architecture index.
6. Cross-document terminology, normative requirements and implementation constraints.

## Authority and interpretation

The Markdown files are the complete AI-readable review set. The controlled DOCX/PDF publication artifacts remain authoritative where formatting or conversion differs.

Codex must not:

- invent architecture;
- weaken a SHALL requirement;
- treat constitutional principles as optional prose;
- infer approval merely because a proposal appears desirable;
- bypass evidence, independence, traceability or reproducibility controls;
- begin implementation before completing the architecture review.

## Required Codex output

Codex should produce a written review containing:

- blocking contradictions;
- ambiguous or non-implementable requirements;
- missing interfaces, schemas or state transitions;
- security and separation-of-duties concerns;
- testability gaps;
- operational and deployment gaps;
- traceability issues;
- proposed ADRs for genuinely unresolved implementation choices;
- a final verdict of `READY`, `READY WITH FINDINGS`, or `NOT READY`.

Every finding must cite the exact source file and section. No source material may be silently rewritten during review.
