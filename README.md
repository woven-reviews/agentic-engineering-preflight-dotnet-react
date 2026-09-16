# Environment Preflight

A tiny app on the **same stack** you'll use for the assessment — ASP.NET Core (.NET 10) + Postgres
backend, React + TypeScript + Vite frontend, all orchestrated with Docker Compose. It does nothing
interesting on purpose: its only job is to confirm your machine can **build and run the stack**
*before* your timer starts, so you don't lose any of your window to setup.

Run this ahead of time. If it comes up green, you're ready.

## Run it

```bash
docker compose --profile dev up --watch
```

First run pulls base images and restores/installs dependencies — that's the slow part, and
running it now means it's cached when the real app arrives. Subsequent runs are fast.

Then open:

- **Frontend:** <http://localhost:5173> — should show **✅ Stack is up** with `database: ok`.
- **API health:** <http://localhost:8080/health> → `{"status":"ok"}`

Seeing the green check on the frontend means the whole chain works: the frontend built and
served, reached the backend, and the backend reached Postgres.

## If it doesn't come up

- **Docker not running** — start Docker Desktop and retry.
- **Compose `--watch` not recognized** — you need Docker Compose v2.22 or newer.
- **Port already in use** (5173, 8080) — stop whatever's using it, or set `API_HOST_PORT` /
  `FRONTEND_HOST_PORT` before running the command above.
- **Slow first build** — expected; let it finish once.

Tear down with `docker compose --profile dev down` (add `--volumes` if you also want to drop the
database volume).

## Exporting session logs

When you're done, export your session log and upload it to Qualified. Run this from inside
your AI harness, in this checkout:

- **Claude Code** — run the `/extract-claude-session-logs` slash command.
- **Codex** — invoke the `extract-codex-session-logs` skill (`$extract-codex-session-logs`
  or from the skills UI).
- **GitHub Copilot** — invoke the `extract-copilot-session-logs` skill
  (`$extract-copilot-session-logs` or from the skills UI).

Each writes a `session_log_*.md` (the readable log) and a matching `*_raw_*.json` (the raw
envelope, needed so a grader can see any images you pasted) into the repo root, then fills in
descriptions for any pasted images automatically. Upload **both files** — the markdown is
what gets scored, the raw envelope is what lets a human grader see the images and your actual
output.

See the command/skill for the full set of options (e.g. exporting just one session).
