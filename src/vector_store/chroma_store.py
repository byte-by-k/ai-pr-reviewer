"""
ChromaDB vector store — persists and queries embedded code review rules.
"""

from __future__ import annotations
from typing import List, Tuple
import chromadb
from chromadb.utils import embedding_functions
from src.rules.loader import Rule


COLLECTION_NAME = "code_review_rules"


class RuleVectorStore:
    """
    Wraps a ChromaDB collection that stores code review rules as embeddings.

    Usage:
        store = RuleVectorStore(persist_dir=".chroma")
        store.embed_rules(rules)                        # one-time / on rule change
        matches = store.query(diff_chunk, top_k=5)      # at review time
    """

    def __init__(self, persist_dir: str = ".chroma", model_name: str = "all-MiniLM-L6-v2"):
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    def embed_rules(self, rules: List[Rule], force_refresh: bool = False) -> None:
        """Embed all rules into ChromaDB. Skips existing unless force_refresh=True."""
        existing_ids = set(self._collection.get()["ids"])
        new_rules = [r for r in rules if r.id not in existing_ids] if not force_refresh else rules
        if force_refresh and existing_ids:
            self._collection.delete(ids=list(existing_ids))
        if not new_rules:
            return
        self._collection.add(
            ids=[r.id for r in new_rules],
            documents=[r.to_embedding_text() for r in new_rules],
            metadatas=[
                {"name": r.name, "category": r.category, "severity": r.severity, "tags": ",".join(r.tags)}
                for r in new_rules
            ],
        )

    def query(self, diff_chunk: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Retrieve top_k most semantically relevant rule IDs for a diff chunk."""
        results = self._collection.query(
            query_texts=[diff_chunk],
            n_results=min(top_k, self._collection.count()),
            include=["distances"],
        )
        return list(zip(results["ids"][0], results["distances"][0]))

    def count(self) -> int:
        return self._collection.count()
