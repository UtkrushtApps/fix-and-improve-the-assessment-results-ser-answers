# Solution Steps

1. Update the service layer so `list_results()` builds a MongoDB filter dict and passes it directly to the repository instead of fetching everything and filtering in Python.

2. Change the repository `find_results()` implementation to call `collection.find(filters, {"_id": 0})`, using the provided filter dict as the MongoDB query.

3. Replace the old insert-based POST flow with an idempotent upsert flow keyed on `candidate_id` and `skill_name`. Add a repository method such as `upsert_result()` that uses `update_one(..., upsert=True)` and returns the inserted or matched document id.

4. Update `CatalogService.submit_result()` to call `upsert_result()` instead of `insert_result()`, while still creating the domain model and defaulting `status` and `submitted_at`.

5. Rewrite candidate summary generation so the service calls a repository aggregation method, not `find_results()`. The repository method should run a MongoDB pipeline with `$match` on `candidate_id`, `$group` for totals and aggregates, and `$project` to shape the final response.

6. Add repository index creation for the existing `candidate_id` index and a new compound index on `(skill_name, status)` using `create_index([("skill_name", ASCENDING), ("status", ASCENDING)])`.

7. Introduce structured repository exceptions, for example `RepositoryError`, and wrap `pymongo` operations in `try/except` blocks so raw database exceptions are converted into controlled internal errors.

8. Introduce structured service exceptions with HTTP status codes, for example `ServiceError(message, status_code)`, and translate repository failures into clean service-level errors without exposing raw exception text.

9. Keep request validation in the Flask routes for invalid JSON and missing POST fields, and add service-side validation for bad numeric conversions or invalid update payloads so malformed data returns `400` instead of an unhandled `500`.

10. Update the Flask routes to return `{"error": ...}` with the `ServiceError.status_code` for handled failures, and include a generic fallback `except Exception` that returns a safe `500` JSON body.

11. Preserve the existing route paths and response envelope shapes: `{"results": ...}` for list, `{"upserted_id": ...}` for POST, `{"updated": ...}` for PATCH, and the summary object directly for the summary endpoint.

12. Run the test suite to confirm that filters are passed to MongoDB, summary uses aggregation, POST is idempotent via upsert, exceptions are sanitized, and all endpoints return the expected status codes and shapes.

