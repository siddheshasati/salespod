# Sales Pod architecture

## Scope of this slice

The first slice proves the most important production boundary: agents and MCP
clients cannot mutate CRM state directly. They call one application service,
which owns validation, optimistic concurrency, idempotency, and transactions.

```text
Manager / MCP client
        |
        +--> FastMCP adapter (stdio now, authenticated HTTP later)
        |
        +--> Supervisor graph (LangGraph when installed; deterministic fallback)
                         |
                   CRM application service
                         |
                     SQLAlchemy repositories
                          |
                    Alembic migrations
                          |
                    SQLite now / Postgres later
```

The domain layer has no dependency on FastMCP, LangGraph, Ollama, or SQLAlchemy.
Transport and model integrations are adapters around typed application
contracts.

## Module boundaries

```text
src/salespod/
  config.py                         environment-backed settings
  domain/                           enums and Pydantic contracts
  application/crm_service.py       transactional CRM use cases
  infrastructure/db/                SQLAlchemy schema, sessions, seed data
  interfaces/mcp/                   FastMCP tool adapter
  agents/                           state, routing, Ollama, graph adapter
scripts/                            reproducible local commands
tests/                              offline unit/integration/contract tests
```

## Data and safety rules

- UUID5 identifiers make generated fixtures stable across runs.
- Money is stored as integer minor units, never floating point.
- Timestamps are timezone-aware UTC values.
- Deal stage updates require `expected_version`; stale writes return a conflict.
- Activity and stage updates accept an idempotency key. Replays return the
  original result instead of duplicating the side effect.
- Generated ground truth is written to a separate JSON evaluation artifact and
  is never included in the agent context.
- Full transcript bodies are not logged by default.

## Current MCP contract

| Tool | Purpose | Mutation |
| --- | --- | --- |
| `search_leads` | lexical lead/company search with cursor pagination | no |
| `get_deal` | deal, company, lead, activity, and stage history | no |
| `update_stage` | guarded stage transition | yes |
| `log_activity` | append an auditable activity | yes |
| `get_pipeline_snapshot` | stage totals and weighted forecast | no |
| `list_signal_events` | list durable company signal events | no |
| `get_signal_event` | retrieve one signal event | no |
| `acknowledge_signal` | mark a signal as reviewed | yes |

The HTTP control plane adds durable `approval_requests` and `audit_events`
tables. Approval candidates are synchronized from transcript evidence, while
approval decisions, stage changes, and logged activities append audit events.
The policy engine currently auto-approves low-risk CRM reads/notes/stage
updates and escalates discounts above 15%, executive outreach, and contract
changes.

The `signal_events` table stores company-level market and account events with
source metadata, relevance scores, suggested actions, and an acknowledgement
status. Signals are exposed through both the HTTP API and the MCP adapter so
the frontend, supervisor, and future research/writer agents can share one
durable event stream.

Mutation tools are only reachable from the graph when the manager request is
explicitly an update/log request. A natural-language question cannot silently
change CRM state.

## Production hardening path

1. Add PostgreSQL deployment, row-level authorization, and migration checks to the Alembic-backed schema lifecycle.
2. Put the HTTP MCP transport behind OAuth/service identity, rate limits, and
   an allow-list of mutation scopes.
3. Add Supervisor routing for research, writer, scheduler, strategist, coach,
   compliance, and competitive-intel agents.
4. Add event ingestion with an outbox/inbox and replayable signal events.
5. Add vector storage for playbooks using `nomic-embed-text`; keep CRM lexical
   search as a deterministic fallback.
6. Add forecast evidence trails, planted-truth evaluation, and dashboard
   metrics before exposing the system to real customer data.
