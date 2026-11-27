import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOCLEAN_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("AUTOCLEAN_TABULAR_MODEL", str(tmp_path / "missing-tabular.joblib"))
    monkeypatch.setenv("AUTOCLEAN_IMAGE_MODEL", str(tmp_path / "missing-image.joblib"))
    with TestClient(app) as test_client:
        yield test_client


def upload_csv(client, body=b"a,b\n1,2\n"):
    return client.post("/api/upload", files={"file": ("sample.csv", body, "text/csv")})


def test_health_reports_missing_models(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["models"]["tabular"]["status"] == "not_configured"
    assert response.json()["models"]["image"]["artifact_available"] is False


def test_dashboard_reads_real_upload_repair_and_validation_artifacts(client):
    upload = upload_csv(client, b"feature,diagnosis\n1,M\n,B\n").json()
    file_id = upload["file_id"]
    assert client.post(f"/api/repair/{file_id}").status_code == 200

    response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["datasets_processed"] == 1
    assert payload["files_analyzed"] == 1
    assert payload["defects_detected"] == 1
    assert payload["repairs_completed"] == 1
    assert payload["records_repaired"] == 1
    assert payload["validation"]["passed"] == 1
    assert payload["jobs"][0]["file_id"] == file_id
    assert payload["jobs"][0]["records_repaired"] == 1
    assert payload["repair_history"][0]["column"] == "feature"


def test_image_dataset_csv_zip_analysis_recovery_repair_and_report(client):
    manifest = b"image_id,image_path,class_label\nlow,low.png,cat\nmissing,missing.png,dog\nbroken,broken.png,bird\nnoisy,noisy.png,dog\n"
    image_buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color=(50, 80, 120)).save(image_buffer, format="PNG")
    reference_buffer = io.BytesIO()
    Image.new("RGB", (80, 80), color=(140, 40, 10)).save(reference_buffer, format="JPEG")
    noise_buffer = io.BytesIO()
    import numpy as np
    noisy = np.random.default_rng(3).integers(0, 256, size=(128, 128, 3), dtype=np.uint8)
    Image.fromarray(noisy).save(noise_buffer, format="PNG")
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("low.png", image_buffer.getvalue())
        archive.writestr("missing.jpg", reference_buffer.getvalue())
        archive.writestr("broken.png", b"not an image")
        archive.writestr("noisy.png", noise_buffer.getvalue())

    response = client.post("/api/upload/image-dataset", files={
        "manifest": ("images.csv", manifest, "text/csv"),
        "images_zip": ("images.zip", archive_buffer.getvalue(), "application/zip"),
    })
    assert response.status_code == 201, response.text
    uploaded = response.json()
    assert uploaded["data_type"] == "image_dataset"
    assert uploaded["inspection"]["missing_file_count"] == 1

    analysis = client.get(f"/api/analysis/{uploaded['file_id']}").json()
    assert analysis["data_type"] == "image_dataset"
    assert analysis["summary"]["defect_counts"]["missing"] == 1
    assert analysis["summary"]["defect_counts"]["corrupted"] == 1
    assert analysis["summary"]["defect_counts"]["low_resolution"] == 1
    assert analysis["summary"]["defect_counts"]["noise"] == 1

    repaired = client.post(f"/api/repair/{uploaded['file_id']}")
    assert repaired.status_code == 200, repaired.text
    result = repaired.json()
    assert result["repair_summary"]["images_repaired"] == 3
    assert result["repair_summary"]["manual_review"] == 1
    assert result["validation"]["status"] == "passed"
    assert result["validation"]["manual_review"][0]["image_id"] == "broken"
    assert client.get(result["outputs"]["repaired_images_zip"]).status_code == 200
    assert client.get(result["outputs"]["repair_history_csv"]).status_code == 200

    report = client.get(f"/api/reports/{uploaded['file_id']}").json()
    assert report["quality_report"]["status"] == "generated"
    assert report["repaired_image"]["status"] == "generated"
    quality = client.get(report["quality_report"]["download_url"]).json()
    assert quality["image_count"] == 4
    assert quality["defect_counts"]["corrupted"] == 1
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["datasets_processed"] == 1
    assert dashboard["defects_detected"] == analysis["summary"]["defect_total"]
    assert dashboard["records_repaired"] == 3


def test_image_dataset_zip_rejects_path_traversal(client):
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("../escape.png", b"unsafe")
    response = client.post("/api/upload/image-dataset", files={
        "manifest": ("images.csv", b"image_id,image_path,class_label\na,escape.png,cat\n", "text/csv"),
        "images_zip": ("images.zip", archive_buffer.getvalue(), "application/zip"),
    })
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsafe_archive_path"


