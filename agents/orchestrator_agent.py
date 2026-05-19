"""Orchestrator (Supervisor) Agent — the brain of the multi-agent system.

Responsibilities:
  1. Understand user goal and context
  2. Decide which agents run and in what order
  3. Resolve conflicts between agent outputs
  4. Trigger retries for failed tasks
  5. Validate final plan completeness
  6. Authorize PDF generation
"""
import json
import re
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import get_llm
from state.trip_state import TripState


SYSTEM_PROMPT = """You are the Orchestrator Agent of a Multi-Agent AI Trip Planner.
You are the MOST IMPORTANT agent — you control all other agents.

You will receive the current trip planning state and decide what to do next.

Available agents:
- user_input_agent: Collect and validate user requirements
- memory_agent: Retrieve past user preferences
- weather_agent: Get weather forecast
- transport_agent: Find flights/trains/routes
- hotel_agent: Find hotels within budget
- places_agent: Find attractions and local experiences
- budget_agent: Calculate and optimize budget
- itinerary_agent: Create day-wise plan
- review_agent: Validate and check for conflicts
- memory_update_agent: Save trip to memory
- pdf_generator_agent: Generate PDF report
- END: Trip plan is complete

Return a JSON object:
{
  "next_agent": "agent_name or END",
  "reason": "why this agent should run next",
  "action": "what this agent should do",
  "retry_override": false,
  "priority": "high|medium|low"
}

Decision rules:
1. After user_input_agent → run memory_agent
2. After memory_agent → run weather_agent, transport_agent, hotel_agent, places_agent in parallel sequence
3. After all data agents → run budget_agent
4. After budget_agent → run itinerary_agent
5. After itinerary_agent → run review_agent
6. After review_agent:
   - If approved → run memory_update_agent then pdf_generator_agent then END
   - If not approved + retry_count < 3 → retry the failed agents
   - If retry_count >= 3 → run pdf_generator_agent anyway (best effort) then END
7. If hotel exceeds budget → re-run hotel_agent with lower budget preference
8. If weather is severe → re-run places_agent with indoor alternatives only
9. If transport failed → note alternative transport options
Return ONLY the JSON, no markdown."""


def orchestrator_agent(state: TripState) -> dict:
    """Orchestrator decides which agent runs next based on current state."""
    llm = get_llm(temperature=0.1)

    state_summary = _build_state_summary(state)

    try:
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=state_summary),
        ])
        raw = response.content.strip()
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        decision = json.loads(raw)
    except Exception as e:
        decision = _rule_based_decision(state)
        decision["llm_error"] = str(e)

    return {
        "orchestrator_decision": decision,
        "messages": [{"role": "orchestrator", "content":
                      f"Orchestrator → {decision.get('next_agent', '?')}: {decision.get('reason', '')}"}],
    }


def orchestrator_validate(state: TripState) -> dict:
    """Final validation step — checks if plan is complete and approves PDF generation."""
    review = state.get("review_status", {})
    budget = state.get("budget_summary", {})
    retry_count = state.get("retry_count", 0)

    approved = review.get("approved", False)
    over_budget = budget.get("over_budget", False)
    over_50_pct = (
        budget.get("total_estimated", 0) >
        budget.get("total_budget", 1) * 1.5
    )

    conflicts = review.get("conflicts", [])
    retry_agents = review.get("retry_agents", [])

    # Orchestrator final decision
    if approved and not over_50_pct:
        decision = {
            "next_agent": "memory_update_agent",
            "reason": "Plan approved and within budget. Saving to memory and generating PDF.",
            "approved": True,
            "retry_agents": [],
        }
    elif retry_count >= 3 or not retry_agents:
        decision = {
            "next_agent": "pdf_generator_agent",
            "reason": "Max retries reached or no retry needed. Generating best-effort PDF.",
            "approved": False,
            "retry_agents": [],
        }
    else:
        decision = {
            "next_agent": "retry",
            "reason": f"Issues found: {', '.join(conflicts)}. Retrying: {', '.join(retry_agents)}",
            "approved": False,
            "retry_agents": retry_agents,
        }

    return {
        "orchestrator_decision": decision,
        "messages": [{"role": "orchestrator", "content":
                      f"Orchestrator Validation: {'APPROVED' if decision.get('approved') else 'NEEDS RETRY'} — {decision['reason']}"}],
    }


