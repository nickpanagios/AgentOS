#!/usr/bin/env python3
"""
Knowledge Base Client — Shared RAG system for executive agents.

Uses ChromaDB with built-in default embeddings for semantic search.
Persistent store: /home/executive-workspace/knowledge/chromadb_store/

Usage:
    from knowledge_client import KnowledgeBase
    kb = KnowledgeBase()
    kb.store("decisions", "We chose PostgreSQL for the main DB", {"author": "jarvis", "date": "2026-02-14"})
    results = kb.query("decisions", "database choice")
    collections = kb.list_collections()

CLI:
    python knowledge_client.py store decisions "some text" '{"key": "val"}'
    python knowledge_client.py query decisions "search text" [n_results]
    python knowledge_client.py list
"""

import chromadb
import hashlib
import json
import sys
import time
from pathlib import Path

CHROMADB_PATH = "/home/executive-workspace/knowledge/chromadb_store"

# Pre-defined collections for organizational structure
DEFAULT_COLLECTIONS = [
    "decisions",
    "lessons_learned",
    "project_notes",
    "research",
    "reports",
    "code_snippets",
]


class KnowledgeBase:
    """Shared knowledge base backed by ChromaDB with persistent storage."""

    def __init__(self, path: str = CHROMADB_PATH):
        self._client = chromadb.PersistentClient(path=path)
        self._ensure_collections()

    def _ensure_collections(self):
        """Create default collections if they don't exist."""
        for name in DEFAULT_COLLECTIONS:
            self._client.get_or_create_collection(name=name)

    def store(self, collection: str, text: str, metadata: dict | None = None) -> str:
        """
        Store a document in a collection.

        Args:
            collection: Collection name (e.g. 'decisions', 'research')
            text: The text content to store
            metadata: Optional dict of metadata (author, date, tags, etc.)

        Returns:
            The generated document ID
        """
        col = self._client.get_or_create_collection(name=collection)
        # Deterministic ID from content + timestamp for dedup
        doc_id = hashlib.sha256(f"{text}{time.time()}".encode()).hexdigest()[:16]
        meta = metadata or {}
        meta.setdefault("stored_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        col.add(documents=[text], metadatas=[meta], ids=[doc_id])
        return doc_id

    def query(self, collection: str, query_text: str, n_results: int = 5) -> list[dict]:
        """
        Semantic search across a collection.

        Args:
            collection: Collection name
            query_text: Natural language query
            n_results: Max results to return (default 5)

        Returns:
            List of dicts with keys: id, document, metadata, distance
        """
        col = self._client.get_or_create_collection(name=collection)
        if col.count() == 0:
            return []
        n = min(n_results, col.count())
        results = col.query(query_texts=[query_text], n_results=n)
        out = []
        for i in range(len(results["ids"][0])):
            out.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return out

    def list_collections(self) -> list[str]:
        """List all collection names."""
        return [c.name for c in self._client.list_collections()]

    def count(self, collection: str) -> int:
        """Count documents in a collection."""
        return self._client.get_or_create_collection(name=collection).count()

    def delete(self, collection: str, doc_id: str):
        """Delete a document by ID."""
        self._client.get_or_create_collection(name=collection).delete(ids=[doc_id])


def main():
    """CLI interface."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    kb = KnowledgeBase()
    cmd = sys.argv[1]

    if cmd == "store" and len(sys.argv) >= 4:
        collection, text = sys.argv[2], sys.argv[3]
        metadata = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        doc_id = kb.store(collection, text, metadata)
        print(f"Stored: {doc_id}")

    elif cmd == "query" and len(sys.argv) >= 4:
        collection, query_text = sys.argv[2], sys.argv[3]
        n = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        results = kb.query(collection, query_text, n)
        for r in results:
            print(f"[{r['distance']:.4f}] {r['document'][:120]}")
            if r["metadata"]:
                print(f"  meta: {json.dumps(r['metadata'])}")

    elif cmd == "list":
        for name in kb.list_collections():
            print(f"  {name} ({kb.count(name)} docs)")

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
