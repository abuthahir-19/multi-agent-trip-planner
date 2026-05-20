"""
Multi-Agent Trip Planner — Streamlit Web Application
Run: streamlit run app.py
"""
import os
import sys
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Multi-Agent AI Trip Planner",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────
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
.success-box {
    background: #e8f5e9; border: 2px solid #1A6B3C;
    padding: 15px; border-radius: 8px; text-align: center;
}
.error-box {
    background: #ffebee; border: 2px solid #c62828;
    padding: 15px; border-radius: 8px;
}
.metric-card {
    background: white; border: 1px solid #e0e0e0;
    padding: 15px; border-radius: 8px; text-align: center;
}
</style>
""", unsafe_allow_html=True)


def main():
    # ── Header ───────────────────────────────────────────────
    st.markdown("""
    <div class="main-title">
        <h1>✈ Multi-Agent AI Trip Planner</h1>
        <p>Powered by LangGraph • Claude AI • 10 Specialized Agents</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar — Trip Form ──────────────────────────────────
    with st.sidebar:
        st.header("Trip Details")

        source = st.text_input("Source City", value="Bangalore")
        destination = st.text_input("Destination City", value="Goa")

        col1, col2 = st.columns(2)
        with col1:
            num_days = st.number_input("Days", min_value=1, max_value=30, value=5)
        with col2:
            num_travelers = st.number_input("Travelers", min_value=1, max_value=20, value=2)

        travel_dates = st.text_input("Travel Dates", value="June 10 to June 15, 2025")
        budget = st.number_input("Total Budget (₹)", min_value=5000, max_value=500000,
                                  value=30000, step=1000)

        trip_type = st.selectbox("Trip Type", ["couple", "solo", "family", "business"])
        transport_pref = st.selectbox("Transport Preference",
                                       ["flight", "train", "car", "bus", "any"])
        hotel_pref = st.selectbox("Hotel Preference",
                                   ["3-star", "4-star", "5-star", "budget", "beach resort",
                                    "luxury", "heritage"])
        food_pref = st.selectbox("Food Preference",
                                  ["any", "veg", "non-veg", "seafood", "vegan"])

        places_interest = st.multiselect(
            "Places of Interest",
            ["Beach", "Heritage", "Nature", "Adventure", "Shopping",
             "Nightlife", "Religious", "Museum", "Scenic"],
            default=["Beach", "Nightlife", "Heritage"]
        )

        luxury_budget = st.select_slider("Preference",
                                          options=["budget", "mid-range", "luxury"],
                                          value="mid-range")

        special_req = st.text_area("Special Requirements", placeholder="Any special needs...")

        user_id = st.text_input("User ID (for memory)", value="user_001")

        st.markdown("---")
        openai_key = st.text_input("OpenAI API Key", type="password",
                                    value=os.getenv("OPENAI_API_KEY", ""),
                                    help="Get from platform.openai.com")

        plan_button = st.button("Plan My Trip", type="primary", use_container_width=True)

    # ── Main area ────────────────────────────────────────────
    if not plan_button:
        _show_welcome()
        return

    if not openai_key:
        st.error("Please enter your OpenAI API Key in the sidebar.")
        return

    # Set API key for this session
    os.environ["OPENAI_API_KEY"] = openai_key

    # Reload settings with the new key
    import importlib
    import config.settings as _cfg
    importlib.reload(_cfg)

    # Build query from form inputs
    user_query = (
        f"Plan a {num_days}-day {destination} trip from {source} for "
        f"{'a ' if num_travelers == 2 and trip_type == 'couple' else str(num_travelers) + ' '}"
        f"{trip_type}. Travel dates: {travel_dates}. "
        f"Budget: ₹{budget:,}. "
        f"Transport: {transport_pref}. Hotel: {hotel_pref}. "
        f"Food: {food_pref}. "
        f"Interested in: {', '.join(places_interest)}. "
        f"{luxury_budget} preference. "
        f"{('Special requirements: ' + special_req) if special_req else ''}"
    )

    # Initial state
    initial_state = {
        "user_query": user_query,
        "user_profile": {"user_id": user_id, "name": "Traveler"},
        "trip_preferences": {},
        "weather_data": {},
        "transport_data": {},
        "hotel_data": {},
        "places_data": {},
        "budget_summary": {},
        "itinerary": {},
        "review_status": {},
        "pdf_status": {},
        "memory_context": {},
        "orchestrator_decision": {},
        "retry_count": 0,
        "error_log": [],
        "messages": [],
        "final_output": None,
        "status": "running",
    }

    # ── Run workflow ─────────────────────────────────────────
    st.markdown("## Workflow Execution")

    progress = st.progress(0, text="Initializing agents...")
    agent_log = st.container()
    status_area = st.empty()

    final_state = {}
    agent_steps = [
        "orchestrator_agent", "user_input_agent", "memory_retrieval_agent",
        "weather_agent", "transport_agent", "hotel_agent", "places_agent",
        "budget_agent", "itinerary_agent", "review_agent",
        "orchestrator_validate", "memory_update_agent", "pdf_generator_agent"
    ]
    total_steps = len(agent_steps)
    step_counter = [0]

    try:
        from workflow.graph import build_graph
        graph = build_graph()

        with agent_log:
            for step in graph.stream(initial_state, stream_mode="updates"):
                for node_name, updates in step.items():
                    step_counter[0] += 1
                    pct = min(int(step_counter[0] / total_steps * 100), 95)
                    progress.progress(pct, text=f"Running: {node_name}...")

                    msgs = updates.get("messages", [])
                    for msg in msgs:
                        content = msg.get("content", "")
                        role = msg.get("role", "system")
                        if role == "orchestrator":
                            css_class = "orch-card"
                            icon = "ORCH"
                        elif role == "guardrail":
                            css_class = "guardrail-card"
                            icon = "GUARD"
                        else:
                            css_class = "agent-card"
                            icon = node_name.replace("_", " ").title()
                        st.markdown(
                            f'<div class="{css_class}"><b>[{icon}]</b> {content}</div>',
                            unsafe_allow_html=True
                        )

                    # Accumulate final state
                    for k, v in updates.items():
                        if isinstance(v, list) and k in final_state and isinstance(final_state.get(k), list):
                            final_state[k] = final_state.get(k, []) + v
                        else:
                            final_state[k] = v

        progress.progress(100, text="Workflow complete!")

    except Exception as e:
        st.error(f"Workflow error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return

    # ── Display Results ──────────────────────────────────────
    st.markdown("---")
    _display_results(final_state, initial_state)


def _show_welcome():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### System Features
        - **Orchestrator Agent** (Supervisor)
        - **10 Specialized Agents**
        - **LangGraph Workflow**
        - **Memory System** (ChromaDB)
        - **PDF Report Generation**
        """)
    with col2:
        st.markdown("""
        ### Agents
        1. User Input Agent
        2. Memory Agent
        3. Weather Agent
        4. Transport Agent
        5. Hotel Agent
        6. Places Explorer Agent
        7. Budget Agent
        8. Itinerary Agent
        9. Final Review Agent
        10. PDF Generator Agent
        """)
    with col3:
        st.markdown("""
        ### Sample Query
        *"Plan a 5-day Goa trip from Bangalore for a couple. Budget ₹30,000. Need beach resort, nightlife, sightseeing, seafood, flight preferred."*

        ### How to Use
        1. Fill in trip details in sidebar
        2. Enter your Anthropic API key
        3. Click **Plan My Trip**
        4. Download the PDF report
        """)

    st.info("Fill in your trip details in the sidebar and click **Plan My Trip** to start.")


def _display_results(state: dict, init_state: dict):
    prefs = state.get("trip_preferences", {}) or init_state.get("trip_preferences", {})
    budget = state.get("budget_summary", {})
    itinerary = state.get("itinerary", {})
    weather = state.get("weather_data", {})
    hotel = state.get("hotel_data", {})
    transport = state.get("transport_data", {})
    review = state.get("review_status", {})
    pdf_status = state.get("pdf_status", {})
    places = state.get("places_data", {})

    st.markdown("## Trip Plan Results")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Destination", prefs.get("destination", "N/A"))
    col2.metric("Duration", f"{prefs.get('num_days', 'N/A')} days")
    col3.metric("Budget", f"₹{int(prefs.get('budget', 0)):,}")
    col4.metric("Estimated Cost", f"₹{int(budget.get('total_estimated', 0)):,}")

    # Review status
    if review.get("approved"):
        st.success(f"Plan Approved | Quality Score: {review.get('quality_score', 0)}/100")
    else:
        st.warning(f"Plan Generated (with notes) | Score: {review.get('quality_score', 0)}/100")

    # PDF Download
    if pdf_status.get("generated") and pdf_status.get("path"):
        with open(pdf_status["path"], "rb") as f:
            st.download_button(
                label="Download Trip Plan PDF",
                data=f.read(),
                file_name=pdf_status.get("filename", "trip_plan.pdf"),
                mime="application/pdf",
                type="primary",
            )

    # Tabs for sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Itinerary", "Hotels", "Transport", "Budget", "Places & Weather"
    ])

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

    with tab2:
        rec = hotel.get("recommended", {})
        if rec:
            st.subheader(f"Recommended: {rec.get('name', '')}")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Category:** {rec.get('category', '')}")
                st.write(f"**Rating:** ⭐ {rec.get('rating', '')}")
                st.write(f"**Price/Night:** ₹{rec.get('price_per_night', 0):,}")
                st.write(f"**Area:** {rec.get('area', '')}")
            with col_b:
                st.write(f"**Amenities:** {', '.join(rec.get('amenities', []))}")
                st.write(f"**Reviews:** {rec.get('reviews', '')}")
                st.write(f"**Booking:** {rec.get('booking_link', '')}")

        st.markdown("### All Options")
        for h in hotel.get("hotels", []):
            with st.expander(f"{h.get('name')} — ₹{h.get('price_per_night', 0):,}/night"):
                st.write(f"Category: {h.get('category')} | Rating: ⭐{h.get('rating')}")
                st.write(f"Amenities: {', '.join(h.get('amenities', []))}")
                st.write(f"Booking: {h.get('booking_link', '')}")

    with tab3:
        rec_t = transport.get("recommended", "")
        if rec_t:
            st.success(f"Recommended: {rec_t}")

        if transport.get("flights"):
            st.markdown("### Flight Options")
            for f in transport["flights"]:
                st.write(
                    f"**{f.get('airline')}** {f.get('flight_no')} | "
                    f"{f.get('departure')} → {f.get('arrival')} ({f.get('duration')}) | "
                    f"₹{f.get('price_per_person', 0):,}/person"
                )

        if transport.get("trains"):
            st.markdown("### Train Options")
            for t in transport["trains"]:
                st.write(
                    f"**{t.get('name')}** {t.get('train_no')} | "
                    f"{t.get('class')} | "
                    f"₹{t.get('price_per_person', 0):,}/person | "
                    f"{t.get('availability', '')}"
                )

        if transport.get("transfer_tips"):
            st.markdown("### Transfer Tips")
            for tip in transport["transfer_tips"]:
                st.write(f"• {tip}")

    with tab4:
        if budget:
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Total Budget", f"₹{budget.get('total_budget', 0):,}")
            col_b.metric("Estimated Cost", f"₹{budget.get('total_estimated', 0):,}")
            savings = budget.get("savings_or_deficit", 0)
            col_c.metric(
                "Savings" if savings >= 0 else "Over Budget",
                f"₹{abs(savings):,}",
                delta=f"{'Under' if savings >= 0 else 'Over'} budget"
            )

            st.markdown("### Cost Breakdown")
            breakdown = budget.get("breakdown", {})
            pcts = budget.get("percentages", {})
            for cat, vals in breakdown.items():
                pct = pcts.get(cat, 0)
                st.write(f"**{cat.replace('_', ' ').title()}**: "
                         f"₹{vals['total']:,} (₹{vals['per_person']:,}/person) — {pct}%")
                st.progress(int(pct))

            if budget.get("optimization_tips"):
                st.markdown("### Optimization Tips")
                for tip in budget["optimization_tips"]:
                    st.write(f"💡 {tip}")

    with tab5:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### Weather")
            st.write(weather.get("summary", "N/A"))
            st.warning(weather.get("travel_advisory", ""))

            if weather.get("forecasts"):
                st.markdown("**7-day Forecast:**")
                for f in weather["forecasts"][:5]:
                    st.write(f"📅 {f.get('date')} | "
                             f"{f.get('temp_min')}°C – {f.get('temp_max')}°C | "
                             f"{f.get('description')}")

        with col_b:
            st.markdown("### Top Attractions")
            for attr in places.get("top_attractions", []):
                with st.expander(f"{attr.get('name')} ({attr.get('type')})"):
                    st.write(attr.get("description", ""))
                    st.write(f"Entry: {attr.get('entry')} | Best time: {attr.get('best_time')} | "
                             f"Duration: {attr.get('duration')}")

            st.markdown("### Food Spots")
            for food in places.get("food_spots", []):
                st.write(f"**{food.get('name')}** ({food.get('cuisine')}) — "
                         f"{food.get('price')} | Must try: {', '.join(food.get('must_try', []))}")

    # Errors
    errors = state.get("error_log", [])
    if errors:
        with st.expander("Warnings / Errors"):
            for e in errors:
                st.warning(e)


if __name__ == "__main__":
    main()
