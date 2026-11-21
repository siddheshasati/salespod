# Contributing to Salespod

Thanks for your interest in contributing to the Autonomous Sales Pod! This guide
covers how to set up the project, run the tests, and submit changes.

By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
To report a security issue, **do not open a public issue**; follow
[SECURITY.md](SECURITY.md) instead.

## Ways to contribute

- Report bugs or suggest features through GitHub Issues
- Improve documentation (README, `docs/`, code comments)
- Add tests or fix failing ones
- Pick up an open issue and send a pull request

For anything larger than a small fix, please open an issue first so we can agree
on the approach before you spend time on it.

## Development setup

**Requirements:** Python 3.11+ (adjust to the version in `pyproject.toml`) and Git.

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/salespod.git
cd salespod

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 3. Install the project with dev dependencies
pip install -e ".[dev]"

# 4. Copy the example environment file
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
```

The project runs offline-first with synthetic data and a mock SMTP sandbox, so
you do not need any real API keys or email accounts to develop or test.
**Never commit real credentials or real customer data.**

## Running the tests

Run the full suite:

```bash
pytest
```

Run a specific layer while you work:

```bash
pytest tests/unit -v           # pure logic (scoring, compliance gates, etc.)
pytest tests/integration -v    # multi-stage pipeline workflows
pytest tests/contract -v       # MCP server contracts
pytest tests/api -v            # FastAPI endpoints
```

Useful single-file runs:

```bash
pytest tests/integration/test_signal_workflow.py -v
pytest tests/contract/test_signals_mcp.py -v
```

All tests must pass before a pull request can be merged.

## Where tests go

| Directory | What belongs there |
| :--- | :--- |
| `tests/unit/` | Isolated logic with no I/O, e.g. `test_signal_stream.py` |
| `tests/integration/` | End-to-end pipeline flows across stages, e.g. `test_signal_workflow.py` |
| `tests/contract/` | Input/output contracts of MCP servers, e.g. `test_signals_mcp.py` |
| `tests/api/` | HTTP endpoint behavior, e.g. `test_signal_api.py` |

## Rule: every new MCP tool needs a contract test

Any time you add or change a tool on an MCP server (for example in
`src/salespod/interfaces/mcp/`), you must add or update a **contract test** in
`tests/contract/` in the same pull request. The test should verify:

1. The tool is registered under the expected name
2. It accepts the documented arguments (and rejects invalid ones)
3. It returns the documented response shape, including field names and types
4. It behaves deterministically against the synthetic/offline data

Pull requests that add or change an MCP tool without a matching contract test
will not be merged. Other agents and pipeline stages depend on these contracts,
so they need to stay stable and visible.

## Making changes

### Branching

Create a branch from `main` with a short, descriptive name:

```
feat/<short-description>     # new feature
fix/<short-description>      # bug fix
docs/<short-description>     # documentation only
test/<short-description>     # tests only
refactor/<short-description> # no behavior change
```

### Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(pipeline): add leadership_change scoring weight
fix(compliance): handle missing unsubscribe footer
docs: fix relative links in pipeline doc
test(contract): cover get_funding_events error path
```

Keep commits focused, and explain the *why* in the body when it isn't obvious.

### Code style

Before pushing, run the linters (if configured in your checkout):

```bash
ruff check .
ruff format .
mypy src
```

- Add type hints to new code
- Keep functions small and single-purpose
- Prefer clear names over comments; add comments for non-obvious decisions

### Pull request checklist

Before opening a PR, confirm that:

- [ ] `pytest` passes locally
- [ ] New behavior has tests (and any new MCP tool has a contract test)
- [ ] Docs are updated if behavior, endpoints, or stages changed
- [ ] No secrets, real personal data, or `.env` files are included
- [ ] The PR description explains what changed and why, and links the issue

A maintainer will review your PR. Expect some feedback; it's a normal part of
the process, not a rejection.

## Compliance and responsible use

Stage 8 of the pipeline is a **sandbox mock send**: no real emails are sent, and
the repo should only ever contain synthetic data. Contributions must not add
real outbound sending, scraping of real personal data, or bypass the Stage 6
compliance gates or the Stage 7 human approval step. The compliance checks are a
technical aid, not legal advice.

## License

By contributing, you agree that your contributions will be licensed under the
same license as this project (see [LICENSE](LICENSE)).
