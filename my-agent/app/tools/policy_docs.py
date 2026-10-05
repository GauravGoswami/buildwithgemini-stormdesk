"""Policy documentation RAG search tool using Vertex AI RAG Engine."""

import os
from typing import Any, Dict, List
import vertexai
from vertexai import rag

from app.config import LOCATION, PROJECT_ID


def search_policy_docs(query: str) -> List[Dict[str, Any]]:
    """Search policy documents, guidelines, and SOPs for relevant coverage rules and clauses.

    Args:
        query: Search query string (e.g. "roof age depreciation", "wind hail deductible", "22-year-old roof").

    Returns:
        List of top 5 passages with text snippet and source file name.
    """
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    corpora = list(rag.list_corpora())
    target_corpus = None
    for corpus in corpora:
        if corpus.display_name == "stormdesk-policy-docs":
            target_corpus = corpus
            break

    if not target_corpus:
        return [{"error": "Corpus stormdesk-policy-docs not found"}]

    response = rag.retrieval_query(
        rag_resources=[rag.RagResource(rag_corpus=target_corpus.name)],
        text=query,
        rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
    )

    results = []
    for ctx in response.contexts.contexts:
        source_name = (
            getattr(ctx, "source_display_name", None)
            or getattr(ctx, "source_uri", "").split("/")[-1]
            or "unknown"
        )
        results.append({
            "source_file": source_name,
            "text": ctx.text,
        })

    return results
