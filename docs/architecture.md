# Autonomous Sales Pod Architecture

## Overview & Scope

The **Autonomous Sales Pod** is an offline-first, production-oriented AI revenue engine and manager command center. It enforces strict architectural boundaries to guarantee data integrity: **autonomous agents, LLMs, and external MCP clients cannot mutate CRM or customer-facing state directly**.

All state mutations flow through transactional application services that enforce optimistic concurrency control, idempotency guards, compliance clearance, and human-in-the-loop (HITL) approval workflows.

```text
               Manager Dashboard / MCP Clients / Agents
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌───────────────────────────────┐         ┌───────────────────────────────┐
│     salespod-mcp Server       │         │  salespod-signals-mcp Server  │
│      (CRM Tool Boundary)      │         │ (Market Intelligence Server)  │
│ • search_leads                │         │ • get_company_news            │
│ • get_deal                    │         │ • get_funding_events          │
│ • update_stage (guarded)      │         │ • get_tech_stack              │
│ • log_activity (guarded)      │         └───────────────┬───────────────┘
│ • get_pipeline_snapshot       │                         │
│ • list/get/ack signal_events  │                         │
└───────────────┬───────────────┘                         │
                │                                         │
                ▼                                         ▼
┌───────────────────────────────┐         ┌───────────────────────────────┐
│      CRM Application Service  │         │   Signal Stream & Pipeline    │
│  (Validation, OCC, Idempotency)│◄────────│  (9-Stage Autonomous Engine)  │
└───────────────┬───────────────┘         └───────────────┬───────────────┘
                │                                         │
                └───────────────────┬─────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Policy & Compliance Engine                           │
│     (5 Safety Gates · Risk Scoring · Human Approval Routing)            │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SQLAlchemy Core Repositories                       │
│    (Companies, Leads, Deals, Activities, Signals, Approvals, Audits)    │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Alembic Migrations / Storage Engine                   │
│                       SQLite (dev) / PostgreSQL (prod)                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architectural Principles

1. **Separation of Concerns & Hexagonal Boundaries**:
   The domain layer (`domain/`) has zero external dependencies on FastMCP, LangGraph, Ollama, FastAPI, or SQLAlchemy. Transport protocols and AI models are pluggable adapters around typed contracts.
2. **Offline-First & Local LLM Execution**:
   All core CRM operations, pipeline stages, compliance checks, and deterministic tests run offline without external cloud dependencies. When local [Ollama](https://ollama.com/) is running, `qwen2.5:3b` powers natural-language reasoning and `nomic-embed-text` handles vector retrieval.
3. **Guarded State Mutations**:
   All write operations require an explicit `expected_version` (optimistic locking) and an `idempotency_key`. Race conditions return `ConflictError (409)` rather than silently overwriting data.
4. **Deterministic Evaluation & Separated Ground Truth**:
   Synthetic seed datasets feature objectively verifiable deal risks (missing economic buyers, stalled negotiations) and corporate signals. Evaluation ground truth is segregated in `data/ground_truth.json` and never leaked into agent context.

---

## Subsystems & Module Structure

```text
src/salespod/
  config.py                         Environment-backed configuration settings
  domain/
    enums.py                        DealStage, ActivityType, SignalEventType, SignalStatus
    contracts.py                    Pydantic domain DTOs and API request/response contracts
    errors.py                       ConflictError, NotFoundError, ValidationError, PolicyViolation
  application/
    crm_service.py                  Transactional CRM operations, versioning & idempotency
    signal_service.py               Signal event retrieval, lifecycle & acknowledgment
    signal_stream.py                Simulated signal event generator across 5 corporate triggers
    signal_workflow.py              Autonomous 9-stage orchestrator (research, committee, variants, compliance)
  infrastructure/
    db/
      models.py                     SQLAlchemy ORM models
      session.py                    Database session lifecycle & connection factory
      seed.py                       Deterministic fixture generation
  interfaces/
    http/
      api.py                        FastAPI routes for dashboard, signals, and agent copilot
      schemas.py                    HTTP request/response schemas
      approvals.py                  Durable approval repository & dispatch handlers
      dashboard.py                  Dashboard overview & pipeline aggregation service
    mcp/
      server.py                     FastMCP CRM server (salespod-mcp)
      signals_server.py             FastMCP market intelligence server (salespod-signals-mcp)
  agents/                           LangGraph supervisor, prompts & local Ollama runner