def test_valid_csv_upload_and_profile(client):
    response = upload_csv(client, b"feature,diagnosis\n1,M\n, B\n1,M\n")
    assert response.status_code == 201, response.text
    uploaded = response.json()
    assert uploaded["data_type"] == "tabular"
    assert uploaded["inspection"]["row_count"] == 3
    assert uploaded["inspection"]["column_count"] == 2
    assert uploaded["inspection"]["missing_by_column"]["feature"] == 1
    assert uploaded["inspection"]["duplicate_row_count"] == 1
    assert uploaded["inspection"]["protected_columns"] == ["diagnosis"]
    assert uploaded["file_name"] == "sample.csv"

    analysis = client.get(f"/api/analysis/{uploaded['file_id']}")
    assert analysis.status_code == 200
    assert analysis.json()["status"] == "profiled"
    assert analysis.json()["model_status"] == "not_configured"
    assert analysis.json()["summary"]["numeric_summary"]["feature"]["count"] == 2.0


def test_valid_image_is_content_inspected_but_not_predicted(client):
    image_bytes = io.BytesIO()
    Image.new("RGB", (8, 5), color="navy").save(image_bytes, format="PNG")
    upload = client.post("/api/upload", files={"file": ("photo.png", image_bytes.getvalue(), "image/png")})
    assert upload.status_code == 201, upload.text
    payload = upload.json()
    assert payload["inspection"]["format"] == "PNG"
    assert payload["inspection"]["width"] == 8
    analysis = client.get(f"/api/analysis/{payload['file_id']}")
    assert analysis.json()["status"] == "model_not_available"
    assert analysis.json()["summary"] == {}


