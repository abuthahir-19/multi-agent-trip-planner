"""LangGraph Multi-Agent Workflow Definition.

Workflow:
  START
  → orchestrator_agent (understand goal)
  → user_input_agent
  → memory_retrieval_agent
  → orchestrator_decide (route to parallel agents)
  → [weather_agent, transport_agent, hotel_agent, places_agent]  (sequential, simulating parallel)
  → budget_agent
  → itinerary_agent
  → review_agent
  → orchestrator_validate
  → IF approved: memory_update_agent → pdf_generator_agent → END
  → ELSE: retry failed agents → back to review_agent
  → END
"""
from langgraph.graph import StateGraph, END
from state.trip_state import TripState
from agents.orchestrator_agent import orchestrator_agent, orchestrator_validate
from agents.user_input_agent import user_input_agent
from agents.memory_agent import memory_retrieval_agent, memory_update_agent
from agents.weather_agent import weather_agent
from agents.transport_agent import transport_agent
from agents.hotel_agent import hotel_agent
from agents.places_agent import places_agent
from agents.budget_agent import budget_agent
from agents.itinerary_agent import itinerary_agent
from agents.review_agent import review_agent
from agents.pdf_generator_agent import pdf_generator_agent


def _route_after_validate(state: TripState) -> str:
    """Conditional edge: after orchestrator_validate, decide next step."""
    decision = state.get("orchestrator_decision", {})
    next_agent = decision.get("next_agent", "pdf_generator_agent")
    retry_count = state.get("retry_count", 0)

    if next_agent == "memory_update_agent":
        return "memory_update_agent"
    elif next_agent == "retry" and retry_count < 3:
        return "retry_loop"
    else:
        return "pdf_generator_agent"


def _retry_router(state: TripState) -> str:
    """Routes retries back to the appropriate failed agent."""
    decision = state.get("orchestrator_decision", {})
    retry_agents = decision.get("retry_agents", [])

    if "hotel_agent" in retry_agents:
        return "hotel_agent"
    elif "transport_agent" in retry_agents:
        return "transport_agent"
    elif "itinerary_agent" in retry_agents:
        return "itinerary_agent"
    elif "places_agent" in retry_agents:
        return "places_agent"
    else:
        return "itinerary_agent"


def _increment_retry(state: TripState) -> dict:
    """Increment retry counter."""
    return {"retry_count": state.get("retry_count", 0) + 1}


def build_graph() -> StateGraph:
    """Build and compile the LangGraph multi-agent workflow."""
    graph = StateGraph(TripState)

    # ── Add all agent nodes ──────────────────────────────────
    graph.add_node("orchestrator_agent", orchestrator_agent)
    graph.add_node("user_input_agent", user_input_agent)
    graph.add_node("memory_retrieval_agent", memory_retrieval_agent)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("transport_agent", transport_agent)
    graph.add_node("hotel_agent", hotel_agent)
    graph.add_node("places_agent", places_agent)
    graph.add_node("budget_agent", budget_agent)
    graph.add_node("itinerary_agent", itinerary_agent)
    graph.add_node("review_agent", review_agent)
    graph.add_node("orchestrator_validate", orchestrator_validate)
    graph.add_node("memory_update_agent", memory_update_agent)
    graph.add_node("pdf_generator_agent", pdf_generator_agent)
    graph.add_node("retry_loop", _increment_retry)

    # ── Set entry point ──────────────────────────────────────
    graph.set_entry_point("orchestrator_agent")

    # ── Main sequential flow ─────────────────────────────────
    graph.add_edge("orchestrator_agent", "user_input_agent")
    graph.add_edge("user_input_agent", "memory_retrieval_agent")

    # Simulated parallel execution — runs sequentially but independently
    graph.add_edge("memory_retrieval_agent", "weather_agent")
    graph.add_edge("weather_agent", "transport_agent")
    graph.add_edge("transport_agent", "hotel_agent")
    graph.add_edge("hotel_agent", "places_agent")

    # Sequential post-processing
    graph.add_edge("places_agent", "budget_agent")
    graph.add_edge("budget_agent", "itinerary_agent")
    graph.add_edge("itinerary_agent", "review_agent")
    graph.add_edge("review_agent", "orchestrator_validate")

    # ── Conditional edges after validation ──────────────────
    graph.add_conditional_edges(
        "orchestrator_validate",
        _route_after_validate,
        {
            "memory_update_agent": "memory_update_agent",
            "retry_loop": "retry_loop",
            "pdf_generator_agent": "pdf_generator_agent",
        }
    )

    # After memory update → PDF → END
    graph.add_edge("memory_update_agent", "pdf_generator_agent")
    graph.add_edge("pdf_generator_agent", END)

    # ── Retry routing ────────────────────────────────────────
    graph.add_conditional_edges(
        "retry_loop",
        _retry_router,
        {
            "hotel_agent": "hotel_agent",
            "transport_agent": "transport_agent",
            "itinerary_agent": "itinerary_agent",
            "places_agent": "places_agent",
        }
    )

    return graph.compile()
