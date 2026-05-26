"""Evaluation runner — execute from project root:

  python -m evaluation.run_evaluation --guardrails
  python -m evaluation.run_evaluation --rag
  python -m evaluation.run_evaluation --all
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()


def run_guardrail_tests():
    from evaluation.guardrail_tester import GuardrailTester
    print("\n" + "=" * 65)
    print("  RUNNING GUARDRAIL TESTS")
    print("=" * 65)
    tester = GuardrailTester()
    report = tester.run_all()
    tester.print_report()
    tester.save_report("output/guardrail_test_report.json")
    return report


def run_rag_evaluation(query: str = None, user_id: str = "eval_user"):
    """Run a full workflow then evaluate the RAG pipeline."""
    from workflow.graph import build_graph
    from evaluation.rag_evaluator import TripPlannerRAGEvaluator

    query = query or (
        "Plan a 5-day trip to Goa from Bangalore for a couple. "
        "Budget: Rs 30000. Beach resort, nightlife, seafood, flight preferred."
    )

    print("\n" + "=" * 65)
    print("  RUNNING RAG EVALUATION")
    print("=" * 65)
    print(f"  Query: {query[:70]}")
    print("=" * 65)

    graph = build_graph()
    initial_state = {
        "user_query": query,
        "user_profile": {"user_id": user_id, "name": "Eval User"},
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
        "guardrail_log": [],
        "final_output": None,
        "status": "running",
    }

    print("\n  Step 1/2: Running workflow to collect RAG data...")
    final_state = dict(initial_state)
    for step in graph.stream(initial_state, stream_mode="updates"):
        for node_name, updates in step.items():
            print(f"    [{node_name}] done")
            for k, v in updates.items():
                if isinstance(v, list) and isinstance(final_state.get(k), list):
                    final_state[k] = final_state.get(k, []) + v
                else:
                    final_state[k] = v

    print("\n  Step 2/2: Evaluating RAG pipeline with DeepEval...")
    evaluator = TripPlannerRAGEvaluator()
    result = evaluator.evaluate_state(final_state)
    evaluator.save_report([result], "output/rag_eval_report.json")
    return result


def run_heuristic_rag_evaluation(query: str = None, user_id: str = "eval_user"):
    """Run workflow + heuristic RAG evaluation (no extra API quota needed)."""
    from workflow.graph import build_graph
    from evaluation.rag_evaluator import TripPlannerRAGEvaluator

    query = query or (
        "Plan a 5-day trip to Goa from Bangalore for a couple. "
        "Budget: Rs 30000. Beach resort, nightlife, seafood, flight preferred."
    )

    print("\n" + "=" * 65)
    print("  RUNNING RAG EVALUATION (heuristic mode)")
    print("=" * 65)

    graph = build_graph()
    initial_state = {
        "user_query": query,
        "user_profile": {"user_id": user_id, "name": "Eval User"},
        "trip_preferences": {}, "weather_data": {}, "transport_data": {},
        "hotel_data": {}, "places_data": {}, "budget_summary": {},
        "itinerary": {}, "review_status": {}, "pdf_status": {},
        "memory_context": {}, "orchestrator_decision": {},
        "retry_count": 0, "error_log": [], "messages": [],
        "guardrail_log": [], "final_output": None, "status": "running",
    }

    final_state = dict(initial_state)
    for step in graph.stream(initial_state, stream_mode="updates"):
        for node_name, updates in step.items():
            print(f"    [{node_name}] done")
            for k, v in updates.items():
                if isinstance(v, list) and isinstance(final_state.get(k), list):
                    final_state[k] = final_state.get(k, []) + v
                else:
                    final_state[k] = v

    evaluator = TripPlannerRAGEvaluator()
    result = evaluator.evaluate_heuristic(final_state)
    evaluator.save_report([result], "output/rag_eval_report.json")
    return result


def main():
    parser = argparse.ArgumentParser(description="Trip Planner Evaluation Suite")
    parser.add_argument("--guardrails", action="store_true", help="Run guardrail tests")
    parser.add_argument("--rag",        action="store_true", help="Run RAG evaluation (DeepEval, needs API quota)")
    parser.add_argument("--heuristic",  action="store_true", help="Run heuristic RAG evaluation (no extra API quota)")
    parser.add_argument("--all",        action="store_true", help="Run guardrails + heuristic RAG")
    parser.add_argument("--query",      type=str, default=None, help="Custom query for RAG eval")
    args = parser.parse_args()

    if not (args.guardrails or args.rag or args.heuristic or args.all):
        parser.print_help()
        sys.exit(0)

    results = {}

    if args.guardrails or args.all:
        results["guardrails"] = run_guardrail_tests()

    if args.rag:
        results["rag"] = run_rag_evaluation(query=args.query)

    if args.heuristic or args.all:
        results["rag"] = run_heuristic_rag_evaluation(query=args.query)

    # Combined summary
    print("\n" + "=" * 65)
    print("  EVALUATION COMPLETE")
    print("=" * 65)
    if "guardrails" in results:
        g = results["guardrails"]
        print(f"  Guardrails : {g['passed']}/{g['total']} tests passed")
    if "rag" in results:
        r = results["rag"]
        mode = r.get("eval_mode", "deepeval")
        print(f"  RAG [{mode}]: {r['passed']}/{r['total']} metrics passed  "
              f"({'PASS' if r['overall_pass'] else 'FAIL'})")
    print("=" * 65)


if __name__ == "__main__":
    main()
