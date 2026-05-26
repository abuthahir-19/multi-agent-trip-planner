"""LangSmith observability helpers for the multi-agent trip planner.

Tracing is activated automatically when LANGCHAIN_API_KEY and
LANGCHAIN_TRACING_V2=true are present in the environment (loaded from .env
or set as Render env vars).  No code change is needed to toggle it on/off.
"""
import os
from contextlib import contextmanager, nullcontext
from typing import Optional


# ─────────────────────────────────────────────────────────────────
# Status helpers
# ─────────────────────────────────────────────────────────────────

def is_tracing_enabled() -> bool:
    """Return True when both the API key and tracing flag are present."""
    return bool(
        os.environ.get("LANGCHAIN_API_KEY")
        and os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
    )


def get_project_url() -> str:
    """Return the LangSmith project dashboard URL."""
    project = os.environ.get("LANGCHAIN_PROJECT", "multi-agent-trip-planner")
    return f"https://smith.langchain.com/projects/{project}"


# ─────────────────────────────────────────────────────────────────
# Run configuration
# ─────────────────────────────────────────────────────────────────

def get_run_config(user_id: str, destination: str, query: str) -> dict:
    """Build a LangGraph run config dict with LangSmith metadata.

    Pass the returned dict as the ``config=`` argument to ``graph.stream()``.
    When tracing is disabled the dict is still valid — LangGraph ignores
    unknown keys, so this is always safe to pass.
    """
    return {
        "run_name": f"trip_plan_{destination.lower().replace(' ', '_')}",
        "tags": ["trip-planner", "multi-agent", "langgraph"],
        "metadata": {
            "user_id": user_id,
            "destination": destination,
            "query_length": len(query),
        },
    }


# ─────────────────────────────────────────────────────────────────
# Run ID capture
# ─────────────────────────────────────────────────────────────────

@contextmanager
def capture_run_id():
    """Context manager that yields a mutable dict.

    After the ``with`` block the dict contains ``run_id`` (str or None).

    Usage::

        with capture_run_id() as run_meta:
            for step in graph.stream(...):
                ...
        run_id = run_meta.get("run_id")
    """
    meta = {"run_id": None}

    if not is_tracing_enabled():
        yield meta
        return

    try:
        from langchain_core.tracers.context import collect_runs
        with collect_runs() as cb:
            yield meta
        if cb.traced_runs:
            meta["run_id"] = str(cb.traced_runs[0].id)
    except Exception:
        yield meta


# ─────────────────────────────────────────────────────────────────
# Feedback submission
# ─────────────────────────────────────────────────────────────────

def submit_feedback(run_id: Optional[str], eval_results: dict) -> str:
    """Post RAG evaluation scores as LangSmith feedback entries.

    Returns a short status string suitable for display in the UI.
    """
    if not is_tracing_enabled():
        return "LangSmith tracing not enabled — feedback skipped."
    if not run_id:
        return "No run ID captured — feedback skipped."

    try:
        from langsmith import Client
        client = Client()
        metrics = eval_results.get("metrics", [])
        for m in metrics:
            key = (
                m["metric"]
                .replace(" (heuristic)", "")
                .lower()
                .replace(" ", "_")
            )
            client.create_feedback(
                run_id=run_id,
                key=key,
                score=float(m.get("score", 0)),
                comment=m.get("reason", ""),
            )
        return f"Submitted {len(metrics)} feedback score(s) for run {run_id[:8]}…"
    except Exception as exc:
        return f"Feedback submission error: {exc}"


# ─────────────────────────────────────────────────────────────────
# Trace URL
# ─────────────────────────────────────────────────────────────────

def get_trace_url(run_id: Optional[str]) -> Optional[str]:
    """Return a direct LangSmith trace URL for the given run ID, or None."""
    if not run_id or not is_tracing_enabled():
        return None
    try:
        from langsmith import Client
        client = Client()
        # read_run gives us a Run object; its url field (if present) is canonical
        run = client.read_run(run_id)
        url = getattr(run, "url", None)
        if url:
            return url
    except Exception:
        pass
    # Fallback: construct URL from known run_id (works for most orgs)
    project = os.environ.get("LANGCHAIN_PROJECT", "multi-agent-trip-planner")
    return f"https://smith.langchain.com/projects/{project}/runs/{run_id}"