def test_invalid_file_type(client):
    response = client.post("/api/upload", files={"file": ("payload.exe", b"not executable", "application/octet-stream")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_malformed_csv_is_rejected_and_not_saved(client, tmp_path):
    response = upload_csv(client, b"a,b\n1,2\n3,4,5\n")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "malformed_csv"
    assert list((tmp_path / "storage" / "uploads").iterdir()) == []


def test_invalid_image_content_and_mismatched_extension(client):
    invalid = client.post("/api/upload", files={"file": ("broken.png", b"not an image", "image/png")})
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_image_content"

    image_bytes = io.BytesIO()
    Image.new("RGB", (3, 3)).save(image_bytes, format="JPEG")
    mismatch = client.post("/api/upload", files={"file": ("misnamed.png", image_bytes.getvalue(), "image/png")})
    assert mismatch.status_code == 400
    assert mismatch.json()["error"]["code"] == "image_format_mismatch"


def test_missing_file_id_and_path_traversal_return_404(client):
    missing = client.get("/api/analysis/00000000000000000000000000000000")
    traversal = client.get("/api/analysis/%2e%2e%2fmain.py")
    assert missing.status_code == 404
    assert traversal.status_code == 404
    assert missing.json()["error"]["code"] == "file_not_found"


def test_file_size_limit(client, monkeypatch):
    monkeypatch.setenv("AUTOCLEAN_MAX_UPLOAD_BYTES", "4")
    response = upload_csv(client, b"a,b\n1,2\n")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_csv_repair_generates_cleaned_history_and_arva_validation(client):
    source = b"feature,category,diagnosis\n1,red,M\n,blue,\n3,,B\n"
    uploaded = upload_csv(client, source).json()
    file_id = uploaded["file_id"]

    repaired = client.post(f"/api/repair/{file_id}")
    assert repaired.status_code == 200, repaired.text
    payload = repaired.json()
    assert payload["status"] == "completed"
    assert payload["repair_summary"]["cells_repaired"] == 2
    assert payload["repair_summary"]["diagnosis_preserved"] is True
    assert payload["validation"]["status"] == "passed"
    assert all(check["passed"] for check in payload["validation"]["checks"])

    cleaned = client.get(payload["outputs"]["cleaned_csv"])
    assert cleaned.status_code == 200
    assert cleaned.text == "feature,category,diagnosis\n1.0,red,M\n2.0,blue,\n3.0,blue,B\n"
    history = client.get(payload["outputs"]["repair_history_csv"])
    assert history.status_code == 200
    assert "median_imputation" in history.text
    assert "most_frequent_imputation" in history.text

    validation = client.get(f"/api/validation/{file_id}")
    assert validation.status_code == 200
    assert validation.json()["status"] == "passed"
    assert validation.json()["checks"] == payload["validation"]["checks"]

    reports = client.get(f"/api/reports/{file_id}")
    assert reports.status_code == 200, reports.text
    report_payload = reports.json()
    assert report_payload["status"] == "generated"
    assert report_payload["cleaned_csv"]["status"] == "generated"
    assert report_payload["repair_history_csv"]["status"] == "generated"
    assert report_payload["quality_report"]["status"] == "generated"
    assert report_payload["validation_report"]["status"] == "generated"

    quality_download = client.get(report_payload["quality_report"]["download_url"])
    assert quality_download.status_code == 200
    assert quality_download.headers["content-type"].startswith("application/json")
    assert "attachment" in quality_download.headers["content-disposition"]
    quality_json = quality_download.json()
    assert quality_json["file_id"] == file_id
    assert quality_json["file_name"] == "sample.csv"
    assert quality_json["data_type"] == "tabular"
    assert quality_json["row_count"] == 3
    assert quality_json["column_count"] == 3
    assert quality_json["columns"][0]["name"] == "feature"
    assert "analysis_timestamp" in quality_json

    validation_download = client.get(report_payload["validation_report"]["download_url"])
    assert validation_download.status_code == 200
    validation_json = validation_download.json()
    assert validation_json["file_id"] == file_id
    assert validation_json["validation_status"] == "passed"
    assert validation_json["checks"] == payload["validation"]["checks"]
    assert "generated_at" in validation_json


def test_repair_missing_file_id_returns_404(client):
    response = client.post("/api/repair/00000000000000000000000000000000")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "file_not_found"


def test_model_dependent_repair_returns_503_when_adda_unavailable(client):
    uploaded = upload_csv(client, b"feature,diagnosis\ntext, M\n1, B\n").json()
    response = client.post(f"/api/repair/{uploaded['file_id']}")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "adda_unavailable"
    assert "preprocessing" in response.json()["error"]["message"]


def test_repair_rejects_data_when_no_supported_change_occurs(client):
    uploaded = upload_csv(client, b"feature,diagnosis\n1,M\n2,B\n").json()
    response = client.post(f"/api/repair/{uploaded['file_id']}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "no_supported_repairs"


def test_repair_returns_400_for_image_upload(client):
    image_bytes = io.BytesIO()
    Image.new("RGB", (3, 3)).save(image_bytes, format="PNG")
    uploaded = client.post("/api/upload", files={"file": ("photo.png", image_bytes.getvalue(), "image/png")}).json()
    response = client.post(f"/api/repair/{uploaded['file_id']}")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_repair_input"


def test_repair_returns_422_for_invalid_stored_csv(client, tmp_path):
    uploaded = upload_csv(client).json()
    source_path = tmp_path / "storage" / "uploads" / f"{uploaded['file_id']}.csv"
    source_path.write_bytes(b"feature,diagnosis\n1,M\n2,B,extra\n")
    response = client.post(f"/api/repair/{uploaded['file_id']}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_csv"


def test_quality_report_is_generated_before_repair_validation_is_not(client):
    uploaded = upload_csv(client).json()
    file_id = uploaded["file_id"]
    repair = client.post(f"/api/repair/{file_id}")
    validation = client.get(f"/api/validation/{file_id}")
    report = client.get(f"/api/reports/{file_id}")
    assert repair.status_code == 422
    assert validation.json()["status"] == "not_available"
    payload = report.json()
    assert payload["status"] == "partial"
    assert payload["quality_report"]["status"] == "generated"
    assert payload["quality_report"]["download_url"]
    assert payload["validation_report"]["status"] == "not_generated"
    assert payload["validation_report"]["download_url"] is None
    assert payload["cleaned_csv"]["status"] == "not_generated"


def test_report_missing_file_id_returns_404(client):
    response = client.get("/api/reports/00000000000000000000000000000000")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "file_not_found"


def test_output_route_rejects_unknown_and_traversal_artifacts(client):
    uploaded = upload_csv(client).json()
    file_id = uploaded["file_id"]
    unknown = client.get(f"/api/outputs/{file_id}/unknown")
    traversal = client.get(f"/api/outputs/{file_id}/%2e%2e%2fmain.py")
    assert unknown.status_code == 404
    assert traversal.status_code == 404


def test_image_report_is_inspection_only_and_image_repair_is_unavailable(client):
    image_bytes = io.BytesIO()
    Image.new("RGB", (4, 3), color="navy").save(image_bytes, format="PNG")
    uploaded = client.post("/api/upload", files={"file": ("cover.png", image_bytes.getvalue(), "image/png")}).json()
    report = client.get(f"/api/reports/{uploaded['file_id']}")
    assert report.status_code == 200
    payload = report.json()
    assert payload["quality_report"]["status"] == "generated"
    assert payload["repaired_image"]["status"] == "not_generated"
    quality = client.get(payload["quality_report"]["download_url"]).json()
    assert quality["data_type"] == "image"
    assert quality["row_count"] is None
    assert quality["image_inspection"]["width"] == 4


def test_request_validation_uses_consistent_error_shape(client):
    response = client.post("/api/upload")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
