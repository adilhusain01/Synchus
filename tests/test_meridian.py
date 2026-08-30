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
