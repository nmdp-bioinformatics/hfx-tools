"""Validation and normalization for HFX submission identities."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_GITHUB_USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")
_ORCID_RE = re.compile(r"^(\d{4})-(\d{4})-(\d{4})-(\d{3}[\dX])$")
_ORCID_URI_RE = re.compile(r"^https?://orcid\.org/(.+?)/?$", re.IGNORECASE)


def normalize_orcid(value: str) -> str:
    """Return a canonical ORCID or raise ``ValueError`` for an invalid one."""
    candidate = value.strip()
    uri_match = _ORCID_URI_RE.fullmatch(candidate)
    if uri_match:
        candidate = uri_match.group(1)
    candidate = candidate.upper()
    match = _ORCID_RE.fullmatch(candidate)
    if not match:
        raise ValueError("ORCID must be 0000-0000-0000-0000 or an orcid.org URI")

    digits = candidate.replace("-", "")
    total = 0
    for digit in digits[:15]:
        total = (total + int(digit)) * 2
    expected = (12 - (total % 11)) % 11
    expected_check_digit = "X" if expected == 10 else str(expected)
    if digits[-1] != expected_check_digit:
        raise ValueError("ORCID checksum is invalid")
    return candidate


def validate_submission_identity(identity: Mapping[str, Any]) -> dict[str, str]:
    """Validate required identity fields and return a clean bundle-ready mapping."""
    name = str(identity.get("name", "")).strip()
    affiliation = str(identity.get("affiliation", "")).strip()
    github = str(identity.get("github", "")).strip()
    if not name:
        raise ValueError("Contributor name is required")
    if not affiliation:
        raise ValueError("Affiliation is required")
    if not _GITHUB_USERNAME_RE.fullmatch(github):
        raise ValueError("GitHub username is invalid")

    result = {"name": name, "affiliation": affiliation, "github": github}
    orcid = str(identity.get("orcid", "")).strip()
    if orcid:
        result["orcid"] = normalize_orcid(orcid)
    return result
