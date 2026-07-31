"""The runtime can name more than one methodology, and still refuses unknown ones.

The identity of the methodology profile used to be a constant in `rbe_runtime`, and
its location a hardcoded path in the loader. That made the runtime capable of exactly
one methodology by construction -- not by policy, and with no error to read.

Moving identity into a registry is the whole seam, and it has to preserve the check it
replaced. A package states its own id and version in `PROFILE.json`, so validating
that against the package itself proves only that a file equals itself. The registry is
the independent claim: the runtime says what it expects to find, and a package that
disagrees fails to load.
"""

from __future__ import annotations

import pytest

from controlled_authority import profiles
from controlled_authority.rbm_package import validate_package
from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError


class TestTheRegistry:
    def test_the_research_board_is_registered(self):
        spec = profiles.get("RBM-001")

        assert spec.profile_version == "2.2.0"
        assert spec.package_root.name == "review-board"

    def test_omitting_the_id_resolves_the_research_board(self):
        """Existing callers named no profile, so the default must stay what it was."""

        assert profiles.get() is profiles.get("RBM-001")

    def test_an_unregistered_profile_is_refused_rather_than_defaulted(self):
        """A caller that asked for RBM-002 and silently got RBM-001 would run an
        engineering review under research rules with nothing to say so."""

        with pytest.raises(LookupError, match="RBM-999"):
            profiles.get("RBM-999")

    def test_every_registered_profile_is_keyed_by_its_own_id(self):
        for key, spec in profiles.PROFILES.items():
            assert key == spec.profile_id


class TestIdentityIsStillCheckedIndependently:
    def test_a_package_cannot_declare_its_own_identity(self):
        """The registry's claim wins. This is the check the refactor had to keep."""

        impostor = profiles.PackageSpec(
            profile_id="RBM-001",
            profile_version="9.9.9",
            package_root=profiles.RBM_001.package_root,
            schema_files=profiles.RBM_001.schema_files,
            reviewer_spec_count=profiles.RBM_001.reviewer_spec_count,
            methodology_document=profiles.RBM_001.methodology_document,
        )

        with pytest.raises(Exception, match="version mismatch"):
            validate_package(impostor)

    def test_a_missing_reviewer_spec_is_detected_not_absorbed(self):
        """Counting the directory would make a missing file undetectable: the
        expectation would simply become one fewer."""

        expecting_more = profiles.PackageSpec(
            profile_id="RBM-001",
            profile_version="2.2.0",
            package_root=profiles.RBM_001.package_root,
            schema_files=profiles.RBM_001.schema_files,
            reviewer_spec_count=9,
            methodology_document=profiles.RBM_001.methodology_document,
            methodology_terms=profiles.RBM_001.methodology_terms,
        )

        with pytest.raises(Exception, match="reviewer specifications"):
            validate_package(expecting_more)


class TestTheLoader:
    def test_the_bundle_carries_the_profile_it_was_loaded_under(self):
        bundle = AuthorityBundle.load()

        assert bundle.profile_id == "RBM-001"
        assert bundle.profile["profile_id"] == bundle.spec.profile_id

    def test_loading_an_unregistered_profile_fails(self):
        with pytest.raises(LookupError):
            AuthorityBundle.load(profile_id="RBM-999")

    def test_a_non_canonical_repo_root_is_still_refused(self, tmp_path):
        """Unchanged by the refactor and worth pinning: the package validators derive
        their own roots, so a different repo_root would load unvalidated authority."""

        with pytest.raises(RBEError) as error:
            AuthorityBundle.load(repo_root=tmp_path)

        assert error.value.code == "RBE_AUTHORITY_ROOT_NOT_VALIDATABLE"
