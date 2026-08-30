# Meridian Context

An active operational-memory demo built from the supplied Meridian Freight challenge data. It combines files, spreadsheets, emails, interviews, worker messages and voice into one provenance-preserving SQLite context layer.

The agent is allowed to retrieve, reconcile, reason, log and stage changes. It is not allowed to silently turn a model output into canonical operational truth. Human approval is the promotion boundary.

## Run

```bash
uv sync
uv run streamlit run app.py --server.address 127.0.0.1
```

The first run builds `data/meridian.db` from `candidate_bundle/`. The app loads local settings from `.env`; real values are ignored by Git. Copy `.env.example` if needed.

## Model choices

Text/document reasoning uses the first configured provider in this order:

1. `GEMINI_API_KEY` — hosted free-tier demo default (`gemini-2.5-flash`)
2. `GROQ_API_KEY` — fast hosted OSS model default (`openai/gpt-oss-20b`)
3. `OPENAI_API_KEY`
4. No key — deterministic, auditable rules fallback

Override the text model with `MERIDIAN_MODEL`. Sarvam handles submitted voice notes when only `SARVAM_API_KEY` is present:

```bash
cp .env.example .env
# add SARVAM_API_KEY locally
uv run streamlit run app.py --server.address 127.0.0.1
```

No key is printed by the app. Without a speech key, typed Hindi, Hinglish and English still exercise the entire intake/approval flow.

## True live voice

`voice_server.py` serves the animated browser orb backed by a persistent, full-duplex Gemini Live session: 16 kHz microphone input, 24 kHz audio output, server voice-activity detection, interruption, live transcripts and bounded context/database tools. The API key remains on the server.

```bash
uv sync --extra live
# add GEMINI_API_KEY to .env
uv run python voice_server.py
# open http://127.0.0.1:8765
```

Use `uv run python live_agent.py` for the terminal microphone client. Both paths are distinct from record-then-transcribe. The optional architecture boundary is compatible with LiveKit or Pipecat; Moshi/MLX is the fully local experiment for capable Apple Silicon, but is deliberately not a default dependency.

## Telegram worker gateway

The bot accepts text, voice notes and supported documents. Every input becomes an immutable, redacted event. The intake agent chooses `answer`, `log_only`, `stage_context`, or `urgent_escalation`; canonical context still needs an approver.

```bash
uv sync --extra telegram
# add TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_IDS=123,456 to .env
uv run python telegram_bot.py
```

Polling is the zero-infrastructure demo mode. Production should use a secret-token webhook, explicit identity mapping, retention limits and a queue. Telegram is a field channel, not the system of record.

## Autonomous file intake

Upload `.txt`, `.md`, `.csv`, `.tsv`, `.json`, `.xlsx`, `.pdf` or `.docx` in the app, or place one in `inbox/`. On the next rerun the agent extracts it, treats document content as untrusted data, finds useful claims/connections/conflicts, logs its decisions and stages proposals. SHA-256 fingerprints prevent duplicate processing.

Run the standardized deterministic pipeline without the UI:

```bash
uv run python meridian.py pipeline
uv run python meridian.py pipeline --tickets candidate_bundle/tickets.json path/to/surprise_tickets.json
```

It writes `outputs/work_orders.jsonl`, `outputs/comms_pending.jsonl`, `outputs/comms_sent.jsonl`, `outputs/quarantine.jsonl`, and `audit/audit.jsonl`. Re-running the same inputs produces byte-identical files. Approved communications retain their first persisted `sent_at` timestamp.

## Demo path

1. Open **Control room** and show the real data-quality alerts.
2. Open **Route**, select Delhi → Ludhiana, Vertex Retail and a winter date. Fleet filters, route evidence, truck glyphs and map update as one shared state.
3. Open **Ask** and try `RJ43DD3546 Orion ke liye eligible hai?`.
4. Open **Inbox**, record/type a bridge diversion or upload a document. The agent decides its disposition automatically.
5. Open **Approvals** and inspect the agent's confidence, reasoning, connections and source before promotion.
6. Open **Live** for the voice-orb, realtime-agent and Telegram launch paths.

Stale trip records are labeled historical, fleet home assignments are never called parked/live locations, driver PII is not copied into the context database, and missing operational state remains `UNKNOWN` rather than becoming a false `PASS`.
