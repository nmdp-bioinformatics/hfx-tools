import json

from hfx_tools.cli import main


def test_generic_inspect_subcommand_accepts_an_hfx_document(tmp_path, capsys):
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        json.dumps({"version": "0.1.1", "metadata": {"frequencyLocation": "inline"}}),
        encoding="utf-8",
    )

    main(["inspect", str(metadata_path)])

    assert "frequencyLocation: inline" in capsys.readouterr().out
