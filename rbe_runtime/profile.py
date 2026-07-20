"""Profile-driven role, quorum, and reviewer-spec policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError


_ROLE_LINE = re.compile(r"^\*\*Reviewer Role:\*\* .*\(([A-Z]{2,3})\)$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class RoleSeat:
    role: str
    actor: str
    reviewer_spec_id: str
    sequence: int


@dataclass(frozen=True, slots=True)
class ProfilePolicy:
    profile: dict[str, Any]
    role_to_spec: dict[str, str]

    @classmethod
    def from_authority(cls, authority: AuthorityBundle) -> "ProfilePolicy":
        role_to_spec: dict[str, str] = {}
        for spec_id, path in authority.reviewer_specs.items():
            match = _ROLE_LINE.search(path.read_text(encoding="utf-8"))
            if match is None:
                raise RBEError(
                    "RBE_REVIEWER_SPEC_INVALID",
                    f"Reviewer role is absent from {path.name}",
                    "RBE-ES-ORC-004",
                )
            role = match.group(1)
            if role in role_to_spec:
                raise RBEError(
                    "RBE_REVIEWER_SPEC_INVALID",
                    f"Multiple reviewer specifications claim role {role}",
                    "RBE-ES-ORC-004",
                )
            role_to_spec[role] = spec_id
        return cls(profile=authority.profile, role_to_spec=role_to_spec)

    def plan_roles(self, initiation: dict[str, Any]) -> tuple[RoleSeat, ...]:
        tier = initiation["tier"]
        quorum = self.profile["quorum"][f"tier_{tier}"]
        specialists = {
            role.upper(): actor
            for role, actor in initiation["specialists"].items()
            if actor is not None
        }
        allowed_specialists = set(quorum["specialist_pool"])
        unexpected = sorted(set(specialists) - allowed_specialists)
        if unexpected:
            raise RBEError(
                "RBE_ROLE_NOT_PERMITTED_FOR_TIER",
                f"Tier {tier} includes specialists outside its configured pool",
                "RBE-ES-ORC-004",
                {"roles": unexpected},
            )
        if len(specialists) < quorum["specialists_required"]:
            raise RBEError(
                "RBE_QUORUM_INSUFFICIENT",
                f"Tier {tier} requires {quorum['specialists_required']} specialists",
                "RBE-ES-ORC-002",
                {"assigned_specialists": sorted(specialists)},
            )

        role_actors = {
            "BC": initiation["board_chair"],
            "MA": initiation["methodology_auditor"],
            "SR": initiation["sceptical_reviewer"],
            **specialists,
        }
        required_roles = set(quorum["required_roles"])
        missing = sorted(role for role in required_roles if not role_actors.get(role))
        if missing:
            raise RBEError(
                "RBE_REQUIRED_ROLE_MISSING",
                "A methodology-required board role is unassigned",
                "RBE-ES-ORC-002",
                {"roles": missing},
            )
        actors = list(role_actors.values())
        non_human = sorted(
            role
            for role, actor in role_actors.items()
            if actor.lower().startswith(("ai:", "model:", "automation:"))
        )
        if non_human:
            raise RBEError(
                "RBE_NON_HUMAN_BOARD_ROLE",
                "AI or automation actors cannot hold accountable board roles",
                "RBE-ES-DES-002",
                {"roles": non_human},
            )
        if self.profile["role_policy"]["distinct_human_per_board_role"] and len(
            actors
        ) != len(set(actors)):
            raise RBEError(
                "RBE_ROLE_CONFLICT",
                "Board roles must be held by distinct human actors",
                "RBE-ES-ORC-003",
            )

        review_roles = ["MA", *sorted(specialists), "SR"]
        return tuple(
            RoleSeat(
                role=role,
                actor=role_actors[role],
                reviewer_spec_id=self.role_to_spec[role],
                sequence=index,
            )
            for index, role in enumerate(review_roles, start=1)
        )

    def require_role_spec(self, role: str, spec_id: str) -> None:
        expected = self.role_to_spec.get(role)
        if expected != spec_id:
            raise RBEError(
                "RBE_REVIEWER_SPEC_MISMATCH",
                f"Role {role} must use {expected or 'a known reviewer specification'}",
                "RBE-ES-ORC-004",
                {"role": role, "expected": expected, "received": spec_id},
            )
