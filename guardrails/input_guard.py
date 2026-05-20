"""Input-level guardrails: prompt injection, PII detection, budget and destination validation."""
import re
from typing import Tuple, List

# ── Prompt injection & attack patterns ───────────────────────────
INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions?", "prompt injection"),
    (r"you\s+are\s+now\s+(a\s+|an\s+|the\s+)?\w+", "role override"),
    (r"forget\s+(your|all|the|previous)\s+(instructions?|rules?|guidelines?|system)", "instruction override"),
    (r"\bact\s+as\s+(a|an|the|if)\s+", "persona hijacking"),
    (r"\b(jailbreak|DAN\s+mode|developer\s+mode|god\s+mode)\b", "jailbreak attempt"),
    (r"<\s*script[^>]*>", "script injection"),
    (r"javascript\s*:", "javascript injection"),
    (r"\bSELECT\b.{0,30}\bFROM\b", "SQL injection"),
    (r"\bDROP\b.{0,20}\bTABLE\b", "SQL DROP injection"),
    (r";\s*(--|//|/\*)", "SQL comment injection"),
    (r"(\.\./){2,}", "path traversal"),
    (r"\b(reveal|show|print|output)\s+(your|the)\s+(prompt|system|instructions?|context)\b", "system prompt extraction"),
    (r"\$\{.{0,50}\}", "template injection"),
    (r"\{\{.{0,50}\}\}", "template injection"),
    (r"\\x[0-9a-fA-F]{2}", "hex encoding evasion"),
]

# ── PII patterns ──────────────────────────────────────────────────
PII_PATTERNS = [
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "credit/debit card number"),
    (r"\b\d{12}\b", "potential Aadhaar number"),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "PAN card number"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "email address"),
    (r"\b(?:password|passwd|pwd|secret|api[_-]?key|token)\s*[=:]\s*\S+", "credential exposure"),
]

MAX_QUERY_LENGTH = 1000
MIN_BUDGET_INR = 500
MAX_BUDGET_INR = 50_000_000  # 5 crore INR

VALID_TRIP_TYPES = {"solo", "couple", "family", "business", "group"}
VALID_HOTEL_PREFS = {"budget", "3-star", "4-star", "5-star", "luxury", "beach resort", "heritage", "hostel", "resort"}
VALID_TRANSPORT_PREFS = {"flight", "train", "car", "bus", "any"}


def validate_user_query(query: str) -> Tuple[bool, List[str]]:
    """
    Validate raw user query for injection attacks and PII.
    Returns (is_safe, list_of_violations).
    Injection attacks → blocked (is_safe=False).
    PII → logged as warning but not blocked.
    """
    if not query or not query.strip():
        return False, ["Empty or blank query"]

    violations = []

    if len(query) > MAX_QUERY_LENGTH:
        violations.append(f"Query too long: {len(query)} chars (max {MAX_QUERY_LENGTH})")

    # Injection detection (blocking)
    q_lower = query.lower()
    blocking_labels = set()
    for pattern, label in INJECTION_PATTERNS:
        if re.search(pattern, q_lower, re.IGNORECASE):
            violations.append(f"Security: {label} detected in input")
            blocking_labels.add(label)

    # PII detection (non-blocking, advisory only)
    for pattern, label in PII_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            violations.append(f"PII warning: {label} found in query — will be sanitized")

    is_safe = (len(blocking_labels) == 0) and (len(query) <= MAX_QUERY_LENGTH)
    return is_safe, violations


def sanitize_text(text: str) -> str:
    """Strip HTML/script tags, dangerous patterns, and normalize whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)                          # strip HTML tags
    text = re.sub(r"javascript\s*:", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\{\{.*?\}\}", "", text)                       # strip template expressions
    text = re.sub(r"\$\{.*?\}", "", text)
    text = re.sub(r"\\x[0-9a-fA-F]{2}", "", text)                # strip hex escapes
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_QUERY_LENGTH]


def validate_trip_preferences(prefs: dict) -> Tuple[bool, List[str]]:
    """
    Validate extracted trip preferences from user_input_agent output.
    Returns (is_valid, list_of_issues).
    """
    if not prefs:
        return False, ["Trip preferences are empty"]

    issues = []

    # Destination
    dest = prefs.get("destination", "")
    if not dest or str(dest).lower() in ("null", "none", "", "n/a", "not set"):
        issues.append("Destination is missing or null")
    elif re.match(r"^\d+$", str(dest).strip()):
        issues.append(f"Destination looks like a number, not a city: '{dest}'")
    elif len(str(dest)) > 100:
        issues.append("Destination name is unusually long (possible injection)")

    # Budget bounds
    budget = prefs.get("budget", 0)
    try:
        budget = float(budget or 0)
        if budget < MIN_BUDGET_INR:
            issues.append(f"Budget too low: ₹{budget:.0f} (minimum ₹{MIN_BUDGET_INR})")
        elif budget > MAX_BUDGET_INR:
            issues.append(f"Budget suspiciously high: ₹{budget:.0f} — possible data error")
    except (TypeError, ValueError):
        issues.append(f"Budget is not a valid number: '{budget}'")

    # Days
    try:
        num_days = int(prefs.get("num_days") or 0)
        if num_days < 1:
            issues.append("num_days must be at least 1")
        elif num_days > 365:
            issues.append(f"Unrealistic trip duration: {num_days} days (max 365)")
    except (TypeError, ValueError):
        issues.append(f"num_days is not a valid integer: '{prefs.get('num_days')}'")

    # Travelers
    try:
        pax = int(prefs.get("num_travelers") or 1)
        if pax < 1:
            issues.append("num_travelers must be at least 1")
        elif pax > 500:
            issues.append(f"Unusually high traveler count: {pax}")
    except (TypeError, ValueError):
        issues.append(f"num_travelers is not valid: '{prefs.get('num_travelers')}'")

    return len(issues) == 0, issues
