"""FastAPI routes over the core calculations (URS-API-001 to 006).

Each endpoint takes the existing pydantic input model and returns the core result model
unchanged. Invalid input is a 422 with the validation messages; a ValueError raised by a core
function (for example CV limits fail without bootstrap settings) is also a 422, never a 500.
A result that fails its own model inside an endpoint is a defect in the tool: a 500.
Educational and decision-support use only. Not validated for GxP use.

Run: uv run uvicorn cmc_stats.api:app --reload
"""

from datetime import datetime
from typing import Annotated

from fastapi import Body, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from cmc_stats import __version__
from cmc_stats.core.be import assess_bioequivalence
from cmc_stats.core.dissolution import compare_profiles
from cmc_stats.core.stability import estimate_shelf_life
from cmc_stats.models import (
    DISCLAIMER,
    BeInput,
    BeResult,
    BootstrapSettings,
    DissolutionInput,
    DissolutionResult,
    StabilityInput,
    StabilityResult,
)

app = FastAPI(title="CMC Stats Toolkit API", version=__version__, description=DISCLAIMER)


def get_timestamp() -> datetime | None:
    """Calculation time handed to the core; None lets the core stamp the current UTC time.

    A dependency so tests can fix the time and compare API and core results exactly.
    """
    return None


Timestamp = Annotated[datetime | None, Depends(get_timestamp)]


@app.exception_handler(ValueError)
async def value_error_as_422(request: Request, exc: ValueError) -> JSONResponse:
    """URS-API-006: a core ValueError is the caller's input problem: 422 with its message.

    A pydantic ValidationError (also a ValueError) cannot come from the request here, since
    FastAPI validates the body before the endpoint runs; inside an endpoint it means a result
    failed its own model, which is a defect in the tool. That is a 500, never blamed on input.
    """
    if isinstance(exc, ValidationError):
        return JSONResponse(
            status_code=500,
            content={"detail": "internal error: a result failed validation (defect in the tool)"},
        )
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict[str, str]:
    """URS-API-001: liveness, app version and disclaimer."""
    return {"status": "ok", "version": __version__, "disclaimer": DISCLAIMER}


@app.post("/dissolution", response_model=DissolutionResult)
def dissolution(
    data: Annotated[DissolutionInput, Body()],
    timestamp: Timestamp,
    bootstrap: Annotated[BootstrapSettings | None, Body()] = None,
) -> DissolutionResult:
    """URS-API-002: ``compare_profiles`` (FDA IR dissolution guidance, 1997; bootstrap per
    Shah et al., Pharm Res 1998, provisional). Body: ``{"data": ..., "bootstrap": ...}``."""
    return compare_profiles(data, bootstrap, timestamp=timestamp)


@app.post("/stability", response_model=StabilityResult)
def stability(data: StabilityInput, timestamp: Timestamp) -> StabilityResult:
    """URS-API-003: ``estimate_shelf_life`` (ICH Q1E, 2003). Body: a ``StabilityInput``."""
    return estimate_shelf_life(data, timestamp=timestamp)


@app.post("/be", response_model=BeResult)
def bioequivalence(data: BeInput, timestamp: Timestamp) -> BeResult:
    """URS-API-004: ``assess_bioequivalence`` (ICH M13A, 2024; FDA BE statistics guidance).
    Body: a ``BeInput``."""
    return assess_bioequivalence(data, timestamp=timestamp)
