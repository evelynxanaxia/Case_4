import os

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

    # Prepare record
    record = submission.dict()
    record["received_at"] = datetime.utcnow().isoformat()
    record["ip"] = request.remote_addr
    record["user_agent"] = request.headers.get("User-Agent", None)

    # Ensure directory exists
    os.makedirs("data", exist_ok=True)

    # Save to file
    with open("data/survey.ndjson", "a") as f:
        f.write(json.dumps(record) + "\n")

    # Return response
    return jsonify({"status": "ok"}), 201
