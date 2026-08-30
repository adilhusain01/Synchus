from __future__ import annotations

import html
import json
import os
from datetime import date

import pandas as pd
import pydeck as pdk
import streamlit as st

import agent
import meridian as m

st.set_page_config(page_title="Meridian Context", page_icon="◉", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--ink:#17201c;--paper:#f2efe6;--lime:#c8ff3d;--signal:#ff5c35;--blue:#2e64f5;--line:#d7d1c3}
.stApp{background:var(--paper);color:var(--ink);font-family:'Manrope',sans-serif}
[data-testid="stSidebar"]{background:#17201c;border-right:1px solid #344039}[data-testid="stSidebar"] *{color:#f7f4ea!important}[data-testid="stSidebar"] button{border-color:#58645e!important}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.04em}h1{font-size:clamp(2.2rem,5vw,5.4rem)!important;line-height:.92!important;font-weight:800!important}
.eyebrow,.source,.stamp{font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:.08em;font-size:.72rem}
.hero{border-top:2px solid var(--ink);border-bottom:1px solid var(--line);padding:1.2rem 0 1.5rem;margin-bottom:1.5rem}.hero p{font-size:clamp(1rem,1.4vw,1.22rem);max-width:780px;color:#4b554f}
.live-dot{display:inline-block;width:9px;height:9px;background:var(--lime);border-radius:50%;box-shadow:0 0 0 5px #c8ff3d22;margin-right:8px}
.metric-card{border-top:3px solid var(--ink);padding:12px 2px 14px}.metric-card .v{font-size:clamp(1.8rem,3vw,3rem);font-weight:800;letter-spacing:-.06em}.metric-card .k{font-family:'DM Mono',monospace;font-size:.72rem;color:#606963;text-transform:uppercase}
.signal{border-left:5px solid var(--signal);background:#fffaf0;padding:15px 18px;margin:.6rem 0}.signal.warning{border-color:#e7a817}.signal.info{border-color:var(--blue)}.signal b{font-size:1rem}.signal p{margin:.35rem 0 0;color:#56605a}.signal .source{margin-top:.55rem;color:#7f877f}
.answer{background:#17201c;color:#f7f4ea;padding:clamp(1.1rem,3vw,2rem);border-radius:2px;margin-top:1rem;box-shadow:10px 10px 0 var(--lime)}.answer h3{font-size:clamp(1.3rem,2vw,2rem);margin:0 0 .8rem;color:white}.answer p{color:#d9dedb}
.chip{display:inline-block;background:#303b35;color:#e7ece9;border:1px solid #526058;padding:4px 8px;margin:3px;font-family:'DM Mono';font-size:.68rem}.rule{border-top:1px solid var(--line);padding:13px 0}.rule h4{margin:0 0 5px}.rule p{color:#59615c;margin:0}.critical{color:#c83a20}.unknown{background:#e8e3d7;border:1px dashed #938d81;padding:10px 12px;margin:.4rem 0;font-family:'DM Mono';font-size:.78rem}
.orb-stage{min-height:430px;background:#050706;display:grid;place-items:center;position:relative;overflow:hidden;border:1px solid #283029}.orb{width:min(42vw,300px);aspect-ratio:1;border-radius:50%;position:relative;background:radial-gradient(circle at 38% 34%,#f4fbff 0 8%,#c9d4ff 24%,#7793ff 51%,#4052bc 74%,#17224f 100%);box-shadow:0 0 90px #7898ff55,inset -32px -28px 70px #101b5b88;animation:breathe 3.8s ease-in-out infinite}.orb:before,.orb:after{content:"";position:absolute;border-radius:48%;filter:blur(18px);mix-blend-mode:screen;animation:drift 7s ease-in-out infinite alternate}.orb:before{inset:13% 6% 45% 9%;background:#ffffff99;transform:rotate(-12deg)}.orb:after{inset:50% 12% 12% 38%;background:#788fff99;animation-delay:-2.5s}.orb-label{position:absolute;bottom:24px;color:#b9c3bd;font-family:'DM Mono';font-size:.75rem;letter-spacing:.12em;text-transform:uppercase}
@keyframes breathe{0%,100%{transform:scale(.97);filter:saturate(.9)}50%{transform:scale(1.025);filter:saturate(1.2)}}@keyframes drift{to{transform:translate(20px,28px) rotate(26deg) scale(1.15)}}@media(prefers-reduced-motion:reduce){.orb,.orb:before,.orb:after{animation:none}}
div[data-testid="stMetric"]{background:transparent;border-top:3px solid var(--ink);padding-top:10px}.stButton>button,.stDownloadButton>button{border-radius:0;font-weight:700;min-height:44px;border:1px solid var(--ink)}.stButton>button[kind="primary"]{background:var(--ink);color:white}.stTextInput input,.stTextArea textarea,.stSelectbox>div>div{border-radius:0!important}
[data-testid="stWidgetLabel"] p{color:var(--ink)!important}[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{color:#f7f4ea!important}[data-testid="stTab"]{font-family:'DM Mono';text-transform:uppercase;letter-spacing:.04em}[data-testid="stTab"] p{color:#5c645f!important;opacity:1!important}[data-testid="stTab"][aria-selected="true"] p{color:var(--signal)!important}
@media(max-width:700px){.hero{padding-top:.7rem}.answer{box-shadow:6px 6px 0 var(--lime)}[data-testid="stSidebar"]{min-width:260px}.orb-stage{min-height:360px}.orb{width:230px}}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def db():
    return m.ensure_db()


conn = db()
agent.scan_inbox(conn)
provider = agent.provider_status()

with st.sidebar:
    st.markdown("## ◉ MERIDIAN")
    st.caption("OPERATIONAL MEMORY / DEMO")
    st.markdown("<span class='live-dot'></span><span class='stamp'>Context online</span>", unsafe_allow_html=True)
    st.caption(f"Reasoning: {provider['provider']} · {provider['model']}")
    st.divider()
    st.info("No live GPS or yard feed is connected. Truck glyphs show fleet-master **home assignments**, never current parked positions.")
    if st.button("Rebuild supplied context", width="stretch"):
        db.clear(); m.rebuild().close(); st.rerun()
    st.download_button("Download audit JSONL", m.export_audit(conn), "meridian-audit.jsonl", "application/jsonl", width="stretch")
    st.caption("Driver phones, Aadhaar and licence numbers are excluded or redacted.")

st.markdown("<div class='hero'><div class='eyebrow'>Active operational intelligence · 30 Aug 2026</div><h1>Ground truth,<br>ready for action.</h1><p>Files, spreadsheets, workers and agents meet in one reusable context layer. Meridian reasons across them, preserves the raw event, stages useful claims, surfaces conflicts and asks a human before changing canonical truth.</p></div>", unsafe_allow_html=True)

tabs = st.tabs(["CONTROL ROOM", "ROUTE", "ASK", "INBOX", "LIVE", "APPROVALS", "AUDIT"])

with tabs[0]:
    s = m.stats(conn); pipeline = m.run_pipeline(conn)
    cols = st.columns(5)
    for col, (value, label) in zip(cols, [(s["vehicles"], "canonical vehicles"), (s["trips"], "historical trips"), (s["drivers"], "PII-safe drivers"), (s["rules"], "approved rules"), (s["pending"], "awaiting approval")]):
        col.markdown(f"<div class='metric-card'><div class='v'>{value:,}</div><div class='k'>{label}</div></div>", unsafe_allow_html=True)
    st.caption(f"Pipeline ready · {pipeline['work_orders']} work orders · {pipeline['pending']} client drafts · {pipeline['quarantine']} quarantined · deterministic outputs preserved")
    st.markdown("### What needs attention")
    for item in m.data_quality(conn):
        st.markdown(f"<div class='signal {item['severity']}'><b>{item['title']}</b><p>{item['detail']}</p><div class='source'>SOURCE · {item['source']}</div></div>", unsafe_allow_html=True)
    st.markdown("### Rules that can stop a dispatch")
    for _, r in pd.read_sql_query("SELECT title,body,scope,severity,source_ref FROM rule ORDER BY severity,scope", conn).iterrows():
        st.markdown(f"<div class='rule'><div class='eyebrow {r.severity}'>{r.scope} · {r.severity}</div><h4>{r.title}</h4><p>{r.body}</p><div class='source'>↳ {r.source_ref}</div></div>", unsafe_allow_html=True)

with tabs[1]:
    st.markdown("### Route intelligence")
    st.caption("Hotelist-inspired shared state: route selectors and fleet filters update the evidence list and map together; the assistant reasons over the same selection.")
    a, b, c, d = st.columns(4)
    origin = a.selectbox("Origin", list(m.HUBS), index=list(m.HUBS).index("Delhi"))
    destinations = [x for x in m.PLACES if x != origin]
    destination = b.selectbox("Destination", destinations, index=destinations.index("Ludhiana") if "Ludhiana" in destinations else 0)
    client = c.selectbox("Client", ["Internal", "Shakti Cement", "Vertex Retail", "Apex Chemicals", "Orion Pharma"])
    travel_on = d.date_input("Travel date", date.today())
    e, f, g = st.columns(3)
    min_year = e.slider("Minimum model year shown", 2014, 2026, 2014)
    bs_filter = f.selectbox("BS stage shown", ["All", "BS6", "BS4", "BS3"])
    show_incidents = g.toggle("Historical incidents", True)
    with st.spinner("Compiling route evidence…"):
        route = m.route_intelligence(conn, origin, destination, client, travel_on)
    filtered_candidates = [v for v in route["candidates"] if v["year"] >= min_year and (bs_filter == "All" or v["bs_stage"] == bs_filter)]
    filtered_trucks = [v for v in m.truck_rows(conn) if v["year"] >= min_year and (bs_filter == "All" or v["bs_stage"] == bs_filter)]
    if route["is_approximate"]:
        st.warning("OSRM was unavailable, so the line is an approximate endpoint connection—not a road route.")

    listing, map_col, assistant_col = st.columns([1.05, 1.65, .95], gap="small")
    with listing:
        st.markdown(f"#### {len(filtered_candidates)} origin assignments")
        st.caption("Conditional static screening—not current availability")
        if filtered_candidates:
            for candidate in filtered_candidates:
                with st.expander(f"{candidate['assessment']} · {candidate['registration']} · {candidate['year']} {candidate['bs_stage']}"):
                    st.write(candidate["model"])
                    st.write("\n".join(f"- {check}" for check in candidate["checks"]))
        else:
            st.info("No origin assignments match these filters.")
        st.markdown("#### Route evidence")
        for p in route["precautions"]:
            st.markdown(f"**{p['status']} · {p['title']}**  \n{p['why_now']}  \n`{p['source_ref']}`")
    with map_col:
        hubs = m.hub_rows(conn)
        route_row = [{"path": route["path"], "label": f"{origin} → {destination}", "source": route["geometry_source"]}]
        layers = [
            pdk.Layer("PathLayer", route_row, get_path="path", get_color="[255,92,53,235]", get_width=6, width_min_pixels=4, pickable=True),
            pdk.Layer("ScatterplotLayer", hubs, get_position="[lon,lat]", get_radius=4500, get_fill_color="[200,255,61,190]", get_line_color="[23,32,28,255]", line_width_min_pixels=2, pickable=True),
            pdk.Layer("TextLayer", filtered_trucks, get_position="[lon,lat]", get_text="glyph", get_size=20, size_min_pixels=13, size_max_pixels=24, get_color="[23,32,28,255]", pickable=True),
            pdk.Layer("ScatterplotLayer", route["precautions"], get_position="[lon,lat]", get_radius=4200, get_fill_color="[255,184,46,220]", get_line_color="[23,32,28,255]", line_width_min_pixels=1, pickable=True),
        ]
        if show_incidents:
            layers.append(pdk.Layer("ScatterplotLayer", route["incidents"], get_position="[lon,lat]", get_radius=4800, get_fill_color="[46,100,245,220]", get_line_color="[255,255,255,255]", line_width_min_pixels=2, pickable=True))
        span = max(abs(m.PLACES[origin][0] - m.PLACES[destination][0]), abs(m.PLACES[origin][1] - m.PLACES[destination][1]))
        zoom = 6.4 if span < 2 else 5.4 if span < 5 else 4.5
        deck = pdk.Deck(layers=layers, map_style="light", initial_view_state=pdk.ViewState(latitude=(m.PLACES[origin][0] + m.PLACES[destination][0]) / 2, longitude=(m.PLACES[origin][1] + m.PLACES[destination][1]) / 2, zoom=zoom, pitch=16), tooltip={"html": "<b>{hub}{registration}{title}{ticket_id}{label}</b><br/>{vehicles} fleet assignments<br/>{evidence}{body}{issue}{why_now}<br/><small>{source_ref}{source}</small>"})
        st.pydeck_chart(deck, width="stretch", height=650)
        st.caption("🟧 route · 🟡 precaution · 🔵 historical incident · 🟢 hub · 🚚 home assignment")
    with assistant_col:
        st.markdown("#### Route assistant")
        st.metric("Distance", f"{route['distance_km']:,.0f} km", route["geometry_source"])
        st.metric("Precautions", len(route["precautions"]))
        st.metric("Parked now", "Unknown", "yard feed not connected")
        route_question = st.text_area("Ask about this selection", placeholder="What are the biggest risks, and which assigned trucks survive static checks?", height=120)
        if st.button("Ask route agent", type="primary", width="stretch", disabled=not route_question.strip()):
            full_question = f"For {origin} to {destination} on {travel_on}, client {client}: {route_question}"
            result = agent.ask(conn, full_question)
            st.markdown(f"**{result['headline']}**")
            st.write(result["detail"])
            for unknown in result["unknowns"]:
                st.warning("Unknown: " + unknown)
        with st.expander("Unknowns that block certainty", expanded=True):
            st.write("\n".join(f"- {u}" for u in route["unknowns"]))

with tabs[2]:
    st.markdown("### Ask the operational agent")
    st.caption("The agent retrieves bounded evidence, reconciles conflicts, reasons, and responds in the asker's Hindi, Hinglish or English.")
    examples = ["RJ43DD3546 Orion ke liye eligible hai?", "Shakti ka real SLA kitna hai?", "Breakdown origin se 40 km hai—replacement kahan se aaye?"]
    pick = st.selectbox("Quick scenario", ["Choose an example…", *examples])
    q = st.text_input("Question", value="" if pick.startswith("Choose") else pick, placeholder="e.g. Kya DL30AN8381 ko winter mein Delhi bhej sakte hain?")
    if st.button("Reason over context", type="primary", width="stretch", disabled=not q.strip()):
        with st.spinner("Retrieving → reconciling → answering…"):
            result = agent.ask(conn, q)
        citations = "".join(f"<span class='chip'>{html.escape(str(x))}</span>" for x in result["citations"]) or "<span class='chip'>NO DIRECT SOURCE</span>"
        st.markdown(f"<div class='answer'><div class='eyebrow'>ANSWER · {html.escape(result['provider']['provider'])}</div><h3>{html.escape(result['headline'])}</h3><p>{html.escape(result['detail'])}</p><div>{citations}</div></div>", unsafe_allow_html=True)
        for extra in result.get("extras", []): st.info(extra)
        for unknown in result["unknowns"]: st.markdown(f"<div class='unknown'>UNKNOWN · {html.escape(str(unknown))}</div>", unsafe_allow_html=True)
        st.caption("Agent trace: " + " → ".join(result["trace"]))
        with st.expander("Retrieved evidence"):
            for hit in m.search(conn, q): st.markdown(f"**{hit['title']}**  \n{hit['body'][:500]}  \n`{hit['source_ref']}`")

with tabs[3]:
    st.markdown("### Autonomous intake")
    st.caption("Every input is preserved as an event. The agent decides whether to answer, log only, stage reusable context, or escalate—and records why.")
    uploaded = st.file_uploader("Drop company documents", type=["txt", "md", "csv", "tsv", "json", "xlsx", "pdf", "docx"], accept_multiple_files=True)
    for file in uploaded:
        try:
            result = agent.ingest_upload(conn, file.name, file.getvalue(), file.type or "", actor="App uploader")
            st.caption(f"{file.name} · {'already processed' if result.get('duplicate') else f'{len(result['proposal_ids'])} proposal(s) staged'}")
        except Exception as exc: st.error(f"{file.name}: {exc}")
    left, right = st.columns(2)
    with left:
        audio = st.audio_input("Leave a voice note (Hindi / Hinglish / English)")
        if audio and st.button("Interpret voice note", type="primary", width="stretch"):
            try:
                transcript = agent.transcribe_audio(audio.getvalue(), audio.type); st.session_state["worker_transcript"] = transcript
                result = agent.ingest_text(conn, transcript, actor="App worker", channel="voice_note", source_ref="app voice note")
                st.success(f"Agent decision: {', '.join(result['dispositions'])} · {len(result['proposal_ids'])} staged")
            except Exception as exc: st.error(str(exc))
    with right:
        note = st.text_area("Typed ground update", value=st.session_state.get("worker_transcript", ""), height=150, placeholder="Kal se Lucknow–Kanpur route par Unnao bridge ke paas diversion hai…")
        reporter = st.text_input("Reporter / role", placeholder="Driver 17 or Lucknow dispatcher")
        if st.button("Let agent triage this update", type="primary", width="stretch", disabled=not note.strip()):
            result = agent.ingest_text(conn, note, actor=reporter or "App worker", channel="app_text", source_ref="app worker update")
            st.success(f"Decision: {', '.join(result['dispositions'])}. Staged: {len(result['proposal_ids'])}. Run: {result['run_id']}")
    st.info("Watched folder: place supported files in `inbox/`; fingerprints prevent duplicate processing on future app reruns.")

with tabs[4]:
    st.markdown("### Live voice + worker channels")
    live_ready = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    st.markdown(f"<div class='orb-stage'><div class='orb'></div><div class='orb-label'>{'ready · gemini live' if live_ready else 'model key required'}</div></div>", unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        st.markdown("#### Real-time conversation")
        st.write("Persistent speech-to-speech with interruption, live transcription and bounded context tools. This is not record-then-transcribe.")
        st.code("uv sync --extra live\nexport GEMINI_API_KEY='…'\nuv run python live_agent.py", language="bash")
        st.caption("Free hosted demo: Gemini Live. Optional transport: LiveKit/Pipecat. Fully local experiment: Moshi/MLX on capable Apple Silicon; hardware-heavy, so not the default.")
    with b:
        st.markdown("#### Telegram field gateway")
        st.write("Workers send text, voice notes or documents. The same agent answers, logs, stages reusable context, and flags urgent safety updates.")
        st.code("uv sync --extra telegram\nexport TELEGRAM_BOT_TOKEN='…'\nexport TELEGRAM_ALLOWED_USER_IDS='123,456'\nuv run python telegram_bot.py", language="bash")
        st.caption("Configured" if os.getenv("TELEGRAM_BOT_TOKEN") else "Not configured · add a BotFather token and explicit user allowlist")
    st.warning("Telegram is a field channel, not the system of record. Restrict users, redact PII, minimize retention of raw voice, and store only the operational data you need.")

with tabs[5]:
    st.markdown("### Human approval queue")
    st.markdown("#### Client communications")
    approved_comms = {r["ticket_id"] for r in conn.execute("SELECT ticket_id FROM comm_approval")}
    comms = [json.loads(line) for line in (m.OUTPUTS / "comms_pending.jsonl").read_text().splitlines() if line]
    unapproved = [draft for draft in comms if draft["ticket_id"] not in approved_comms]
    if unapproved:
        selected_ticket = st.selectbox("Draft to review", [d["ticket_id"] for d in unapproved]); draft = next(d for d in unapproved if d["ticket_id"] == selected_ticket)
        with st.container(border=True):
            st.markdown(f"<div class='eyebrow'>{draft['message_id']} · TO {draft['recipient']}</div>", unsafe_allow_html=True); st.write(draft["body"]); st.json(draft["context"], expanded=False); st.caption("Sources: " + " · ".join(draft["citations"]))
            approver = st.text_input("Communication approver", value="Operations lead")
            if st.button("Approve this client message", type="primary", width="stretch"): m.approve_communication(conn, selected_ticket, approver); st.rerun()
    else: st.success("All client drafts have been decided.")
    st.markdown("#### Agent-staged context")
    pending = list(conn.execute("SELECT * FROM proposal WHERE status='pending' ORDER BY risk='critical' DESC,created_at DESC"))
    if not pending: st.success("Queue clear. No unreviewed claims.")
    for r in pending:
        with st.container(border=True):
            st.markdown(f"<div class='eyebrow'>{r['id']} · {r['risk']} risk · {r['confidence']:.0%} confidence</div><h3>{html.escape(r['kind'].title())}</h3>", unsafe_allow_html=True); st.write(r["redacted_text"])
            st.caption(f"Agent: {r['agent_name']} · Reporter: {r['reporter']} · Location: {r['location'] or 'not inferred'} · Vehicle: {r['entity_ref'] or 'not inferred'} · Expiry: {r['valid_until'] or 'durable/unknown'}")
            if r["reasoning"]: st.info("Why staged: " + r["reasoning"])
            connections = json.loads(r["connections_json"] or "[]")
            if connections: st.caption("Connections: " + " · ".join(connections))
            x, y = st.columns(2)
            if x.button("Approve into context", key="a" + r["id"], type="primary", width="stretch"): m.decide_proposal(conn, r["id"], True); st.rerun()
            if y.button("Reject", key="r" + r["id"], width="stretch"): m.decide_proposal(conn, r["id"], False); st.rerun()

with tabs[6]:
    st.markdown("### Provenance, events & agent trace")
    st.caption("Raw inputs remain events; proposed facts, human decisions and model/tool runs stay separable and inspectable.")
    st.markdown("#### Agent runs"); st.dataframe(pd.read_sql_query("SELECT started_at,provider,task,source_ref,status,trace_json FROM agent_run ORDER BY started_at DESC LIMIT 100", conn), hide_index=True, width="stretch")
    st.markdown("#### Intake event log"); st.dataframe(pd.read_sql_query("SELECT at,channel,actor_ref,event_type,disposition,reasoning,source_ref FROM context_event ORDER BY at DESC LIMIT 200", conn), hide_index=True, width="stretch")
    st.markdown("#### Source ledger"); st.dataframe(pd.read_sql_query("SELECT kind,path,substr(fingerprint,1,16) AS sha256,ingested_at FROM source ORDER BY path", conn), hide_index=True, width="stretch")
    st.markdown("#### Decision ledger"); st.dataframe(pd.read_sql_query("SELECT at,actor,action,object_type,object_id,details FROM audit_event ORDER BY at DESC", conn), hide_index=True, width="stretch")
    st.markdown("#### Quarantine"); st.dataframe(pd.read_sql_query("SELECT ticket_id,created_at,vehicle_reg,driver_id,issue,source_ref FROM ticket WHERE valid=0", conn), hide_index=True, width="stretch")
