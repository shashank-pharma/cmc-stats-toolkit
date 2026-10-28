"""FastAPI layer tests with TestClient. Each test cites the requirement it proves."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from cmc_stats import __version__, api
from cmc_stats.core import be, dissolution, stability
from cmc_stats.models import (
    DISCLAIMER,
    BeInput,
    BootstrapSettings,
    DissolutionInput,
    SourceFile,
    StabilityInput,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
GOLDEN = Path(__file__).parent / "golden" / "data"
TIMES = [5.0, 10.0, 15.0, 20.0, 30.0, 45.0]
REF_MEAN = [20.0, 40.0, 60.0, 75.0, 88.0, 95.0]
TEST_MEAN = [18.0, 37.0, 56.0, 72.0, 86.0, 94.0]
HIGH_LATE_CV = [0.02, 0.02, 0.02, 0.02, 0.4, 0.4]


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Client with the timestamp fixed, so API and core results can be compared exactly."""
    api.app.dependency_overrides[api.get_timestamp] = lambda: FIXED_TIME
    with TestClient(api.app) as c:
        yield c
    api.app.dependency_overrides.clear()


def golden_inputs(case: str) -> dict[str, Any]:
    inputs: dict[str, Any] = json.loads((GOLDEN / f"{case}.json").read_text("utf-8"))["inputs"]
    return inputs


def units(means: list[float], spread: float | list[float] = 0.02) -> list[list[float]]:
    """Dummy unit data: 12 units spread symmetrically around each mean."""
    spreads = spread if isinstance(spread, list) else [spread] * len(means)
    factors = [2 * i / 11 - 1 for i in range(12)]
    return [[m * (1 + s * f) for m, s in zip(means, spreads, strict=True)] for f in factors]


def dissolution_body(ref_spread: float | list[float] = 0.02) -> dict[str, Any]:
    return {
        "reference": {
            "label": "Reference",
            "times_min": TIMES,
            "units": units(REF_MEAN, ref_spread),
        },
        "test": {"label": "Test", "times_min": TIMES, "units": units(TEST_MEAN)},
    }


# --- URS-API-001 --------------------------------------------------------------------------


