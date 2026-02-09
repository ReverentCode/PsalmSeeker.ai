import os
import requests
from dotenv import load_dotenv

load_dotenv()

class OllamaClient:
    def __init__(self):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.llm_model = os.getenv("OLLAMA_LLM_MODEL", "llama3:8b")
        self.embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    def generate(self, system: str, prompt: str) -> str:
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()

    def embed(self, text: str) -> list[float]:
        url = f"{self.host}/api/embeddings"
        payload = {"model": self.embed_model, "prompt": text}
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        emb = data.get("embedding")
        if not emb:
            raise RuntimeError("No embedding returned. Ensure an embedding model is installed and configured.")
        return emb