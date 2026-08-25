import json
import zipfile

import pytest

from hfx_tools.pack import pack_hfx
from hfx_tools.submission_identity import normalize_orcid, validate_submission_identity


def test_normalize_orcid_accepts_uri_and_identifier():
    assert normalize_orcid("https://orcid.org/0000-0002-1825-0097") == "0000-0002-1825-0097"
    assert normalize_orcid("0000-0002-1825-0097") == "0000-0002-1825-0097"


@pytest.mark.parametrize(
    "identity",
    [
        {"name": "", "affiliation": "Institute", "github": "octocat"},
        {"name": "Ada", "affiliation": "", "github": "octocat"},
        {"name": "Ada", "affiliation": "Institute", "github": "-octocat"},
        {"name": "Ada", "affiliation": "Institute", "github": "octo--cat"},
        {
            "name": "Ada",
            "affiliation": "Institute",
            "github": "octocat",
            "orcid": "0000-0002-1825-0098",
        },
    ],
)
def test_invalid_submission_identities_are_rejected(identity):
    with pytest.raises(ValueError):
        validate_submission_identity(identity)


def test_packer_embeds_identity_without_changing_source_metadata(tmp_path):
    metadata_path = tmp_path / "metadata.json"
    source = {
        "version": "0.1.1",
        "metadata": {
            "producer": "Scientific producer remains intact",
            "frequencyLocation": "inline",
        },
        "frequencyData": [],
    }
    metadata_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    original_contents = metadata_path.read_text(encoding="utf-8")

    archive_path = tmp_path / "submission.hfx"
    pack_hfx(
        metadata_path,
        archive_path,
        submission_identity={
            "name": "Ada Lovelace",
            "affiliation": "Analytical Engine Institute",
            "github": "ada-lovelace",
            "orcid": "https://orcid.org/0000-0002-1825-0097",
        },
    )

    assert metadata_path.read_text(encoding="utf-8") == original_contents
    assert json.loads(original_contents)["metadata"].get("submissionIdentity") is None
    with zipfile.ZipFile(archive_path) as archive:
        bundled = json.loads(archive.read("metadata.json"))
    assert bundled["metadata"]["producer"] == source["metadata"]["producer"]
    assert bundled["metadata"]["submissionIdentity"] == {
        "name": "Ada Lovelace",
        "affiliation": "Analytical Engine Institute",
        "github": "ada-lovelace",
        "orcid": "0000-0002-1825-0097",
    }
