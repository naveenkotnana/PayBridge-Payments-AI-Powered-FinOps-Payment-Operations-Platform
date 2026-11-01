"""Unit tests for the local RAG vector store and role-based clearance filtering."""
from app.rag.store import get_store, Chunk, ACCESS_ORDER, ROLE_CLEARANCE


def test_rag_store_initialization():
    store = get_store()
    stats = store.stats()
    assert stats["chunks"] > 0
    assert stats["documents"] > 0
    assert stats["mode"] in ("tfidf", "ollama")


def test_clearance_filtering_analyst():
    store = get_store()
    results = store.search("privacy anonymised policy", k=10, role="ANALYST")
    assert len(results) > 0
    analyst_clearance = ACCESS_ORDER[ROLE_CLEARANCE["ANALYST"]]
    for res in results:
        assert ACCESS_ORDER[res["access_level"]] <= analyst_clearance


def test_clearance_filtering_admin():
    store = get_store()
    results = store.search("revenue calculation SOP proration rules", k=10, role="ADMIN")
    assert len(results) > 0
    admin_clearance = ACCESS_ORDER[ROLE_CLEARANCE["ADMIN"]]
    for res in results:
        assert ACCESS_ORDER[res["access_level"]] <= admin_clearance


def test_chunk_citation_property():
    chunk = Chunk(
        chunk_id="CHK-1",
        document_id="DOC-001",
        title="Revenue Calculation SOP",
        document_type="SOP",
        version="1.0",
        effective_date="2026-01-01",
        department="FINANCE",
        access_level="INTERNAL",
        section="1.1",
        text="Sample text",
    )
    assert chunk.citation == "[DOC-001 v1.0 §1.1] Revenue Calculation SOP"


def test_empty_search_query_handling():
    store = get_store()
    results = store.search("", k=3, role="ANALYST")
    assert isinstance(results, list)
