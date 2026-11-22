"""Agentenregister, Ablauf und Ergebnisvertrag (REQ-AGT-001, REQ-AGT-002, REQ-AGT-004)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from flowagents import registry as registry_module
from flowagents.contract import ContractError, extract_json, validate

from .conftest import AGENTS_DIR


def copy_agents(tmp_path: Path) -> Path:
    target = tmp_path / "agents"
    shutil.copytree(AGENTS_DIR, target)
    return target


def edit(path: Path, change) -> None:  # noqa: ANN001
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_registry_has_all_roles_ceo_and_gates(registry) -> None:  # noqa: ANN001
    roles = {agent.role for agent in registry.agents.values()}
    assert {"anforderungen", "anforderungspruefung", "architektur", "sicherheit", "planung", "entwicklung",
            "akzeptanztest", "codepruefung", "dokumentation", "nachweise", "schwachstellen",
            "geschaeftsfuehrung"} == roles
    assert [step.id for step in registry.steps if step.kind == "gate"] == ["G1", "G2", "G3", "G4", "G5"]
    ceo = registry.agent("geschaeftsfuehrung")
    assert ceo.autonomy == "A0" and "rm.create_draft" not in ceo.tools
    assert all(not registry_module.FORBIDDEN_TOOL.search(tool) for agent in registry.agents.values()
               for tool in agent.tools)


def test_reviewers_are_independent_from_creators(registry) -> None:  # noqa: ANN001
    for step in registry.steps:
        if step.kind == "review" and step.subject != "auftrag":
            creator = registry.producer(step.subject)
            assert registry_module.independent(registry.agent(creator.role), registry.agent(step.role))


def test_same_family_reviewer_is_rejected(tmp_path: Path) -> None:
    agents = copy_agents(tmp_path)
    edit(agents / "registry.yaml", lambda d: d["model_profiles"]["pruefer"].update(family="qwen"))
    with pytest.raises(registry_module.RegistryError, match="unabhängig|Modellfamilie"):
        registry_module.load(agents)


def test_acceptance_tester_may_not_read_implementation(tmp_path: Path) -> None:
    agents = copy_agents(tmp_path)

    def change(data: dict) -> None:
        tester = next(a for a in data["agents"] if a["role"] == "akzeptanztest")
        tester["reads"].append("implementierung")

    edit(agents / "registry.yaml", change)
    with pytest.raises(registry_module.RegistryError, match="Implementierung"):
        registry_module.load(agents)


@pytest.mark.parametrize("tool", ["rm.approve", "git.merge", "deploy.release"])
def test_approval_merge_and_deploy_tools_are_forbidden(tmp_path: Path, tool: str) -> None:
    agents = copy_agents(tmp_path)
    edit(agents / "registry.yaml", lambda d: d["tools"].update({tool: "verboten"}))
    with pytest.raises(registry_module.RegistryError, match="keiner Agentenrolle"):
        registry_module.load(agents)


def test_agent_level_a4_and_g4_automation_are_rejected(tmp_path: Path) -> None:
    agents = copy_agents(tmp_path)
    edit(agents / "registry.yaml", lambda d: d["agents"][0].update(autonomy="A4"))
    with pytest.raises(registry_module.RegistryError, match="A4"):
        registry_module.load(agents)
    agents = copy_agents(tmp_path / "second")
    edit(agents / "workflow.yaml", lambda d: d["classes"]["standard"].update(human_gates=["G5"]))
    with pytest.raises(registry_module.RegistryError, match="menschlich"):
        registry_module.load(agents)


def test_expired_approval_makes_agent_inactive(registry) -> None:  # noqa: ANN001
    from datetime import date

    agent = registry.agent("anforderungen")
    assert agent.active(date(2027, 5, 31))
    assert not agent.active(date(2027, 6, 1))
    assert not registry.agent("schwachstellen").active()


def test_extract_json_ignores_thinking_and_fences() -> None:
    raw = '<think>Ich überlege {nicht json}</think>```json\n{"status": "fertig", "summary": "ok"}\n```'
    assert extract_json(raw) == {"status": "fertig", "summary": "ok"}
    with pytest.raises(ContractError):
        extract_json("kein json")


def requirement(**extra):  # noqa: ANN003, ANN201
    return {"type": "anforderung", "key": "R1", "title": "T", "text": "Das System muss …", "priority": "Muss",
            "source": "A-001", "acceptance_criteria": ["AC-1: …"], **extra}


def test_valid_requirement_handoff() -> None:
    handoff = validate({"status": "fertig", "summary": "1 Anforderung", "artifacts": [requirement()]},
                       role="anforderungen", kind="create")
    assert handoff.artifacts[0]["key"] == "R1"


@pytest.mark.parametrize(
    ("payload", "role", "kind", "message"),
    [
        ({"status": "fertig", "summary": "x", "artifacts": [requirement(extra="x")]}, "anforderungen", "create", "unbekannte"),
        ({"status": "fertig", "summary": "x", "artifacts": [], "hidden": 1}, "anforderungen", "create", "unbekannte"),
        ({"status": "fertig", "summary": "x", "artifacts": []}, "anforderungen", "create", "mindestens ein Artefakt"),
        ({"status": "erledigt", "summary": "x"}, "anforderungen", "create", "status"),
        ({"status": "nacharbeit", "summary": "x", "findings": [{"severity": "niedrig", "location": "R1", "impact": "i"}]},
         "anforderungspruefung", "review", "mindestens einen Befund"),
        ({"status": "fertig", "summary": "x", "findings": [{"severity": "hoch", "location": "R1", "impact": "i"}]},
         "anforderungspruefung", "review", "blockierenden"),
        ({"status": "fertig", "summary": "x", "artifacts": [requirement()]}, "anforderungspruefung", "review", "Prüfrollen"),
        ({"status": "entscheidung_offen", "summary": "x", "artifacts": []}, "anforderungen", "create", "Frage"),
        ({"status": "entscheidung_offen", "summary": "x", "questions": [{"to": "jeder", "question": "?"}]},
         "anforderungen", "create", "questions"),
    ],
)
def test_contract_violations_block_the_handoff(payload: dict, role: str, kind: str, message: str) -> None:
    with pytest.raises(ContractError, match=message):
        validate(payload, role=role, kind=kind)


def test_limits_from_registry_are_enforced() -> None:
    artifacts = [requirement(key=f"R{i}") for i in range(3)]
    with pytest.raises(ContractError, match="höchstens 2"):
        validate({"status": "fertig", "summary": "x", "artifacts": artifacts}, role="anforderungen", kind="create", limit=2)
