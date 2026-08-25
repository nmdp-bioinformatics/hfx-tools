from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

COMMANDS = ("hfx-build", "hfx-pack", "hfx-qc", "hfx-inspect")


@pytest.fixture
def metadata_path(tmp_path: Path) -> Path:
    metadata = {
        "version": "0.1.1",
        "metadata": {
            "outputResolution": [{"locus": "A", "resolution": "g"}],
            "hfeMethod": {"method": "EM"},
            "cohortDescription": {
                "species": "Homo sapiens",
                "cohortSize": 2,
                "population": [],
            },
            "nomenclatureUsed": {
                "database": "IPD-IMGT/HLA",
                "version": "3.58.0",
            },
            "frequencyLocation": "inline",
        },
        "frequencyData": [
            {"haplotype": "A*01:01", "frequency": 0.6},
            {"haplotype": "A*02:01", "frequency": 0.4},
        ],
    }
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    return path


def run_command(*args: str | Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
    )


@pytest.mark.parametrize("command", COMMANDS)
def test_installed_command_help_uses_standalone_parser(command: str) -> None:
    result = run_command(command, "--help")

    assert result.returncode == 0, result.stderr
    assert f"usage: {command}" in result.stdout
    assert "{pack,qc,inspect,build}" not in result.stdout


def test_hfx_pack_direct_invocation(metadata_path: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "packed.hfx"

    result = run_command("hfx-pack", metadata_path, "-o", output_path)

    assert result.returncode == 0, result.stderr
    assert output_path.is_file()


def test_hfx_qc_direct_invocation(metadata_path: Path) -> None:
    result = run_command("hfx-qc", metadata_path)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["nHaplotypes"] == 2


def test_hfx_inspect_direct_invocation(metadata_path: Path) -> None:
    result = run_command("hfx-inspect", metadata_path)

    assert result.returncode == 0, result.stderr
    assert "frequencyLocation: inline" in result.stdout


def test_hfx_build_direct_invocation(metadata_path: Path, tmp_path: Path) -> None:
    result = run_command("hfx-build", tmp_path, "-n", "built")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "built.hfx").is_file()
    assert (tmp_path / "built.build.log").is_file()
