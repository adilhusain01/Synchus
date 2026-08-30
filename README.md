# Meridian Context

An approval-gated operational memory demo built from the supplied Meridian Freight challenge data. It combines files, spreadsheets, emails, interviews and frontline voice notes into one provenance-preserving SQLite context layer.

## Run

```bash
uv sync
uv run streamlit run app.py --server.address 127.0.0.1
```

The first run builds `data/meridian.db` from `candidate_bundle/`. Delete that database or use **Rebuild context** in the sidebar after changing source files.

Optional speech-to-text:

```bash
export SARVAM_API_KEY="..."
uv run streamlit run app.py --server.address 127.0.0.1
```

Sarvam is only called after an audio recording is submitted. Without a key, the Teach screen still accepts a typed Hindi, Hinglish or English transcript so the full approval workflow remains demoable.

Run the standardized deterministic pipeline without the UI:

```bash
uv run python meridian.py pipeline
uv run python meridian.py pipeline --tickets candidate_bundle/tickets.json path/to/surprise_tickets.json
```

It writes `outputs/work_orders.jsonl`, `outputs/comms_pending.jsonl`, `outputs/comms_sent.jsonl`, `outputs/quarantine.jsonl`, and `audit/audit.jsonl`. Re-running the same inputs produces byte-identical files. Approved communications retain their first persisted `sent_at` timestamp.

## Demo path

1. Open **Control room** and show the real data-quality alerts.
2. Open **Ask** and try `RJ43DD3546 Orion ke liye eligible hai?`.
3. Open **Teach**, record or type a ground observation, then submit it.
4. Open **Approvals**, compare the proposal with its source and approve it.
5. Return to **Map** and toggle the approved-knowledge layer.

No outbound action is automatic. Stale trip records are labeled historical, driver PII is not copied into the context database, and unknown operational state remains unknown.
