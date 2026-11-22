import json
from pathlib import Path

import pytest
from app.config import Settings, settings
from app.mes import MesError, MesNotFoundError, MesService
from app.store import ScenarioStore


def _service(tmp_path: Path) -> tuple[ScenarioStore, MesService]:
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(settings.seed_file.read_text(encoding="utf-8"), encoding="utf-8")
    local_store = ScenarioStore(tmp_path / "state.json", seed_file)
    return local_store, MesService(local_store, Settings())


def test_store_domain_reset_preserves_unrelated_progress(tmp_path: Path) -> None:
    local_store, service = _service(tmp_path)
    local_store.set_stage("production")
    service.start("JC-2027-0130", "DEMO-EMP-002")

    reset = local_store.reset_domain("mes")

    production = next(step for step in reset["process"] if step["id"] == "production")
    assert production["status"] == "active"
    assert service.job("JC-2027-0130")["status"] == "ready"
    with pytest.raises(KeyError):
        local_store.reset_domain("unknown")


def test_failed_store_mutation_is_not_persisted(tmp_path: Path) -> None:
    local_store, _ = _service(tmp_path)
    before = local_store.get()

    def fail(state: dict[str, object]) -> None:
        state["order"] = {"id": "BROKEN"}
        raise RuntimeError("reject")

    with pytest.raises(RuntimeError, match="reject"):
        local_store.mutate(fail)
    assert local_store.get() == before


def test_mes_rejects_unknown_operator_job_and_wrong_assignment(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    with pytest.raises(MesNotFoundError, match="Bedienperson"):
        service.dashboard("UNKNOWN")
    with pytest.raises(MesNotFoundError, match="Arbeitsgang"):
        service.job("UNKNOWN")
    with pytest.raises(MesError, match="anderen Person"):
        service.start("JC-2027-0130", "DEMO-EMP-001")


@pytest.mark.parametrize("minutes", [0, 721])
def test_mes_rejects_invalid_manual_time(tmp_path: Path, minutes: int) -> None:
    _, service = _service(tmp_path)
    with pytest.raises(MesError, match="zwischen 1 und 720"):
        service.book_time(
            "JC-2027-0130", "DEMO-EMP-002", minutes, "Fertigungszeit"
        )


def test_mes_requires_exactly_one_serial_number_per_good_unit(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    service.start("JC-2027-0130", "DEMO-EMP-002")

    with pytest.raises(MesError, match="genau eine eindeutige Seriennummer"):
        service.complete(
            "JC-2027-0130",
            "DEMO-EMP-002",
            5,
            0,
            [f"SN-{number}" for number in range(6)],
            ["esd", "revision", "j4", "visual"],
        )

    assert service.job("JC-2027-0130")["status"] == "in_progress"


def test_seed_json_remains_valid_after_unit_mutations(tmp_path: Path) -> None:
    local_store, service = _service(tmp_path)
    service.book_time("JC-2027-0130", "DEMO-EMP-002", 15, "Rüstzeit")
    persisted = json.loads(local_store.data_file.read_text(encoding="utf-8"))
    job = next(
        item for item in persisted["mes"]["jobs"] if item["id"] == "JC-2027-0130"
    )
    assert job["time_logs"][-1]["minutes"] == 15
