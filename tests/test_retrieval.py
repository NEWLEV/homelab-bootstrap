import os
import shutil
from pathlib import Path

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))

from app.indexer import is_allowed
from app.main import build_metadata_filter
from app.retrieval import rerank_candidates

REPO_ROOT = Path("C:/Users/ZBook/Documents/Aisha")
SCRATCH_ROOT = REPO_ROOT / ".test-retrieval-fixtures"


def test_build_metadata_filter_supports_path_prefix() -> None:
    where = build_metadata_filter(path_prefix="docs/")

    assert where == {"path": {"$contains": "docs/"}}


def test_build_metadata_filter_supports_directory_prefix() -> None:
    where = build_metadata_filter(directory_prefix="docs/guides")

    assert where == {"directory": {"$contains": "docs/guides"}}


def test_rerank_candidates_prefers_lexical_overlap() -> None:
    ranked = rerank_candidates(
        query="alpha beta",
        matches=[
            {"path": "one.md", "snippet": "alpha alpha", "distance": 0.4},
            {"path": "two.md", "snippet": "beta", "distance": 0.05},
        ],
        limit=2,
    )

    assert ranked[0]["path"] == "one.md"
    assert ranked[0]["matching_tokens"] == ["alpha"]
    assert ranked[0]["combined_score"] >= ranked[1]["combined_score"]


def test_rerank_candidates_prefers_docs_over_tests_for_operational_queries() -> None:
    ranked = rerank_candidates(
        query="How are backups configured and scheduled?",
        matches=[
            {
                "path": "tests/test_bootstrap_backup.py",
                "snippet": "backups scheduled daily with snapshot rotation",
                "distance": 0.2,
            },
            {
                "path": "docs/services.md",
                "snippet": "Encrypted backups with daily snapshot rotation and restore verification.",
                "distance": 0.22,
            },
        ],
        limit=2,
    )

    assert ranked[0]["path"] == "docs/services.md"
    assert ranked[0]["path_bias"] > ranked[1]["path_bias"]


def test_is_allowed_excludes_ephemeral_request_artifacts() -> None:
    assert not is_allowed(REPO_ROOT / "conversation-request.json")
    assert not is_allowed(REPO_ROOT / "grounded-request.json")
    assert not is_allowed(REPO_ROOT / "diagnose-generation.py")


def test_is_allowed_excludes_virtualenv_and_generated_bundle_artifacts() -> None:
    if SCRATCH_ROOT.exists():
        shutil.rmtree(SCRATCH_ROOT)

    venv_file = SCRATCH_ROOT / ".venv" / "lib" / "python3.13" / "site-packages" / "pkg" / "file.py"
    venv_file.parent.mkdir(parents=True)
    venv_file.write_text("print('x')", encoding="utf-8")

    generated = SCRATCH_ROOT / "bootstrap" / "prep-bundle-test" / "bootstrap.report.json"
    generated.parent.mkdir(parents=True)
    generated.write_text("{}", encoding="utf-8")

    docs_file = SCRATCH_ROOT / "docs" / "services.md"
    docs_file.parent.mkdir(parents=True)
    docs_file.write_text("real docs", encoding="utf-8")

    config_file = SCRATCH_ROOT / "configs" / "services.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text("{}", encoding="utf-8")

    try:
        assert not is_allowed(venv_file)
        assert not is_allowed(generated)
        assert is_allowed(docs_file)
        assert is_allowed(config_file)
    finally:
        shutil.rmtree(SCRATCH_ROOT, ignore_errors=True)