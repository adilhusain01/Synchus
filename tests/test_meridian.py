from pathlib import Path
import hashlib

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
