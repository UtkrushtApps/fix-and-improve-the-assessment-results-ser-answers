"""MongoDB data access layer for assessment results."""
from typing import Optional

from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

from config import COLLECTION_NAME


class RepositoryError(Exception):
    """Raised when a database operation fails."""


class ResultRepository:
    def __init__(self, mongo_uri: str, db_name: str):
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client[db_name]
            self.collection = self.db[COLLECTION_NAME]
            self._ensure_indexes()
        except PyMongoError as exc:
            raise RepositoryError("Failed to initialize repository") from exc
        except Exception as exc:
            raise RepositoryError("Failed to initialize repository") from exc

    def _ensure_indexes(self):
        try:
            self.collection.create_index([("candidate_id", ASCENDING)])
            self.collection.create_index([
                ("skill_name", ASCENDING),
                ("status", ASCENDING),
            ])
        except PyMongoError as exc:
            raise RepositoryError("Failed to ensure indexes") from exc
        except Exception as exc:
            raise RepositoryError("Failed to ensure indexes") from exc

    def find_results(self, filters: dict) -> list:
        try:
            mongo_filters = filters or {}
            cursor = self.collection.find(mongo_filters, {"_id": 0})
            return list(cursor)
        except PyMongoError as exc:
            raise RepositoryError("Failed to fetch assessment results") from exc
        except Exception as exc:
            raise RepositoryError("Failed to fetch assessment results") from exc

    def upsert_result(self, document: dict) -> str:
        try:
            candidate_id = document["candidate_id"]
            skill_name = document["skill_name"]
            selector = {
                "candidate_id": candidate_id,
                "skill_name": skill_name,
            }
            result = self.collection.update_one(
                selector,
                {"$set": document},
                upsert=True,
            )
            if result.upserted_id is not None:
                return str(result.upserted_id)

            existing = self.collection.find_one(selector, {"_id": 1})
            if existing and existing.get("_id") is not None:
                return str(existing["_id"])

            raise RepositoryError("Failed to resolve upserted document id")
        except KeyError as exc:
            raise RepositoryError("Invalid assessment result document") from exc
        except PyMongoError as exc:
            raise RepositoryError("Failed to save assessment result") from exc
        except Exception as exc:
            if isinstance(exc, RepositoryError):
                raise
            raise RepositoryError("Failed to save assessment result") from exc

    def insert_result(self, document: dict) -> str:
        """Backward-compatible insert method; retained for compatibility only."""
        try:
            result = self.collection.insert_one(document)
            return str(result.inserted_id)
        except PyMongoError as exc:
            raise RepositoryError("Failed to insert assessment result") from exc
        except Exception as exc:
            raise RepositoryError("Failed to insert assessment result") from exc

    def find_one_by_candidate(self, candidate_id: str) -> Optional[dict]:
        try:
            return self.collection.find_one({"candidate_id": candidate_id}, {"_id": 0})
        except PyMongoError as exc:
            raise RepositoryError("Failed to fetch candidate result") from exc
        except Exception as exc:
            raise RepositoryError("Failed to fetch candidate result") from exc

    def update_candidate_result(self, candidate_id: str, payload: dict) -> Optional[dict]:
        try:
            if not payload:
                raise RepositoryError("Invalid update payload")

            safe_payload = {k: v for k, v in payload.items() if k != "_id"}
            updated = self.collection.find_one_and_update(
                {"candidate_id": candidate_id},
                {"$set": safe_payload},
                return_document=ReturnDocument.AFTER,
                projection={"_id": 0},
            )
            return updated
        except PyMongoError as exc:
            raise RepositoryError("Failed to update candidate result") from exc
        except Exception as exc:
            if isinstance(exc, RepositoryError):
                raise
            raise RepositoryError("Failed to update candidate result") from exc

    def aggregate_candidate_summary(self, candidate_id: str) -> Optional[dict]:
        try:
            pipeline = [
                {"$match": {"candidate_id": candidate_id}},
                {
                    "$group": {
                        "_id": "$candidate_id",
                        "total_attempts": {"$sum": 1},
                        "average_score": {"$avg": "$score"},
                        "highest_score": {"$max": "$score"},
                        "skills_attempted": {"$addToSet": "$skill_name"},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "candidate_id": "$_id",
                        "total_attempts": 1,
                        "average_score": {"$round": ["$average_score", 2]},
                        "highest_score": 1,
                        "skills_attempted": 1,
                    }
                },
            ]
            cursor = self.collection.aggregate(pipeline)
            return next(cursor, None)
        except PyMongoError as exc:
            raise RepositoryError("Failed to aggregate candidate summary") from exc
        except Exception as exc:
            raise RepositoryError("Failed to aggregate candidate summary") from exc

    def get_candidate_summary_pipeline(self, candidate_id: str) -> Optional[dict]:
        """Backward-compatible alias for older callers."""
        return self.aggregate_candidate_summary(candidate_id)
