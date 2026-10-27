"""Pluggable dense embeddings for hybrid retrieval.

- voyage: Voyage AI's finance-tuned model over HTTPS (needs VOYAGE_API_KEY)
- local:  fastembed ONNX model on CPU (pip install fastembed; downloads once)
- none:   lexical BM25 only

Retrieval always works without embeddings; they improve recall on paraphrased
questions ("how much cash do they burn" vs "net cash used in operating activities").
"""

import logging
from functools import lru_cache
from typing import Literal, Protocol

import httpx
import numpy as np

from app.config import settings
from app.errors import UpstreamError

log = logging.getLogger(__name__)

Kind = Literal["document", "query"]


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str], kind: Kind) -> np.ndarray: ...


def _normalise(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class VoyageEmbedder:
    url = "https://api.voyageai.com/v1/embeddings"
    batch_size = 64

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.name = f"voyage:{model}"

    def embed(self, texts: list[str], kind: Kind) -> np.ndarray:
        out = []
        with httpx.Client(timeout=60) as client:
            for i in range(0, len(texts), self.batch_size):
                response = client.post(
                    self.url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"input": texts[i : i + self.batch_size], "model": self.model, "input_type": kind},
                )
                if response.status_code >= 400:
                    raise UpstreamError(f"Voyage embeddings failed: HTTP {response.status_code}", source="Voyage AI")
                out.extend(item["embedding"] for item in sorted(response.json()["data"], key=lambda d: d["index"]))
        return _normalise(np.array(out))


class LocalEmbedder:
    def __init__(self, model: str):
        from fastembed import TextEmbedding  # optional dependency

        self._model = TextEmbedding(model_name=model)
        self.name = f"fastembed:{model}"

    def embed(self, texts: list[str], kind: Kind) -> np.ndarray:
        embed = self._model.query_embed if kind == "query" else self._model.passage_embed
        return _normalise(np.array(list(embed(texts))))


@lru_cache(maxsize=1)
def get_embedder() -> Embedder | None:
    mode = settings.embeddings
    if mode == "none":
        return None
    if mode in ("voyage", "auto") and settings.voyage_api_key:
        return VoyageEmbedder(settings.voyage_api_key, settings.voyage_model)
    if mode in ("local", "auto"):
        try:
            return LocalEmbedder(settings.local_embedding_model)
        except Exception as exc:  # not installed, or model download blocked
            level = logging.WARNING if mode == "local" else logging.INFO
            log.log(level, "Local embeddings unavailable (%s); using BM25 only", exc)
    return None
