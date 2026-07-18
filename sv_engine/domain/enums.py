"""Versioned vocabulary used by the SV Engine methodology."""

from enum import Enum


class StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class EvidenceClass(StringEnum):
    DIRECT_OPERATIONAL = "E1_DIRECT_OPERATIONAL"
    DIRECT_BUYER = "E2_DIRECT_BUYER"
    DIRECT_USER = "E3_DIRECT_USER"
    AUTHORITATIVE_EXTERNAL = "E4_AUTHORITATIVE_EXTERNAL"
    COMPETITIVE_MARKET = "E5_COMPETITIVE_MARKET"
    INTERNAL_ESTIMATE = "E6_INTERNAL_ESTIMATE"
    PROTOTYPE = "E7_PROTOTYPE"


class EvidenceSufficiency(StringEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class GateStatus(StringEnum):
    PASS = "PASS"
    UNRESOLVED = "UNRESOLVED"
    FAIL = "FAIL"


class ReviewState(StringEnum):
    APPROVED = "APPROVED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"


class VerdictValue(StringEnum):
    BUILD_PROTOTYPE = "BUILD PROTOTYPE"
    VALIDATE_FURTHER = "VALIDATE FURTHER"
    DO_NOT_BUILD = "DO NOT BUILD"


class ScenarioName(StringEnum):
    DOWNSIDE = "downside"
    BASE = "base"
    UPSIDE = "upside"


class ValueKind(StringEnum):
    OBSERVED = "OBSERVED"
    CALCULATED = "CALCULATED"
    BOUNDED_ESTIMATE = "BOUNDED_ESTIMATE"
    ESTIMATE = "ESTIMATE"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"
    CONTRADICTION = "CONTRADICTION"

