from pathlib import Path

from bootstrap.bundle import write_bootstrap_bundle
from bootstrap.manifests import infrastructure_manifest
from bootstrap.readiness import build_readiness_summary, render_readiness_summary


def test_build_readiness_summary_marks_phase_two_ready() -> None:
    manifest = infrastructure_manifest()
    summary = build_readiness_summary(
        manifest,
        Path("bootstrap") / "compose.generated.yaml",
        Path("bootstrap") / "bootstrap.report.json",
        Path("bootstrap") / "bundle",
    )

    assert summary.manifest == "infrastructure"
    assert summary.ready is True
    assert summary.checks["storage"] is True
    assert summary.checks["exposure"] is True
    assert summary.artifacts["bundle_dir"] == "bootstrap/bundle"


def test_render_readiness_summary_returns_notes() -> None:
    manifest = infrastructure_manifest()
    summary = render_readiness_summary(
        manifest,
        Path("bootstrap") / "compose.generated.yaml",
        Path("bootstrap") / "bootstrap.report.json",
        Path("bootstrap") / "bundle",
    )

    assert summary["ready"] is True
    assert any("Storage" in note or "storage" in note for note in summary["notes"])
