import json
from flask import Flask, request, jsonify
from pydantic import BaseModel, Field, EmailStr, ValidationError
from typing import Optional
from datetime import datetime
import hashlib

app = Flask(__name__)

# Pydantic model
class SurveySubmission(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(..., ge=13, le=120)
    consent: bool = True
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=1000)
    source: str = "other"
    user_agent: Optional[str] = None
    submission_id: Optional[str] = None

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "details": ve.errors()}), 422

    # Add submission_id if missing
    if not getattr(submission, "submission_id", None):
        submission.submission_id = hashlib.sha256(
            (submission.email + datetime.utcnow().strftime("%Y%m%d%H")).encode()
        ).hexdigest()
    # Hash email and age
    submission.email = hashlib.sha256(submission.email.encode()).hexdigest()
    submission.age = hashlib.sha256(str(submission.age).encode()).hexdigest()

    # Save to file
    record = submission.dict()
    record["received_at"] = datetime.utcnow().isoformat()
    record["ip"] = request.remote_addr
    record["user_agent"] = request.headers.get("User-Agent", None)

    with open("data/survey.ndjson", "a") as f:
        f.write(json.dumps(record) + "\n")

    # Return response
    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)