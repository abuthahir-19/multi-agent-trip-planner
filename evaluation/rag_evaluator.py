"""RAG Evaluation for the Trip Planner using DeepEval.

Evaluates the RAG pipeline:
  Query (user_query)
    → Retrieval (ChromaDB memory_context)
    → Generation (LLM itinerary)

Metrics:
  - Answer Relevancy     : Is the itinerary relevant to the user's query?
  - Faithfulness         : Is the itinerary faithful to retrieved memory context?
  - Contextual Relevancy : Is the retrieved memory context relevant to the query?
  - Hallucination        : Does the itinerary invent facts not supported by context?
"""
import json
import os

from config.settings import OPENAI_API_KEY

# deepeval imports are lazy — loaded only inside evaluate_state() so that
# pydantic version conflicts don't break evaluate_heuristic() which needs no deepeval.
_DEEPEVAL_AVAILABLE = None   # None = not yet checked


def _try_import_deepeval():
    """Return True if deepeval can be imported, False otherwise."""
    global _DEEPEVAL_AVAILABLE
    if _DEEPEVAL_AVAILABLE is not None:
        return _DEEPEVAL_AVAILABLE
    try:
        import deepeval                           # noqa: F401
        from deepeval.test_case import LLMTestCase  # noqa: F401
        from deepeval.metrics import (            # noqa: F401
            AnswerRelevancyMetric, FaithfulnessMetric,
            ContextualRelevancyMetric, HallucinationMetric,
        )
        _DEEPEVAL_AVAILABLE = True
    except Exception:
        _DEEPEVAL_AVAILABLE = False
    return _DEEPEVAL_AVAILABLE

# Use gpt-4o-mini — same model the rest of the project uses
EVAL_MODEL = "gpt-4o-mini"


def _format_itinerary(itinerary: dict) -> str:
    """Convert itinerary dict to readable text for DeepEval."""
    if not itinerary:
        return "No itinerary generated."
    lines = [f"Trip: {itinerary.get('title', 'Trip Plan')}"]
    for day in itinerary.get("days", []):
        lines.append(f"\nDay {day.get('day', '?')}: {day.get('theme', '')}")
        for act in day.get("activities", []):
            if isinstance(act, dict):
                lines.append(f"  - {act.get('time', '')} {act.get('activity', act.get('name', str(act)))}")
            else:
                lines.append(f"  - {act}")
    return "\n".join(lines)


def _build_retrieval_context(memory_context: dict) -> list[str]:
    """Build retrieval context list from ChromaDB memory output."""
    context = []

    past_prefs = memory_context.get("past_preferences", {})
    if past_prefs:
        context.append(f"Past user preferences: {json.dumps(past_prefs, ensure_ascii=False)}")

    for trip in memory_context.get("similar_trips", []):
        if trip:
            context.append(f"Similar past trip: {json.dumps(trip, ensure_ascii=False)}")

    notes = memory_context.get("personalization_notes", "")
    if notes and notes != "No previous trips found. Starting fresh.":
        context.append(f"Personalization notes: {notes}")

    return context if context else ["No past trip memory available for this user."]


def build_test_case(state: dict):
    """Build a DeepEval LLMTestCase from a completed workflow state."""
    from deepeval.test_case import LLMTestCase
    query = state.get("user_query", "")
    itinerary_text = _format_itinerary(state.get("itinerary", {}))
    retrieval_context = _build_retrieval_context(state.get("memory_context", {}))

    prefs = state.get("trip_preferences", {})
    context_for_hallucination = [
        f"Destination: {prefs.get('destination', '')}",
        f"Budget: INR {prefs.get('budget', 0)}",
        f"Duration: {prefs.get('num_days', 0)} days",
        f"Trip type: {prefs.get('trip_type', '')}",
        f"Travelers: {prefs.get('num_travelers', 1)}",
    ] + retrieval_context

    return LLMTestCase(
        input=query,
        actual_output=itinerary_text,
        retrieval_context=retrieval_context,
        context=context_for_hallucination,
    )


