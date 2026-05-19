"""
Multi-Agent Trip Planner — CLI Entry Point
Usage: python main.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from workflow.graph import build_graph
from config.settings import ANTHROPIC_API_KEY

SAMPLE_QUERY = (
    "Plan a 5-day Goa trip from Bangalore for a couple. "
    "Budget: ₹30,000. Need beach resort, nightlife, sightseeing, seafood, flight preferred."
)

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║        Multi-Agent AI Trip Planner — LangGraph System       ║
║    Orchestrator • 10 Agents • Memory • PDF Generator        ║
╚══════════════════════════════════════════════════════════════╝
"""


def run_trip_planner(user_query: str, user_id: str = "user_001") -> dict:
    """Execute the full multi-agent trip planning workflow."""
    if not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY in your .env file.")
        sys.exit(1)

    print(BANNER)
    print(f"Query: {user_query}\n")
    print("=" * 60)

    graph = build_graph()

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

    print("\nStarting Multi-Agent Workflow...\n")
    final_state = None

    for step in graph.stream(initial_state, stream_mode="updates"):
        for node_name, updates in step.items():
            msgs = updates.get("messages", [])
            for msg in msgs:
                content = msg.get("content", "")
                role = msg.get("role", "system")
                prefix = "ORCH" if role == "orchestrator" else "    "
                print(f"[{prefix}] {node_name}: {content}")
        final_state = step

    print("\n" + "=" * 60)

    # Extract final state values
    result = {}
    if final_state:
        last_node = list(final_state.keys())[-1]
        result = final_state[last_node]

    # Gather full state by merging (stream gives partial updates)
    return result


def main():
    print(BANNER)
    print("Welcome to the Multi-Agent AI Trip Planner!\n")

    use_sample = input("Use sample query? (y/n): ").strip().lower()
    if use_sample == "y":
        query = SAMPLE_QUERY
    else:
        print("\nEnter your trip query (e.g., '5-day Goa trip from Bangalore for couple, budget 30000'):")
        query = input("> ").strip()
        if not query:
            query = SAMPLE_QUERY

    user_id = input("\nEnter user ID (press Enter for 'user_001'): ").strip() or "user_001"

    result = run_trip_planner(query, user_id)

    pdf_status = result.get("pdf_status", {})
    if pdf_status.get("generated"):
        print(f"\nSUCCESS! Trip plan PDF generated:")
        print(f"  File: {pdf_status.get('path')}")
    else:
        print(f"\nWorkflow completed. Check output/ folder for results.")
        if pdf_status.get("error"):
            print(f"PDF error: {pdf_status.get('error')}")

    print("\nThank you for using Multi-Agent AI Trip Planner!")


if __name__ == "__main__":
    main()
