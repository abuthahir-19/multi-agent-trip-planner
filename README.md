# Multi-Agent Trip Planner

An AI-powered travel planning system built with **LangGraph** and **LangChain** that uses a team of specialized agents to generate complete, personalized trip plans — including weather forecasts, hotel options, transport routes, day-wise itineraries, budget breakdowns, and a downloadable PDF report.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Agent Descriptions](#agent-descriptions)
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
┌─────────────────┐
│ Memory Retrieval│  ← Loads past trips / user preferences from ChromaDB
└────────┬────────┘
         │
    ┌────┴─────────────────────────────┐
    │         Parallel Research        │
    │  ┌──────────┐  ┌─────────────┐  │
    │  │ Weather  │  │  Transport  │  │
    │  └──────────┘  └─────────────┘  │
    │  ┌──────────┐  ┌─────────────┐  │
    │  │  Hotels  │  │   Places    │  │
    │  └──────────┘  └─────────────┘  │
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
