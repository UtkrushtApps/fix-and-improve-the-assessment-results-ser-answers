"""Flask application entry point for the Assessment Results Service."""
from flask import Flask, request, jsonify
from services.catalog_service import CatalogService, ServiceError
from services.repository import ResultRepository
from config import MONGO_URI, DB_NAME


GENERIC_ERROR_MESSAGE = "Internal server error"


def create_app():
    app = Flask(__name__)

    repository = ResultRepository(MONGO_URI, DB_NAME)
    service = CatalogService(repository)

    def error_response(message: str, status_code: int):
        return jsonify({"error": message}), status_code

    @app.route("/results", methods=["GET"])
    def list_results():
        skill_name = request.args.get("skill_name")
        status = request.args.get("status")
        try:
            results = service.list_results(skill_name=skill_name, status=status)
            return jsonify({"results": results}), 200
        except ServiceError as exc:
            return error_response(exc.message, exc.status_code)
        except Exception:
            return error_response(GENERIC_ERROR_MESSAGE, 500)

    @app.route("/results", methods=["POST"])
    def submit_result():
        payload = request.get_json(force=True, silent=True)
        if not payload:
            return error_response("Invalid JSON payload", 400)

        required = {"candidate_id", "skill_name", "score", "max_score"}
        missing = required - payload.keys()
        if missing:
            return error_response(f"Missing fields: {sorted(missing)}", 400)

        try:
            result = service.submit_result(payload)
            return jsonify({"upserted_id": result}), 200
        except ServiceError as exc:
            return error_response(exc.message, exc.status_code)
        except Exception:
            return error_response(GENERIC_ERROR_MESSAGE, 500)

    @app.route("/results/<candidate_id>", methods=["PATCH"])
    def update_result(candidate_id):
        payload = request.get_json(force=True, silent=True)
        if not payload:
            return error_response("Invalid JSON payload", 400)

        try:
            updated = service.update_result(candidate_id, payload)
            if updated is None:
                return error_response("Candidate not found", 404)
            return jsonify({"updated": updated}), 200
        except ServiceError as exc:
            return error_response(exc.message, exc.status_code)
        except Exception:
            return error_response(GENERIC_ERROR_MESSAGE, 500)

    @app.route("/results/<candidate_id>/summary", methods=["GET"])
    def get_summary(candidate_id):
        try:
            summary = service.get_candidate_summary(candidate_id)
            if summary is None:
                return error_response("Candidate not found", 404)
            return jsonify(summary), 200
        except ServiceError as exc:
            return error_response(exc.message, exc.status_code)
        except Exception:
            return error_response(GENERIC_ERROR_MESSAGE, 500)

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, port=5050)
