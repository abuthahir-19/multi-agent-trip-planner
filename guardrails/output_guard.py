"""Output-level guardrails: schema validation, price sanity checks, PII scrubbing."""
import re
from typing import Tuple, List, Any

# ── Required fields per agent output ─────────────────────────────
AGENT_OUTPUT_SCHEMAS = {
    "user_input_agent":    ["destination", "budget", "num_days", "num_travelers"],
    "weather_agent":       ["city", "forecast"],
    "transport_agent":     ["flights", "trains"],
    "hotel_agent":         ["hotels"],
    "places_agent":        ["attractions"],
    "budget_agent":        ["total_budget", "total_estimated", "breakdown"],
    "itinerary_agent":     ["days", "title"],
    "review_agent":        ["approved", "quality_score"],
    "pdf_generator_agent": ["generated"],
}

# ── Price sanity bounds (INR) ─────────────────────────────────────
PRICE_BOUNDS = {
    "flight_per_person":  (500,    200_000),
    "train_per_person":   (100,     20_000),
    "hotel_per_night":    (200,    100_000),
    "budget_total":       (500, 50_000_000),
    "budget_per_day":     (100,    500_000),
}

# ── PII redaction map ─────────────────────────────────────────────
PII_REDACT_PATTERNS = [
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",                "[CARD REDACTED]"),
    (r"\b\d{12}\b",                                               "[AADHAAR REDACTED]"),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b",                                  "[PAN REDACTED]"),
    (r"\b\d{3}-\d{2}-\d{4}\b",                                   "[SSN REDACTED]"),
    (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",         "[EMAIL REDACTED]"),
    (r"\b(?:password|passwd|token|api[_-]?key)\s*[=:]\s*\S+",    "[CREDENTIAL REDACTED]"),
]


def validate_agent_output(agent_name: str, output: dict) -> Tuple[bool, List[str]]:
    """
    Check that agent output contains required fields and is not an error response.
    Returns (is_valid, list_of_issues).
    """
    if not output:
        return False, [f"{agent_name}: output is empty or None"]

    issues = []
    required = AGENT_OUTPUT_SCHEMAS.get(agent_name, [])
    for field in required:
        val = output.get(field)
        if val is None or val == "" or val == [] or val == {}:
            issues.append(f"{agent_name}: required field '{field}' is missing or empty")

    if output.get("error"):
        issues.append(f"{agent_name}: output contains error flag: {output['error']}")

    return len(issues) == 0, issues


def check_price_sanity(value: Any, price_type: str) -> Tuple[bool, str]:
    """
    Detect hallucinated or corrupted prices.
    Returns (is_sane, message).
    """
    bounds = PRICE_BOUNDS.get(price_type)
    if not bounds:
        return True, ""
    try:
        v = float(value)
        lo, hi = bounds
        if v < lo:
            return False, f"Price too low for {price_type}: ₹{v:.0f} (min ₹{lo})"
        if v > hi:
            return False, f"Price too high for {price_type}: ₹{v:.0f} (max ₹{hi:,})"
    except (TypeError, ValueError):
        return False, f"Price is not a number for {price_type}: '{value}'"
    return True, ""


def validate_budget_output(budget_summary: dict) -> Tuple[bool, List[str]]:
    """Validate budget agent output for data sanity."""
    if not budget_summary:
        return False, ["Budget summary is empty"]

    issues = []
    total_budget = budget_summary.get("total_budget", 0)
    total_estimated = budget_summary.get("total_estimated", 0)

    sane, msg = check_price_sanity(total_budget, "budget_total")
    if not sane:
        issues.append(msg)

    sane, msg = check_price_sanity(total_estimated, "budget_total")
    if not sane:
        issues.append(msg)

    # Over by more than 10x suggests a data error, not a legit overage
    try:
        if float(total_budget) > 0 and float(total_estimated) > float(total_budget) * 10:
            issues.append(
                f"Estimated ₹{total_estimated:,} is >10x the budget ₹{total_budget:,} — possible calculation error"
            )
    except (TypeError, ValueError):
        pass

    return len(issues) == 0, issues


def validate_itinerary_output(itinerary: dict) -> Tuple[bool, List[str]]:
    """Validate itinerary agent output structure."""
    if not itinerary:
        return False, ["Itinerary is empty"]

    issues = []
    days = itinerary.get("days", [])
    if not days:
        issues.append("Itinerary has no days")
        return False, issues

    for i, day in enumerate(days):
        if not isinstance(day, dict):
            issues.append(f"Day {i+1} is not a dict (got {type(day).__name__})")
            continue
        has_activities = (
            day.get("activities") or day.get("morning") or
            day.get("afternoon") or day.get("evening")
        )
        if not has_activities:
            issues.append(f"Day {i+1} has no activities")

    return len(issues) == 0, issues


def scrub_pii(text: str) -> str:
    """Redact PII patterns from any generated text before it appears in PDF or UI."""
    if not text:
        return text
    for pattern, replacement in PII_REDACT_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text