```

---

## FastMCP Tool Contracts

### 1. CRM Server (`salespod-mcp`)
Exposed via stdio or SSE/HTTP:

| Tool | Purpose | Mutation | Safety Mechanism |
| :--- | :--- | :---: | :--- |
| `search_leads` | Lexical lead and company account search with cursor pagination | No | Read-only deterministic query |
| `get_deal` | Complete deal details, company, contacts, and stage history | No | Read-only aggregated view |
| `update_stage` | Guarded deal stage transition | **Yes** | Requires `expected_version` and idempotency key |
| `log_activity` | Append auditable note, call, meeting, or email activity | **Yes** | Validates actor, deal/lead IDs, and idempotency key |
| `get_pipeline_snapshot` | Aggregated stage counts and weighted revenue totals | No | Read-only summary snapshot |
| `list_signal_events` | List durable company signal events with filters | No | Read-only query |
| `get_signal_event` | Retrieve specific signal event and source metadata | No | Read-only query |
| `acknowledge_signal` | Mark a signal as reviewed by a manager | **Yes** | Transactional status update and audit logging |

### 2. Market Intelligence Server (`salespod-signals-mcp`)
Exposed to agents, research workflows, and external clients:

| Tool | Parameters | Purpose | Output |
| :--- | :--- | :--- | :--- |
| `get_company_news` | `domain: str` | Retrieves categorized press, executive changes, and regulatory news | Structured headlines, source citations, and summaries |
| `get_funding_events` | `domain: str` | Retrieves venture/debt funding rounds, valuations, and lead investors | Round history, capital raised, and strategic growth context |
| `get_tech_stack` | `domain: str` | Identifies active technologies across cloud, CRM, data warehouse, and security | Categorized tech items with adoption/migration status |

---

## The 9-Stage Signal Pipeline Subsystem

The autonomous signal pipeline orchestrator (`SignalWorkflowOrchestrator`) connects market triggers to governed outbound actions:

1. **Signal Ingestion**: Ingests `funding_round`, `new_cto`, `layoffs`, `tech_stack`, or `leadership_change`.
2. **Account Research**: Queries `signals-mcp` tools (`get_company_news`, `get_funding_events`, `get_tech_stack`).
3. **ICP Scoring**: Computes firmographic fit (0–100%) and urgency index.
4. **Buying Committee Mapping**: Resolves Economic Buyer, Technical Buyer, and Champion with individual fit scores.
5. **Personalized Variants**: Produces 3 tailored email variants (*Strategic ROI*, *Technical Integration*, *Executive Peer*).
6. **Compliance Gate**: Evaluates 5 safety checks (CAN-SPAM, opt-out statement, truthful subject, persona match, professional tone).
7. **Approval Inbox**: Creates a durable `ApprovalRequest` record with attached evidence.
8. **Sandbox Dispatch**: Emits mock SMTP transmission with unique delivery trace ID.
9. **CRM & Audit Sync**: Appends an `Activity` record to the CRM timeline and writes an immutable `AuditEvent`.

*For comprehensive operational details, see [docs/pipeline.md](pipeline.md).*

---

## Data Schema & Storage

The database layer utilizes SQLAlchemy models managed by Alembic migrations:

- `companies`: Target accounts (name, domain, industry, size, annual revenue).
- `leads`: Prospect contacts (name, email, title, fit score, status).
- `deals`: Opportunities with integer minor-unit amounts, probability weights, stages, and integer versions (`version` column for OCC).
- `activities`: Timestamped notes, calls, emails, and meetings with structured metadata.
- `stage_changes`: Immutable log of deal stage transitions with reason notes and actor IDs.
- `signal_events`: Corporate market triggers with source metadata, relevance scores, and review status.
- `approval_requests`: Human-in-the-loop review queue for deal risk interventions and outbound sales approvals.
- `audit_events`: Append-only cryptographic trace of all system actions, approvals, and mutations.

---

## Frontend Command Center Architecture

Built with React 18, Vite, and Tailwind CSS in [frontend/](file:///d:/salespod/frontend):

- **Executive KPI Telemetry**: Real-time pipeline totals, weighted forecast coverage, and risk indicators.
- **Stage Breakdown & Pipeline Chart**: Interactive Recharts visualization comparing gross vs. weighted amounts.
- **Approval Inbox**: Human review modal with evidence citations, call transcripts, and decision actions.
- **Signal Radar & Pipeline Visualizer**:
  - Event Stream simulation toolbar (Ad-hoc simulation & 5-event cohort seeding).
  - Live corporate signal feed with relevance badges and suggested motions.
  - Interactive 9-Stage Modal with visual step progression, email variant inspection, committee mapping cards, `signals-mcp` telemetry tabs, and one-click Sandbox approval dispatch.
- **Supervisor Copilot**: Embedded conversational panel connected to the LangGraph supervisor.
- **Audit Log View**: Complete chronological feed of immutable system audit events.

---

## Related Documentation

- [Business Case & GTM Strategy](business.md)
- [9-Stage Signal Pipeline Specification](pipeline.md)
- [Project Readme](../README.md)
