from importlib.metadata import version

from hfx_tools import __version__


def test_package_metadata_version_matches_runtime_version() -> None:
    assert version("hfx-tools") == __version__
