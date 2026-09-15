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

`scripts/` has three mechanical extractors that turn an AI coding session into a readable
markdown log (no LLM, no network — stdlib only). Run them from the repo root:

```bash
python3 scripts/extract_session_log.py          # Claude Code sessions (~/.claude/projects/)
python3 scripts/extract_codex_session_log.py    # Codex CLI sessions (~/.codex/sessions/)
python3 scripts/extract_copilot_session_log.py  # GitHub Copilot CLI (~/.copilot/session-store.db)
```

By default each writes the most recent session for the current directory to
`session_log.md` / `codex_session_log.md` / `copilot_session_log.md` in the repo root.

Useful flags (all three scripts):

- `--all` — one file per session (`session_log_<id>.md`, etc.).
- `--strict` — only sessions started in *this exact directory*; skips the parent-dir walk
  and the "newest session anywhere" fallback, so you never accidentally export an unrelated
  project's transcript.
- `--output DIR` — write to `DIR` instead of the repo root (or `--output -` for stdout).
- a session id (or unique prefix) — export just that one session.

Source-specific flags: the Codex extractor takes `--sessions-root DIR` and the Copilot
extractor takes `--db PATH` to point at a non-default session store.

Pasted images can't be read mechanically, so the extractors dump each one to a temp file and
leave a `[Image dumped to … — description pending]` marker in the log. The harness shortcuts
below do a follow-up pass that replaces those markers with a short image description; running
the scripts directly leaves the markers in place.

### From inside your AI harness

Each tool ships a shortcut so you can export without leaving the session:

- **Claude Code** — run the `/extract-claude-session-logs` slash command
  (`.claude/commands/extract-claude-session-logs.md`). Defaults to `--all`; append any of the
  flags above, e.g. `/extract-claude-session-logs --strict`.
- **Codex** — invoke the `extract-codex-session-logs` skill (as `$extract-codex-session-logs`
  or from the skills UI; see `.agents/skills/extract-codex-session-logs/`).
- **GitHub Copilot** — invoke the `extract-copilot-session-logs` skill (as
  `$extract-copilot-session-logs` or from the skills UI; see
  `.agents/skills/extract-copilot-session-logs/`).

Each shortcut runs its extractor with `--all` and passes through extra args like `--strict`
or `--output DIR`.
