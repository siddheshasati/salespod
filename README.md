# Autonomous Sales Pod v2

This repository is the first production-oriented vertical slice of an AI revenue
team. It currently provides a deterministic synthetic CRM, a typed application
service, a FastMCP CRM boundary, and a LangGraph-compatible supervisor flow.

The system is deliberately **offline-first**: core CRM operations and tests do
not require Ollama. When Ollama is available, `qwen2.5:3b` can be used for
optional response synthesis and `nomic-embed-text` is available for the future
knowledge/playbook retrieval layer.

## First vertical slice

The implemented flow is:

1. Generate 80 companies, 500 leads, 120 deals, 1,500 email threads, and 60
   call transcripts with a fixed seed.
2. Persist those records in SQLite through SQLAlchemy.
3. Access CRM operations through five typed MCP tools:
   `search_leads`, `get_deal`, `update_stage`, `log_activity`, and
   `get_pipeline_snapshot`.
4. Send a manager request through a deterministic supervisor graph. The graph
   routes read requests and explicitly requested stage/activity mutations to
   the same application service used by MCP.

## Quick start

Python 3.11 is the supported runtime.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,agents]"
python -m scripts.seed_database --reset
python -m scripts.run_agent "Show the current pipeline snapshot"
```

Run the MCP server over stdio:

```powershell
python -m scripts.run_mcp_server
# or, after installation:
salespod-mcp
```

## Manager command center

The repository now includes a React/Vite/TypeScript/Tailwind dashboard in
[`frontend/`](frontend/). Start the backend and frontend in separate terminals:

Terminal 1:

```powershell
cd D:\salespod
.\.venv\Scripts\Activate.ps1
python -m scripts.run_api
```

Terminal 2:

```powershell
cd D:\salespod\frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite development
server proxies `/api` calls to `http://127.0.0.1:8000`.

The initial command center includes:

- pipeline and weighted-forecast cards
- stage breakdown and forecast watch
- evidence-backed approval inbox with approve/reject actions
- deal evidence drawer with stage history and guarded stage updates
- CRM lead search
- supervisor chat panel backed by `/api/agent/ask`
- signal radar placeholder connected to seeded CRM evidence
- recent pod activity/audit feed

Create a production frontend bundle with:

```powershell
cd D:\salespod\frontend
npm run build
npm run preview
```

The seed command writes `data/salespod.db` and a machine-readable
`data/ground_truth.json`. The ground-truth file is an evaluation artifact and
is not loaded by the agent runtime.

## Ollama

The local models configured by default are:

```text
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen2.5:3b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

Core tests do not call Ollama. To check model availability manually:

```powershell
ollama list
python -m scripts.run_agent "Find leads at Acme"
```

The graph uses a small stdlib HTTP adapter rather than making `langchain-ollama`
a required dependency. It falls back to deterministic routing and response
synthesis when the service is unavailable or returns malformed output.

## Checks

```powershell
python -m pytest
ruff check .
```

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the boundary diagram,
data contracts, concurrency/idempotency rules, and the staged path toward the
full Supervisor, Deal Strategist, Call Coach, Competitive Intel, compliance,
learning, and dashboard features.
