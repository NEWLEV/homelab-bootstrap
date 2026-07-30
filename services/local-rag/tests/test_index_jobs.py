import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.indexer as indexer
import app.main as main
from app.index_jobs import IndexJobAlreadyRunning, IndexJobManager


client = TestClient(main.app)


def test_successful_job_is_persisted(tmp_path: Path) -> None:
    manager = IndexJobManager(tmp_path / "status.json")

    running = manager.begin()
    finished = manager.succeed({"files": 3, "total_chunks": 12})
    reloaded = IndexJobManager(tmp_path / "status.json").snapshot()

    assert running["status"] == "running"
    assert running["started_at"] is not None
    assert finished["status"] == "idle"
    assert finished["last_run_status"] == "succeeded"
    assert finished["finished_at"] is not None
    assert finished["last_success_at"] == finished["finished_at"]
    assert finished["last_result"] == {
        "files": 3,
        "total_chunks": 12,
    }
    assert reloaded == finished


def test_overlapping_job_is_rejected(tmp_path: Path) -> None:
    manager = IndexJobManager(tmp_path / "status.json")
    manager.begin()

    with pytest.raises(IndexJobAlreadyRunning):
        manager.begin()


def test_failed_job_preserves_last_success(tmp_path: Path) -> None:
    manager = IndexJobManager(tmp_path / "status.json")
    manager.begin()
    successful = manager.succeed({"files": 1})
    manager.begin()
    failed = manager.fail(RuntimeError("embedding unavailable"))

    assert failed["status"] == "failed"
    assert failed["last_run_status"] == "failed"
    assert failed["last_error"] == (
        "RuntimeError: embedding unavailable"
    )
    assert failed["last_success_at"] == successful["last_success_at"]
    assert failed["last_result"] == {"files": 1}


def test_running_job_is_marked_interrupted_on_restart(
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "status.json"
    status_path.write_text(
        json.dumps(
            {
                "status": "running",
                "started_at": "2026-07-30T12:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    state = IndexJobManager(status_path).snapshot()

    assert state["status"] == "failed"
    assert state["last_run_status"] == "interrupted"
    assert "service restart" in state["last_error"]
    assert state["finished_at"] is not None


def test_invalid_status_file_is_reported_without_crashing(
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "status.json"
    status_path.write_text("not-json", encoding="utf-8")

    state = IndexJobManager(status_path).snapshot()

    assert state["status"] == "failed"
    assert state["last_run_status"] == "status_read_failed"
    assert state["last_error"].endswith("JSONDecodeError")


def configure_api_manager(
    monkeypatch,
    tmp_path: Path,
) -> IndexJobManager:
    manager = IndexJobManager(tmp_path / "api-status.json")
    monkeypatch.setattr(main, "index_job_manager", manager)
    return manager


def index_result(**kwargs: Any) -> dict[str, Any]:
    return {
        "files": 1,
        "skipped_files": 0,
        "added_chunks": 1,
        "updated_chunks": 0,
        "skipped_chunks": 0,
        "removed_chunks": 0,
        "metadata_migrated_files": 0,
        "total_chunks": 1,
    }


def test_index_endpoint_records_success(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_api_manager(monkeypatch, tmp_path)
    monkeypatch.setattr(indexer, "index_repository", index_result)

    response = client.post("/index")
    status_response = client.get("/index/status")

    assert response.status_code == 200
    assert response.json()["status"] == "indexed"
    assert response.json()["total_chunks"] == 1
    assert response.json()["job"]["last_run_status"] == "succeeded"
    assert status_response.status_code == 200
    assert status_response.json() == response.json()["job"]


def test_index_endpoint_passes_rebuild_flag(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_api_manager(monkeypatch, tmp_path)
    captured: dict[str, Any] = {}

    def capture_index(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return index_result()

    monkeypatch.setattr(indexer, "index_repository", capture_index)

    response = client.post("/index?rebuild=true")

    assert response.status_code == 200
    assert captured == {"rebuild": True}


def test_index_endpoint_rejects_active_job(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manager = configure_api_manager(monkeypatch, tmp_path)
    manager.begin()

    response = client.post("/index")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A repository indexing job is already running."
    )


def test_index_endpoint_records_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_api_manager(monkeypatch, tmp_path)

    def fail_indexing(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("embedding unavailable")

    monkeypatch.setattr(indexer, "index_repository", fail_indexing)

    response = client.post("/index")
    status = client.get("/index/status").json()

    assert response.status_code == 500
    assert response.json()["detail"] == "Repository indexing failed."
    assert status["status"] == "failed"
    assert status["last_run_status"] == "failed"
    assert status["last_error"] == (
        "RuntimeError: embedding unavailable"
    )


def test_health_reflects_active_index_job(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manager = configure_api_manager(monkeypatch, tmp_path)
    manager.begin()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["index_status"] == "running"