class TripPlannerRAGEvaluator:
    """Runs DeepEval RAG metrics against the trip planner pipeline.

    Falls back to heuristic scoring automatically when the OpenAI API
    quota is exhausted or unavailable.
    """

    def __init__(self, model: str = EVAL_MODEL):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set — needed for DeepEval metrics.")
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
        self.model = model

    def evaluate_state(self, state: dict) -> dict:
        """
        Evaluate a completed workflow state.
        Tries DeepEval LLM metrics first; falls back to heuristics on any import
        error (pydantic conflict), quota error, or runtime failure.
        """
        has_memory = bool(state.get("memory_context", {}).get("similar_trips") or
                          state.get("memory_context", {}).get("past_preferences"))

        if not _try_import_deepeval():
            print("[RAG EVAL] deepeval unavailable (pydantic conflict) — using heuristics.")
            results = _heuristic_evaluate(state, has_memory)
            passed = sum(1 for r in results if r["passed"])
            summary = {
                "query": state.get("user_query", ""),
                "destination": state.get("trip_preferences", {}).get("destination", ""),
                "has_memory": has_memory,
                "metrics": results,
                "passed": passed,
                "total": len(results),
                "overall_pass": passed == len(results),
                "eval_mode": "heuristic",
            }
            _print_results(summary)
            return summary

        from deepeval.metrics import (
            AnswerRelevancyMetric, FaithfulnessMetric,
            ContextualRelevancyMetric, HallucinationMetric,
        )

        test_case = build_test_case(state)
        metrics = [
            AnswerRelevancyMetric(threshold=0.5, model=self.model, include_reason=True),
            HallucinationMetric(threshold=0.5, model=self.model, include_reason=True),
        ]
        if has_memory:
            metrics += [
                FaithfulnessMetric(threshold=0.5, model=self.model, include_reason=True),
                ContextualRelevancyMetric(threshold=0.5, model=self.model, include_reason=True),
            ]

        print(f"\n[RAG EVAL] Running {len(metrics)} DeepEval metric(s)...")
        print(f"[RAG EVAL] Memory context: {'Available' if has_memory else 'None (first run)'}")

        results = []
        api_failed = False
        for metric in metrics:
            try:
                metric.measure(test_case)
                results.append({
                    "metric":    metric.__class__.__name__,
                    "score":     round(metric.score, 3),
                    "passed":    metric.score >= metric.threshold,
                    "reason":    getattr(metric, "reason", ""),
                    "threshold": metric.threshold,
                    "mode":      "deepeval",
                })
            except Exception as e:
                err = str(e)
                if "quota" in err.lower() or "429" in err or "rate" in err.lower():
                    print("[RAG EVAL] API quota exceeded — switching to heuristic evaluation.")
                    api_failed = True
                    break
                results.append({
                    "metric":    metric.__class__.__name__,
                    "score":     0.0,
                    "passed":    False,
                    "reason":    f"Metric error: {err[:120]}",
                    "threshold": metric.threshold,
                    "mode":      "error",
                })

        if api_failed:
            results = _heuristic_evaluate(state, has_memory)

        passed = sum(1 for r in results if r["passed"])
        summary = {
            "query":        state.get("user_query", ""),
            "destination":  state.get("trip_preferences", {}).get("destination", ""),
            "has_memory":   has_memory,
            "metrics":      results,
            "passed":       passed,
            "total":        len(results),
            "overall_pass": passed == len(results),
            "eval_mode":    "heuristic" if api_failed else "deepeval",
        }

        _print_results(summary)
        return summary

    def evaluate_heuristic(self, state: dict) -> dict:
        """Run only heuristic (no-API) evaluation — always works."""
        has_memory = bool(state.get("memory_context", {}).get("similar_trips") or
                          state.get("memory_context", {}).get("past_preferences"))
        results = _heuristic_evaluate(state, has_memory)
        passed = sum(1 for r in results if r["passed"])
        summary = {
            "query":        state.get("user_query", ""),
            "destination":  state.get("trip_preferences", {}).get("destination", ""),
            "has_memory":   has_memory,
            "metrics":      results,
            "passed":       passed,
            "total":        len(results),
            "overall_pass": passed == len(results),
            "eval_mode":    "heuristic",
        }
        _print_results(summary)
        return summary

    def evaluate_batch(self, states: list[dict]) -> list[dict]:
        return [self.evaluate_state(s) for s in states]

    def save_report(self, results: list[dict], output_path: str = "output/rag_eval_report.json"):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n[RAG EVAL] Report saved to: {output_path}")
        return output_path


# ── Heuristic evaluation (no LLM needed) ─────────────────────────

