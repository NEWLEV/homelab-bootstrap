from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .bundle import write_bootstrap_bundle
from .cli import main as bootstrap_main
from .infrastructure import load_manifest_from_file


@dataclass(frozen=True)
class BootstrapPrepResult:
    validate_exit_code: int
    compose_exit_code: int
    report_exit_code: int
    bundle_exit_code: int
    compose_path: Path
    report_path: Path
    bundle_dir: Path

    @property
    def succeeded(self) -> bool:
        return (
            self.validate_exit_code == 0
            and self.compose_exit_code == 0
            and self.report_exit_code == 0
            and self.bundle_exit_code == 0
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aisha-bootstrap-prep",
        description="Validate the infrastructure manifest and write deployment-prep artifacts.",
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=Path("bootstrap") / "infrastructure.yaml",
        help="Path to the infrastructure manifest YAML file.",
    )
    parser.add_argument(
        "compose_output",
        nargs="?",
        type=Path,
        default=Path("bootstrap") / "compose.generated.yaml",
        help="Path to write the generated Compose YAML.",
    )
    parser.add_argument(
        "report_output",
        nargs="?",
        type=Path,
        default=Path("bootstrap") / "bootstrap.report.json",
        help="Path to write the generated bootstrap report.",
    )
    parser.add_argument(
        "bundle_dir",
        nargs="?",
        type=Path,
        default=Path("bootstrap") / "bundle",
        help="Path to write the generated bootstrap artifact bundle.",
    )
    parser.add_argument(
        "--manifest",
        dest="manifest_flag",
        type=Path,
        help="Explicit path to the infrastructure manifest YAML file.",
    )
    parser.add_argument(
        "--compose-output",
        dest="compose_output_flag",
        type=Path,
        help="Explicit path to write the generated Compose YAML.",
    )
    parser.add_argument(
        "--report-output",
        dest="report_output_flag",
        type=Path,
        help="Explicit path to write the generated bootstrap report.",
    )
    parser.add_argument(
        "--bundle-dir",
        dest="bundle_dir_flag",
        type=Path,
        help="Explicit path to write the generated bootstrap artifact bundle.",
    )
    return parser


def prepare_bootstrap(
    manifest: Path,
    *,
    compose_output: Path,
    report_output: Path,
    bundle_dir: Path,
) -> BootstrapPrepResult:
    validate_exit_code = bootstrap_main([str(manifest), "--validate"])
    compose_exit_code = bootstrap_main([
        str(manifest),
        "--write-compose",
        "--output",
        str(compose_output),
    ])
    report_exit_code = bootstrap_main([
        str(manifest),
        "--write-report",
        "--report-output",
        str(report_output),
    ])

    manifest_model = load_manifest_from_file(manifest)
    bundle = write_bootstrap_bundle(manifest_model, bundle_dir)
    bundle_exit_code = 0 if bundle.bundle_dir.exists() else 1

    return BootstrapPrepResult(
        validate_exit_code=validate_exit_code,
        compose_exit_code=compose_exit_code,
        report_exit_code=report_exit_code,
        bundle_exit_code=bundle_exit_code,
        compose_path=compose_output,
        report_path=report_output,
        bundle_dir=bundle_dir,
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    manifest = args.manifest_flag or args.manifest
    compose_output = args.compose_output_flag or args.compose_output
    report_output = args.report_output_flag or args.report_output
    bundle_dir = args.bundle_dir_flag or args.bundle_dir

    result = prepare_bootstrap(
        manifest,
        compose_output=compose_output,
        report_output=report_output,
        bundle_dir=bundle_dir,
    )
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
