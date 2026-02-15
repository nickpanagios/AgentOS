#!/usr/bin/env python3
"""
Knowledge Base Client — Shared RAG system for executive agents.

Uses ChromaDB with built-in default embeddings for semantic search.
Persistent store: /home/executive-workspace/knowledge/chromadb_store/

Supports project namespacing: collections are internally stored as
{project}__{collection} (double underscore separator).

Usage:
    from knowledge_client import KnowledgeBase
    kb = KnowledgeBase()
    kb.store("decisions", "We chose PostgreSQL for the main DB", {"author": "jarvis"}, project="acme-corp")
    results = kb.query("decisions", "database choice", project="acme-corp")
    collections = kb.list_collections(project="acme-corp")
    projects = kb.list_projects()

CLI:
    python knowledge_client.py store decisions "some text" '{"key": "val"}' --project acme-corp
    python knowledge_client.py query decisions "search text" [n_results] --project acme-corp
    python knowledge_client.py list [--project acme-corp]
    python knowledge_client.py projects
"""

import chromadb
import hashlib
import json
import sys
import time
from pathlib import Path

CHROMADB_PATH = "/home/executive-workspace/knowledge/chromadb_store"
PROJECT_SEP = "__"
DEFAULT_PROJECT = "default"

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
    """Shared knowledge base backed by ChromaDB with persistent storage and project namespacing."""

    def __init__(self, path: str = CHROMADB_PATH):
        self._client = chromadb.PersistentClient(path=path)
        self._ensure_collections()

    def _col_name(self, collection: str, project: str | None = None) -> str:
        """Build internal collection name with project prefix."""
        p = project or DEFAULT_PROJECT
        return f"{p}{PROJECT_SEP}{collection}"

    def _parse_col_name(self, internal_name: str) -> tuple[str, str]:
        """Parse internal name into (project, collection)."""
        if PROJECT_SEP in internal_name:
            project, collection = internal_name.split(PROJECT_SEP, 1)
            return project, collection
        return DEFAULT_PROJECT, internal_name

    def _ensure_collections(self):
        """Create default collections if they don't exist."""
        for name in DEFAULT_COLLECTIONS:
            self._client.get_or_create_collection(name=self._col_name(name))

    def store(self, collection: str, text: str, metadata: dict | None = None,
              project: str | None = None) -> str:
        """
        Store a document in a collection.

        Args:
            collection: Collection name (e.g. 'decisions', 'research')
            text: The text content to store
            metadata: Optional dict of metadata (author, date, tags, etc.)
            project: Project namespace (default: 'default')

        Returns:
            The generated document ID
        """
        col = self._client.get_or_create_collection(name=self._col_name(collection, project))
        doc_id = hashlib.sha256(f"{text}{time.time()}".encode()).hexdigest()[:16]
        meta = metadata or {}
        meta.setdefault("stored_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        meta["project"] = project or DEFAULT_PROJECT
        col.add(documents=[text], metadatas=[meta], ids=[doc_id])
        return doc_id

    def query(self, collection: str, query_text: str, n_results: int = 5,
              project: str | None = None) -> list[dict]:
        """
        Semantic search across a collection.

        Args:
            collection: Collection name
            query_text: Natural language query
            n_results: Max results to return (default 5)
            project: Project namespace (default: 'default')

        Returns:
            List of dicts with keys: id, document, metadata, distance
        """
        col = self._client.get_or_create_collection(name=self._col_name(collection, project))
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

    def list_collections(self, project: str | None = None) -> list[str]:
        """List collection names, optionally filtered by project."""
        all_cols = [c.name for c in self._client.list_collections()]
        if project is None:
            # Return all with human-readable names
            return [self._parse_col_name(c)[1] for c in all_cols]
        prefix = f"{project}{PROJECT_SEP}"
        return [c[len(prefix):] for c in all_cols if c.startswith(prefix)]

    def list_collections_raw(self) -> list[str]:
        """List all internal collection names (with project prefixes)."""
        return [c.name for c in self._client.list_collections()]

    def count(self, collection: str, project: str | None = None) -> int:
        """Count documents in a collection."""
        return self._client.get_or_create_collection(
            name=self._col_name(collection, project)).count()

    def delete(self, collection: str, doc_id: str, project: str | None = None):
        """Delete a document by ID."""
        self._client.get_or_create_collection(
            name=self._col_name(collection, project)).delete(ids=[doc_id])

    def list_projects(self) -> list[str]:
        """Extract unique project prefixes from all collections."""
        all_cols = [c.name for c in self._client.list_collections()]
        projects = set()
        for c in all_cols:
            p, _ = self._parse_col_name(c)
            projects.add(p)
        return sorted(projects)

    def search_all_projects(self, collection: str, query_text: str,
                            n_results: int = 5) -> list[dict]:
        """Search across all projects for a given collection type."""
        all_cols = [c.name for c in self._client.list_collections()]
        suffix = f"{PROJECT_SEP}{collection}"
        results = []
        for col_name in all_cols:
            if col_name.endswith(suffix) or col_name == collection:
                project, _ = self._parse_col_name(col_name)
                col = self._client.get_or_create_collection(name=col_name)
                if col.count() == 0:
                    continue
                n = min(n_results, col.count())
                res = col.query(query_texts=[query_text], n_results=n)
                for i in range(len(res["ids"][0])):
                    entry = {
                        "id": res["ids"][0][i],
                        "document": res["documents"][0][i],
                        "metadata": res["metadatas"][0][i],
                        "distance": res["distances"][0][i] if res.get("distances") else None,
                        "project": project,
                    }
                    results.append(entry)
        results.sort(key=lambda r: r.get("distance") or 999)
        return results[:n_results]


def _extract_flag(args, flag, default=None):
    """Extract --flag value from args list, returning (value, remaining_args)."""
    remaining = []
    value = default
    i = 0
    while i < len(args):
        if args[i] == flag and i + 1 < len(args):
            value = args[i + 1]
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return value, remaining


def main():
    """CLI interface."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    raw_args = sys.argv[2:]
    project, raw_args = _extract_flag(raw_args, "--project")

    kb = KnowledgeBase()
    cmd = sys.argv[1]

    if cmd == "store" and len(raw_args) >= 2:
        collection, text = raw_args[0], raw_args[1]
        metadata = json.loads(raw_args[2]) if len(raw_args) > 2 else {}
        doc_id = kb.store(collection, text, metadata, project=project)
        print(f"Stored: {doc_id} (project: {project or DEFAULT_PROJECT})")

    elif cmd == "query" and len(raw_args) >= 2:
        collection, query_text = raw_args[0], raw_args[1]
        n = int(raw_args[2]) if len(raw_args) > 2 else 5
        results = kb.query(collection, query_text, n, project=project)
        for r in results:
            print(f"[{r['distance']:.4f}] {r['document'][:120]}")
            if r["metadata"]:
                print(f"  meta: {json.dumps(r['metadata'])}")

    elif cmd == "list":
        for name in kb.list_collections(project=project):
            print(f"  {name} ({kb.count(name, project=project)} docs)")

    elif cmd == "projects":
        for p in kb.list_projects():
            cols = kb.list_collections(project=p)
            print(f"  {p} ({len(cols)} collections)")

    elif cmd == "search-all" and len(raw_args) >= 2:
        collection, query_text = raw_args[0], raw_args[1]
        n = int(raw_args[2]) if len(raw_args) > 2 else 5
        results = kb.search_all_projects(collection, query_text, n)
        for r in results:
            print(f"[{r['distance']:.4f}] [{r['project']}] {r['document'][:120]}")

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
