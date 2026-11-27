import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import analysis, dashboard, health, outputs, repair, reports, upload, validation
from backend.app.core.config import get_settings
from backend.app.schemas.responses import ErrorEnvelope
from backend.app.models.interfaces import model_registry


@asynccontextmanager
async def lifespan(_: FastAPI):
    model_registry.load_once(get_settings())
    yield

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("autoclean.api")

app = FastAPI(title="AutoClean AI API", description="File inspection and profiling for the AutoClean AI prototype.", version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root_health():
    """Expose the API health status at the service's base URL."""
    return health.health()


@app.exception_handler(RequestValidationError)
async def request_validation_error(_: Request, exc: RequestValidationError):
    messages = [item.get("msg", "Invalid request") for item in exc.errors()]
    body = ErrorEnvelope(error={"code": "invalid_request", "message": "; ".join(messages)})
    return JSONResponse(status_code=422, content=body.model_dump())


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "request_failed", "message": str(exc.detail)}
    body = ErrorEnvelope(error=detail)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(), headers=exc.headers)


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception):
    logger.exception("Unhandled API error", exc_info=exc)
    body = ErrorEnvelope(error={"code": "internal_error", "message": "An unexpected server error occurred."})
    return JSONResponse(status_code=500, content=body.model_dump())


for route in (health.router, dashboard.router, upload.router, analysis.router, repair.router, validation.router, reports.router, outputs.router):
    app.include_router(route, prefix="/api")