def _build_state_summary(state: TripState) -> str:
    prefs = state.get("trip_preferences", {})
    return f"""Current Trip Planning State:

User Query: {state.get('user_query', 'N/A')}
Destination: {prefs.get('destination', 'Not set')}
Source: {prefs.get('source', 'Not set')}
Days: {prefs.get('num_days', 'Not set')}
Budget: ₹{prefs.get('budget', 0):,}
Trip Type: {prefs.get('trip_type', 'Not set')}

Agent Completion Status:
- user_input_agent: {"✓ Done" if prefs else "✗ Pending"}
- memory_agent: {"✓ Done" if state.get('memory_context') else "✗ Pending"}
- weather_agent: {"✓ Done" if state.get('weather_data') and not state.get('weather_data', {}).get('error') else "✗ Pending/Error"}
- transport_agent: {"✓ Done" if state.get('transport_data') and not state.get('transport_data', {}).get('error') else "✗ Pending/Error"}
- hotel_agent: {"✓ Done" if state.get('hotel_data') and not state.get('hotel_data', {}).get('error') else "✗ Pending/Error"}
- places_agent: {"✓ Done" if state.get('places_data') and not state.get('places_data', {}).get('error') else "✗ Pending/Error"}
- budget_agent: {"✓ Done" if state.get('budget_summary') and not state.get('budget_summary', {}).get('error') else "✗ Pending/Error"}
- itinerary_agent: {"✓ Done — " + str(len(state.get('itinerary', {}).get('days', []))) + " days" if state.get('itinerary') else "✗ Pending"}
- review_agent: {"✓ Done — " + ("Approved" if state.get('review_status', {}).get('approved') else "Not Approved") if state.get('review_status') else "✗ Pending"}
- pdf_generator_agent: {"✓ Done" if state.get('pdf_status', {}).get('generated') else "✗ Pending"}

Retry Count: {state.get('retry_count', 0)}/3
Errors: {state.get('error_log', [])}
Status: {state.get('status', 'running')}

Decide which agent should run NEXT."""


def _rule_based_decision(state: TripState) -> dict:
    """Deterministic fallback routing when LLM fails."""
    prefs = state.get("trip_preferences", {})
    memory = state.get("memory_context")
    weather = state.get("weather_data")
    transport = state.get("transport_data")
    hotel = state.get("hotel_data")
    places = state.get("places_data")
    budget_sum = state.get("budget_summary")
    itinerary = state.get("itinerary")
    review = state.get("review_status")
    pdf = state.get("pdf_status")

    if not prefs:
        return {"next_agent": "user_input_agent", "reason": "No preferences yet"}
    if not memory:
        return {"next_agent": "memory_agent", "reason": "Load past preferences"}
    if not weather:
        return {"next_agent": "weather_agent", "reason": "Need weather data"}
    if not transport:
        return {"next_agent": "transport_agent", "reason": "Need transport options"}
    if not hotel:
        return {"next_agent": "hotel_agent", "reason": "Need hotel options"}
    if not places:
        return {"next_agent": "places_agent", "reason": "Need attractions"}
    if not budget_sum:
        return {"next_agent": "budget_agent", "reason": "Calculate budget"}
    if not itinerary:
        return {"next_agent": "itinerary_agent", "reason": "Create day plan"}
    if not review:
        return {"next_agent": "review_agent", "reason": "Validate plan"}
    if review.get("approved") and not pdf:
        return {"next_agent": "memory_update_agent", "reason": "Save and generate PDF"}
    if pdf:
        return {"next_agent": "END", "reason": "Trip plan complete"}
    return {"next_agent": "pdf_generator_agent", "reason": "Generate PDF (best effort)"}
