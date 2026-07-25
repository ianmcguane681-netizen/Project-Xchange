"""Bridge Golden Study proof bundles into the Review Board Engine audit chain.

A Golden Study (GS-CF001, GS-P001, ...) proves its own integrity per run: it emits
a proof bundle of raw records, diagnostics, gate results and a manifest, covered by
a checksum file. The RBE runtime proves its own integrity too, via a hash-chained,
append-only audit log.

Until now those were two separate chains with nothing linking them, so no single
verifiable thread ran from a raw source record through to a board decision. This
package closes that join: it verifies a study bundle, reduces it to one
deterministic root hash, and registers it as first-class evidence inside a review
session, so the board's audit chain cryptographically commits to the study's
contents and the exact code that produced them.

The dependency runs one way only - study_bridge depends on rbe_runtime, never the
reverse - so the runtime stays methodology-neutral.
"""

from study_bridge.bundle import (
    StudyBundle,
    StudyBundleError,
    StudyBundleFile,
)
from study_bridge.ingest import IngestResult, ingest_study_bundle

__all__ = [
    "IngestResult",
    "StudyBundle",
    "StudyBundleError",
    "StudyBundleFile",
    "ingest_study_bundle",
]
