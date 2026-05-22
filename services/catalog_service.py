"""Business logic layer for assessment result operations."""
import datetime
from typing import Optional

from models import AssessmentResult
from services.repository import RepositoryError


class ServiceError(Exception):
    """Raised when the service layer encounters a handled problem."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CatalogService:
    def __init__(self, repository):
        self.repository = repository

    def list_results(self, skill_name: Optional[str] = None, status: Optional[str] = None):
        filters = {}
        if skill_name:
            filters["skill_name"] = skill_name
        if status:
            filters["status"] = status

        try:
            return self.repository.find_results(filters)
        except RepositoryError as exc:
            raise ServiceError("Unable to retrieve results", 500) from exc
        except Exception as exc:
            raise ServiceError("Unable to retrieve results", 500) from exc

    def submit_result(self, payload: dict) -> str:
        try:
            required = {"candidate_id", "skill_name", "score", "max_score"}
            missing = required - payload.keys()
            if missing:
                raise ServiceError(f"Missing fields: {sorted(missing)}", 400)

            result = AssessmentResult(
                candidate_id=str(payload["candidate_id"]),
                skill_name=str(payload["skill_name"]),
                score=int(payload["score"]),
                max_score=int(payload["max_score"]),
                status=str(payload.get("status", "completed")),
                submitted_at=datetime.datetime.utcnow(),
            )
            upserted_id = self.repository.upsert_result(result.to_dict())
            return str(upserted_id)
        except ServiceError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ServiceError("Invalid result payload", 400) from exc
        except RepositoryError as exc:
            raise ServiceError("Unable to submit result", 500) from exc
        except Exception as exc:
            raise ServiceError("Unable to submit result", 500) from exc

    def update_result(self, candidate_id: str, payload: dict) -> Optional[dict]:
        try:
            existing = self.repository.find_one_by_candidate(candidate_id)
            if existing is None:
                return None

            update_payload = dict(payload)
            if "score" in update_payload:
                update_payload["score"] = int(update_payload["score"])
            if "max_score" in update_payload:
                update_payload["max_score"] = int(update_payload["max_score"])

            if not update_payload:
                raise ServiceError("Invalid update payload", 400)

            updated_doc = self.repository.update_candidate_result(candidate_id, update_payload)
            return updated_doc
        except ServiceError:
            raise
        except (TypeError, ValueError) as exc:
            raise ServiceError("Invalid update payload", 400) from exc
        except RepositoryError as exc:
            raise ServiceError("Unable to update result", 500) from exc
        except Exception as exc:
            raise ServiceError("Unable to update result", 500) from exc

    def get_candidate_summary(self, candidate_id: str) -> Optional[dict]:
        try:
            return self.repository.aggregate_candidate_summary(candidate_id)
        except RepositoryError as exc:
            raise ServiceError("Unable to retrieve candidate summary", 500) from exc
        except Exception as exc:
            raise ServiceError("Unable to retrieve candidate summary", 500) from exc
