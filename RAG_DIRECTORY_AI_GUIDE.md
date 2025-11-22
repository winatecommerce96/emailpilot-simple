# EmailPilot RAG Directory Integration Guide

This guide explains how another directory-based AI or automation service can use the local `rag/` assets in this repository to perform semantic search, and how to access the hosted RAG APIs documented in the project.

---

## 1. Directory Structure Overview

`rag/` maintains per-client isolation across four companion folders:

| Directory | Purpose | Example |
|-----------|---------|---------|
| `rag/corpus/<client_id>/` | Raw source documents captured during ingestion (`.txt`, `.yaml`, `.html`, uploads, etc.). | `rag/corpus/christopher-bean-coffee/text_3d0b0e04c954_text.txt` |
| `rag/processed/<client_id>/` | Chunked JSON payloads the orchestrator reads during retrieval. Each file mirrors one document and includes metadata plus the chunk list. | `rag/processed/rogue-creamery/text_ecc92e8a4a3a.json` |
| `rag/vectorstores/<client_id>/` | Persisted FAISS indices (`index.faiss`/`index.pkl`) built by the LangChain pipeline for semantic similarity search. | `rag/vectorstores/the-phoenix/index.faiss` |
| `rag/index/` | Reserved for legacy keyword indices. Currently empty in this repo but kept for backward compatibility. |

Paths can be remapped at runtime through the path configuration helpers in `config/paths.py` (see `rag_corpus()` and `rag_vector_stores()`).

---

## 2. Document Format and Metadata

Processed documents are JSON files shaped like:

```jsonc
{
  "doc_id": "text_3d0b0e04c954",
  "client_id": "christopher-bean-coffee",
  "title": "Product Information",
  "chunks": ["...", "..."],
  "metadata": {
    "doc_type": "brand_guidelines",
    "source_type": "text"
  },
  "processed_at": "2025-10-04T00:41:12.473218"
}
```

- Each chunk is a semantically coherent text block already optimized for retrieval.
- Client bleed prevention relies on `client_id`; never mix documents across client folders.
- `metadata` carries ingest-time hints (document type, source URL, campaign tags, etc.) that can be used to filter or weight results.

---

## 3. Loading Content for Semantic Search

### 3.1 Enumerate Available Clients

```python
from pathlib import Path

rag_root = Path("rag")
client_ids = [p.name for p in (rag_root / "processed").iterdir() if p.is_dir()]
```

### 3.2 Keyword-Style Retrieval from Processed JSON

Ideal for lightweight agents without embedding support.

```python
import json
from pathlib import Path

def load_chunks(client_id: str):
    processed_dir = Path("rag/processed") / client_id
    for doc_path in processed_dir.glob("*.json"):
        data = json.loads(doc_path.read_text())
        yield from (
            {
                "doc_id": data["doc_id"],
                "title": data.get("title"),
                "metadata": data.get("metadata", {}),
                "text": chunk,
                "source_path": str(doc_path),
            }
            for chunk in data.get("chunks", [])
        )
```

### 3.3 Vector Retrieval with LangChain + FAISS

The project ships with persisted FAISS indices that can be loaded directly:

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

embeddings = OpenAIEmbeddings(
    model="text-embedding-ada-002",
    openai_api_key="YOUR_KEY"
)

client_id = "rogue-creamery"
vs_path = f"rag/vectorstores/{client_id}"

vectorstore = FAISS.load_local(
    vs_path,
    embeddings,
    index_name="index",
    allow_dangerous_deserialization=True  # safe: indices produced locally
)

docs = vectorstore.similarity_search("seasonal cheese gift ideas", k=5)
```

#### Notes
- Embedding model selection is configurable; the repository defaults to OpenAI (`text-embedding-ada-002`).
- If you need to build a vector store from scratch, reuse the orchestrator in `services/langchain_rag_orchestrator.py`.
- Without an embedding key, fall back to the keyword loader shown above (mirrors `services/rag_service.py`).

---

## 4. Maintaining the Vector Stores

1. **Automatic ingestion** (FastAPI stack): `api_rag_enhanced.py` wires uploads, URL ingestion, and free-form text to async jobs that ultimately populate `rag/processed/` and the FAISS store.
2. **Batch migration**: `scripts/migrate_rag_to_langchain.py` replays an entire client corpus into LangChain/FAISS. Run `python scripts/migrate_rag_to_langchain.py --client <client_id> [--force --test]`.
3. **Runtime configuration**: `USE_LANGCHAIN_RAG=true` switches the API to the LangChain orchestrator. Missing `OPENAI_API_KEY` triggers an automatic keyword-search fallback.
4. **Path overrides**: set `EMAILPILOT_RAG_ROOT`, `EMAILPILOT_RAG_CORPUS`, or `EMAILPILOT_RAG_VECTORS` (see `config/paths.py`) if your agent requires a different storage root.

When rebuilding indices, remember to persist both `index.faiss` and `index.pkl` inside the client folder—the FAISS loader expects both artifacts.

---

## 5. Hosted RAG Access Points

Repository documentation confirms a deployed API at `https://api.emailpilot.ai` with equivalent RAG endpoints for production use (`docs/QUICK_REFERENCE.md`, `docs/API_REFERENCE.md`):

| Environment | Base URL | Example RAG Calls |
|-------------|----------|-------------------|
| Production | `https://api.emailpilot.ai` | `POST /api/rag/enhanced/upload`, `POST /api/rag/enhanced/retrieve`, `GET /api/rag/enhanced/stats/{client_id}` |
| Staging | `https://staging-api.emailpilot.ai` | Same endpoint paths for pre-production validation |
| Local Dev | `http://localhost:8003` (default FastAPI port) | Mirrors the enhanced RAG API under `/api/rag/enhanced/*` |

Example upload (production):

```bash
curl -X POST https://api.emailpilot.ai/api/rag/enhanced/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@brand_guidelines.pdf" \
  -F "client_id=rogue-creamery" \
  -F "doc_type=brand_guidelines"
```

Example retrieval (local):

```bash
curl -X POST http://localhost:8003/api/rag/enhanced/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "rogue-creamery",
    "query": "holiday cheese sampler messaging",
    "top_k": 5,
    "min_relevance": 0.35
  }'
```

> **Authentication:** Production deployments typically require bearer tokens or Clerk-based auth (see `AUTHENTICATION_QUICK_START.md`). Ensure your agent can attach the appropriate headers before hitting hosted endpoints.

---

## 6. Recommended Workflow for an External AI Agent

1. **Discover clients** by scanning `rag/processed/`.
2. **Load processed JSON** to bootstrap a local semantic cache.
3. **Prefer vectorstores** when `index.faiss` exists and you have embedding keys; otherwise use keyword scoring on `chunks`.
4. **Keep indices fresh** by running the migration script or hitting `/api/rag/enhanced/reindex/{client_id}` via the FastAPI service after syncing new documents.
5. **Leverage metadata** (`doc_type`, `source_type`, etc.) to filter snippets per task (brand voice vs. product catalog).
6. **Respect client isolation**—always scope retrieval by `client_id`.
7. **Use hosted APIs** when remote access is required, mirroring the same payloads documented above.

Following these steps lets another directory-aware AI system read, index, and serve the same RAG knowledge either offline (via filesystem access) or online (through the documented API surface).

