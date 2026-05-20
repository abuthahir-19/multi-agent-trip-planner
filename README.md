# Multi-Agent Trip Planner

An AI-powered travel planning system built with **LangGraph** and **LangChain** that uses a team of specialized agents to generate complete, personalized trip plans — including weather forecasts, hotel options, transport routes, day-wise itineraries, budget breakdowns, and a downloadable PDF report.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Agent Descriptions](#agent-descriptions)
- [Guardrails](#guardrails)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output](#output)

---

## Overview

This project demonstrates a **multi-agent orchestration pattern** where a supervisor (orchestrator) agent coordinates a pipeline of specialized sub-agents. Each agent handles one domain of travel planning, passes its results into a shared state, and the orchestrator decides what runs next — including retrying failed steps.

The system supports both a **command-line interface** (`main.py`) and a **Streamlit web app** (`app.py`).

---

## Features

- Natural language trip query parsing
- Real-time weather forecast and travel advisory
- Hotel search with budget-based filtering
- Transport options (flight / train / car / bus)
- Attraction and dining discovery
- Automated budget aggregation and per-person cost breakdown
- AI-generated day-wise itinerary with timings
- Quality review gate with retry logic
- PDF trip report generation
- Persistent memory via ChromaDB (stores past trips and user preferences)
- Streamlit web UI with tabbed results view
- **Multi-layer guardrail system** — input validation, output sanity checks, and cross-agent consistency enforcement

---

## Architecture

The workflow is implemented as a **LangGraph state graph**. The orchestrator agent decides routing at each step. After a quality review, the plan is either approved (→ PDF generation) or specific agents are retried.

```
User Query
    │
    ▼
┌─────────────────┐
│   Orchestrator  │  ← Supervisor: decides next step
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  User Input     │  ← Parses query into structured preferences
└────────┬────────┘
         │
         ▼
┌══════════════════╗
║ Input Guardrail  ║  ← Security layer 1: injection check, PII scan, preference validation
╚════════╤═════════╝
         │
         ▼
┌─────────────────┐
│ Memory Retrieval│  ← Loads past trips / user preferences from ChromaDB
└────────┬────────┘
         │
    ┌────┴─────────────────────────────┐
    │         Parallel Research        │
    │  ┌──────────┐  ┌─────────────┐   │
    │  │ Weather  │  │  Transport  │   │
    │  └──────────┘  └─────────────┘   │
    │  ┌──────────┐  ┌─────────────┐   │
    │  │  Hotels  │  │   Places    │   │
    │  └──────────┘  └─────────────┘   │
    └────────────────┬─────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │     Budget      │  ← Aggregates all costs
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   Itinerary     │  ← Generates day-wise plan
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │     Review      │  ← Quality check + budget validation
            └────────┬────────┘
                     │
            ╔════════╧═════════╗
            ║ Output Guardrail ║  ← Security layer 2: consistency, budget sanity, itinerary completeness
            ╚════════╤═════════╝
                     │
           ┌─────────┴──────────┐
           │  Orchestrator      │
           │  Validation Gate   │
           └─────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          │ APPROVED            │ RETRY
          ▼                     ▼
┌──────────────────┐   Back to failed agent
│  Memory Update   │   (hotel / transport /
└────────┬─────────┘    itinerary / places)
         │
         ▼
┌──────────────────┐
│  PDF Generator   │  ← Produces downloadable trip report
└──────────────────┘
```

---

## Agent Descriptions

| Agent | Role |
|---|---|
| **Orchestrator** | Supervisor agent that decides which agent runs next and validates the final plan |
| **User Input** | Parses a natural language query into structured trip preferences (destination, dates, budget, etc.) |
| **Memory Retrieval** | Queries ChromaDB for past user trips and preferences to personalize the plan |
| **Weather** | Fetches destination weather forecast and generates a travel advisory |
| **Transport** | Searches for transport options (flights, trains, etc.) filtered by budget and preference |
| **Hotel** | Finds hotels matching the traveler's budget (~30% allocation), style, and dates |
| **Places** | Discovers tourist attractions, local experiences, and dining spots |
| **Budget** | Aggregates all cost components and checks against the user's total budget |
| **Itinerary** | Uses an LLM to generate a detailed, day-by-day activity plan with timings and costs |
| **Review** | Quality control agent that scores completeness, flags conflicts, and recommends retries |
| **Memory Update** | Saves the completed trip plan and preferences back to ChromaDB for future personalization |
| **PDF Generator** | Renders the approved trip plan into a formatted, downloadable PDF report |

---

## Guardrails

The system includes a **multi-layer guardrail framework** (`guardrails/`) that protects the pipeline at both ends of the workflow and enforces cross-agent consistency.

### Layer 1 — Input Guardrail (`input_guardrail_node`)

Inserted **after `user_input_agent`**, before memory retrieval. Runs every time a new user query enters the system.

| Check | Details |
|---|---|
| **Prompt injection detection** | Regex-based scan for 14+ attack patterns: role overrides, jailbreak keywords (`DAN mode`, `god mode`), SQL injection, path traversal, script/template injection, hex-encoding evasion |
| **PII detection** | Advisory scan for credit/debit card numbers, Aadhaar, PAN, SSN, email addresses, and exposed credentials — logged as warnings |
| **Query sanitization** | Strips HTML tags, `javascript:` schemes, `{{ }}` / `${ }` template expressions, and hex escapes; normalises whitespace; truncates to 1000 characters |
| **Trip preference validation** | Checks that `destination`, `budget`, `num_days`, and `num_travelers` are present and within sane bounds (budget: ₹500 – ₹5 cr; days: 1 – 365; travelers: 1 – 500) |
| **Auto-fix** | Zero or missing `budget` → ₹30,000; zero/missing `num_days` → 5; zero/missing `num_travelers` → 1 |
| **Hard block** | If an injection attack is detected, `state.status` is set to `"blocked"` and the workflow halts |

### Layer 2 — Output Guardrail (`output_guardrail_node`)

Inserted **after `review_agent`**, before the orchestrator validation gate. Runs on the fully assembled plan.

| Check | Details |
|---|---|
| **State field integrity** | Verifies that `messages`, `error_log`, and `guardrail_log` are lists; `retry_count` is a non-negative int; `status` is a known value |
| **Cross-agent consistency** | Hotel location must match the requested destination; flight arrival city must match destination; `budget_summary.total_budget` must be within 10% of `trip_preferences.budget`; itinerary day count must match `num_days` (±1) |
| **Budget sanity** | Checks `total_budget` and `total_estimated` against absolute INR bounds; flags if estimated cost exceeds budget by more than 10× (likely a calculation error) |
| **Itinerary completeness** | Every day entry must be a dict with at least one of `activities`, `morning`, `afternoon`, or `evening` populated |
| **Review schema** | Confirms `review_agent` output contains `approved` and `quality_score` fields |
| **Retry loop detection** | Flags if `retry_count` exceeds 5, indicating a potential infinite retry loop |

### Layer 3 — Agent Prerequisites (`validate_state_before_agent`)

Defined in `agent_guard.py` and callable from any agent before it starts processing. Each agent has a declared list of required state fields; a missing field triggers an early error rather than a silent downstream failure.

| Agent | Required state fields |
|---|---|
| `memory_retrieval_agent` | `user_query`, `trip_preferences` |
| `weather_agent` / `transport_agent` / `hotel_agent` / `places_agent` | `trip_preferences` |
| `budget_agent` | `trip_preferences`, `transport_data`, `hotel_data` |
| `itinerary_agent` | `trip_preferences`, `weather_data`, `transport_data`, `hotel_data`, `places_data`, `budget_summary` |
| `review_agent` | `trip_preferences`, `itinerary`, `budget_summary` |
| `orchestrator_validate` | `review_status` |
| `memory_update_agent` / `pdf_generator_agent` | `trip_preferences` |

### PII Scrubbing (`scrub_pii`)

Available in `output_guard.py` for use before any generated text is written to the PDF or displayed in the UI. Redacts card numbers, Aadhaar, PAN, SSN, email addresses, and credential strings with safe `[REDACTED]` tokens.

### Guardrail Log

All guardrail events are appended to `state.guardrail_log` (a cumulative list) so every flag is visible in the Streamlit UI and in the console output. The Streamlit app renders guardrail messages in a dedicated styled card.

### Guardrail Module Structure

```
guardrails/
├── __init__.py            # Public API re-exports
├── input_guard.py         # validate_user_query, sanitize_text, validate_trip_preferences
├── output_guard.py        # validate_agent_output, validate_budget_output,
│                          # validate_itinerary_output, check_price_sanity, scrub_pii
├── agent_guard.py         # validate_state_before_agent, check_inter_agent_consistency,
│                          # check_state_field_integrity
└── guardrail_nodes.py     # LangGraph node functions: input_guardrail_node, output_guardrail_node
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM framework | [LangChain](https://github.com/langchain-ai/langchain) |
| Language model | OpenAI `gpt-4o-mini` |
| Vector memory | [ChromaDB](https://www.trychroma.com/) |
| PDF generation | [ReportLab](https://www.reportlab.com/) |
| Web UI | [Streamlit](https://streamlit.io/) |
| Weather data | OpenWeatherMap API |
| Environment config | python-dotenv |

---

## Project Structure

```
MultiAgentTripPlanner/
├── main.py                    # CLI entry point
├── app.py                     # Streamlit web app
├── requirements.txt
├── .env                       # Your API keys (never commit this)
├── .env.example               # Safe template — commit this
│
├── agents/                    # One file per specialized agent
│   ├── orchestrator_agent.py
│   ├── user_input_agent.py
│   ├── weather_agent.py
│   ├── hotel_agent.py
│   ├── transport_agent.py
│   ├── places_agent.py
│   ├── budget_agent.py
│   ├── itinerary_agent.py
│   ├── review_agent.py
│   ├── memory_agent.py
│   └── pdf_generator_agent.py
│
├── tools/                     # External API / utility wrappers
│   ├── weather_tool.py
│   ├── hotel_tool.py
│   ├── transport_tool.py
│   ├── places_tool.py
│   ├── budget_tool.py
│   └── pdf_tool.py
│
├── guardrails/                # Multi-layer safety & validation framework
│   ├── __init__.py
│   ├── input_guard.py         # Prompt injection, PII detection, query sanitization
│   ├── output_guard.py        # Schema validation, price sanity, PII scrubbing
│   ├── agent_guard.py         # Prerequisite checks, cross-agent consistency
│   └── guardrail_nodes.py     # LangGraph nodes: input_guardrail_node, output_guardrail_node
│
├── workflow/
│   └── graph.py               # LangGraph state graph definition
│
├── state/
│   └── trip_state.py          # Shared TypedDict state schema
│
├── memory/
│   ├── vector_store.py        # ChromaDB read/write helpers
│   └── session_store.py       # In-memory session fallback
│
├── config/
│   └── settings.py            # Loads env vars, exposes get_llm()
│
└── output/                    # Generated PDFs and ChromaDB files (git-ignored)
```

---

## Prerequisites

- Python 3.10 or higher
- An **OpenAI API key** (required) — [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- An **OpenWeatherMap API key** (optional, free tier) — [openweathermap.org](https://openweathermap.org/api)

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/MultiAgentTripPlanner.git
   cd MultiAgentTripPlanner
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

1. Copy the example env file:

   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in your keys:

   ```env
   OPENAI_API_KEY=sk-...          # Required
   OPENWEATHER_API_KEY=...        # Optional — enables live weather
   ```

   All other keys in `.env.example` are optional. The system uses smart mock data for any API that is not configured.

---

## Usage

### Streamlit Web App (recommended)

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser. Fill in the sidebar form and click **Plan My Trip**.

The results are displayed in tabs:
- **Itinerary** — day-by-day activity plan
- **Hotels** — recommended accommodation options
- **Transport** — route and transport options
- **Budget** — cost breakdown per person
- **Attractions** — places to visit and dining spots

A PDF download button appears once the plan is approved.

### Command-Line Interface

```bash
python main.py
```

Enter your trip query when prompted, for example:

```
Plan a 5-day trip to Goa for 2 people with a budget of ₹30,000.
We prefer beach activities, good seafood, and mid-range hotels.
```

The agent workflow streams its progress to the console and saves a PDF to the `output/` folder on completion.

---

## Output

- **PDF reports** are saved to `output/TripPlan_<Destination>_<Timestamp>.pdf`
- **Vector memory** (ChromaDB) is stored at `output/chroma_db/` and persists across sessions to improve future recommendations

Both locations are git-ignored and stay local to your machine.
