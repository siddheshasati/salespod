# Autonomous Sales Pod

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-Dual%20Servers-green.svg)](https://github.com/jlowin/fastmcp)
[![LangGraph](https://img.shields.io/badge/LangGraph-Compatible-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%7C%20Vite%20%7C%20Tailwind-blueviolet.svg)](frontend/)
[![Offline First](https://img.shields.io/badge/Architecture-Offline--First-success.svg)](#offline-first--local-llm-architecture)
[![Tests Passing](https://img.shields.io/badge/Tests-28%2F28%20Passing-emerald.svg)](#verification--code-quality)

**Autonomous Sales Pod** is a production-oriented, offline-first AI revenue engine and manager command center. It unifies a deterministic synthetic CRM, transactional application services, a dual FastMCP tool boundary (`salespod-mcp` and `salespod-signals-mcp`), an autonomous 9-stage event-driven GTM engine, a LangGraph-compatible supervisor flow, and an interactive executive dashboard.

The system ensures that autonomous agents cannot mutate CRM state or dispatch customer communications unchecked: every action flows through transactional application services with optimistic concurrency control, idempotency guards, automated 5-gate compliance checks, and human-in-the-loop approvals.

---

## Documentation Quick Links

- [System Architecture Specification](docs/architecture.md): Subsystems, hexagonal boundaries, concurrency control, and schema lifecycle.
- [Business Case & GTM Strategy](docs/business.md): Problem space, multi-threading value drivers, ROI economics, and persona impacts.
- [9-Stage Signal Pipeline Guide](docs/pipeline.md): Comprehensive operational and technical specification of the event-driven signal flow.

---

## Visual Showcase & Features

### 1. Executive Command Center & Forecast Shape
![Executive Command Center](images/1.png)

The **Command Center** gives revenue leaders real-time visibility into pipeline health and pod activity:

- **Executive KPI Telemetry**: Real-time tracking of gross **Tracked Pipeline** ($12.6M across 120 deals), probability-adjusted **Weighted Forecast** ($5.1M coverage), active **Deals at Risk** (5 deals flagged, 1 awaiting manager intervention), and cumulative **Pod Activity** stream actions.
- **Revenue Coverage by Stage (Forecast Shape)**: Dynamic visual comparison of gross pipeline against probability-weighted forecast amounts across every stage of the sales cycle (Discovery, Qualification, Proposal, Negotiation, Closed Won).
- **Pipeline Mix & Stage Breakdown**: Live deal distribution across stages with deal counts and value summaries.
- **Pod Health & Connectivity**: Instant monitoring of CRM connectivity, supervisor graph status, and signal stream readiness with one-click CRM resynchronization.

---

### 2. Deep Forecast Analytics & Human-in-the-Loop (HITL) Governance
![Forecast Shape and Human-in-the-Loop Approvals](images/2.png)

Autonomous execution requires enterprise-grade governance. Sales Pod balances autonomy with strict safety controls:

- **Granular Forecast Inspection**: Interactive hover drill-downs into stage metrics (e.g., inspecting the *Negotiation* stage showing $2,121,806 gross vs. $1,379,174 weighted value) to understand conversion probabilities.
- **Evidence-Backed Approval Inbox**: High-risk actions (such as deals missing an economic buyer, stalled negotiations, or sensitive account adjustments) are routed to the manager's review queue with grounded evidence from call transcripts and email history. Managers can approve or reject with decision notes before any deal is mutated.
- **Pod Activity & Immutable Audit Feed**: Complete chronological trace of every autonomous action, meeting logged, note appended, and stage transition executed by the agent pod.

---

### 3. Scored Lead Prioritization & AI Supervisor Console
![Scored Lead Prioritization and AI Supervisor Console](images/3.png)

Revenue teams get targeted guidance on where to spend effort, paired with an always-on conversational AI copilot:

- **Prioritization Queue ("Leads to work next")**: AI-scored lead workbench sorting prospects by fit score, company account, title, assigned pod owner, and lifecycle status (`QUALIFIED`, `CONTACTED`, `NEW`, `CONVERTED`, `DISQUALIFIED`) to guide the pod's next research or outreach motions.
- **Supervisor Console ("Ask the pod")**: An embedded conversational copilot connected directly to the CRM via typed FastMCP tools and LangGraph. Revenue managers can query pipeline status, ask analytical questions (e.g., *"Why will we miss Q4?"*, *"Show current pipeline"*, *"Find leads at example.com"*), and request guarded updates in natural language.

---

### 4. Real-Time Signal Radar & Autonomous 9-Stage GTM Pipeline

The **Signal Radar** acts as the trigger engine of the pod, translating unstructured market signals into multi-threaded outbound sales sequences:

- **Live Simulated Event Stream**: Generates real corporate triggers across 5 vital categories:
  1. **Funding round**: Capital expansion, valuation context, and growth mandate.
  2. **New CTO**: Engineering leadership appointments and tech roadmap re-evaluations.
  3. **Layoffs / Restructure**: Tool consolidation and cost-efficiency pressures.
  4. **Tech-stack migration**: Adoptions of cloud, data warehouse, and security tooling.
  5. **Leadership change**: VP of Sales / CRO transitions and strategic GTM pivots.
- **9-Stage Autonomous Pod Sequence**:
  ```text
  Signal Event ➔ Account Research (signals-mcp) ➔ Lead/ICP Scoring ➔
  Buying Committee Mapping ➔ 3 Email Variants ➔ Policy & Compliance Check ➔
  Approval Inbox Enqueue ➔ Sandbox Dispatch ➔ CRM Activity & Audit Logging
  ```
- **Interactive 9-Stage Modal Visualizer**:
  - **Live Step Progress Stepper**: Visual execution tracking across research, scoring, committee mapping, copy generation, and clearance.
  - **Multi-Angle Email Variants**: Inspect 3 tailored drafts (*Strategic ROI-driven*, *Technical integration-focused*, *Direct executive peer note*).
  - **Buying Committee Mapping**: Inspect identified Economic Buyer, Technical Buyer, and Champion with fit scores and strategic rationales.
  - **`signals-mcp` Live Telemetry**: Live tech stack categorization and corporate news dossier.
  - **Compliance Clearance**: 5-rule safety scan (CAN-SPAM, opt-out clarity, accurate attribution, non-coercive tone, verified recipient persona).
  - **One-Click Sandbox Dispatch**: Human manager sign-off dispatches to mock SMTP sandbox, updates the CRM timeline, and records an immutable audit log entry.

---

## Core Use Cases

| Use Case | Description | How It Works |
| :--- | :--- | :--- |
| **Event-Driven Signal GTM** | Act on critical market events before competitors even notice. | Simulated or ingested corporate triggers run through the autonomous 9-stage pipeline to generate committee-mapped, compliance-cleared outreach. |
| **Multi-Threaded Committee Mapping** | Prevent stalled deals by reaching Economic, Technical, and Champion stakeholders simultaneously. | Automatically maps corporate hierarchy and generates differentiated messaging angles tailored to each role's priorities. |
| **Pipeline & Forecast Intelligence** | Maintain accurate, real-time revenue forecasts without manual spreadsheet rollups. | The engine aggregates stage totals, applies deterministic probability weighting, and visualizes pipeline health against targets. |
| **Human-in-the-Loop Risk Intervention** | Prevent agent hallucinations or unauthorized changes from corrupting CRM data. | Risky deal transitions and external outbound emails require manager sign-off backed by grounded citations and compliance logs. |
| **Natural Language CRM Operations** | Query deals, leads, and company accounts conversationally from Slack, CLI, or the UI. | LangGraph supervisor routes user prompts through typed FastMCP tools (`search_leads`, `get_deal`, `get_pipeline_snapshot`). |
| **Safe Transactional Deal Management** | Maintain strict data integrity under concurrent multi-agent and user operations. | All CRM mutations require version locking (`expected_version`) and idempotency keys to eliminate race conditions and double-writes. |

---

## Dual FastMCP Server Tool Contracts

The pod architecture separates internal CRM operations from external market intelligence across two dedicated FastMCP servers:

### 1. CRM Server (`salespod-mcp`)

| Tool | Purpose | Mutation | Safety Mechanism |
| :--- | :--- | :---: | :--- |
| `search_leads` | Lexical lead and account search with cursor pagination | No | Read-only deterministic query |
| `get_deal` | Retrieve complete deal details, account, contacts, and stage history | No | Read-only aggregated view |
| `update_stage` | Guarded deal stage transition | **Yes** | Requires `expected_version` and idempotency key |
| `log_activity` | Append auditable note, call, meeting, or email activity | **Yes** | Validates actor, deal/lead IDs, and idempotency key |
| `get_pipeline_snapshot` | Aggregated stage counts and weighted revenue totals | No | Read-only summary snapshot |
| `list_signal_events` | List company signal events with filters | No | Read-only durable signal query |
| `get_signal_event` | Retrieve one signal event and source metadata | No | Read-only durable signal query |
| `acknowledge_signal` | Mark a signal as reviewed by a manager | **Yes** | Transactional status update and audit event |

### 2. Market Intelligence Server (`salespod-signals-mcp`)

| Tool | Parameters | Purpose | Output |
| :--- | :--- | :--- | :--- |
| `get_company_news` | `domain: str` | Retrieves categorized corporate press, executive changes, and regulatory news | Structured headlines, source citations, and summaries |
| `get_funding_events` | `domain: str` | Retrieves venture/debt funding rounds, valuations, and lead investors | Round history, capital raised, and strategic growth context |
| `get_tech_stack` | `domain: str` | Identifies active technologies across cloud, CRM, data warehouse, and security | Categorized tech items with adoption/migration status |

---

## Quick Start

### Prerequisites
- **Python 3.11**
- **Node.js 18+** & npm (for the Command Center dashboard)
- Optional: [Ollama](https://ollama.com/) with `qwen2.5:3b` and `nomic-embed-text`

### 1. Environment Setup

```powershell
# Clone the repository and navigate to root
cd D:\salespod

# Create and activate virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install package with development and agent dependencies
python -m pip install -e ".[dev,agents]"

# Alternative: install all runtime, agent, and development dependencies
python -m pip install -r requirements.txt
```

### 2. Database Migrations & Seeding

```powershell
# Explicitly apply Alembic database migrations
salespod-migrate

# Seed synthetic CRM with deterministic companies, deals, leads, transcripts, and signal events
python -m scripts.seed_database --reset
```

*This creates `data/salespod.db` and writes the evaluation ground truth to `data/ground_truth.json`.*

### 3. Run the Dual FastMCP Servers

```powershell
# Run the core CRM FastMCP server (salespod-mcp)
salespod-mcp

# Run the Market Intelligence FastMCP server (salespod-signals-mcp)
salespod-signals-mcp
```

### 4. Run the CLI Agent

```powershell
python -m scripts.run_agent "Show the current pipeline snapshot"
python -m scripts.run_agent "Find leads at Acme"
python -m scripts.run_agent "Why will we miss Q4?"
```

---

## Running the Command Center Dashboard

The repository includes a modern React/Vite/Tailwind dashboard in [`frontend/`](frontend/).

### Terminal 1: Backend API

```powershell
cd D:\salespod
.\.venv\Scripts\Activate.ps1
python -m scripts.run_api
```
*API runs at `http://127.0.0.1:8000`.*

### Terminal 2: Frontend Dev Server

```powershell
cd D:\salespod\frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Key API Routes for the Command Center & Signal Radar

```text
GET  /api/dashboard/overview              Dashboard KPI totals, pipeline stages, risk summaries
GET  /api/approvals                       Pending human-in-the-loop approval inbox items
POST /api/approvals/{id}/decide           Submit manager decision (approved/rejected)
GET  /api/signals                         Fetch live corporate signal events
POST /api/signals/simulate                Simulate an ad-hoc signal (new_cto, funding, layoffs, etc.)
POST /api/signals/stream/seed             Seed a balanced 5-event live signal stream cohort
POST /api/signals/{id}/pipeline           Execute the 9-stage autonomous GTM pipeline
GET  /api/audit/events                    Immutable cryptographic audit trail
POST /api/agent/ask                       Conversational copilot query
```

---

## Verification & Code Quality

Run the test suite and linters:

```powershell
# Run all unit, integration, and contract tests (28 passed)
pytest

# Run Ruff linter and formatter checks (0 errors)
ruff check .

# Run Frontend TypeScript & Vite production build (0 errors)
npm --prefix frontend run build
```
