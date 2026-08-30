"""Browser voice-orb server: WebSocket audio bridge to Gemini Live with Synchus tools."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from pathlib import Path

import meridian as m
from live_agent import execute_tool, tool_declarations

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
except ImportError:  # Keep the base app importable without the optional live stack.
    FastAPI = WebSocket = WebSocketDisconnect = FileResponse = None

ROOT = Path(__file__).parent
LOGGER = logging.getLogger(__name__)


def create_app():
    if FastAPI is None:
        raise RuntimeError("Install live dependencies: uv sync --extra live")

    app = FastAPI(title="Synchus Live Voice")

    @app.get("/")
    async def index():
        return FileResponse(ROOT / "voice" / "index.html")

    @app.websocket("/ws")
    async def live_socket(websocket: WebSocket):
        await websocket.accept()
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            await websocket.send_json({"type": "error", "text": "GEMINI_API_KEY is not configured on the server."})
            await websocket.close(code=1011)
            return
        from google import genai
        from google.genai import types

        conn = m.ensure_db()
        model = os.getenv("MERIDIAN_LIVE_MODEL", "gemini-3.1-flash-live-preview")
        client = genai.Client(api_key=key)
        config = {
            "response_modalities": ["AUDIO"], "tools": tool_declarations(),
            "input_audio_transcription": {}, "output_audio_transcription": {},
            "realtime_input_config": {"automatic_activity_detection": {"disabled": False}},
            "system_instruction": (
                "You are Synchus, a concise live operational voice agent for Indian logistics workers. "
                "Match Hindi, Hinglish, or English. Use tools before operational claims. Be interruptible. "
                "Never call history or home assignment live state, and never call a vehicle dispatch-ready "
                "when availability or service state is unknown. Stage new worker information with stage_observation; "
                "canonical context always needs human approval."
            ),
        }
        try:
            async with client.aio.live.connect(model=model, config=config) as session:
                await websocket.send_json({"type": "ready", "model": model})

                async def upstream():
                    while True:
                        message = await websocket.receive()
                        if message.get("bytes"):
                            await session.send_realtime_input(audio=types.Blob(data=message["bytes"], mime_type="audio/pcm;rate=16000"))
                        elif message.get("text"):
                            await session.send_realtime_input(text=message["text"])

                async def downstream():
                    while True:
                        async for response in session.receive():
                            if response.data:
                                await websocket.send_json({"type": "audio", "data": base64.b64encode(response.data).decode()})
                            content = response.server_content
                            if content and content.input_transcription and content.input_transcription.text:
                                await websocket.send_json({"type": "user", "text": content.input_transcription.text})
                            if content and content.output_transcription and content.output_transcription.text:
                                await websocket.send_json({"type": "agent", "text": content.output_transcription.text})
                            if content and content.interrupted:
                                await websocket.send_json({"type": "interrupted"})
                            if response.tool_call:
                                function_responses = []
                                for call in response.tool_call.function_calls:
                                    try:
                                        result = execute_tool(conn, call.name, call.args or {})
                                    except Exception as exc:
                                        result = {"error": str(exc)}
                                    await websocket.send_json({"type": "tool", "name": call.name})
                                    function_responses.append(types.FunctionResponse(name=call.name, id=call.id, response={"result": result}))
                                await session.send_tool_response(function_responses=function_responses)

                tasks = [asyncio.create_task(upstream()), asyncio.create_task(downstream())]
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
                for task in pending:
                    task.cancel()
                for task in done:
                    task.result()
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            LOGGER.error("Voice model session failed (%s)", type(exc).__name__)
            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "text": "The voice model session could not be started. Check the voice server log.",
                    }
                )
            except Exception:
                pass

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("voice_server:app", host="127.0.0.1", port=8765, reload=False)
