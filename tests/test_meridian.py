from pathlib import Path
import hashlib

import agent
import meridian as m


def test_ingestion_rules_and_approval(tmp_path: Path):
    conn = m.rebuild(tmp_path / "test.db")
    s = m.stats(conn)
    assert s["vehicles"] == 100
    assert s["trips"] == 10_000
    assert s["drivers"] == 60
    assert s["invalid_tickets"] == 2
    assert m.norm_reg("RJ-43 dd 3546") == "RJ43DD3546"
    answer = m.answer(conn, "RJ43DD3546 Orion ke liye eligible hai?")
    assert "FAIL" in answer["headline"]
    assert "fleet_master.csv" in answer["citations"]
    pid = m.propose(conn, "Test worker", "Kal Lucknow route par bridge diversion hai", "Lucknow", "2026-09-02")
    assert m.stats(conn)["pending"] == 1
    m.decide_proposal(conn, pid, True, "Test approver")
    assert conn.execute("SELECT count(*) FROM knowledge").fetchone()[0] == 1


def test_pipeline_is_byte_stable_and_exactly_once(tmp_path: Path, monkeypatch):
    conn = m.rebuild(tmp_path / "pipeline.db")
    monkeypatch.setattr(m, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(m, "AUDIT_DIR", tmp_path / "audit")
    first = m.run_pipeline(conn)
    hashes_1 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*(tmp_path / "outputs").glob("*.jsonl"), tmp_path / "audit" / "audit.jsonl"]}
    second = m.run_pipeline(conn)
    hashes_2 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*(tmp_path / "outputs").glob("*.jsonl"), tmp_path / "audit" / "audit.jsonl"]}
    assert first == second == {"work_orders": 30, "pending": 30, "sent": 0, "quarantine": 2, "audit_events": 92}
    assert hashes_1 == hashes_2
    assert len((tmp_path / "outputs" / "work_orders.jsonl").read_text().splitlines()) == 30


def test_route_intelligence_is_explicit_about_unknown_live_state(tmp_path: Path, monkeypatch):
    conn = m.rebuild(tmp_path / "route.db")
    monkeypatch.setattr(m, "road_route", lambda origin, destination: {
        "path": [[77.209, 28.6139], [76.8, 29.6], [75.8573, 30.901]],
        "distance_km": 310.0, "duration_hr": 6.0, "geometry_source": "test road route", "is_approximate": False,
    })
    result = m.route_intelligence(conn, "Delhi", "Ludhiana", "Vertex Retail", "2026-12-10")
    ids = {rule["rule_id"] for rule in result["precautions"]}
    assert {"RULE-DELHI-WINTER", "RULE-VERTEX-GATE", "RULE-SERVICE"} <= ids
    assert "parked count now" in result["unknowns"]
    assert all(candidate["assessment"] != "PASS" for candidate in result["candidates"])
    assert {group["label"] for group in result["uncertainty_groups"]} == {
        "Live feeds not connected", "Required field absent", "Historical, not current",
    }
    assert result["origin_conflicts"] == []
    assert any(rule["status"] == "DATA GAP" for rule in result["precautions"])
    assert len(m.truck_rows(conn)) == 100


def test_agent_stages_useful_updates_and_deduplicates_uploads(tmp_path: Path, monkeypatch):
    conn = m.rebuild(tmp_path / "agent.db")
    monkeypatch.setattr(agent, "provider_status", lambda: {"provider": "Rules", "model": "test", "mode": "fallback"})
    data = b"Kal Lucknow route par bridge diversion hai. 20 minute extra rakho."
    first = agent.ingest_upload(conn, "worker-note.txt", data, "text/plain", "Test worker")
    second = agent.ingest_upload(conn, "worker-note.txt", data, "text/plain", "Test worker")
    assert first["proposal_ids"]
    assert second["duplicate"] is True
    event = conn.execute("SELECT disposition FROM context_event").fetchone()
    assert event["disposition"] == "stage_context"
    proposal = conn.execute("SELECT status,reasoning,source_ref FROM proposal").fetchone()
    assert proposal["status"] == "pending"
    assert proposal["reasoning"]
    assert proposal["source_ref"].startswith("upload:worker-note.txt:")


def test_agent_degrades_safely_when_hosted_model_is_unavailable(tmp_path: Path, monkeypatch):
    conn = m.rebuild(tmp_path / "degraded.db")
    hosted = {"provider": "Gemini", "model": "retired-model", "mode": "model"}
    monkeypatch.setattr(agent, "provider_status", lambda: hosted)
    monkeypatch.setattr(agent, "_model", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider unavailable")))

    answer = agent.ask(conn, "Breakdown origin se 40 km hai—replacement kahan se aaye?")
    assert answer["provider"]["provider"] == "Rules"
    assert answer["trace"] == ["retrieve_context", "model_unavailable", "rules_fallback"]
    assert "origin hub" in answer["headline"].lower()

    items, provider = agent.analyze_update("Kal Lucknow route par bridge diversion hai", "test-note")
    assert provider["provider"] == "Rules"
    assert items[0]["disposition"] == "stage_context"


def test_current_gemini_default(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MERIDIAN_MODEL", raising=False)
    assert agent.provider_status()["model"] == "gemini-3.6-flash"


def test_capability_lab_promotes_and_rolls_back_without_losing_evidence(tmp_path: Path):
    conn = m.rebuild(tmp_path / "capability.db")
    proposal_id = m.propose_capability(
        conn,
        title="Cold-chain temperature readings",
        reason="Repeated sensor readings need a typed shape for route and audit use.",
        entity_type="cold_chain_reading",
        fields=[
            {"name": "vehicle_registration", "type": "string", "required": True},
            {"name": "temperature_c", "type": "number", "required": True},
            {"name": "recorded_at", "type": "datetime", "required": True},
        ],
        sample={"vehicle_registration": "DL30AN8381", "temperature_c": 4.2, "recorded_at": "2026-08-30T12:00:00"},
        surfaces=["context", "route", "audit"],
        source_ref="upload:cold-chain.csv:test",
        agent_name="test-agent",
    )
    held = conn.execute("SELECT status FROM extension_record WHERE capability_proposal_id=?", (proposal_id,)).fetchone()
    assert held["status"] == "held"

    m.decide_capability(conn, proposal_id, True, "Test capability approver")
    definition = conn.execute("SELECT status FROM capability_definition WHERE entity_type='cold_chain_reading'").fetchone()
    record = conn.execute("SELECT status FROM extension_record WHERE capability_proposal_id=?", (proposal_id,)).fetchone()
    assert definition["status"] == "active"
    assert record["status"] == "active"

    m.rollback_capability(conn, proposal_id, "Test capability approver")
    definition = conn.execute("SELECT status FROM capability_definition WHERE entity_type='cold_chain_reading'").fetchone()
    record = conn.execute("SELECT status FROM extension_record WHERE capability_proposal_id=?", (proposal_id,)).fetchone()
    assert definition["status"] == "disabled"
    assert record["status"] == "held"
    assert conn.execute("SELECT count(*) FROM audit_event WHERE object_id=?", (proposal_id,)).fetchone()[0] == 3
