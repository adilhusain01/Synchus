# Meridian architecture

## Product thesis

This is not a chatbot over a vector database. It is an active, evidence-preserving operational memory:

1. Company sources and frontline channels create immutable events.
2. An intake agent extracts typed claims and decides whether each deserves only a log, an answer, a staged context proposal, or urgent escalation.
3. A corroboration pass connects claims to existing sources and makes conflicts visible.
4. A human promotes approved proposals into reusable canonical context.
5. Route, Q&A, live voice and Telegram read through the same bounded context tools.

## Trust ladder

| Layer | Examples | May drive decisions? |
|---|---|---|
| Raw event | Telegram message, voice transcript, uploaded sheet | No; preserved evidence only |
| Agent proposal | Structured claim, expiry, entity, reasoning, connections | No; review queue only |
| Approved context | Human-approved rule or ground knowledge | Yes, subject to validity and source |
| Current state | GPS, yard scan, service system, weather/road feed | Only when a real connector exists |

The UI must never visually collapse these layers. A fleet-master home assignment cannot become a parked-truck count; a historical incident cannot become a current hazard; missing service state cannot become a dispatch `PASS`.

## Shared query surface

Hotelist's useful product pattern is the coupling of filters, ranked list, map and assistant around one query state. Meridian adapts it as:

- Filters: origin, destination, date, client, model year and BS stage.
- Ranked/list view: origin assignments with bounded rule checks.
- Map: route geometry, hubs, one glyph per home assignment, applicable precautions and projected historical incidents.
- Assistant: answers about the exact route selection and preserves explicit unknowns.

Hotelist also exposes cross-source consensus rather than treating one rating as unquestionable. Meridian's intake agent similarly labels new claims `single_source`, `corroborated`, or `conflict_present` and shows the connected evidence to the approver.

## Bounded agent tools

The live agent exposes only:

- `search_context(query)`
- `get_vehicle(registration)`
- `inspect_route(origin, destination, client, travel_on)`
- `stage_observation(text, reporter)`

There is intentionally no arbitrary SQL or direct `approve_context` tool. Model reasoning is flexible; authority is narrow.

## Channel strategy

- App inbox: richer documents and explicit review workflows.
- Telegram: low-friction text, voice notes and files for workers/drivers; polling for the demo, authenticated webhook and queue for production.
- Live voice orb: focused, interruptible speech-to-speech for a dispatcher or supervisor, with the same bounded tools.
- API/connectors later: TMS, ERP, maintenance, GPS/yard scan, weather and road restrictions.

## Demo versus production

The demo is SQLite + FTS5 because it is inspectable, portable and sufficient for the supplied dataset. Production should move canonical/event tables to Postgres, add object storage for originals, a job queue for ingestion, row-level access by role/region, encrypted identity mapping, retention policies, evaluation suites and an outbox for approved external actions.

Do not add a graph database until real multi-hop questions cannot be answered by typed relational edges. Do not add a vector database until FTS retrieval measurably fails. The schema and tool boundary are the context layer; a particular retrieval engine is replaceable.
