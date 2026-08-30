"""Local full-duplex Synchus voice agent using Gemini Live and bounded database tools."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import queue
import sys
from datetime import date
from typing import Any

import meridian as m

INPUT_RATE = 16_000
OUTPUT_RATE = 24_000
CHUNK = 1_600

VOICE_INTAKE_POLICY = """
For questions, answer normally. Before staging any worker report, run a short natural interview.
Collect: reporter name or role, report type, what happened, exact location or route, when it happened,
severity, affected vehicle/client/hub when relevant, and how long it is expected to remain true.
For vehicle, maintenance, breakdown, or safety reports, vehicle registration is mandatory.
For route disruptions, expected end time is mandatory; "unknown" is acceptable only if the worker explicitly says so.
Never infer a missing identifier from a route name. Read back a one-sentence summary and ask the worker to confirm.
Call stage_observation only after explicit confirmation. Ask at most two missing details at a time, in the worker's language.
""".strip()


def tool_declarations() -> list[dict]:
    return [{"function_declarations": [
        {
            "name": "search_context", "description": "Search approved operational facts, rules and knowledge.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
        {
            "name": "get_vehicle", "description": "Get a vehicle master record and explicit data conflicts. This does not return live location or availability.",
            "parameters": {"type": "object", "properties": {"registration": {"type": "string"}}, "required": ["registration"]},
        },
        {
            "name": "inspect_route", "description": "Compile route rules, historical incidents and conditional candidates for a route/date/client.",
            "parameters": {"type": "object", "properties": {
                "origin": {"type": "string"}, "destination": {"type": "string"},
                "client": {"type": "string"}, "travel_on": {"type": "string", "description": "YYYY-MM-DD"},
            }, "required": ["origin", "destination", "client", "travel_on"]},
        },
        {
            "name": "stage_observation", "description": "Stage a complete, worker-confirmed observation for intake and human approval. Refuses incomplete reports and never writes canonical truth directly.",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string"}, "reporter": {"type": "string"},
                "event_type": {"type": "string", "enum": ["route_disruption", "vehicle_issue", "maintenance", "safety", "client_rule", "hub_update", "other"]},
                "occurred_at": {"type": "string", "description": "Worker-supplied date/time or relative time such as now or 20 minutes ago."},
                "location": {"type": "string", "description": "Exact hub, road point, route, or facility."},
                "entity_ref": {"type": "string", "description": "Vehicle registration, client, hub, or other affected entity when relevant."},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "valid_until": {"type": "string", "description": "Expected end/expiry, durable, or explicitly unknown."},
                "confirmed_by_worker": {"type": "boolean", "description": "True only after the worker confirms the spoken summary."},
            }, "required": ["text", "reporter", "event_type", "occurred_at", "location", "severity", "confirmed_by_worker"]},
        },
    ]}]


def validate_observation(args: dict[str, Any]) -> list[str]:
    missing = [field for field in ("text", "reporter", "event_type", "occurred_at", "location", "severity")
               if not str(args.get(field, "")).strip()]
    event_type = str(args.get("event_type", ""))
    if event_type in {"vehicle_issue", "maintenance", "safety"} and not m.norm_reg(str(args.get("entity_ref", ""))):
        missing.append("vehicle registration")
    if event_type == "route_disruption" and not str(args.get("valid_until", "")).strip():
        missing.append("expected end time or explicit unknown")
    if args.get("confirmed_by_worker") is not True:
        missing.append("worker confirmation of the final summary")
    return missing


def execute_tool(conn, name: str, args: dict[str, Any]) -> Any:
    if name == "search_context":
        return m.search(conn, str(args.get("query", "")), 8)
    if name == "get_vehicle":
        reg = m.norm_reg(str(args.get("registration", "")))
        vehicle = conn.execute("SELECT * FROM vehicle WHERE registration=?", (reg,)).fetchone()
        conflicts = [dict(r) for r in conn.execute("SELECT * FROM vehicle_conflict WHERE registration=?", (reg,))]
        return {"vehicle": dict(vehicle) if vehicle else None, "conflicts": conflicts, "unknowns": ["live location", "availability", "service-due state"]}
    if name == "inspect_route":
        return m.route_intelligence(conn, args["origin"], args["destination"], args.get("client", "Internal"), args.get("travel_on", date.today().isoformat()))
    if name == "stage_observation":
        import agent
        missing = validate_observation(args)
        if missing:
            return {"status": "needs_clarification", "missing_fields": missing, "staged": False}
        details = [
            str(args["text"]).strip(),
            f"Report type: {args['event_type']}", f"Occurred: {args['occurred_at']}",
            f"Location: {args['location']}", f"Severity: {args['severity']}",
        ]
        if str(args.get("entity_ref", "")).strip():
            details.append(f"Affected entity: {args['entity_ref']}")
        if str(args.get("valid_until", "")).strip():
            details.append(f"Valid until: {args['valid_until']}")
        result = agent.ingest_text(conn, ". ".join(details), actor=str(args["reporter"]), channel="live_voice", source_ref="live Gemini session")
        return {"status": "staged_for_review", "staged": True, **result}
    return {"error": f"Unknown tool: {name}"}


async def run(model: str) -> None:
    try:
        import sounddevice as sd
        from google import genai
        from google.genai import types
    except ImportError:
        raise SystemExit("Install live dependencies: uv sync --extra live")
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY first")

    conn = m.ensure_db()
    client = genai.Client(api_key=key)
    mic: asyncio.Queue[bytes] = asyncio.Queue(maxsize=20)
    speaker: queue.Queue[bytes] = queue.Queue(maxsize=50)
    loop = asyncio.get_running_loop()

    def mic_callback(indata, frames, timing, status):
        chunk = bytes(indata)
        def put() -> None:
            if not mic.full():
                mic.put_nowait(chunk)
        loop.call_soon_threadsafe(put)

    def speaker_callback(outdata, frames, timing, status):
        try:
            data = speaker.get_nowait()
        except queue.Empty:
            data = b""
        needed = len(outdata)
        outdata[:] = (data + b"\x00" * needed)[:needed]

    system = f"""
