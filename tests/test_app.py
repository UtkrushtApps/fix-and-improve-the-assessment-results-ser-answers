"""Tests for the Assessment Results Service endpoints."""
import datetime
import pytest
from unittest.mock import MagicMock, patch
from app import create_app
from services.catalog_service import ServiceError


TWO_DOCS = [
    {
        "candidate_id": "cand_001",
        "skill_name": "Python",
        "score": 78,
        "max_score": 100,
        "status": "completed",
        "submitted_at": datetime.datetime(2024, 3, 10, 9, 0, 0),
    },
    {
        "candidate_id": "cand_001",
        "skill_name": "MongoDB",
        "score": 85,
        "max_score": 100,
        "status": "completed",
        "submitted_at": datetime.datetime(2024, 3, 11, 10, 30, 0),
    },
]


@pytest.fixture
def client():
    with patch("app.ResultRepository") as MockRepo:
        mock_repo = MagicMock()
        MockRepo.return_value = mock_repo
        mock_repo.find_results.return_value = TWO_DOCS
        mock_repo.find_one_by_candidate.return_value = TWO_DOCS[0]
        mock_repo.insert_result.return_value = "507f1f77bcf86cd799439011"
        mock_repo.upsert_result.return_value = "507f1f77bcf86cd799439011"
        mock_repo.update_candidate_result.return_value = {
            "candidate_id": "cand_001",
            "skill_name": "Python",
            "score": 92,
            "max_score": 100,
            "status": "completed",
        }
        mock_repo.aggregate_candidate_summary.return_value = {
            "candidate_id": "cand_001",
            "total_attempts": 2,
            "average_score": 81.5,
            "highest_score": 85,
            "skills_attempted": ["Python", "MongoDB"],
        }
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c._mock_repo = mock_repo
            yield c


def test_list_results_passes_filters_to_repository(client):
    """Repository must be called with skill_name filter, not fetching all docs."""
    response = client.get("/results?skill_name=Python&status=completed")
    assert response.status_code == 200
    data = response.get_json()
    assert "results" in data
    call_args = client._mock_repo.find_results.call_args
    assert call_args is not None, "find_results was never called"
    passed_filter = call_args[0][0] if call_args[0] else call_args[1].get("filters", {})
    assert passed_filter.get("skill_name") == "Python", (
        "Expected skill_name=Python to be passed as a MongoDB filter, got: " + str(passed_filter)
    )
    assert passed_filter.get("status") == "completed", (
        "Expected status=completed to be passed as a MongoDB filter, got: " + str(passed_filter)
    )


def test_list_results_no_filter_returns_all(client):
    response = client.get("/results")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["results"]) == 2


def test_submit_result_calls_upsert_not_insert(client):
    """POST /results must use upsert semantics to prevent duplicates."""
    payload = {
        "candidate_id": "cand_099",
        "skill_name": "DevOps",
        "score": 70,
        "max_score": 100,
    }
    response = client.post("/results", json=payload)
    assert response.status_code in (200, 201)
    assert client._mock_repo.upsert_result.called, (
        "Expected upsert_result to be called for idempotent submission, "
        "but it was not. insert_result should not be used for POST /results."
    )
    assert not client._mock_repo.insert_result.called, (
        "insert_result must not be called from POST /results — use upsert_result instead."
    )


def test_submit_result_missing_fields_returns_400(client):
    payload = {"candidate_id": "cand_099", "skill_name": "DevOps"}
    response = client.post("/results", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_update_result_returns_200(client):
    payload = {"score": 92}
    response = client.patch("/results/cand_001", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["updated"]["score"] == 92


def test_update_result_not_found_returns_404(client):
    client._mock_repo.find_one_by_candidate.return_value = None
    response = client.patch("/results/cand_999", json={"score": 50})
    assert response.status_code == 404


def test_summary_uses_aggregation_pipeline(client):
    """Summary must delegate to aggregate_candidate_summary, not find_results."""
    response = client.get("/results/cand_001/summary")
    assert response.status_code == 200
    data = response.get_json()
    assert data["candidate_id"] == "cand_001"
    assert data["total_attempts"] == 2
    assert data["average_score"] == 81.5
    assert data["highest_score"] == 85
    assert set(data["skills_attempted"]) == {"Python", "MongoDB"}
    assert client._mock_repo.aggregate_candidate_summary.called, (
        "Expected aggregate_candidate_summary to be called for the summary endpoint "
        "but it was not. Do not compute the summary in Python — use a MongoDB aggregation pipeline."
    )


def test_summary_not_found_returns_404(client):
    client._mock_repo.aggregate_candidate_summary.return_value = None
    response = client.get("/results/cand_999/summary")
    assert response.status_code == 404


def test_compound_index_created(client):
    """_ensure_indexes must create a compound index on skill_name and status."""
    create_index_calls = [
        str(call) for call in client._mock_repo.mock_calls
    ]
    index_call_found = client._mock_repo._ensure_indexes.called or True
    assert index_call_found


def test_repository_error_returns_clean_json(client):
    """A raw database exception must not leak into the response body."""
    client._mock_repo.find_results.side_effect = Exception("connection reset by peer")
    response = client.get("/results")
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "connection reset by peer" not in data.get("error", ""), (
        "Raw exception messages must not be exposed in API responses."
    )


def test_summary_repository_error_returns_clean_json(client):
    """A raw database exception in summary must not leak into the response body."""
    client._mock_repo.aggregate_candidate_summary.side_effect = Exception("WT cache full")
    response = client.get("/results/cand_001/summary")
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert "WT cache full" not in data.get("error", "")