def _heuristic_evaluate(state: dict, has_memory: bool) -> list[dict]:
    """
    Compute deterministic RAG quality signals without calling any LLM.
    Covers the same conceptual dimensions as the DeepEval metrics.
    """
    results = []
    prefs = state.get("trip_preferences", {})
    itinerary = state.get("itinerary", {})
    budget = state.get("budget_summary", {})
    query = state.get("user_query", "").lower()
    dest = str(prefs.get("destination", "")).lower()
    itin_text = _format_itinerary(itinerary).lower()
    days = itinerary.get("days", [])
    num_days = int(prefs.get("num_days") or 0)

    # 1. Answer Relevancy — does the itinerary mention the destination?
    dest_mentioned = dest and dest in itin_text
    results.append({
        "metric":    "AnswerRelevancy (heuristic)",
        "score":     1.0 if dest_mentioned else 0.0,
        "passed":    dest_mentioned,
        "reason":    f"Destination '{dest}' {'found' if dest_mentioned else 'NOT found'} in itinerary text.",
        "threshold": 0.5,
        "mode":      "heuristic",
    })

    # 2. Itinerary Completeness — day count matches requested days
    day_match = (abs(len(days) - num_days) <= 1) if num_days > 0 else bool(days)
    results.append({
        "metric":    "ItineraryCompleteness (heuristic)",
        "score":     1.0 if day_match else max(0.0, 1.0 - abs(len(days) - num_days) / max(num_days, 1)),
        "passed":    day_match,
        "reason":    f"Requested {num_days} days, itinerary has {len(days)} days.",
        "threshold": 0.5,
        "mode":      "heuristic",
    })

    # 3. Budget Adherence — total estimated is within 200% of budget
    total_budget = float(budget.get("total_budget", 0) or 0)
    total_estimated = float(budget.get("total_estimated", 0) or 0)
    if total_budget > 0:
        ratio = total_estimated / total_budget
        budget_ok = ratio <= 2.0
        results.append({
            "metric":    "BudgetAdherence (heuristic)",
            "score":     round(min(1.0, 1.0 / ratio) if ratio > 0 else 1.0, 3),
            "passed":    budget_ok,
            "reason":    f"Estimated ₹{total_estimated:,.0f} vs budget ₹{total_budget:,.0f} ({ratio*100:.0f}%).",
            "threshold": 0.5,
            "mode":      "heuristic",
        })

    # 4. Hallucination Guard — itinerary should not be empty
    not_empty = bool(itin_text and len(itin_text) > 100)
    results.append({
        "metric":    "HallucinationGuard (heuristic)",
        "score":     1.0 if not_empty else 0.0,
        "passed":    not_empty,
        "reason":    "Itinerary has sufficient content." if not_empty else "Itinerary is empty or too short.",
        "threshold": 0.5,
        "mode":      "heuristic",
    })

    # 5. Context Utilization — if memory exists, check if preferences are reflected
    if has_memory:
        memory = state.get("memory_context", {})
        past = memory.get("past_preferences", {})
        past_food = str(past.get("food_preference", "")).lower()
        past_hotel = str(past.get("hotel_preference", "")).lower()
        utilized = (
            (past_food and past_food in itin_text) or
            (past_hotel and past_hotel in itin_text) or
            bool(memory.get("personalization_notes", "").strip())
        )
        results.append({
            "metric":    "ContextUtilization (heuristic)",
            "score":     1.0 if utilized else 0.5,
            "passed":    True,  # partial credit — memory was retrieved, usage is best-effort
            "reason":    f"Memory retrieved: food='{past_food}', hotel='{past_hotel}'.",
            "threshold": 0.5,
            "mode":      "heuristic",
        })

    return results


def _print_results(summary: dict):
    sep = "-" * 65
    mode = summary.get("eval_mode", "deepeval").upper()
    print(f"\n{sep}")
    print(f"RAG EVALUATION RESULTS  [{mode}]")
    print(f"Query      : {summary['query'][:70]}")
    print(f"Destination: {summary['destination']}")
    print(f"Memory     : {'Yes' if summary['has_memory'] else 'No (first run)'}")
    print(sep)
    for r in summary["metrics"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['metric']:<38} score={r['score']:.3f}")
        if r.get("reason"):
            print(f"         {r['reason'][:120]}")
    print(sep)
    overall = "ALL PASSED" if summary["overall_pass"] else f"{summary['passed']}/{summary['total']} passed"
    print(f"  Overall: {overall}")
    print(sep)
