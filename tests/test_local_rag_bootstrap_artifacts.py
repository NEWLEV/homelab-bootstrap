from __future__ import annotations

from pathlib import Path


def test_local_rag_bootstrap_artifacts_exist() -> None:
    service_dir = Path(r"C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/local-rag")

    assert (service_dir / "systemd" / "aisha-local-rag.service").exists()
    assert (service_dir / "scripts" / "install-local-rag-service.sh").exists()
    assert (service_dir / "scripts" / "run-local-rag.sh").exists()
