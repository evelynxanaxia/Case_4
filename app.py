import hashlib
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError, BaseModel, Field, EmailStr, ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line

app = Flask(__name__)
CORS(app, resources={r"/v1/*": {"origins": "*"}})


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })


@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    hashed_email = sha256_hex(submission.email)
    hashed_age = sha256_hex(str(submission.age))

    if submission.submission_id:
        submission_id = submission.submission_id
    else:
        current_hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        submission_id = sha256_hex(submission.email + current_hour)

    record = StoredSurveyRecord(
        email=hashed_email,
        age=hashed_age,
        answers=submission.answers,
        user_agent=submission.user_agent,
        submission_id=submission_id,
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )

    record_dict = record.dict()
    record_dict["received_at"] = record.received_at.isoformat()

    # Save to disk
    append_json_line(record_dict)

    return jsonify({"status": "ok", "submission_id": submission_id}), 201


if __name__ == "__main__":
    app.run(port=5000, debug=True)
