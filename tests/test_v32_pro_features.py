import pytest
from fastapi.testclient import TestClient
from app.schemas import (
    BookSearchQuery,
    BookCandidate,
    LicenseStatus,
    LicensingEvidence
)
from app.services.crossref import search_crossref
from app.services.metadata_aggregator import aggregate_and_rank_candidates_with_status
from app.services.approval_service import approval_service
from app.db.repository import repository


def test_v32_pro_scenario_candidates_loaded(client: TestClient):
    """Test that all 4 test scenario candidates are discoverable in mock mode with complete v3.2 metadata."""
    # 1. Frankenstein (Public Domain)
    res_pd = client.post("/api/search", json={"title": "Frankenstein", "use_mock_data": True})
    assert res_pd.status_code == 200
    cands_pd = res_pd.json()["candidates"]
    assert any(c["candidate_id"] == "cand_gut_84" for c in cands_pd)
    cand_pd = next(c for c in cands_pd if c["candidate_id"] == "cand_gut_84")
    assert cand_pd["reader_type"] == "HTML_READER"
    assert cand_pd["can_embed"] is True
    assert cand_pd["reader_url"] is not None

    # 2. Operating Systems: Three Easy Pieces (Open Access)
    res_oa = client.post("/api/search", json={"title": "Operating Systems", "use_mock_data": True})
    assert res_oa.status_code == 200
    cands_oa = res_oa.json()["candidates"]
    cand_oa = next(c for c in cands_oa if c["candidate_id"] == "cand_doab_ostep")
    assert cand_oa["licensing"]["status"] == "VERIFIED_FOR_PERMITTED_DOWNLOAD"
    assert cand_oa["reader_url"] is not None

    # 3. Open Data Structures (High Match / Open Book)
    res_ods = client.post("/api/search", json={"title": "Open Data Structures", "author": "Pat Morin", "use_mock_data": True})
    assert res_ods.status_code == 200
    cands_ods = res_ods.json()["candidates"]
    cand_ods = next(c for c in cands_ods if c["candidate_id"] == "cand_open_data_structures")
    assert cand_ods["confidence"]["total_score"] >= 75.0
    assert cand_ods["reader_type"] == "EMBEDDED_PDF"
    assert cand_ods["can_embed"] is True
    assert cand_ods["licensing"]["status"] == "VERIFIED_FOR_PERMITTED_DOWNLOAD"

    # 4. Introduction to Algorithms (Commercial / Restricted CDL)
    res_clrs = client.post("/api/search", json={"title": "Introduction to Algorithms", "use_mock_data": True})
    assert res_clrs.status_code == 200
    cands_clrs = res_clrs.json()["candidates"]
    cand_clrs = next(c for c in cands_clrs if c["candidate_id"] == "cand_ol_ia_algorithms")
    assert cand_clrs["licensing"]["status"] == "NOT_ELIGIBLE"
    assert cand_clrs["licensing"]["is_legally_downloadable"] is False


def test_commercial_restricted_license_status_blocks_approval(client: TestClient):
    """Test that COMMERCIAL_RESTRICTED candidates cannot be approved under any circumstances."""
    res_aima = client.post("/api/search", json={"title": "Artificial Intelligence", "use_mock_data": True})
    assert res_aima.status_code == 200
    cand_aima = next(c for c in res_aima.json()["candidates"] if c["candidate_id"] == "cand_gb_aima4e")
    assert cand_aima["licensing"]["status"] == "COMMERCIAL_RESTRICTED"

    # Attempt approval with affirmative user flag
    appr_res = client.post(f"/api/candidates/{cand_aima['candidate_id']}/approve", json={
        "user_affirmation": True,
        "user_note": "Attempting to acquire commercial book"
    })
    # Mandatory safeguard: MUST return 403 Forbidden
    assert appr_res.status_code == 403
    assert "Acquisition prohibited" in appr_res.json()["detail"]


@pytest.mark.asyncio
async def test_crossref_connector_handles_query():
    """Test that Crossref connector executes without exception and respects parameters."""
    query = BookSearchQuery(title="Open Data Structures", author="Pat Morin")
    # Live query or graceful exception handling
    results = await search_crossref(query, limit=2)
    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, BookCandidate)
        assert r.source_name == "Crossref Academic Registry"
        assert r.reader_url is not None


def test_audit_history_enrichment(client: TestClient):
    """Test that listing approvals enriches records with real status and evidence details."""
    # 1. Search eligible book
    search_res = client.post("/api/search", json={"title": "Frankenstein", "use_mock_data": True})
    cand = next(c for c in search_res.json()["candidates"] if c["candidate_id"] == "cand_gut_84")

    # 2. Approve
    appr_res = client.post(f"/api/candidates/{cand['candidate_id']}/approve", json={
        "user_affirmation": True,
        "user_note": "Approved for English Lit syllabus"
    })
    assert appr_res.status_code == 200
    appr_id = appr_res.json()["approval_id"]

    # 3. List approvals
    list_res = client.get("/api/approvals")
    assert list_res.status_code == 200
    records = list_res.json()
    assert any(r["approval_id"] == appr_id for r in records)
    rec = next(r for r in records if r["approval_id"] == appr_id)
    assert rec["snapshot_hash"] is not None
    assert len(rec["snapshot_hash"]) == 64
    assert isinstance(rec["evidence_details"], list)
