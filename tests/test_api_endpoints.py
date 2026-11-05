import pytest
from fastapi.testclient import TestClient


def test_health_endpoints(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    api_health = client.get("/api/health")
    assert api_health.status_code == 200


def test_system_status_endpoint(client: TestClient):
    res = client.get("/api/system-status")
    assert res.status_code == 200
    data = res.json()
    assert data["database_connected"] is True
    assert "allowed_domains" in data
    assert "total_approvals_recorded" in data


def test_search_endpoint_discovers_without_download(client: TestClient):
    # Empty query fails
    res_empty = client.post("/api/search", json={})
    assert res_empty.status_code == 400
    assert "At least one search field" in res_empty.json()["detail"]

    # Search with title and author in mock mode
    res = client.post("/api/search", json={
        "title": "Frankenstein",
        "author": "Mary Shelley",
        "use_mock_data": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["total_candidates"] >= 1
    assert "provider_statuses" in data
    assert len(data["provider_statuses"]) >= 1
    cand = data["candidates"][0]
    assert cand["title"] == "Frankenstein; Or, The Modern Prometheus"
    assert cand["confidence"]["total_score"] >= 75.0
    assert cand["licensing"]["status"] == "VERIFIED_FOR_PERMITTED_DOWNLOAD"


def test_get_candidate_details(client: TestClient):
    res = client.get("/api/candidates/cand_gut_84")
    assert res.status_code == 200
    data = res.json()
    assert data["candidate_id"] == "cand_gut_84"
    assert data["source_name"] == "Project Gutenberg"


def test_full_approval_and_download_pipeline(client: TestClient):
    # 1. Search
    search_res = client.post("/api/search", json={"title": "Operating Systems", "use_mock_data": True})
    assert search_res.status_code == 200
    cand = next(c for c in search_res.json()["candidates"] if c["candidate_id"] == "cand_doab_ostep")

    # 2. Approve with affirmation
    appr_res = client.post(f"/api/candidates/{cand['candidate_id']}/approve", json={
        "user_affirmation": True,
        "user_note": "Approved for OS Course"
    })
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["candidate_id"] == cand["candidate_id"]
    approval_id = appr_data["approval_id"]

    # 3. Trigger download simulation
    dl_res = client.post(f"/api/candidates/{cand['candidate_id']}/download", json={
        "approval_id": approval_id,
        "simulate_only": True
    })
    assert dl_res.status_code == 200
    job_data = dl_res.json()
    assert job_data["status"] == "COMPLETED"
    assert job_data["progress"] == 100
    assert job_data["approval_id"] == approval_id
    job_id = job_data["job_id"]

    # 4. Check job status endpoint
    job_status_res = client.get(f"/api/jobs/{job_id}")
    assert job_status_res.status_code == 200
    assert job_status_res.json()["job_id"] == job_id


def test_approval_blocks_commercial_candidate(client: TestClient):
    comm_cand_id = "cand_gb_aima4e"
    res = client.post(f"/api/candidates/{comm_cand_id}/approve", json={
        "user_affirmation": True
    })
    assert res.status_code == 403
    assert "Acquisition prohibited" in res.json()["detail"]


def test_download_rejected_without_prior_approval(client: TestClient):
    # Candidate cand_gut_1342 has not been approved in this session
    res = client.post("/api/candidates/cand_gut_1342/download", json={
        "approval_id": "appr_nonexistent",
        "simulate_only": True
    })
    assert res.status_code == 403
    assert "No approval record found" in res.json()["detail"]
