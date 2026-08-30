from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd
import pydeck as pdk
import streamlit as st

import meridian as m

st.set_page_config(page_title="Meridian Context", page_icon="◉", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--ink:#17201c;--paper:#f2efe6;--lime:#c8ff3d;--signal:#ff5c35;--blue:#2e64f5;--line:#d7d1c3}
.stApp{background:var(--paper);color:var(--ink);font-family:'Manrope',sans-serif}
[data-testid="stSidebar"]{background:#17201c;border-right:1px solid #344039}
[data-testid="stSidebar"] *{color:#f7f4ea!important}
[data-testid="stSidebar"] button{border-color:#58645e!important}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.04em}
h1{font-size:clamp(2.2rem,5vw,5.4rem)!important;line-height:.92!important;font-weight:800!important}
.eyebrow,.source,.stamp{font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:.08em;font-size:.72rem}
.hero{border-top:2px solid var(--ink);border-bottom:1px solid var(--line);padding:1.2rem 0 1.5rem;margin-bottom:1.5rem}
.hero p{font-size:clamp(1rem,1.4vw,1.22rem);max-width:760px;color:#4b554f}
.live-dot{display:inline-block;width:9px;height:9px;background:var(--lime);border-radius:50%;box-shadow:0 0 0 5px #c8ff3d22;margin-right:8px}
.metric-card{border-top:3px solid var(--ink);padding:12px 2px 14px}.metric-card .v{font-size:clamp(1.8rem,3vw,3rem);font-weight:800;letter-spacing:-.06em}.metric-card .k{font-family:'DM Mono',monospace;font-size:.72rem;color:#606963;text-transform:uppercase}
.signal{border-left:5px solid var(--signal);background:#fffaf0;padding:15px 18px;margin:.6rem 0}.signal.warning{border-color:#e7a817}.signal.info{border-color:var(--blue)}.signal b{font-size:1rem}.signal p{margin:.35rem 0 0;color:#56605a}.signal .source{margin-top:.55rem;color:#7f877f}
.answer{background:#17201c;color:#f7f4ea;padding:clamp(1.1rem,3vw,2rem);border-radius:2px;margin-top:1rem;box-shadow:10px 10px 0 var(--lime)}
.answer h3{font-size:clamp(1.3rem,2vw,2rem);margin:0 0 .8rem;color:white}.answer p{color:#d9dedb}.chip{display:inline-block;background:#303b35;color:#e7ece9;border:1px solid #526058;padding:4px 8px;margin:3px;font-family:'DM Mono';font-size:.68rem}
.rule{border-top:1px solid var(--line);padding:13px 0}.rule h4{margin:0 0 5px}.rule p{color:#59615c;margin:0}.critical{color:#c83a20}.unknown{background:#e8e3d7;border:1px dashed #938d81;padding:10px 12px;margin:.4rem 0;font-family:'DM Mono';font-size:.78rem}
div[data-testid="stMetric"]{background:transparent;border-top:3px solid var(--ink);padding-top:10px}
.stButton>button,.stDownloadButton>button{border-radius:0;font-weight:700;min-height:44px;border:1px solid var(--ink)}
.stButton>button[kind="primary"]{background:var(--ink);color:white}.stTextInput input,.stTextArea textarea,.stSelectbox>div>div{border-radius:0!important}
[data-testid="stWidgetLabel"] p{color:var(--ink)!important}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{color:#f7f4ea!important}
[data-testid="stTab"]{font-family:'DM Mono';text-transform:uppercase;letter-spacing:.04em}
[data-testid="stTab"] p{color:#5c645f!important;opacity:1!important}
[data-testid="stTab"][aria-selected="true"] p{color:var(--signal)!important}
@media(max-width:700px){.hero{padding-top:.7rem}.answer{box-shadow:6px 6px 0 var(--lime)}[data-testid="stSidebar"]{min-width:260px}}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def db():
    return m.ensure_db()


conn = db()
with st.sidebar:
    st.markdown("## ◉ MERIDIAN")
    st.caption("OPERATIONAL MEMORY / DEMO")
    st.markdown("<span class='live-dot'></span><span class='stamp'>Context online</span>", unsafe_allow_html=True)
    st.divider()
    language = st.radio("Interface language", ["English", "हिन्दी / Hinglish"], horizontal=False)
    st.info("Current positions are **unknown**. Map markers show home-hub assignments—not GPS.")
    if st.button("Rebuild context", width="stretch"):
        db.clear()
        m.rebuild().close()
        st.rerun()
    st.download_button("Download audit JSONL", m.export_audit(conn), "meridian-audit.jsonl", "application/jsonl", width="stretch")
    st.caption("No driver phone, Aadhaar or licence number is copied into the context database.")

st.markdown("<div class='hero'><div class='eyebrow'>Truth-preserving operations layer · 30 Aug 2026</div><h1>Ground truth,<br>ready for action.</h1><p>Files tell part of the story. People on the ground tell the rest. Meridian joins both—without hiding conflicts, guessing live state, or publishing a claim before a human approves it.</p></div>", unsafe_allow_html=True)

tabs = st.tabs(["CONTROL ROOM", "MAP", "ASK", "TEACH", "APPROVALS", "AUDIT"])

with tabs[0]:
    s = m.stats(conn)
    pipeline = m.run_pipeline(conn)
    cols = st.columns(5)
    for col, (value, label) in zip(cols, [(s["vehicles"], "canonical vehicles"), (s["trips"], "historical trips"), (s["drivers"], "PII-safe drivers"), (s["rules"], "approved rules"), (s["pending"], "awaiting approval")]):
        col.markdown(f"<div class='metric-card'><div class='v'>{value:,}</div><div class='k'>{label}</div></div>", unsafe_allow_html=True)
    st.caption(f"Pipeline ready · {pipeline['work_orders']} work orders · {pipeline['pending']} client drafts · {pipeline['quarantine']} quarantined · deterministic JSONL written to outputs/")
    st.markdown("### What needs attention")
    for item in m.data_quality(conn):
        st.markdown(f"<div class='signal {item['severity']}'><b>{item['title']}</b><p>{item['detail']}</p><div class='source'>SOURCE · {item['source']}</div></div>", unsafe_allow_html=True)
    st.markdown("### Rules that can stop a dispatch")
    rules = pd.read_sql_query("SELECT title,body,scope,severity,source_ref FROM rule ORDER BY severity,scope", conn)
    for _, r in rules.iterrows():
        st.markdown(f"<div class='rule'><div class='eyebrow {r.severity}'>{r.scope} · {r.severity}</div><h4>{r.title}</h4><p>{r.body}</p><div class='source'>↳ {r.source_ref}</div></div>", unsafe_allow_html=True)

with tabs[1]:
    st.markdown("### Fleet context map")
    st.caption("A map must communicate evidence quality. Circles are home assignments; no marker claims a live location.")
    c1, c2 = st.columns([1, 3])
    with c1:
        show_routes = st.toggle("Historical route hints", True)
        show_rules = st.toggle("Rule corridors", True)
        show_knowledge = st.toggle("Approved ground notes", True)
        st.markdown("**Legend**")
        st.markdown("🟢 Home-hub assignment  \n🟠 Rule corridor  \n🔵 Approved worker context  \n⚪ Unknown live position")
    hubs = m.hub_rows(conn)
    layers = [pdk.Layer("ScatterplotLayer", hubs, get_position="[lon, lat]", get_radius="4000 + vehicles * 550", get_fill_color="[200,255,61,185]", get_line_color="[23,32,28,255]", line_width_min_pixels=2, pickable=True)]
    if show_routes:
        arcs = []
        for origin, dest, client in conn.execute("SELECT origin_hub,destination,client FROM ticket WHERE valid=1 LIMIT 30"):
            if origin in m.HUBS and dest in m.HUBS:
                arcs.append({"source": [m.HUBS[origin][1], m.HUBS[origin][0]], "target": [m.HUBS[dest][1], m.HUBS[dest][0]], "client": client})
        layers.append(pdk.Layer("ArcLayer", arcs, get_source_position="source", get_target_position="target", get_source_color="[46,100,245,110]", get_target_color="[46,100,245,30]", get_width=2, pickable=True))
    if show_rules:
        delhi = m.HUBS["Delhi"]
        rule_arcs = [{"source": [m.HUBS[h][1], m.HUBS[h][0]], "target": [delhi[1], delhi[0]], "rule": "Oct–Feb: BS6 only"} for h in ("Jaipur", "Ludhiana", "Lucknow", "Rudrapur")]
        layers.append(pdk.Layer("ArcLayer", rule_arcs, get_source_position="source", get_target_position="target", get_source_color="[255,92,53,150]", get_target_color="[255,92,53,220]", get_width=5, pickable=True))
    if show_knowledge:
        notes = []
        for r in conn.execute("SELECT title,body,location FROM knowledge WHERE location IS NOT NULL"):
            if r["location"] in m.HUBS:
                lat, lon = m.HUBS[r["location"]]
                notes.append({"lat": lat + .04, "lon": lon + .04, "title": r["title"], "body": r["body"]})
        layers.append(pdk.Layer("ScatterplotLayer", notes, get_position="[lon,lat]", get_radius=4200, get_fill_color="[46,100,245,220]", pickable=True))
    deck = pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=28.7, longitude=78.2, zoom=5.1, pitch=22), map_style="light", tooltip={"html": "<b>{hub}{title}</b><br/>Vehicles assigned: {vehicles}<br/>{position_type}{body}{rule}{client}"})
    with c2:
        st.pydeck_chart(deck, width="stretch", height=620)

with tabs[2]:
    st.markdown("### Ask operations in your own language")
    st.caption("Try Hindi, Hinglish or English. Answers separate facts from unknown current state and cite their source.")
    examples = ["RJ43DD3546 Orion ke liye eligible hai?", "Shakti ka real SLA kitna hai?", "Breakdown origin se 40 km hai—replacement kahan se aaye?"]
    pick = st.selectbox("Quick scenario", ["Choose an example…", *examples])
    default_q = "" if pick.startswith("Choose") else pick
    q = st.text_input("Question", value=default_q, placeholder="e.g. Kya DL30AN8381 ko winter mein Delhi bhej sakte hain?")
    if st.button("Check context", type="primary", width="stretch") and q:
        a = m.answer(conn, q)
        citations = "".join(f"<span class='chip'>{x}</span>" for x in a["citations"]) or "<span class='chip'>NO DIRECT SOURCE</span>"
        st.markdown(f"<div class='answer'><div class='eyebrow'>ANSWER · GROUNDED</div><h3>{a['headline']}</h3><p>{a['detail']}</p><div>{citations}</div></div>", unsafe_allow_html=True)
        for u in a["unknowns"]:
            st.markdown(f"<div class='unknown'>UNKNOWN · {u}</div>", unsafe_allow_html=True)
        with st.expander("Retrieved evidence"):
            for hit in m.search(conn, q):
                st.markdown(f"**{hit['title']}**  \n{hit['body'][:500]}  \n`{hit['source_ref']}`")

with tabs[3]:
    st.markdown("### Teach the context layer")
    st.caption("Bolkar batao. The system drafts a claim; a human approver decides whether it becomes operational context.")
    left, right = st.columns([1.1, 1])
    with left:
        audio = st.audio_input("Record Hindi, Hinglish or English")
        transcript = ""
        if audio and st.button("Transcribe with Sarvam"):
            try:
                with st.spinner("Listening…"):
                    transcript = m.transcribe_sarvam(audio.getvalue(), audio.type)
                st.session_state["transcript"] = transcript
            except Exception as e:
                st.error(str(e))
        transcript = st.text_area("Transcript / typed fallback", value=st.session_state.get("transcript", ""), height=170, placeholder="Kal se Lucknow–Kanpur route par Unnao bridge ke paas diversion hai. 15 minute extra rakho.")
    with right:
        reporter = st.text_input("Reporter", placeholder="Name or role")
        location = st.selectbox("Location", ["", *m.HUBS.keys()])
        entity = st.text_input("Vehicle (optional)", placeholder="e.g. UP86CM7252")
        temporary = st.checkbox("This observation should expire", value=True)
        valid_until = st.date_input("Valid until", date.today() + timedelta(days=7), disabled=not temporary)
        if transcript:
            st.markdown(f"**Draft type:** `{m.classify(transcript)}`  \n**Detected language:** `{m.detect_language(transcript)}`")
        if st.button("Send for approval", type="primary", width="stretch", disabled=not transcript.strip()):
            pid = m.propose(conn, reporter, transcript, location, str(valid_until) if temporary else "", entity)
            st.success(f"{pid} is waiting for approval. Nothing was published automatically.")
            st.session_state["transcript"] = ""

with tabs[4]:
    st.markdown("### Human approval queue")
    st.markdown("#### Client communications")
    approved_comms = {r["ticket_id"] for r in conn.execute("SELECT ticket_id FROM comm_approval")}
    comms = [json.loads(line) for line in (m.OUTPUTS / "comms_pending.jsonl").read_text().splitlines() if line]
    unapproved = [draft for draft in comms if draft["ticket_id"] not in approved_comms]
    if unapproved:
        selected_ticket = st.selectbox("Draft to review", [d["ticket_id"] for d in unapproved])
        draft = next(d for d in unapproved if d["ticket_id"] == selected_ticket)
        with st.container(border=True):
            st.markdown(f"<div class='eyebrow'>{draft['message_id']} · TO {draft['recipient']}</div>", unsafe_allow_html=True)
            st.write(draft["body"])
            st.json(draft["context"], expanded=False)
            st.caption("Sources: " + " · ".join(draft["citations"]))
            approver = st.text_input("Communication approver", value="Operations lead")
            if st.button("Approve this client message", type="primary", width="stretch"):
                m.approve_communication(conn, selected_ticket, approver)
                st.rerun()
    else:
        st.success("All client drafts have been decided.")
    st.markdown("#### Worker knowledge")
    pending = list(conn.execute("SELECT * FROM proposal WHERE status='pending' ORDER BY created_at DESC"))
    if not pending:
        st.success("Queue clear. No unreviewed worker claims.")
    for r in pending:
        with st.container(border=True):
            st.markdown(f"<div class='eyebrow'>{r['id']} · {r['language']} · {r['created_at']}</div><h3>{r['kind'].title()}</h3>", unsafe_allow_html=True)
            if r["transcript"] != r["redacted_text"]:
                st.warning("PII was detected and redacted before publication.")
            st.write(r["redacted_text"])
            st.caption(f"Reporter: {r['reporter']} · Location: {r['location'] or 'not set'} · Vehicle: {r['entity_ref'] or 'not set'} · Expiry: {r['valid_until'] or 'durable'}")
            a, b = st.columns(2)
            if a.button("Approve into context", key="a" + r["id"], type="primary", width="stretch"):
                m.decide_proposal(conn, r["id"], True)
                st.rerun()
            if b.button("Reject", key="r" + r["id"], width="stretch"):
                m.decide_proposal(conn, r["id"], False)
                st.rerun()
    history = pd.read_sql_query("SELECT id,created_at,reporter,kind,language,status FROM proposal ORDER BY created_at DESC", conn)
    if not history.empty:
        st.markdown("#### Decision history")
        st.dataframe(history, hide_index=True, width="stretch")

with tabs[5]:
    st.markdown("### Provenance & audit")
    st.caption("Every source has a stable fingerprint. Every proposal and decision leaves an append-only event.")
    st.markdown("#### Source ledger")
    sources = pd.read_sql_query("SELECT kind,path,substr(fingerprint,1,16) AS sha256,ingested_at FROM source ORDER BY path", conn)
    st.dataframe(sources, hide_index=True, width="stretch")
    st.markdown("#### Decision ledger")
    audit = pd.read_sql_query("SELECT at,actor,action,object_type,object_id,details FROM audit_event ORDER BY at DESC", conn)
    st.dataframe(audit, hide_index=True, width="stretch")
    st.markdown("#### Quarantine")
    invalid = pd.read_sql_query("SELECT ticket_id,created_at,vehicle_reg,driver_id,issue,source_ref FROM ticket WHERE valid=0", conn)
    st.dataframe(invalid, hide_index=True, width="stretch")
