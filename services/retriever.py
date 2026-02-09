import os
import json
import numpy as np
from dotenv import load_dotenv
from sklearn.neighbors import NearestNeighbors

from services.ollama import OllamaClient

load_dotenv()

def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12
    return v / n

class PsalmRetriever:
    """
    Loads a prebuilt index (npz) containing:
      - texts: list[str]
      - meta: list[dict]
      - emb: float32 matrix [N, D]
    and runs cosine KNN.
    """

    def __init__(self):
        self.index_path = os.getenv("INDEX_PATH", "storage/psalms_index.npz")
        self._ollama = OllamaClient()

        self._loaded = False
        self._texts = []
        self._meta = []
        self._emb = None
        self._knn = None

        self._try_load()

    def _try_load(self):
        if not os.path.exists(self.index_path):
            return

        data = np.load(self.index_path, allow_pickle=True)
        self._texts = data["texts"].tolist()
        self._meta = data["meta"].tolist()
        self._emb = data["emb"].astype(np.float32)

        X = _normalize(self._emb)
        self._knn = NearestNeighbors(n_neighbors=min(10, len(X)), metric="cosine")
        self._knn.fit(X)

        self._loaded = True

    def ready(self) -> bool:
        return self._loaded

    def search(self, query: str, k: int = 6) -> list[dict]:
        if not self._loaded:
            raise RuntimeError(f"Index not found at {self.index_path}. Run: python scripts/build_index.py")

        q = np.array(self._ollama.embed(query), dtype=np.float32)
        q = _normalize(q.reshape(1, -1))

        distances, indices = self._knn.kneighbors(q, n_neighbors=min(k, len(self._texts)))
        distances = distances[0]
        indices = indices[0]

        results = []
        for rank, (i, d) in enumerate(zip(indices, distances)):
            score = float(1.0 - d)  # cosine similarity
            meta = dict(self._meta[i])
            results.append(
                {
                    "id": meta.get("id", i),
                    "score": score,
                    "text": self._texts[i],
                    **meta,
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results