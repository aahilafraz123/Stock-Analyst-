import os
import sys
import tempfile
from pathlib import Path

import pytest

# Configure before the app is imported: isolated data dir, no external keys or embeddings.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="stockanalyzer-test-")
os.environ["EMBEDDINGS"] = "none"
for key in ("ANTHROPIC_API_KEY", "FINNHUB_API_KEY", "VOYAGE_API_KEY", "EARNINGSCALL_API_KEY"):
    os.environ[key] = ""
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import cache  # noqa: E402
from app.config import settings  # noqa: E402
from app.rag import embeddings  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """Fresh SQLite database (cache, index, history) and empty in-memory cache per test."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "embeddings", "none")
    embeddings.get_embedder.cache_clear()
    cache.clear_memory()
    yield
    embeddings.get_embedder.cache_clear()
    cache.clear_memory()


@pytest.fixture
def fixture_text():
    def load(name: str) -> str:
        return (FIXTURES / name).read_text()

    return load
