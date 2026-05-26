"""
Multi-Agent Trip Planner — Streamlit Web Application
Run: streamlit run app.py
"""
import os
import sys
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Multi-Agent AI Trip Planner",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main-title {
    background: linear-gradient(135deg, #1A6B3C, #2C3E50);
    color: white; padding: 20px; border-radius: 10px;
    text-align: center; margin-bottom: 20px;
}
.agent-card {
    background: #f8f9fa; border-left: 4px solid #1A6B3C;
    padding: 10px 15px; margin: 5px 0; border-radius: 4px;
    font-size: 0.9em;
}
.orch-card {
    background: #fff8e1; border-left: 4px solid #F5A623;
    padding: 10px 15px; margin: 5px 0; border-radius: 4px;
    font-size: 0.9em; font-weight: bold;
}
.guardrail-card {
    background: #f0f4ff; border-left: 4px solid #3b5bdb;
    padding: 10px 15px; margin: 5px 0; border-radius: 4px;
    font-size: 0.85em; color: #364fc7;
}
.eval-pass {
    background: #e8f5e9; border-left: 4px solid #2e7d32;
    padding: 8px 14px; margin: 4px 0; border-radius: 4px; font-size: 0.88em;
}
.eval-fail {
    background: #fff3e0; border-left: 4px solid #e65100;
    padding: 8px 14px; margin: 4px 0; border-radius: 4px; font-size: 0.88em;
}
.query-box {
    background: #f9f9f9; border: 1px solid #ddd;
    border-radius: 10px; padding: 16px; margin-bottom: 16px;
}
.security-block {
    background: #ffebee; border: 2px solid #c62828;
    border-radius: 8px; padding: 16px; margin: 10px 0;
}
.success-box {
    background: #e8f5e9; border: 2px solid #1A6B3C;
    padding: 15px; border-radius: 8px; text-align: center;
}
.metric-card {
    background: white; border: 1px solid #e0e0e0;
    padding: 15px; border-radius: 8px; text-align: center;
}
.langsmith-card {
    background: #f3f0ff; border-left: 4px solid #7950f2;
    padding: 10px 15px; margin: 5px 0; border-radius: 4px;
    font-size: 0.85em; color: #5f3dc4;
}
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown("""
    <div class="main-title">
        <h1>✈ Multi-Agent AI Trip Planner</h1>
        <p>Powered by LangGraph &nbsp;|&nbsp; 10 Specialized Agents &nbsp;|&nbsp; Guardrails &nbsp;|&nbsp; RAG Memory</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar — structured settings ────────────────────────────
    with st.sidebar:
        st.header("Trip Settings")
        source       = st.text_input("Source City", value="Bangalore")
        destination  = st.text_input("Destination City", value="Goa")

        c1, c2 = st.columns(2)
        num_days      = c1.number_input("Days",      min_value=1,  max_value=30,     value=5)
        num_travelers = c2.number_input("Travelers", min_value=1,  max_value=20,     value=2)

        travel_dates   = st.text_input("Travel Dates", value="June 10 to June 15, 2025")
        budget         = st.number_input("Total Budget (₹)", min_value=5000,
                                          max_value=500000, value=30000, step=1000)
        trip_type      = st.selectbox("Trip Type", ["couple", "solo", "family", "business"])
        transport_pref = st.selectbox("Transport", ["flight", "train", "car", "bus", "any"])
        hotel_pref     = st.selectbox("Hotel", ["3-star", "4-star", "5-star", "budget",
                                                 "beach resort", "luxury", "heritage"])
        food_pref      = st.selectbox("Food", ["any", "veg", "non-veg", "seafood", "vegan"])
        places_interest = st.multiselect(
            "Interests",
            ["Beach", "Heritage", "Nature", "Adventure", "Shopping",
             "Nightlife", "Religious", "Museum", "Scenic"],
            default=["Beach", "Nightlife"]
        )
        luxury_budget  = st.select_slider("Style",
                                           options=["budget", "mid-range", "luxury"],
                                           value="mid-range")
        special_req    = st.text_area("Special Requirements", placeholder="Any special needs...")
        user_id        = st.text_input("User ID (for memory)", value="user_001")

        st.markdown("---")
        # LangSmith tracing status
        from monitoring.langsmith_setup import is_tracing_enabled, get_project_url
        if is_tracing_enabled():
            st.markdown(
                f'<div class="langsmith-card">🔭 <b>LangSmith tracing ON</b><br>'
                f'<a href="{get_project_url()}" target="_blank">Open project dashboard →</a></div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("LangSmith tracing off — add LANGCHAIN_API_KEY to .env to enable.")

        st.markdown("---")
        _server_key = os.environ.get("OPENAI_API_KEY", "")
        if _server_key:
            st.success("Server API key is configured.", icon="🔑")
        openai_key = st.text_input(
            "OpenAI API Key" + (" (optional override)" if _server_key else " (required)"),
            type="password",
            value="",
            placeholder="sk-proj-... paste to use your own key",
            help=(
                "Leave blank to use the server-configured key."
                if _server_key else
                "Required — get yours at platform.openai.com"
            ),
        )

    # ── Main area — query prompt ──────────────────────────────────
    st.markdown("### Describe your trip")
    st.caption("Type a natural language query, or let it auto-fill from the sidebar settings.")

    auto_query = (
        f"Plan a {num_days}-day {destination} trip from {source} for "
        f"{'a ' if num_travelers == 2 and trip_type == 'couple' else str(num_travelers) + ' '}"
        f"{trip_type}. Travel dates: {travel_dates}. Budget: ₹{budget:,}. "
        f"Transport: {transport_pref}. Hotel: {hotel_pref}. Food: {food_pref}. "
        f"Interested in: {', '.join(places_interest) if places_interest else 'general sightseeing'}. "
        f"{luxury_budget} preference."
        f"{' Special: ' + special_req if special_req else ''}"
    )

    user_query = st.text_area(
        label="Your Trip Query",
        value=auto_query,
        height=100,
        label_visibility="collapsed",
        placeholder="E.g. Plan a 5-day Goa trip from Bangalore for a couple, budget ₹30,000...",
        key="query_input",
    )

    plan_button = st.button("Plan My Trip", type="primary", use_container_width=False)

    if not plan_button:
        _show_welcome()
        return

    # ── Validation ────────────────────────────────────────────────
    if not user_query.strip():
        st.error("Please describe your trip in the query box above.")
        return

    # Key priority: frontend input > server env var (.env / Render)
    effective_key = openai_key.strip() or os.environ.get("OPENAI_API_KEY", "")
    if not effective_key:
        st.error("No OpenAI API Key found. Paste your key in the sidebar.")
        return

    os.environ["OPENAI_API_KEY"] = effective_key   # get_llm() reads this at call time

    # ── Build initial state ───────────────────────────────────────
    initial_state = {
        "user_query":           user_query,
        "user_profile":         {"user_id": user_id, "name": "Traveler"},
        "trip_preferences":     {},
        "weather_data":         {},
        "transport_data":       {},
        "hotel_data":           {},
        "places_data":          {},
        "budget_summary":       {},
        "itinerary":            {},
        "review_status":        {},
        "pdf_status":           {},
        "memory_context":       {},
        "orchestrator_decision":{},
        "retry_count":          0,
        "error_log":            [],
        "messages":             [],
        "guardrail_log":        [],
        "final_output":         None,
        "status":               "running",
    }

    # ── Run workflow ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## Workflow Execution")

    agent_steps = [
        "orchestrator_agent", "user_input_agent", "input_guardrail",
        "memory_retrieval_agent", "weather_agent", "transport_agent",
        "hotel_agent", "places_agent", "budget_agent", "itinerary_agent",
        "review_agent", "output_guardrail", "orchestrator_validate",
        "memory_update_agent", "pdf_generator_agent",
    ]
    total_steps  = len(agent_steps)
    step_counter = [0]
    progress     = st.progress(0, text="Initializing agents...")
    agent_log    = st.container()
    final_state  = dict(initial_state)

    try:
        from workflow.graph import build_graph
        from monitoring.langsmith_setup import get_run_config, capture_run_id
        graph = build_graph()

        _prefs_dest = initial_state.get("trip_preferences", {}).get("destination", destination)
        run_config  = get_run_config(user_id, destination, user_query)
        run_meta    = {}

        with agent_log:
            with capture_run_id() as run_meta:
                for step in graph.stream(initial_state, config=run_config, stream_mode="updates"):
                    for node_name, updates in step.items():
                        step_counter[0] += 1
                        pct = min(int(step_counter[0] / total_steps * 100), 95)
                        progress.progress(pct, text=f"Running: {node_name}...")

                        msgs = updates.get("messages", [])
                        for msg in msgs:
                            content = msg.get("content", "")
                            role    = msg.get("role", "system")
                            if role == "orchestrator":
                                css, icon = "orch-card",      "ORCH"
                            elif role == "guardrail":
                                css, icon = "guardrail-card", "GUARD"
                            else:
                                css  = "agent-card"
                                icon = node_name.replace("_", " ").title()
                            st.markdown(
                                f'<div class="{css}"><b>[{icon}]</b> {content}</div>',
                                unsafe_allow_html=True
                            )

                        for k, v in updates.items():
                            if isinstance(v, list) and isinstance(final_state.get(k), list):
                                final_state[k] = final_state.get(k, []) + v
                            else:
                                final_state[k] = v

                        # Stop immediately if input was blocked by guardrail
                        if final_state.get("status") == "blocked":
                            progress.progress(100, text="Blocked by security guardrail.")
                            break

                    if final_state.get("status") == "blocked":
                        break

        progress.progress(100, text="Complete!")

    except Exception as e:
        st.error(f"Workflow error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return

    # ── Blocked by guardrail ──────────────────────────────────────
    if final_state.get("status") == "blocked":
        st.markdown("""
        <div class="security-block">
            <h3>Security Alert — Input Blocked</h3>
            <p>Your query was flagged by the input guardrail and the workflow was stopped.</p>
        </div>
        """, unsafe_allow_html=True)
        glog = final_state.get("guardrail_log", [])
        for entry in glog:
            st.error(entry)
        return

    # ── Auto-run RAG evaluation ───────────────────────────────────
    eval_results   = None
    langsmith_run_id = run_meta.get("run_id")
    feedback_status  = None

    try:
        from evaluation.rag_evaluator import TripPlannerRAGEvaluator
        evaluator    = TripPlannerRAGEvaluator()
        eval_results = evaluator.evaluate_heuristic(final_state)
        evaluator.save_report([eval_results])
    except Exception as e:
        eval_results = {"error": str(e)}

    # Submit RAG scores as LangSmith feedback
    if eval_results and "error" not in eval_results and langsmith_run_id:
        from monitoring.langsmith_setup import submit_feedback
        feedback_status = submit_feedback(langsmith_run_id, eval_results)

    # ── Display results ───────────────────────────────────────────
    st.markdown("---")
    _display_results(final_state, initial_state, eval_results,
                     langsmith_run_id=langsmith_run_id,
                     feedback_status=feedback_status)


# ─────────────────────────────────────────────────────────────────
# Welcome screen
# ─────────────────────────────────────────────────────────────────

def _show_welcome():
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### System Features
        - **Orchestrator Agent** (Supervisor)
        - **10 Specialized Agents**
        - **LangGraph Workflow**
        - **ChromaDB Memory** (RAG)
        - **PDF Report Generation**
        - **Guardrails** (4 layers)
        - **RAG Evaluation** (auto)
        - **LangSmith Observability**
        """)
    with col2:
        st.markdown("""
        ### Security Layers
        1. **Input Guard** — Injection / PII / validation
        2. **Output Guard** — Schema / price sanity / PII scrub
        3. **Agent Guard** — State consistency
        4. **Guardrail Nodes** — LangGraph integration

        ### RAG Evaluation (automatic)
        - Answer Relevancy
        - Itinerary Completeness
        - Budget Adherence
        - Hallucination Guard
        """)
    with col3:
        st.markdown("""
        ### How to Use
        1. Adjust trip settings in the **sidebar**
        2. Edit the **query box** if needed
        3. Enter your **OpenAI API key**
        4. Click **Plan My Trip**
        5. Results appear with an **Evaluation tab**

        ### Sample
        *"5-day Goa trip from Bangalore for a couple, budget ₹30,000,
        beach resort, seafood, flight."*
        """)
    st.info("Adjust settings in the sidebar, review your query above, then click **Plan My Trip**.")