def test_health_returns_version_and_disclaimer(client: TestClient) -> None:
    """URS-API-001: status ok, app version and disclaimer."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__, "disclaimer": DISCLAIMER}


# --- URS-API-002 to 004: results returned unchanged ---------------------------------------


def test_dissolution_mean_f2_matches_core(client: TestClient) -> None:
    """URS-API-002: without bootstrap settings the response equals compare_profiles."""
    body = dissolution_body()
    response = client.post("/dissolution", json={"data": body})
    assert response.status_code == 200
    expected = dissolution.compare_profiles(
        DissolutionInput.model_validate(body), timestamp=FIXED_TIME
    )
    assert response.json() == expected.model_dump(mode="json")
    assert response.json()["decision_basis"] == "mean_f2"


def test_dissolution_bootstrap_matches_core(client: TestClient) -> None:
    """URS-API-002: with bootstrap settings the seeded bootstrap result is returned unchanged."""
    body = dissolution_body(HIGH_LATE_CV)
    settings = {"seed": 20261028, "n_resamples": 1000}
    response = client.post("/dissolution", json={"data": body, "bootstrap": settings})
    assert response.status_code == 200
    expected = dissolution.compare_profiles(
        DissolutionInput.model_validate(body),
        BootstrapSettings.model_validate(settings),
        timestamp=FIXED_TIME,
    )
    assert response.json() == expected.model_dump(mode="json")
    assert response.json()["bootstrap"]["seed"] == 20261028


@pytest.mark.parametrize("case", ["GOLD-STAB-001", "GOLD-STAB-002", "GOLD-STAB-003"])
def test_stability_matches_core(client: TestClient, case: str) -> None:
    """URS-API-003: the response equals estimate_shelf_life for the golden inputs."""
    inputs = golden_inputs(case)
    response = client.post("/stability", json=inputs)
    assert response.status_code == 200
    expected = stability.estimate_shelf_life(
        StabilityInput.model_validate(inputs), timestamp=FIXED_TIME
    )
    assert response.json() == expected.model_dump(mode="json")


@pytest.mark.parametrize("case", ["GOLD-BE-001", "GOLD-BE-002", "GOLD-BE-003"])
def test_be_matches_core(client: TestClient, case: str) -> None:
    """URS-API-004: the response equals assess_bioequivalence for the golden inputs."""
    inputs = golden_inputs(case)
    response = client.post("/be", json=inputs)
    assert response.status_code == 200
    expected = be.assess_bioequivalence(BeInput.model_validate(inputs), timestamp=FIXED_TIME)
    assert response.json() == expected.model_dump(mode="json")


def test_api_results_have_no_source_files(client: TestClient) -> None:
    """URS-GEN-003: JSON requests carry no uploaded file, so source_files is empty."""
    response = client.post("/stability", json=golden_inputs("GOLD-STAB-001"))
    assert response.json()["metadata"]["source_files"] == []


def test_timestamp_defaults_to_now_without_override() -> None:
    """URS-GEN-002: without the test override the core stamps the current UTC time."""
    with TestClient(api.app) as c:
        before = datetime.now(UTC)
        response = c.post("/be", json=golden_inputs("GOLD-BE-003"))
    stamped = datetime.fromisoformat(response.json()["metadata"]["timestamp"])
    assert before <= stamped <= datetime.now(UTC)


# --- URS-API-005, 006: bad input never reaches a 500 --------------------------------------


def messages(response: Any) -> str:
    return json.dumps(response.json()["detail"])


def test_missing_field_returns_422(client: TestClient) -> None:
    """URS-API-005: a missing required field is a 422 naming the field."""
    inputs = golden_inputs("GOLD-STAB-001")
    del inputs["lower_limit"]
    response = client.post("/stability", json=inputs)
    assert response.status_code == 422
    assert "lower_limit" in messages(response)


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_non_finite_json_returns_422(client: TestClient, value: float) -> None:
    """URS-API-005: NaN or Infinity tokens in the JSON body are rejected."""
    inputs = golden_inputs("GOLD-STAB-001")
    inputs["lower_limit"] = value
    response = client.post(
        "/stability", content=json.dumps(inputs), headers={"content-type": "application/json"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("path", "case", "field", "value"),
    [
        ("/stability", "GOLD-STAB-001", "direction", "increase"),
        ("/be", "GOLD-BE-001", "design", "replicate"),
        ("/be", "GOLD-BE-001", "limits", "reference_scaled"),
    ],
)
def test_unsupported_options_return_422_with_model_message(
    client: TestClient, path: str, case: str, field: str, value: str
) -> None:
    """URS-API-005: the model's "not supported in v1" message reaches the client."""
    inputs = golden_inputs(case)
    inputs[field] = value
    response = client.post(path, json=inputs)
    assert response.status_code == 422
    assert "not supported in v1" in messages(response)


def test_core_value_error_returns_422_not_500(client: TestClient) -> None:
    """URS-API-006: CV limits fail with no bootstrap settings: 422 with the core message."""
    response = client.post("/dissolution", json={"data": dissolution_body(HIGH_LATE_CV)})
    assert response.status_code == 422
    assert "bootstrap f2 is required" in response.json()["detail"]


def test_internal_validation_error_is_500_not_blamed_on_input(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """URS-API-006: a result failing its own model inside an endpoint is a 500 defect."""

    def broken(*args: Any, **kwargs: Any) -> Any:
        return SourceFile.model_validate({})  # raises pydantic ValidationError

    monkeypatch.setattr(api, "estimate_shelf_life", broken)
    response = client.post("/stability", json=golden_inputs("GOLD-STAB-001"))
    assert response.status_code == 500
    assert "defect in the tool" in response.json()["detail"]
