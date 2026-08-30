# Synchus

An active operational-memory product built from the supplied Meridian Freight challenge data. Synchus combines files, spreadsheets, emails, interviews, worker messages and voice in one provenance-preserving context layer.

The agent is allowed to retrieve, reconcile, reason, log and stage changes. It is not allowed to silently turn a model output into canonical operational truth. Human approval is the promotion boundary.

## Run

The primary UI is the reactive TanStack client. It uses TanStack Router and Query, Zustand, shadcn-style primitives, inline Tailwind utilities, MapLibre and the shared FastAPI context service.

```bash
uv sync --extra live --extra telegram --extra web
uv run python api_server.py

# in another terminal
cd web
pnpm install
pnpm dev
```

Open `http://127.0.0.1:5173` for Synchus Live or `http://127.0.0.1:5173/app` for the operations workspace. TanStack Query listens to the API event stream, so new voice, Telegram, document, approval, and audit activity refreshes open workspaces without a page reload. The original Streamlit prototype remains available with `uv run streamlit run app.py --server.address 127.0.0.1`.

The first run builds `data/meridian.db` from `candidate_bundle/`. Services load local settings from `.env`; real values are ignored by Git. Copy `.env.example` if needed.

## Model choices

Text/document reasoning uses the first configured provider in this order:

1. `GEMINI_API_KEY` — hosted demo default (`gemini-3.6-flash`)
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

## Map and data coverage

Synchus uses an OpenStreetMap road base for the visible operational map so account-level CARTO tile watermarks never obscure route evidence. `CARTO_API_BASE_URL` and the CARTO access token stay server-side for future authenticated CARTO data layers; neither is sent to the browser.

The route workspace deliberately uses **static planning mode** when the supplied demo data has no live GPS, yard occupancy, live road/weather, or verified service-due feed. Historical trips and home hub assignments are useful for planning, but Synchus will not label them as live. Connect those sources (or upload a verified equivalent) to remove the relevant coverage gaps.

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

## Voice intake gate

Before staging a worker report, the voice agent must collect the minimum operational facts: reporter, event type, time, location, severity, worker confirmation, and entity reference where relevant. Vehicle issues also require a registration; route disruptions require an expected end time or an explicit `unknown`. The agent can answer first, ask follow-up questions, log incomplete information, or stage a complete report for approval — but it cannot silently promote it.

## Capability Lab

If a document introduces a useful fact that the current context model cannot represent, Synchus creates a **capability proposal** rather than changing code or the database directly. The proposal contains a bounded declarative schema, validation checks, expected surfaces, risk, source link and rollback plan. A human can approve, reject, or later roll back the extension; every action is written to the audit ledger.

## Stage demo kit and deck

`demo/` contains realistic, synthetic upload files and the timed stage runbook:

- `01_route_disruption_report.txt` — complete field report for the voice/approval story.
- `02_cold_chain_readings.csv` — a model-gap example for Capability Lab.
- `03_yard_snapshot.json` — point-in-time yard inventory (explicitly not live GPS).
- `04_client_gate_change.md` — client operating-window evidence.
- `DEMO_RUNBOOK.md` — exact 5-minute narration, interactions and voice lines.

The editable 1920×1080 pitch deck is `presentation/Synchus_Operational_Memory.pptx`. It is paired with locally generated and captured visual assets under `presentation/assets/`.

## Demo path

1. Open **Control room** and show the real data-quality alerts.
2. Open **Route**, select Delhi → Ludhiana, Vertex Retail and a winter date. Fleet filters, route evidence, truck glyphs and map update as one shared state.
3. Open **Ask** and try `RJ43DD3546 Orion ke liye eligible hai?`.
4. Open **Inbox**, record/type a bridge diversion or upload a document. The agent decides its disposition automatically and asks for missing facts before it stages a report.
5. Open **Approvals** and inspect the agent's confidence, reasoning, connections and source before promotion.
6. Return to `/` for the full-screen, audio-reactive live voice agent.

Stale trip records are labeled historical, fleet home assignments are never called parked/live locations, driver PII is not copied into the context database, and missing operational state remains `UNKNOWN` rather than becoming a false `PASS`.