# ─────────────────────────────────────────────────────────────────
# Results display
# ─────────────────────────────────────────────────────────────────

def _display_results(state: dict, init_state: dict, eval_results: dict,
                     langsmith_run_id: str = None, feedback_status: str = None):
    prefs     = state.get("trip_preferences", {}) or init_state.get("trip_preferences", {})
    budget    = state.get("budget_summary", {})
    itinerary = state.get("itinerary", {})
    weather   = state.get("weather_data", {})
    hotel     = state.get("hotel_data", {})
    transport = state.get("transport_data", {})
    review    = state.get("review_status", {})
    pdf_status= state.get("pdf_status", {})
    places    = state.get("places_data", {})

    st.markdown("## Trip Plan Results")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Destination",    prefs.get("destination", "N/A"))
    c2.metric("Duration",       f"{prefs.get('num_days', 'N/A')} days")
    c3.metric("Budget",         f"₹{int(prefs.get('budget', 0)):,}")
    c4.metric("Estimated Cost", f"₹{int(budget.get('total_estimated', 0)):,}")

    if review.get("approved"):
        st.success(f"Plan Approved | Quality Score: {review.get('quality_score', 0)}/100")
    else:
        st.warning(f"Plan Generated (with notes) | Score: {review.get('quality_score', 0)}/100")

    if pdf_status.get("generated") and pdf_status.get("path"):
        try:
            with open(pdf_status["path"], "rb") as f:
                st.download_button(
                    label="Download Trip Plan PDF",
                    data=f.read(),
                    file_name=pdf_status.get("filename", "trip_plan.pdf"),
                    mime="application/pdf",
                    type="primary",
                )
        except Exception:
            pass

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Itinerary", "Hotels", "Transport", "Budget", "Places & Weather", "Evaluation"
    ])

    # ── Tab 1: Itinerary ─────────────────────────────────────────
    with tab1:
        st.subheader(itinerary.get("trip_title", "Day-wise Itinerary"))
        st.write(itinerary.get("overview", ""))
        for day in itinerary.get("days", []):
            with st.expander(f"Day {day.get('day')} — {day.get('title', '')}"):
                for act in day.get("activities", []):
                    st.markdown(
                        f"**{act.get('time', '')}** | "
                        f"{act.get('activity', '')} — "
                        f"{act.get('details', '')} | "
                        f"*{act.get('cost', '')}*"
                    )
                if day.get("notes"):
                    st.info(day["notes"])

    # ── Tab 2: Hotels ─────────────────────────────────────────────
    with tab2:
        rec = hotel.get("recommended", {})
        if rec:
            st.subheader(f"Recommended: {rec.get('name', '')}")
            ca, cb = st.columns(2)
            with ca:
                st.write(f"**Category:** {rec.get('category', '')}")
                st.write(f"**Rating:** {rec.get('rating', '')}")
                st.write(f"**Price/Night:** ₹{rec.get('price_per_night', 0):,}")
                st.write(f"**Area:** {rec.get('area', '')}")
            with cb:
                st.write(f"**Amenities:** {', '.join(rec.get('amenities', []))}")
                st.write(f"**Reviews:** {rec.get('reviews', '')}")
        st.markdown("### All Options")
        for h in hotel.get("hotels", []):
            with st.expander(f"{h.get('name')} — ₹{h.get('price_per_night', 0):,}/night"):
                st.write(f"Category: {h.get('category')} | Rating: {h.get('rating')}")
                st.write(f"Amenities: {', '.join(h.get('amenities', []))}")

    # ── Tab 3: Transport ──────────────────────────────────────────
    with tab3:
        if transport.get("recommended"):
            st.success(f"Recommended: {transport['recommended']}")
        if transport.get("flights"):
            st.markdown("### Flights")
            for f in transport["flights"]:
                st.write(f"**{f.get('airline')}** {f.get('flight_no')} | "
                         f"{f.get('departure')} → {f.get('arrival')} ({f.get('duration')}) | "
                         f"₹{f.get('price_per_person', 0):,}/person")
        if transport.get("trains"):
            st.markdown("### Trains")
            for t in transport["trains"]:
                st.write(f"**{t.get('name')}** {t.get('train_no')} | "
                         f"{t.get('class')} | ₹{t.get('price_per_person', 0):,}/person")
        if transport.get("transfer_tips"):
            st.markdown("### Transfer Tips")
            for tip in transport["transfer_tips"]:
                st.write(f"• {tip}")

    # ── Tab 4: Budget ─────────────────────────────────────────────
    with tab4:
        if budget:
            ca, cb, cc = st.columns(3)
            ca.metric("Total Budget",   f"₹{budget.get('total_budget', 0):,}")
            cb.metric("Estimated Cost", f"₹{budget.get('total_estimated', 0):,}")
            sav = budget.get("savings_or_deficit", 0)
            cc.metric(
                "Savings" if sav >= 0 else "Over Budget",
                f"₹{abs(sav):,}",
                delta=f"{'Under' if sav >= 0 else 'Over'} budget",
            )
            st.markdown("### Cost Breakdown")
            for cat, vals in budget.get("breakdown", {}).items():
                pct = budget.get("percentages", {}).get(cat, 0)
                st.write(f"**{cat.replace('_', ' ').title()}**: "
                         f"₹{vals['total']:,} (₹{vals['per_person']:,}/person) — {pct}%")
                st.progress(int(min(pct, 100)))
            if budget.get("optimization_tips"):
                st.markdown("### Optimization Tips")
                for tip in budget["optimization_tips"]:
                    st.write(f"• {tip}")

    # ── Tab 5: Places & Weather ───────────────────────────────────
    with tab5:
        ca, cb = st.columns(2)
        with ca:
            st.markdown("### Weather")
            st.write(weather.get("summary", "N/A"))
            if weather.get("travel_advisory"):
                st.warning(weather["travel_advisory"])
            for f in weather.get("forecasts", [])[:5]:
                st.write(f"{f.get('date')} | {f.get('temp_min')}–{f.get('temp_max')}°C | "
                         f"{f.get('description')}")
        with cb:
            st.markdown("### Top Attractions")
            for attr in places.get("top_attractions", []):
                with st.expander(f"{attr.get('name')} ({attr.get('type')})"):
                    st.write(attr.get("description", ""))
                    st.write(f"Entry: {attr.get('entry')} | Best time: {attr.get('best_time')}")
            st.markdown("### Food Spots")
            for food in places.get("food_spots", []):
                st.write(f"**{food.get('name')}** ({food.get('cuisine')}) — "
                         f"Must try: {', '.join(food.get('must_try', []))}")

    # ── Tab 6: Evaluation ─────────────────────────────────────────
    with tab6:
        _render_evaluation_tab(state, eval_results,
                               langsmith_run_id=langsmith_run_id,
                               feedback_status=feedback_status)

    # Errors
    errors = state.get("error_log", [])
    if errors:
        with st.expander(f"Warnings / Errors ({len(errors)})"):
            for e in errors:
                st.warning(e)


