from __future__ import annotations

import csv
import argparse
import hashlib
import json
import os
import re
import sqlite3
import urllib.request
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook

ROOT = Path(__file__).parent
BUNDLE = ROOT / "candidate_bundle"
DB_PATH = ROOT / "data" / "meridian.db"
OUTPUTS = ROOT / "outputs"
AUDIT_DIR = ROOT / "audit"

HUBS = {
    "Delhi": (28.6139, 77.2090),
    "Gurgaon": (28.4595, 77.0266),
    "Jaipur": (26.9124, 75.7873),
    "Ambala": (30.3782, 76.7767),
    "Chandigarh": (30.7333, 76.7794),
    "Ludhiana": (30.9010, 75.8573),
    "Kanpur": (26.4499, 80.3319),
    "Lucknow": (26.8467, 80.9462),
    "Rudrapur": (28.9875, 79.4141),
}

RULES = [
    ("RULE-DELHI-WINTER", "Delhi winter: BS6 only", "October to February, any route touching Delhi, Gurgaon, Faridabad or Noida requires a BS6 vehicle.", "dispatcher_interview.txt", "route", "critical"),
    ("RULE-HILLS-WINTER", "Winter hill eligibility", "November to February, Rudrapur and Nainital-side routes require an engine heater and no brake work in the previous 30 days.", "dispatcher_interview.txt", "route", "critical"),
    ("RULE-SHAKTI-SLA", "Shakti planning SLA", "Plan Shakti Cement loads to a 36-hour internal SLA even though the paper contract says 48 hours.", "dispatcher_interview.txt; emails/thread_01_shakti_sla.txt", "client", "warning"),
    ("RULE-VERTEX-GATE", "Vertex Ludhiana gate", "Vertex Ludhiana accepts 08:00–18:00. Hold after-hours arrivals, notify the prior evening, and mark scheduled morning delivery—not failed delivery.", "dispatcher_interview.txt; emails/thread_09_vertex_gate.txt", "client", "warning"),
    ("RULE-APEX-ROTATE", "Apex vehicle rotation", "After any incident on an Apex run, rotate the vehicle for the next Apex dispatch.", "dispatcher_interview.txt; emails/thread_13_apex_rotation.txt", "client", "warning"),
    ("RULE-ORION", "Orion pharma constraints", "Never leave an Orion load unrefrigerated overnight and use a vehicle from model year 2020 or later.", "dispatcher_interview.txt; emails/thread_17_orion_age.txt", "client", "critical"),
    ("RULE-MONSOON", "Eastern monsoon ETA", "July to September, routes east of Lucknow require at least 20% added ETA and no standard SLA promise.", "dispatcher_interview.txt; emails/thread_23_internal_monsoon.txt", "route", "warning"),
    ("RULE-BREAKDOWN", "Breakdown replacement", "Within 50 km of origin, the origin hub sends replacement. Beyond 50 km, use the nearest hub with an eligible vehicle.", "dispatcher_interview.txt", "response", "critical"),
    ("RULE-SERVICE", "Overdue service grounding", "A vehicle more than 30 days past due service is grounded. Missing due-service data is UNKNOWN, never PASS.", "dispatcher_interview.txt", "safety", "critical"),
    ("RULE-JUGAAD", "Temporary repair clock", "A temporary or jugaad repair needs permanent repair within seven days; until repaired, keep the vehicle in its home region.", "dispatcher_interview.txt; emails/thread_25_internal_jugaad.txt", "maintenance", "critical"),
    ("RULE-NIGHT", "New driver night restriction", "A driver with less than six months tenure cannot run solo at night.", "dispatcher_interview.txt; emails/thread_24_internal_nightroster.txt", "driver", "critical"),
]


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def norm_reg(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def redact(text: str) -> str:
    text = re.sub(r"(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}", "[PHONE REDACTED]", text)
    text = re.sub(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b", "[AADHAAR REDACTED]", text)
    return text


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS source (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, path TEXT NOT NULL UNIQUE,
          fingerprint TEXT NOT NULL, ingested_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vehicle (
          registration TEXT PRIMARY KEY, vehicle_id TEXT, model TEXT, year INTEGER,
          bs_stage TEXT, engine_heater TEXT, home_hub TEXT, capacity REAL, status TEXT,
          source_ref TEXT NOT NULL, raw_variants INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS vehicle_conflict (
          id INTEGER PRIMARY KEY, registration TEXT NOT NULL, field TEXT NOT NULL,
          values_json TEXT NOT NULL, source_ref TEXT NOT NULL,
          UNIQUE(registration, field)
        );
        CREATE TABLE IF NOT EXISTS driver (
          driver_id TEXT PRIMARY KEY, joining_date TEXT, home_hub TEXT, source_ref TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS trip (
          trip_id TEXT PRIMARY KEY, created_at TEXT, origin TEXT, destination TEXT,
          vehicle_reg TEXT, driver_id TEXT, client TEXT, status TEXT, actual_time_min REAL,
          source_ref TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ticket (
          ticket_id TEXT PRIMARY KEY, created_at TEXT, vehicle_reg TEXT, driver_id TEXT,
          origin_hub TEXT, km_from_origin REAL, destination TEXT, issue TEXT, severity TEXT,
          client TEXT, status TEXT, resolution TEXT, valid INTEGER NOT NULL, source_ref TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maintenance (
          id INTEGER PRIMARY KEY, date TEXT, vehicle_reg TEXT, odometer_km REAL,
          mechanic TEXT, notes TEXT, is_temporary INTEGER NOT NULL,
          is_brake_work INTEGER NOT NULL, source_ref TEXT NOT NULL,
          UNIQUE(date, vehicle_reg, odometer_km, notes)
        );
        CREATE TABLE IF NOT EXISTS rule (
          rule_id TEXT PRIMARY KEY, title TEXT, body TEXT, source_ref TEXT,
          scope TEXT, severity TEXT, version INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS knowledge (
          id TEXT PRIMARY KEY, title TEXT, body TEXT, kind TEXT, language TEXT,
          entity_ref TEXT, location TEXT, valid_until TEXT, source_ref TEXT,
          approved_at TEXT, approved_by TEXT
        );
        CREATE TABLE IF NOT EXISTS proposal (
          id TEXT PRIMARY KEY, created_at TEXT NOT NULL, reporter TEXT NOT NULL,
          transcript TEXT NOT NULL, redacted_text TEXT NOT NULL, kind TEXT NOT NULL,
          language TEXT NOT NULL, entity_ref TEXT, location TEXT, valid_until TEXT,
          status TEXT NOT NULL, source_ref TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_event (
          id TEXT PRIMARY KEY, at TEXT NOT NULL, actor TEXT NOT NULL,
          action TEXT NOT NULL, object_type TEXT NOT NULL, object_id TEXT NOT NULL,
          details TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS comm_approval (
          ticket_id TEXT PRIMARY KEY, approved_by TEXT NOT NULL, sent_at TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS context_fts USING fts5(
          title, body, source_ref, object_type, object_id UNINDEXED
        );
        """
    )


def _source(conn: sqlite3.Connection, path: Path, kind: str) -> str:
    rel = str(path.relative_to(BUNDLE))
    sid = "SRC-" + hashlib.sha1(rel.encode()).hexdigest()[:12]
    conn.execute(
        "INSERT OR REPLACE INTO source VALUES (?, ?, ?, ?, ?)",
        (sid, kind, rel, sha(path), datetime.now().isoformat(timespec="seconds")),
    )
    return rel


def rebuild(path: Path = DB_PATH) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    conn = connect(path)
    _schema(conn)
    _ingest_fleet(conn)
    _ingest_drivers(conn)
    _ingest_trips(conn)
    _ingest_tickets(conn)
    _ingest_maintenance(conn)
    _ingest_text(conn)
    for rule in RULES:
        conn.execute("INSERT INTO rule VALUES (?, ?, ?, ?, ?, ?, 1, 'approved')", rule)
    _refresh_fts(conn)
    _audit(conn, "system", "context.rebuilt", "database", "meridian", "All supplied sources ingested")
    conn.commit()
    return conn


def ensure_db() -> sqlite3.Connection:
    conn = connect()
    _schema(conn)
    if not conn.execute("SELECT 1 FROM source LIMIT 1").fetchone():
        conn.close()
        conn = rebuild()
        run_pipeline(conn)
        return conn
    run_pipeline(conn)
    return conn


def _ingest_fleet(conn: sqlite3.Connection) -> None:
    path = BUNDLE / "fleet_master.csv"
    ref = _source(conn, path, "csv")
    groups: dict[str, list[dict]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            groups[norm_reg(row["registration_number"])].append(row)
    for reg, rows in groups.items():
        # ponytail: prefer the identified row; conflicts stay explicit instead of inventing precedence.
        chosen = next((r for r in rows if r["vehicle_id"]), rows[0])
        vals = lambda field: sorted({r[field].strip() for r in rows if r.get(field, "").strip()})
        conn.execute(
            "INSERT INTO vehicle VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (reg, chosen["vehicle_id"] or None, chosen["model"], int(chosen["year"]), chosen["bs_stage"],
             chosen["engine_heater"] or None, chosen["home_hub"], float(chosen["capacity_tonnes"]) if chosen["capacity_tonnes"] else None,
             chosen["status"], ref, len(rows)),
        )
        for field in ("year", "engine_heater", "capacity_tonnes"):
            values = vals(field)
            if len(values) > 1:
                conn.execute("INSERT INTO vehicle_conflict(registration,field,values_json,source_ref) VALUES (?,?,?,?)",
                             (reg, field, json.dumps(values), ref))


def _ingest_drivers(conn: sqlite3.Connection) -> None:
    path = BUNDLE / "drivers_roster.csv"
    ref = _source(conn, path, "csv")
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            conn.execute("INSERT INTO driver VALUES (?,?,?,?)", (r["driver_id"], r["joining_date"], r["home_hub"], ref))


def _ingest_trips(conn: sqlite3.Connection) -> None:
    path = BUNDLE / "meridian_trips.csv"
    ref = _source(conn, path, "csv")
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = ((r["trip_id"], r["created_at"], r["origin_name"], r["dest_name"], norm_reg(r["vehicle_reg"]),
                 r["driver_id"], r["client"], r["status"], float(r["actual_time_min"]), ref) for r in csv.DictReader(f))
        conn.executemany("INSERT INTO trip VALUES (?,?,?,?,?,?,?,?,?,?)", rows)


def _ingest_tickets(conn: sqlite3.Connection) -> None:
    path = BUNDLE / "tickets.json"
    ref = _source(conn, path, "json")
    seen: set[str] = set()
    for r in json.loads(path.read_text()):
        tid = str(r.get("ticket_id") or "")
        if tid in seen:
            continue
        seen.add(tid)
        valid = int(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", str(r.get("created_at") or ""))
                         and norm_reg(r.get("vehicle")) and r.get("driver_id") and r.get("issue")))
        conn.execute(
            "INSERT INTO ticket VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, r.get("created_at"), norm_reg(r.get("vehicle")), r.get("driver_id"), r.get("origin_hub"),
             r.get("km_from_origin_hub"), r.get("destination"), r.get("issue"), r.get("severity"),
             r.get("client"), r.get("status"), redact(str(r.get("resolution_note") or "")), valid, ref),
        )


def _ingest_maintenance(conn: sqlite3.Connection) -> None:
    path = BUNDLE / "maintenance_log.xlsx"
    ref = _source(conn, path, "xlsx")
    ws = load_workbook(path, read_only=True, data_only=True).active
    for row in ws.iter_rows(min_row=2, values_only=True):
        dt, vehicle, odo, mechanic, notes = row
        note = redact(str(notes or ""))
        low = note.lower()
        conn.execute(
            "INSERT OR IGNORE INTO maintenance(date,vehicle_reg,odometer_km,mechanic,notes,is_temporary,is_brake_work,source_ref) VALUES (?,?,?,?,?,?,?,?)",
            (str(dt)[:10], norm_reg(str(vehicle)), odo, mechanic, note,
             int(any(k in low for k in ("jugaad", "temporary", "permanent fix"))),
             int("brake" in low), ref),
        )


def _ingest_text(conn: sqlite3.Connection) -> None:
    files = [BUNDLE / "dispatcher_interview.txt", *sorted((BUNDLE / "emails").glob("*.txt"))]
    for path in files:
        _source(conn, path, "interview" if "interview" in path.name else "email")


def _refresh_fts(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM context_fts")
    for row in conn.execute("SELECT rule_id,title,body,source_ref FROM rule"):
        conn.execute("INSERT INTO context_fts VALUES (?,?,?,?,?)", (row["title"], row["body"], row["source_ref"], "rule", row["rule_id"]))
    for path in [BUNDLE / "dispatcher_interview.txt", *sorted((BUNDLE / "emails").glob("*.txt"))]:
        rel = str(path.relative_to(BUNDLE))
        conn.execute("INSERT INTO context_fts VALUES (?,?,?,?,?)", (path.stem.replace("_", " ").title(), redact(path.read_text(errors="replace")), rel, "source", rel))
    for row in conn.execute("SELECT id,title,body,source_ref FROM knowledge"):
        conn.execute("INSERT INTO context_fts VALUES (?,?,?,?,?)", (row["title"], row["body"], row["source_ref"], "knowledge", row["id"]))


def _audit(conn: sqlite3.Connection, actor: str, action: str, object_type: str, object_id: str, details: str) -> None:
    conn.execute("INSERT INTO audit_event VALUES (?,?,?,?,?,?,?)",
                 (str(uuid.uuid4()), datetime.now().isoformat(timespec="seconds"), actor, action, object_type, object_id, details))


def stats(conn: sqlite3.Connection) -> dict[str, int]:
    scalar = lambda q: int(conn.execute(q).fetchone()[0])
    return {
        "vehicles": scalar("SELECT count(*) FROM vehicle"),
        "trips": scalar("SELECT count(*) FROM trip"),
        "drivers": scalar("SELECT count(*) FROM driver"),
        "rules": scalar("SELECT count(*) FROM rule WHERE status='approved'"),
        "conflicts": scalar("SELECT count(*) FROM vehicle_conflict"),
        "invalid_tickets": scalar("SELECT count(*) FROM ticket WHERE valid=0"),
        "temporary_repairs": scalar("SELECT count(*) FROM maintenance WHERE is_temporary=1"),
        "pending": scalar("SELECT count(*) FROM proposal WHERE status='pending'"),
    }


def data_quality(conn: sqlite3.Connection) -> list[dict]:
    raw_fleet = sum(1 for _ in csv.DictReader((BUNDLE / "fleet_master.csv").open()))
    canonical = conn.execute("SELECT count(*) FROM vehicle").fetchone()[0]
    raw_tickets = len(json.loads((BUNDLE / "tickets.json").read_text()))
    unique_tickets = conn.execute("SELECT count(*) FROM ticket").fetchone()[0]
    regressions = 0
    by_vehicle: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for r in conn.execute("SELECT date,vehicle_reg,odometer_km FROM maintenance ORDER BY vehicle_reg,date"):
        if r["odometer_km"] is not None:
            by_vehicle[r["vehicle_reg"]].append((r["date"], r["odometer_km"]))
    for points in by_vehicle.values():
        regressions += sum(b[1] < a[1] for a, b in zip(points, points[1:]))
    return [
        {"severity": "warning", "title": f"{raw_fleet - canonical} duplicate fleet rows merged", "detail": f"{raw_fleet} source rows → {canonical} canonical registrations", "source": "fleet_master.csv"},
        {"severity": "critical", "title": "Model-year conflicts block automatic age decisions", "detail": "CH42HD4155, RJ34GX8933 and UP40IM3144 disagree inside the fleet source; RJ43DD3546 also conflicts with an email claim.", "source": "fleet_master.csv + email"},
        {"severity": "warning", "title": f"{raw_tickets - unique_tickets} duplicate ticket rows ignored", "detail": f"{raw_tickets} source rows → {unique_tickets} unique ticket IDs", "source": "tickets.json"},
        {"severity": "critical", "title": "2 tickets quarantined", "detail": "TKT-9101 and TKT-9102 lack required identity/date/location evidence.", "source": "tickets.json"},
        {"severity": "warning", "title": f"{regressions} odometer regression events", "detail": "Maintenance mileage cannot be treated as a monotonic current odometer without reconciliation.", "source": "maintenance_log.xlsx"},
        {"severity": "info", "title": "Trip history is not live telemetry", "detail": "10,000 trips are from Sep–Oct 2018. Map locations show home assignment or historical routes—not current vehicle positions.", "source": "meridian_trips.csv"},
    ]


def hub_rows(conn: sqlite3.Connection) -> list[dict]:
    counts = {r["home_hub"]: r["n"] for r in conn.execute("SELECT home_hub,count(*) n FROM vehicle GROUP BY home_hub")}
    incidents = {r["origin_hub"]: r["n"] for r in conn.execute("SELECT origin_hub,count(*) n FROM ticket WHERE status!='CLOSED' AND valid=1 GROUP BY origin_hub")}
    rows = []
    for name, (lat, lon) in HUBS.items():
        rows.append({"hub": name, "lat": lat, "lon": lon, "vehicles": counts.get(name, 0), "incidents": incidents.get(name, 0), "position_type": "home assignment"})
    return rows


def search(conn: sqlite3.Connection, question: str, limit: int = 6) -> list[dict]:
    tokens = re.findall(r"[A-Za-z0-9]+", question)
    if not tokens:
        return []
    match = " OR ".join(f'"{t}"' for t in tokens[:10])
    try:
        return [dict(r) for r in conn.execute(
            "SELECT title,body,source_ref,object_type,object_id,bm25(context_fts) score FROM context_fts WHERE context_fts MATCH ? ORDER BY score LIMIT ?",
            (match, limit),
        )]
    except sqlite3.OperationalError:
        return []


def answer(conn: sqlite3.Connection, question: str) -> dict:
    q = question.lower()
    hindi = any(k in q for k in ("hai", "kya", "ke liye", "gaadi", "bhej", "karna", "sahi"))
    reg_match = re.search(r"\b(?:[a-z]{2}[\s-]?\d{1,2}[\s-]?[a-z]{1,2}[\s-]?\d{4})\b", question, re.I)
    citations: list[str] = []
    unknowns: list[str] = []
    headline = "यह फैसला उपलब्ध संदर्भ से नहीं निकलता।" if hindi else "The available context is not enough for a safe decision."
    detail = ""
    if reg_match:
        reg = norm_reg(reg_match.group())
        v = conn.execute("SELECT * FROM vehicle WHERE registration=?", (reg,)).fetchone()
        if v:
            citations.append("fleet_master.csv")
            if "orion" in q:
                citations += ["dispatcher_interview.txt", "emails/thread_17_orion_age.txt"]
                eligible = v["year"] >= 2020
                headline = (f"नहीं—{reg} Orion के लिए age rule में FAIL है।" if hindi and not eligible else
                            f"हाँ—{reg} Orion के 2020+ age rule में PASS है।" if hindi else
                            f"{'PASS' if eligible else 'FAIL'} — {reg} is {'new enough' if eligible else 'too old'} for Orion.")
                detail = f"Fleet master says model year {v['year']}; Orion requires 2020 or later. BS stage: {v['bs_stage']}; home assignment: {v['home_hub']}."
                if reg == "RJ43DD3546":
                    detail += " An email calls it a brand-new 2021 vehicle, conflicting with the fleet master's 2017; the conservative result remains FAIL pending RC verification."
            elif any(k in q for k in ("delhi", "gurgaon", "noida", "faridabad")):
                citations.append("dispatcher_interview.txt")
                eligible = v["bs_stage"] == "BS6"
                headline = f"{'PASS' if eligible else 'FAIL'} — {reg} is {v['bs_stage']} for the Delhi winter BS6 rule."
                detail = "This restriction applies October through February on routes touching Delhi NCR."
            else:
                headline = f"{reg}: {v['model']}, {v['year']}, {v['bs_stage']}, home assignment {v['home_hub']}."
                detail = "Current location, availability and service-due state are not present in the supplied sources."
                unknowns += ["current GPS/location", "current availability", "verified service-due status"]
    elif "shakti" in q and any(k in q for k in ("sla", "hour", "time", "kitna", "deadline")):
        headline = "Shakti ke liye 36 ghante ka internal SLA plan karo." if hindi else "Plan Shakti loads to a 36-hour internal SLA."
        detail = "The paper contract says 48 hours, but the dispatcher interview and email evidence say operations escalate after 36."
        citations = ["dispatcher_interview.txt", "emails/thread_01_shakti_sla.txt"]
    elif any(k in q for k in ("breakdown", "toot", "kharab")) and any(k in q for k in ("50", "replacement", "badli")):
        headline = "50 km ke andar origin hub replacement bhejega; uske baad nearest eligible hub." if hindi else "Within 50 km, the origin hub sends replacement; beyond 50 km, use the nearest eligible hub."
        detail = "Eligibility still requires route/season compliance, maintenance safety and availability."
        citations = ["dispatcher_interview.txt"]
        unknowns = ["live hub inventory", "current service-due state"]
    else:
        evidence = search(conn, question)
        if evidence:
            top = evidence[0]
            headline = top["title"]
            detail = top["body"][:650].strip()
            citations = list(dict.fromkeys(r["source_ref"] for r in evidence[:3]))
        unknowns.append("No live operational feed is connected; verify current state before dispatch.")
    return {"headline": headline, "detail": detail, "citations": list(dict.fromkeys(citations)), "unknowns": unknowns}


def detect_language(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi"
    if any(k in text.lower().split() for k in ("hai", "tha", "gaadi", "jugaad", "kal", "aaj", "nahi")):
        return "Hinglish"
    return "English"


def classify(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ("route", "road", "rasta", "raasta", "bridge", "diversion")):
        return "route precaution"
    if any(k in low for k in ("repair", "brake", "engine", "tyre", "leak", "jugaad")):
        return "maintenance observation"
    if any(k in low for k in ("client", "gate", "warehouse", "sla", "delivery")):
        return "client rule"
    return "ground observation"


def propose(conn: sqlite3.Connection, reporter: str, transcript: str, location: str = "", valid_until: str = "", entity_ref: str = "") -> str:
    pid = "PROP-" + uuid.uuid4().hex[:10].upper()
    clean = redact(transcript.strip())
    conn.execute("INSERT INTO proposal VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (pid, datetime.now().isoformat(timespec="seconds"), reporter.strip() or "Anonymous worker", clean, clean,
                  classify(clean), detect_language(clean), norm_reg(entity_ref) or None, location or None, valid_until or None, "pending", "worker voice/text"))
    _audit(conn, reporter or "Anonymous worker", "proposal.created", "proposal", pid, f"{classify(clean)} awaiting approval")
    conn.commit()
    return pid


def decide_proposal(conn: sqlite3.Connection, proposal_id: str, approve: bool, actor: str = "Operations approver") -> None:
    row = conn.execute("SELECT * FROM proposal WHERE id=? AND status='pending'", (proposal_id,)).fetchone()
    if not row:
        return
    status = "approved" if approve else "rejected"
    conn.execute("UPDATE proposal SET status=? WHERE id=?", (status, proposal_id))
    if approve:
        kid = "KNOW-" + proposal_id.removeprefix("PROP-")
        conn.execute("INSERT INTO knowledge VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (kid, row["kind"].title(), row["redacted_text"], row["kind"], row["language"], row["entity_ref"], row["location"],
                      row["valid_until"], row["source_ref"] + "; " + proposal_id, datetime.now().isoformat(timespec="seconds"), actor))
        _refresh_fts(conn)
    _audit(conn, actor, f"proposal.{status}", "proposal", proposal_id, "Human decision recorded")
    conn.commit()


def transcribe_sarvam(audio_bytes: bytes, mime: str = "audio/wav") -> str:
    key = os.getenv("SARVAM_API_KEY")
    if not key:
        raise RuntimeError("SARVAM_API_KEY is not configured")
    boundary = "----Meridian" + uuid.uuid4().hex
    chunks = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nsaaras:v3\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"language_code\"\r\n\r\nunknown\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"worker-note.wav\"\r\nContent-Type: {mime}\r\n\r\n".encode(),
        audio_bytes,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    req = urllib.request.Request("https://api.sarvam.ai/speech-to-text", data=b"".join(chunks), method="POST",
                                 headers={"api-subscription-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read())["transcript"]


def export_audit(conn: sqlite3.Connection) -> str:
    rows = [dict(r) for r in conn.execute("SELECT * FROM audit_event ORDER BY at,id")]
    return "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n"


ALIASES = {
    "ticket_id": ("ticket_id", "ticketId", "id"),
    "created_at": ("created_at", "createdAt", "reported_at", "timestamp"),
    "vehicle": ("vehicle", "vehicle_reg", "registration", "vehicle_registration"),
    "driver_id": ("driver_id", "driverId", "driver"),
    "origin_hub": ("origin_hub", "origin", "source_hub"),
    "km_from_origin_hub": ("km_from_origin_hub", "km_from_origin", "distance_from_origin_km"),
    "destination": ("destination", "dest", "destination_hub"),
    "issue": ("issue", "problem", "description"),
    "severity": ("severity", "priority"),
    "client": ("client", "customer"),
    "status": ("status", "ticket_status"),
    "resolution_note": ("resolution_note", "resolution", "notes"),
}


def _adapt_ticket(raw: dict) -> dict:
    return {field: next((raw.get(k) for k in names if raw.get(k) not in (None, "")), None) for field, names in ALIASES.items()}


def _ticket_errors(ticket: dict) -> list[str]:
    errors = []
    required = ("ticket_id", "created_at", "vehicle", "driver_id", "origin_hub", "km_from_origin_hub", "destination", "issue", "severity", "client")
    errors.extend(f"missing {k}" for k in required if ticket.get(k) in (None, ""))
    try:
        datetime.fromisoformat(str(ticket.get("created_at")))
    except ValueError:
        errors.append("invalid created_at")
    if ticket.get("vehicle") and not norm_reg(str(ticket["vehicle"])):
        errors.append("invalid vehicle")
    return sorted(set(errors))


def _deterministic_id(prefix: str, value: str) -> str:
    return f"{prefix}-" + hashlib.sha256(value.encode()).hexdigest()[:14].upper()


def _jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) for row in rows)
    path.write_text(content + ("\n" if content else ""), encoding="utf-8")


def run_pipeline(conn: sqlite3.Connection, ticket_paths: Iterable[Path] | None = None) -> dict[str, int]:
    paths = list(ticket_paths or [BUNDLE / "tickets.json"])
    canonical: dict[str, dict] = {}
    duplicate_counts: Counter = Counter()
    source_for: dict[str, str] = {}
    for path in paths:
        payload = json.loads(path.read_text())
        records = payload if isinstance(payload, list) else payload.get("tickets", payload.get("records", []))
        for raw in records:
            ticket = _adapt_ticket(raw)
            tid = str(ticket.get("ticket_id") or _deterministic_id("MISSING", json.dumps(raw, sort_keys=True)))
            duplicate_counts[tid] += 1
            canonical.setdefault(tid, ticket)
            source_for.setdefault(tid, path.name)

    work_orders, pending, quarantine, audit = [], [], [], []
    for tid in sorted(canonical):
        t = canonical[tid]
        source = source_for[tid]
        errors = _ticket_errors(t)
        if errors:
            quarantine.append({"ticket_id": tid, "reasons": errors, "source": source})
            audit.append({"step": "quarantined", "ticket_id": tid, "decision": "; ".join(errors), "citations": [source]})
            continue
        reg = norm_reg(str(t["vehicle"]))
        km = float(t["km_from_origin_hub"])
        response = f"Origin hub ({t['origin_hub']}) sends replacement" if km <= 50 else "Nearest hub with an eligible vehicle sends replacement"
        citations = [source, "dispatcher_interview.txt"]
        wo_id = _deterministic_id("WO", tid)
        msg_id = _deterministic_id("MSG", tid)
        work_orders.append({
            "work_order_id": wo_id, "ticket_id": tid, "vehicle_reg": reg,
            "created_at": str(t["created_at"]), "citations": citations,
        })
        body = (f"Meridian update {tid}: a {str(t['severity']).lower()} {t['issue']} incident is recorded "
                f"for vehicle {reg} on the {t['origin_hub']}–{t['destination']} movement. {response}. "
                "This draft awaits operations approval.")
        pending.append({
            "message_id": msg_id, "ticket_id": tid, "recipient": t["client"], "body": redact(body),
            "context": {"severity": t["severity"], "status": t.get("status"), "km_from_origin_hub": km, "response": response},
            "citations": citations, "approval_status": "pending",
        })
        audit.extend([
            {"step": "normalized", "ticket_id": tid, "decision": f"canonicalized; {duplicate_counts[tid]} source row(s)", "citations": [source]},
            {"step": "response_decided", "ticket_id": tid, "decision": response, "rule_id": "RULE-BREAKDOWN", "citations": citations},
            {"step": "outputs_drafted", "ticket_id": tid, "decision": f"{wo_id}; {msg_id}", "citations": citations},
        ])

    approvals = {r["ticket_id"]: dict(r) for r in conn.execute("SELECT * FROM comm_approval")}
    sent = []
    for draft in pending:
        approval = approvals.get(draft["ticket_id"])
        if approval:
            sent.append({"message_id": draft["message_id"], "ticket_id": draft["ticket_id"], "recipient": draft["recipient"],
                         "body": draft["body"].replace(" This draft awaits operations approval.", ""),
                         "approved_by": approval["approved_by"], "sent_at": approval["sent_at"]})

    _jsonl(OUTPUTS / "work_orders.jsonl", work_orders)
    _jsonl(OUTPUTS / "comms_pending.jsonl", pending)
    _jsonl(OUTPUTS / "comms_sent.jsonl", sent)
    _jsonl(OUTPUTS / "quarantine.jsonl", quarantine)
    _jsonl(AUDIT_DIR / "audit.jsonl", audit)
    return {"work_orders": len(work_orders), "pending": len(pending), "sent": len(sent), "quarantine": len(quarantine), "audit_events": len(audit)}


def approve_communication(conn: sqlite3.Connection, ticket_id: str, approved_by: str) -> None:
    conn.execute("INSERT OR IGNORE INTO comm_approval VALUES (?,?,?)", (ticket_id, approved_by, datetime.now().isoformat(timespec="seconds")))
    _audit(conn, approved_by, "communication.approved", "ticket", ticket_id, "Draft moved to comms_sent exactly once")
    conn.commit()
    run_pipeline(conn)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Meridian deterministic context pipeline")
    parser.add_argument("command", choices=["pipeline", "rebuild"])
    parser.add_argument("--tickets", nargs="*", type=Path, help="Ticket JSON files; aliases are normalized")
    args = parser.parse_args()
    conn = rebuild() if args.command == "rebuild" else ensure_db()
    result = run_pipeline(conn, args.tickets or None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    cli()