You are Synchus, a concise live operational voice agent for Indian logistics workers.
Speak in the user's Hindi, Hinglish, or English. You may be interrupted naturally.
Use tools before operational claims. Distinguish fleet home assignment/history from live state.
Never say a vehicle is dispatch-ready when availability, current location, or service-due state is unknown.
When a worker supplies new information, call stage_observation; explain whether it was logged or staged.
Canonical context always requires human approval. Today is {date.today().isoformat()}.
{VOICE_INTAKE_POLICY}
"""
    config = {
        "response_modalities": ["AUDIO"], "system_instruction": system, "tools": tool_declarations(),
        "input_audio_transcription": {}, "output_audio_transcription": {},
        "realtime_input_config": {"automatic_activity_detection": {"disabled": False}},
    }

    with sd.RawInputStream(samplerate=INPUT_RATE, blocksize=CHUNK, channels=1, dtype="int16", callback=mic_callback), \
         sd.RawOutputStream(samplerate=OUTPUT_RATE, blocksize=2400, channels=1, dtype="int16", callback=speaker_callback):
        async with client.aio.live.connect(model=model, config=config) as session:
            print("Synchus Live connected. Speak naturally; Ctrl+C exits.", flush=True)

            async def send_audio() -> None:
                while True:
                    await session.send_realtime_input(audio=types.Blob(data=await mic.get(), mime_type=f"audio/pcm;rate={INPUT_RATE}"))

            async def receive() -> None:
                while True:
                    async for response in session.receive():
                        if response.data:
                            try:
                                speaker.put_nowait(response.data)
                            except queue.Full:
                                pass
                        content = response.server_content
                        if content and content.input_transcription and content.input_transcription.text:
                            print(f"\nYOU: {content.input_transcription.text}", flush=True)
                        if content and content.output_transcription and content.output_transcription.text:
                            print(content.output_transcription.text, end="", flush=True)
                        if content and content.interrupted:
                            while not speaker.empty():
                                try: speaker.get_nowait()
                                except queue.Empty: break
                            print("\n[interrupted]", flush=True)
                        if response.tool_call:
                            responses = []
                            for call in response.tool_call.function_calls:
                                try:
                                    result = execute_tool(conn, call.name, call.args or {})
                                except Exception as exc:
                                    result = {"error": str(exc)}
                                print(f"\n[tool: {call.name}]", flush=True)
                                responses.append(types.FunctionResponse(name=call.name, id=call.id, response={"result": result}))
                            await session.send_tool_response(function_responses=responses)

            tasks = [asyncio.create_task(send_audio()), asyncio.create_task(receive())]
            try:
                await asyncio.gather(*tasks)
            finally:
                for task in tasks:
                    task.cancel()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Synchus's full-duplex local voice agent")
    parser.add_argument("--model", default=os.getenv("MERIDIAN_LIVE_MODEL", "gemini-3.1-flash-live-preview"))
    args = parser.parse_args()
    try:
        asyncio.run(run(args.model))
    except KeyboardInterrupt:
        sys.exit(0)