def _render_evaluation_tab(state: dict, eval_results: dict,
                            langsmith_run_id: str = None,
                            feedback_status: str = None):
    st.markdown("## Security & Quality Evaluation")
    st.caption("Runs automatically after every workflow execution.")

    # ── LangSmith trace panel ─────────────────────────────────────
    from monitoring.langsmith_setup import is_tracing_enabled, get_trace_url, get_project_url
    if is_tracing_enabled():
        trace_url = get_trace_url(langsmith_run_id) if langsmith_run_id else None
        if trace_url:
            st.markdown(
                f'<div class="langsmith-card">🔭 <b>LangSmith Trace</b> — '
                f'<a href="{trace_url}" target="_blank">Open full trace →</a>'
                f'{"  |  " + feedback_status if feedback_status else ""}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="langsmith-card">🔭 <b>LangSmith</b> — tracing enabled. '
                f'<a href="{get_project_url()}" target="_blank">View project →</a></div>',
                unsafe_allow_html=True,
            )
    st.markdown("")

    # ── Guardrail Results ─────────────────────────────────────────
    st.markdown("### Guardrail Log")
    glog = state.get("guardrail_log", [])
    if not glog:
        st.success("All guardrail checks passed — no issues detected.")
    else:
        security_issues  = [e for e in glog if "Security" in e or "BLOCK" in e]
        pii_warnings     = [e for e in glog if "PII" in e]
        auto_fixes       = [e for e in glog if "AUTO-FIX" in e]
        other_flags      = [e for e in glog if e not in security_issues + pii_warnings + auto_fixes]

        if security_issues:
            for e in security_issues:
                st.error(f"Security: {e}")
        if pii_warnings:
            for e in pii_warnings:
                st.warning(f"PII: {e}")
        if auto_fixes:
            for e in auto_fixes:
                st.info(f"Auto-fix: {e}")
        if other_flags:
            for e in other_flags:
                st.warning(e)

    # Breakdown by guardrail layer
    with st.expander("Guardrail layer summary"):
        layers = {
            "Input Guard (injection / PII / validation)": [e for e in glog if "[INPUT]" in e or "[PREFS]" in e],
            "Output Guard (schema / price sanity / PII)": [e for e in glog if "[BUDGET]" in e or "[ITINERARY]" in e or "[REVIEW]" in e],
            "Consistency Guard (inter-agent)":            [e for e in glog if "[CONSISTENCY]" in e or "[INTEGRITY]" in e],
        }
        for layer, entries in layers.items():
            status = "PASS" if not entries else f"{len(entries)} flag(s)"
            icon   = "✅" if not entries else "⚠️"
            st.write(f"{icon} **{layer}**: {status}")
            for e in entries:
                st.caption(f"  → {e}")

    st.markdown("---")

    # ── RAG Evaluation Results ────────────────────────────────────
    st.markdown("### RAG Evaluation")
    st.caption("Evaluates retrieval quality and generation accuracy of the trip planner pipeline.")

    if not eval_results:
        st.info("RAG evaluation did not run.")
        return

    if "error" in eval_results:
        st.error(f"RAG evaluation error: {eval_results['error']}")
        return

    mode = eval_results.get("eval_mode", "heuristic").upper()
    st.caption(f"Mode: **{mode}** | Memory context: {'Available' if eval_results.get('has_memory') else 'None (first run)'}")

    metrics = eval_results.get("metrics", [])
    if not metrics:
        st.info("No metrics returned.")
        return

    # Score cards
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        score = m.get("score", 0)
        passed = m.get("passed", False)
        color = "#2e7d32" if passed else "#e65100"
        col.markdown(
            f"""<div style="border:1px solid {color}; border-radius:8px; padding:12px; text-align:center;">
            <div style="font-size:0.75em; color:#666;">{m['metric'].replace(' (heuristic)', '')}</div>
            <div style="font-size:1.8em; font-weight:bold; color:{color};">{score:.2f}</div>
            <div style="font-size:0.8em; color:{color};">{'PASS' if passed else 'FAIL'}</div>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("")

    # Detailed breakdown
    with st.expander("Metric details"):
        for m in metrics:
            status = "PASS" if m.get("passed") else "FAIL"
            css    = "eval-pass" if m.get("passed") else "eval-fail"
            reason = m.get("reason", "")
            st.markdown(
                f'<div class="{css}"><b>[{status}] {m["metric"]}</b> — score: {m["score"]:.3f}'
                f'{"  |  " + reason if reason else ""}</div>',
                unsafe_allow_html=True
            )

    # Overall badge
    passed_count = eval_results.get("passed", 0)
    total_count  = eval_results.get("total", 0)
    all_pass     = eval_results.get("overall_pass", False)
    if all_pass:
        st.success(f"RAG Evaluation: {passed_count}/{total_count} metrics passed")
    else:
        st.warning(f"RAG Evaluation: {passed_count}/{total_count} metrics passed")


if __name__ == "__main__":
    main()
