from typing import Any, Literal

from pydantic import BaseModel, Field


class APIError(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: APIError


class ModelAvailability(BaseModel):
    status: Literal["not_configured", "loaded_preprocessing_unavailable", "unavailable"]
    artifact_available: bool
    model_loaded: bool
    preprocessing_available: bool
    expected_input_features: int | None = None
    class_ids: list[int] | None = None
    message: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    models: dict[str, ModelAvailability]
    upload_limit_bytes: int


class UploadResponse(BaseModel):
    file_id: str
    file_name: str
    data_type: Literal["tabular", "image", "image_dataset"]
    size_bytes: int
    content_type: str
    inspection: dict[str, Any]
    status: Literal["uploaded"] = "uploaded"


class AnalysisResponse(BaseModel):
    file_id: str
    data_type: Literal["tabular", "image", "image_dataset"]
    status: Literal["profiled", "model_not_available"]
    summary: dict[str, Any] = Field(default_factory=dict)
    model_status: str
    model_input_features: int | None = None
    message: str


class RepairResponse(BaseModel):
    file_id: str
    status: Literal["completed"]
    outputs: dict[str, str]
    repair_summary: dict[str, Any]
    validation: dict[str, Any]
    model_status: str
    message: str


class ValidationResponse(BaseModel):
    file_id: str
    status: Literal["passed", "failed", "not_available"]
    checks: list[dict[str, Any]] = Field(default_factory=list)
    message: str


class ReportArtifact(BaseModel):
    status: Literal["generated", "not_generated"]
    download_url: str | None = None
    message: str


class ReportResponse(BaseModel):
    file_id: str
    status: Literal["generated", "partial", "not_generated"]
    cleaned_csv: ReportArtifact
    repair_history_csv: ReportArtifact
    quality_report: ReportArtifact
    validation_report: ReportArtifact
    repaired_image: ReportArtifact
    message: str
