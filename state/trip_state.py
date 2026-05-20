from typing import TypedDict, Annotated, Optional, List, Dict, Any
import operator


class TripState(TypedDict):
    # -- Input ---------------------------------------------------
    user_query: str                          # Raw user request
    user_profile: Dict[str, Any]            # Name, email, past trips
    trip_preferences: Dict[str, Any]        # Source, dest, dates, budget, pax

    # -- Agent outputs -------------------------------------------
    weather_data: Dict[str, Any]
    transport_data: Dict[str, Any]
    hotel_data: Dict[str, Any]
    places_data: Dict[str, Any]
    budget_summary: Dict[str, Any]
    itinerary: Dict[str, Any]
    review_status: Dict[str, Any]           # {approved, conflicts, notes}
    pdf_status: Dict[str, Any]              # {generated, path, error}
    memory_context: Dict[str, Any]          # Past preferences retrieved

    # -- Orchestrator control ------------------------------------
    orchestrator_decision: Dict[str, Any]   # {next_agent, reason, retry_agents}
    retry_count: int
    error_log: Annotated[List[str], operator.add]
    messages: Annotated[List[Dict[str, Any]], operator.add]
    guardrail_log: Annotated[List[str], operator.add]  # security & quality check log
    final_output: Optional[str]
    status: str                             # running | approved | failed | blocked | done
