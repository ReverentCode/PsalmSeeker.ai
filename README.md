# PsalmSeeker

*A contemplative, local-first Scripture companion.*

**PsalmSeeker** is a Dash application that retrieves Psalms by **semantic meaning** (embeddings) and guides the user into **reverent reflection** using a **local Ollama LLM**.

The experience is intentionally structured as a journey:

**Gates → Courts → Holy of Holies**

Moving from honest posture, to Scripture selection, to quiet reflection.

No cloud APIs. No data leaves your machine.

---

## ✨ Features

- 🔍 **Semantic Psalm Retrieval**  
  Finds Psalms by *meaning*, not keywords, using vector embeddings.

- 🧠 **Local LLM Reflection**  
  Generates Scripture-centered reflections using a locally running model (default: `llama3:8b`).

- 🛐 **Intentional UX Flow**  
  Progress-based interaction encourages slowing down, choosing carefully, and abiding.

- 🏠 **Local-First & Private**  
  Runs entirely on your machine via Ollama.

---

## 🧩 Architecture Overview

- **UI**: Dash + Dash Bootstrap Components  
- **Retrieval**: Vector embeddings + cosine similarity  
- **Embedding Model**: `nomic-embed-text`  
- **Reflection Model**: `llama3:8b` (configurable)  
- **Index Storage**: NumPy `.npz` (precomputed)

---

## 🖼️ Preview

![PsalmSeeker interface](assets/demo/PsalmSeeker_Main.png)

## 🚀 Setup & Run

### 1️⃣ Create a virtual environment & install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Download `ollama`
- https://ollama.com/
- **Check that it's running:**
- `http://localhost:11434`

<br>
### Pull Models
- `ollama pull llama3:8b`
- `ollama pull nomic-embed-text`

### Build index of psalm corpus
This step takes awhile, as it's indexing, chunking, and embedding all the psalms into a local NumPy compressed vector store.
- `python scripts\build_index.py`

### Run that bad boi
- `python app.py`
- Open: `http://127.0.0.1:8050`

## ⚙️ Configuration

PsalmSeeker supports configuration via a `.env` file.

**Example:**
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b
EMBEDDING_MODEL=nomic-embed-text
```
