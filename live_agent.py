"""Local full-duplex Meridian voice agent using Gemini Live and bounded database tools."""

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
            "name": "stage_observation", "description": "Log a worker observation and let the intake agent decide whether to stage it for human approval. Never writes canonical truth directly.",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string"}, "reporter": {"type": "string"},
            }, "required": ["text"]},
        },
    ]}]


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

        return agent.ingest_text(conn, str(args.get("text", "")), actor=str(args.get("reporter", "Live voice worker")), channel="live_voice", source_ref="live Gemini session")
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
You are Meridian, a concise live operational voice agent for Indian logistics workers.
Speak in the user's Hindi, Hinglish, or English. You may be interrupted naturally.
Use tools before operational claims. Distinguish fleet home assignment/history from live state.
Never say a vehicle is dispatch-ready when availability, current location, or service-due state is unknown.
When a worker supplies new information, call stage_observation; explain whether it was logged or staged.
Canonical context always requires human approval. Today is {date.today().isoformat()}.
"""
    config = {
        "response_modalities": ["AUDIO"], "system_instruction": system, "tools": tool_declarations(),
        "input_audio_transcription": {}, "output_audio_transcription": {},
        "realtime_input_config": {"automatic_activity_detection": {"disabled": False}},
    }

    with sd.RawInputStream(samplerate=INPUT_RATE, blocksize=CHUNK, channels=1, dtype="int16", callback=mic_callback), \
         sd.RawOutputStream(samplerate=OUTPUT_RATE, blocksize=2400, channels=1, dtype="int16", callback=speaker_callback):
        async with client.aio.live.connect(model=model, config=config) as session:
            print("Meridian Live connected. Speak naturally; Ctrl+C exits.", flush=True)

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
    parser = argparse.ArgumentParser(description="Run Meridian's full-duplex local voice agent")
    parser.add_argument("--model", default=os.getenv("MERIDIAN_LIVE_MODEL", "gemini-3.1-flash-live-preview"))
    args = parser.parse_args()
    try:
        asyncio.run(run(args.model))
    except KeyboardInterrupt:
        sys.exit(0)
