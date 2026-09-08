"""Shared test-environment configuration.

The Compose service uses production-like settings. Tests must establish
their own deterministic defaults before test modules import app.main.
"""

import os
import sys
import tempfile
from pathlib import Path


LOCAL_RAG_ROOT = Path(__file__).resolve().parents[1]
if str(LOCAL_RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(LOCAL_RAG_ROOT))


# Authentication is disabled by default in ordinary API tests.
# Authentication-specific tests enable it explicitly with monkeypatch.
os.environ.pop("API_AUTH_TOKEN", None)
os.environ.pop("API_AUTH_TOKEN_FILE", None)

# Keep health endpoint expectations and unit tests independent of the
# production Compose configuration.
os.environ["RERANKER_ENABLED"] = "false"
os.environ["RATE_LIMIT_REQUESTS_PER_MINUTE"] = "0"
os.environ["RATE_LIMIT_BURST"] = "10"
os.environ["MAX_CONCURRENT_REQUESTS"] = "0"
os.environ["MAX_REQUEST_BODY_BYTES"] = "0"

test_data_dir = Path(
    os.environ.get(
        "AISHA_LOCAL_RAG_TEST_ROOT",
        str(Path(tempfile.gettempdir()) / "aisha-local-rag-tests"),
    )
)
test_data_dir.mkdir(parents=True, exist_ok=True)
temp_dir = test_data_dir / "tmp"
temp_dir.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(temp_dir)
os.environ["TMP"] = str(temp_dir)
os.environ["TEMP"] = str(temp_dir)
tempfile.tempdir = str(temp_dir)
os.environ["CHROMA_PATH"] = str(test_data_dir / "chroma")
os.environ["INDEX_STATUS_PATH"] = str(test_data_dir / "index-status.json")
