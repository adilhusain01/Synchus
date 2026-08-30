"""Reactive HTTP surface for the TanStack Synchus client."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import agent
import meridian as m


@asynccontextmanager
async def lifespan(_app: FastAPI):
    m.ensure_db().close()
    yield


app = FastAPI(title="Synchus Context API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4_000)


class IntakeRequest(BaseModel):
    text: str = Field(min_length=2, max_length=80_000)
    actor: str = Field(default="App worker", max_length=180)
    channel: str = Field(default="web_text", max_length=80)


class ProposalDecision(BaseModel):
    decision: str
    actor: str = Field(default="Operations approver", max_length=180)


class CommunicationDecision(BaseModel):
    actor: str = Field(default="Operations lead", max_length=180)


def database() -> Generator:
    conn = m.connect()
    try:
        yield conn
    finally:
        conn.close()


def _json_rows(conn, query: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(query, params)]


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _revision() -> str:
    conn = m.connect()
    try:
        values = []
        for table, time_field in (
            ("audit_event", "at"),
            ("context_event", "at"),
            ("agent_run", "started_at"),
            ("proposal", "created_at"),
            ("capability_proposal", "created_at"),
        ):
            row = conn.execute(
                f"SELECT count(*),coalesce(max({time_field}),''),coalesce(group_concat(DISTINCT status),'') "
                f"FROM {table}" if table in {"agent_run", "proposal", "capability_proposal"} else
                f"SELECT count(*),coalesce(max({time_field}),''),'' FROM {table}"
            ).fetchone()
            values.extend(str(value) for value in row)
        return hashlib.sha1("|".join(values).encode()).hexdigest()[:14]
    finally:
        conn.close()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ready", "revision": _revision()}


@app.get("/api/bootstrap")
def bootstrap(conn=Depends(database)) -> dict:
    pipeline = {
        "work_orders": len(_jsonl(m.OUTPUTS / "work_orders.jsonl")),
        "communications": len(_jsonl(m.OUTPUTS / "comms_pending.jsonl")),
        "quarantine": len(_jsonl(m.OUTPUTS / "quarantine.jsonl")),
    }
    rules = _json_rows(
        conn,
        "SELECT rule_id,title,body,scope,severity,source_ref FROM rule WHERE status='approved' ORDER BY severity,scope,title",
    )
    return {
        "stats": m.stats(conn),
        "pipeline": pipeline,
        "quality": m.data_quality(conn),
        "rules": rules,
        "provider": agent.provider_status(),
        "revision": _revision(),
    }


@app.get("/api/route/options")
def route_options() -> dict:
    return {
        "origins": list(m.HUBS),
        "destinations": list(m.PLACES),
        "clients": ["Internal", "Shakti Cement", "Vertex Retail", "Apex Chemicals", "Orion Pharma"],
    }


@app.get("/api/map/config")
def map_config() -> dict:
    return {
        "provider": "CARTO",
        "api_base_url": os.getenv("CARTO_API_BASE_URL", "https://gcp-asia-northeast1.api.carto.com"),
        "api_access_configured": bool(os.getenv("CARTO_API_KEY") or os.getenv("CARTO_ACCESS_TOKEN")),
        "basemap": "Positron",
    }


@app.get("/api/route")
def route(
    origin: str = Query(default="Delhi"),
    destination: str = Query(default="Ludhiana"),
    client: str = Query(default="Internal"),
    travel_on: str = Query(default="2026-08-30"),
    conn=Depends(database),
) -> dict:
    if origin == destination:
        raise HTTPException(status_code=422, detail="Origin and destination must differ")
    try:
        intelligence = m.route_intelligence(conn, origin, destination, client, travel_on)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return {
        **intelligence,
        "hubs": m.hub_rows(conn),
        "trucks": m.truck_rows(conn),
    }


@app.post("/api/ask")
def ask(payload: AskRequest, conn=Depends(database)) -> dict:
    return agent.ask(conn, payload.question.strip())


@app.post("/api/intake/text")
def intake_text(payload: IntakeRequest, conn=Depends(database)) -> dict:
    return agent.ingest_text(
        conn,
        payload.text.strip(),
        actor=payload.actor.strip() or "App worker",
        channel=payload.channel,
        source_ref=f"tanstack:{payload.channel}",
    )


@app.post("/api/intake/upload")
async def intake_upload(
    file: UploadFile = File(...),
    actor: str = Form(default="Company document inbox"),
    conn=Depends(database),
) -> dict:
    data = await file.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 20 MB demo limit")
    try:
        return agent.ingest_upload(
            conn,
            file.filename or "uploaded-document",
            data,
            media_type=file.content_type or "application/octet-stream",
            actor=actor.strip() or "Company document inbox",
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.get("/api/inbox")
def inbox(conn=Depends(database)) -> dict:
    return {
        "metrics": {
            "events": conn.execute("SELECT count(*) FROM context_event").fetchone()[0],
            "pending": conn.execute("SELECT count(*) FROM proposal WHERE status='pending'").fetchone()[0],
            "approved": conn.execute("SELECT count(*) FROM proposal WHERE status='approved'").fetchone()[0],
            "channels": conn.execute("SELECT count(DISTINCT channel) FROM context_event").fetchone()[0],
        },
        "events": _json_rows(
            conn,
            "SELECT id,at,channel,actor_ref,event_type,disposition,reasoning,source_ref "
            "FROM context_event ORDER BY at DESC LIMIT 30",
        ),
    }


@app.get("/api/approvals")
def approvals(conn=Depends(database)) -> dict:
    proposals = _json_rows(
        conn,
        "SELECT * FROM proposal WHERE status='pending' ORDER BY risk='critical' DESC,created_at DESC",
    )
    for proposal in proposals:
        proposal["connections"] = json.loads(proposal.pop("connections_json") or "[]")
    approved_communications = {
        row["ticket_id"] for row in conn.execute("SELECT ticket_id FROM comm_approval")
    }
    communications = [
        item for item in _jsonl(m.OUTPUTS / "comms_pending.jsonl")
        if item["ticket_id"] not in approved_communications
    ]
    capabilities = _json_rows(
        conn,
        "SELECT * FROM capability_proposal WHERE status='pending' ORDER BY risk IN ('critical','high') DESC,created_at DESC",
    )
    for capability in capabilities:
        capability["schema"] = json.loads(capability.pop("schema_json"))
        capability["sample"] = json.loads(capability.pop("sample_json"))
        capability["surfaces"] = json.loads(capability.pop("surfaces_json"))
        capability["validation"] = json.loads(capability.pop("validation_json"))
    active_capabilities = _json_rows(
        conn,
        """SELECT d.id,d.entity_type,d.version,d.schema_json,d.approved_at,d.approved_by,
                  d.source_proposal_id,p.title,p.risk
           FROM capability_definition d JOIN capability_proposal p ON p.id=d.source_proposal_id
           WHERE d.status='active' ORDER BY d.approved_at DESC""",
    )
    for capability in active_capabilities:
        capability["schema"] = json.loads(capability.pop("schema_json"))
    return {
        "proposals": proposals,
        "capabilities": capabilities,
        "active_capabilities": active_capabilities,
        "communications": communications,
        "counts": {
            "pending_proposals": len(proposals),
            "pending_capabilities": len(capabilities),
            "pending_communications": len(communications),
            "approved": conn.execute("SELECT count(*) FROM proposal WHERE status='approved'").fetchone()[0],
            "rejected": conn.execute("SELECT count(*) FROM proposal WHERE status='rejected'").fetchone()[0],
        },
    }


@app.post("/api/approvals/capabilities/{proposal_id}")
def decide_capability(proposal_id: str, payload: ProposalDecision, conn=Depends(database)) -> dict:
    decision = payload.decision.lower().strip()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="Decision must be approve or reject")
    if not conn.execute("SELECT 1 FROM capability_proposal WHERE id=? AND status='pending'", (proposal_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Pending capability proposal not found")
    m.decide_capability(conn, proposal_id, decision == "approve", payload.actor)
    return {"proposal_id": proposal_id, "status": "approved" if decision == "approve" else "rejected"}


@app.post("/api/approvals/capabilities/{proposal_id}/rollback")
def rollback_capability(proposal_id: str, payload: CommunicationDecision, conn=Depends(database)) -> dict:
    if not conn.execute("SELECT 1 FROM capability_definition WHERE source_proposal_id=? AND status='active'", (proposal_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Active capability not found")
    m.rollback_capability(conn, proposal_id, payload.actor)
    return {"proposal_id": proposal_id, "status": "rolled_back"}


@app.post("/api/approvals/proposals/{proposal_id}")
def decide_proposal(proposal_id: str, payload: ProposalDecision, conn=Depends(database)) -> dict:
    decision = payload.decision.lower().strip()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="Decision must be approve or reject")
    exists = conn.execute(
        "SELECT 1 FROM proposal WHERE id=? AND status='pending'", (proposal_id,)
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Pending proposal not found")
    m.decide_proposal(conn, proposal_id, decision == "approve", payload.actor)
    return {"proposal_id": proposal_id, "status": "approved" if decision == "approve" else "rejected"}


@app.post("/api/approvals/communications/{ticket_id}")
def approve_communication(ticket_id: str, payload: CommunicationDecision, conn=Depends(database)) -> dict:
    if not conn.execute("SELECT 1 FROM ticket WHERE ticket_id=?", (ticket_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Ticket not found")
    m.approve_communication(conn, ticket_id, payload.actor)
    return {"ticket_id": ticket_id, "status": "approved"}


LEDGERS = {
    "runs": "SELECT started_at,provider,task,source_ref,status,trace_json FROM agent_run ORDER BY started_at DESC LIMIT 100",
    "events": "SELECT at,channel,actor_ref,event_type,disposition,reasoning,source_ref FROM context_event ORDER BY at DESC LIMIT 200",
    "sources": "SELECT kind,path,substr(fingerprint,1,16) AS sha256,ingested_at FROM source ORDER BY path",
    "decisions": "SELECT at,actor,action,object_type,object_id,details FROM audit_event ORDER BY at DESC LIMIT 200",
    "quarantine": "SELECT ticket_id,created_at,vehicle_reg,driver_id,issue,source_ref FROM ticket WHERE valid=0",
    "capabilities": "SELECT created_at,id,title,entity_type,change_class,risk,status,source_ref,decided_by FROM capability_proposal ORDER BY created_at DESC LIMIT 200",
}


@app.get("/api/audit/{ledger}")
def audit(ledger: str, conn=Depends(database)) -> dict:
    query = LEDGERS.get(ledger)
    if not query:
        raise HTTPException(status_code=404, detail="Unknown ledger")
    rows = _json_rows(conn, query)
    return {
        "ledger": ledger,
        "rows": rows,
        "counts": {
            "runs": conn.execute("SELECT count(*) FROM agent_run").fetchone()[0],
            "events": conn.execute("SELECT count(*) FROM context_event").fetchone()[0],
            "sources": conn.execute("SELECT count(*) FROM source").fetchone()[0],
            "quarantine": conn.execute("SELECT count(*) FROM ticket WHERE valid=0").fetchone()[0],
            "capabilities": conn.execute("SELECT count(*) FROM capability_proposal").fetchone()[0],
        },
    }


@app.get("/api/live/status")
def live_status() -> dict:
    return {
        "voice_ready": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "telegram_ready": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "voice_url": "http://127.0.0.1:8765",
        "provider": agent.provider_status(),
    }


@app.get("/api/events")
async def events() -> StreamingResponse:
    async def stream():
        previous = ""
        heartbeat = 0
        while True:
            revision = _revision()
            if revision != previous:
                previous = revision
                yield f"event: context\ndata: {json.dumps({'revision': revision})}\n\n"
            heartbeat += 1
            if heartbeat % 15 == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="127.0.0.1", port=8780, reload=False)
