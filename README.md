# Screener

**A relentless, fail-closed research engine for Solana memecoins.**

Every ten minutes, Screener sweeps fresh Solana pairs, interrogates them
against a transparent 100-point rubric, and pushes only the survivors to
Discord. No wallet ever touches this codebase. No trade is ever placed. It
watches, it scores, it tells you — and then it gets out of the way.

FastAPI owns every piece of judgment: collection, filtering, scoring,
storage, scheduling, notification. Streamlit is a window onto that
judgment, nothing more — it speaks to the API over HTTP and holds no logic
of its own. That boundary is deliberate: the brain is testable, versioned,
and swappable from its face.

## Why Screener is built this way

Memecoin data is incomplete by nature, and most scanners quietly paper
over the gaps — an unknown holder concentration becomes a `0`, a missing
buyer count becomes "fine." Screener refuses that shortcut. Every rule is
**fail-closed**: if the data required to clear a check isn't there, the
check fails, not passes.

- Unknown mint or freeze authority fails a required-authority rule.
- Unknown holder concentration fails the holder rule.
- Unknown unique-buyer count fails that rule when a minimum is configured.
- Unknown checks earn zero score — never a benefit of the doubt.

With the default strict criteria, this means Screener will sometimes go
quiet rather than guess. That silence is the feature.

## What's under the hood

- FastAPI API with automatic Swagger documentation
- APScheduler running a scan every 10 minutes, plus an on-demand scan endpoint
- Bounded-concurrency pipeline: pair discovery and Solana risk checks run
  in parallel (semaphore-limited, tunable via `SCAN_CONCURRENCY`), not one
  candidate at a time
- Redis distributed lock, processed-pair cache, and alert deduplication
- DEX Screener discovery and live pair metrics
- Solana RPC checks for mint authority, freeze authority, and largest-holder concentration
- Conservative filters feeding a transparent, fully-explained 100-point score
- PostgreSQL history for every scan, opportunity, setting, and Discord attempt
- Periodic price tracking: current price, maximum gain, maximum decline
- Streamlit views for overview, opportunities, token inspection, alerts, scans, and configuration
- Alembic migrations, Docker Compose, and a real unit test suite

## Start locally

Requirements: Docker Desktop (or Docker Engine with Compose).

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Dashboard: <http://localhost:8501>
- API: <http://localhost:8000>
- API documentation: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5423`
- Redis: `localhost:6379`

The default database password is intended only for local development. Change
`POSTGRES_PASSWORD` and the matching password in `DATABASE_URL` before using the
stack on any shared machine. Add `DISCORD_WEBHOOK_URL` to `.env`, or set it on
the Configuration page. Keep `.env` private.

Compose binds every published port to `127.0.0.1`, so the services are not
exposed to other devices on the network by default.

Run a scan from the dashboard or:

```bash
curl -X POST http://localhost:8000/api/scans/run
```

Stop the services with `docker compose down`. Data remains in named volumes.
To intentionally delete local database and Redis data, use
`docker compose down --volumes`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | API, PostgreSQL, Redis, and scanner state |
| `GET` | `/api/opportunities` | Filterable opportunity list |
| `GET` | `/api/opportunities/{pair_address}` | Opportunity detail |
| `GET` | `/api/alerts` | Discord delivery history |
| `POST` | `/api/alerts/{id}/resend` | Retry a stored alert |
| `GET` | `/api/scans` | Scan history |
| `POST` | `/api/scans/run` | Start a non-overlapping scan |
| `GET` | `/api/stats` | Dashboard summary |
| `GET` | `/api/settings` | Criteria and scanner configuration |
| `PATCH` | `/api/settings` | Update criteria, interval, or webhook |
| `POST` | `/api/scanner/pause` | Pause future scan starts |
| `POST` | `/api/scanner/resume` | Resume scanning |

Query parameters on `/api/opportunities` include `qualified`, `min_score`,
`limit`, and `offset`.

## Conservative data handling

DEX Screener does not expose a complete chronological feed of every new pool,
unique buyer counts, or a 10-minute metric bucket. Screener discovers Solana
tokens from its latest token-profile feed and retrieves their pairs. It uses the
available five-minute volume and transaction bucket as a conservative lower
bound for the configured recent-activity threshold.

Unavailable data is never converted to a safe result — see
[Why Screener is built this way](#why-screener-is-built-this-way) above.

With the default strict criteria, DEX Screener's missing unique-buyer field means
candidates will not alert until that field comes from an additional indexer or
the operator deliberately sets `minimum_unique_buyers_10m` to `0`. This is an
intentional fail-closed default.

The public Solana RPC endpoint can rate-limit requests. Set `SOLANA_RPC_URL` in
`.env` to a reliable private endpoint if needed. Direct Raydium, Meteora, and
launchpad monitoring is the logical next step if discovery coverage is too
narrow.

## Development without Docker

Use Python 3.12 and start PostgreSQL and Redis first.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend uvicorn app.main:app --reload
```

For this non-Docker path, change the `.env` service hosts from `postgres` and
`redis` to `localhost` before running the migration.

In a second terminal:

```bash
source .venv/bin/activate
BACKEND_URL=http://localhost:8000 streamlit run dashboard/streamlit_app.py
```

Run tests:

```bash
pytest
```

## Safety

Scores and alerts are experimental research signals, not financial advice.
Token contracts, liquidity, permissions, holder distribution, and social claims
can change after a scan. Verify independently, use a separate manual trading
workflow, and assume any memecoin can lose all its value.

Screener does one job — watch and report. It never holds a key, never signs
a transaction, and never will.
