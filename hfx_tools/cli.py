#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from .build import build_hfx_from_folder
from .inspect import inspect_any
from .pack import pack_hfx
from .qc import qc_hfx


def _add_pack_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("metadata_json", type=Path)
    parser.add_argument("-o", "--out", type=Path, required=True, help="Output .hfx path")
    parser.add_argument(
        "--manifest", action="store_true", help="Write MANIFEST.json into the archive"
    )
    parser.add_argument(
        "--hash",
        choices=["md5", "sha256"],
        default=None,
        help="Include checksums in manifest/SHA* file",
    )


def _add_qc_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("metadata_json", type=Path)
    parser.add_argument(
        "--write-metadata",
        action="store_true",
        help="Write computed QC stats into top-level hfx.qc",
    )
    parser.add_argument(
        "--index-row",
        action="store_true",
        help="Print a flattened JSON row intended for phycus catalog/index",
    )
    parser.add_argument(
        "--topk",
        type=int,
        nargs="*",
        default=[10, 100, 1000],
        help="Top-K cutoffs for cumulative frequency",
    )


def _add_inspect_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", type=Path)


def _add_build_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "input_folder", type=Path, help="Folder containing metadata and frequency data files"
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        required=True,
        help="Output name (without .hfx extension)",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Output directory (defaults to input folder)",
    )
    parser.add_argument("--no-manifest", action="store_true", help="Skip writing MANIFEST.json")
    parser.add_argument(
        "--hash",
        choices=["md5", "sha256", "none"],
        default="sha256",
        help="Hash algorithm",
    )
    parser.add_argument(
        "--no-auto-update-location",
        action="store_true",
        help="Don't auto-update metadata.frequencyLocation for detected data files",
    )


def _run_pack(args: argparse.Namespace) -> None:
    pack_hfx(
        metadata_json=args.metadata_json,
        out_path=args.out,
        write_manifest=args.manifest,
        hash_alg=args.hash,
    )


def _run_qc(args: argparse.Namespace) -> None:
    qc_hfx(
        metadata_json=args.metadata_json,
        write_metadata=args.write_metadata,
        index_row=args.index_row,
        topk=args.topk,
    )


def _run_inspect(args: argparse.Namespace) -> None:
    inspect_any(args.path)


def _run_build(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO)
    hash_alg = None if args.hash == "none" else args.hash
    result = build_hfx_from_folder(
        input_folder=args.input_folder,
        output_name=args.name,
        output_dir=args.out,
        write_manifest=not args.no_manifest,
        hash_alg=hash_alg,
        auto_update_frequency_location=not args.no_auto_update_location,
    )
    if not result["success"]:
        raise SystemExit(f"Build failed: {result.get('error', 'validation errors')}")


def pack_main(argv: Sequence[str] | None = None) -> None:
    """Run the standalone ``hfx-pack`` command."""
    parser = argparse.ArgumentParser(
        prog="hfx-pack", description="Build a bundled .hfx archive from metadata.json"
    )
    _add_pack_arguments(parser)
    _run_pack(parser.parse_args(argv))


def qc_main(argv: Sequence[str] | None = None) -> None:
    """Run the standalone ``hfx-qc`` command."""
    parser = argparse.ArgumentParser(
        prog="hfx-qc", description="Compute QC stats from an HFX submission JSON"
    )
    _add_qc_arguments(parser)
    _run_qc(parser.parse_args(argv))


def inspect_main(argv: Sequence[str] | None = None) -> None:
    """Run the standalone ``hfx-inspect`` command."""
    parser = argparse.ArgumentParser(
        prog="hfx-inspect", description="Inspect metadata.json or a bundled .hfx"
    )
    _add_inspect_arguments(parser)
    _run_inspect(parser.parse_args(argv))


def build_main(argv: Sequence[str] | None = None) -> None:
    """Run the standalone ``hfx-build`` command."""
    parser = argparse.ArgumentParser(
        prog="hfx-build", description="Build an HFX bundle from a folder"
    )
    _add_build_arguments(parser)
    _run_build(parser.parse_args(argv))


def main(argv: Sequence[str] | None = None) -> None:
    """Run the subcommand-based interface used by direct Python callers."""
    parser = argparse.ArgumentParser(prog="hfx-tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pack = sub.add_parser("pack", help="Build a bundled .hfx archive (zip) from metadata.json")
    _add_pack_arguments(p_pack)
    p_pack.set_defaults(handler=_run_pack)

    p_qc = sub.add_parser("qc", help="Compute QC stats from an HFX submission JSON")
    _add_qc_arguments(p_qc)
    p_qc.set_defaults(handler=_run_qc)

    p_ins = sub.add_parser("inspect", help="Inspect metadata.json or a bundled .hfx")
    _add_inspect_arguments(p_ins)
    p_ins.set_defaults(handler=_run_inspect)

    p_build = sub.add_parser("build", help="Build an HFX bundle from a folder")
    _add_build_arguments(p_build)
    p_build.set_defaults(handler=_run_build)

    args = parser.parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
