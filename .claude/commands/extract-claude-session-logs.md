---
description: Extract all Claude Code session logs for this project
allowed-tools: Bash(python3 scripts/extract_session_log.py:*), Bash(grep:*), Read, Edit
---

Run the session log extractor and report what it wrote.

!`python3 scripts/extract_session_log.py --all $ARGUMENTS`

Defaults to `--all`: one `session_log_<session-id>.md` per session in the repo root. Pass-through args (optional): `--output DIR` for a different directory, `--strict` to only export sessions started in this exact directory (no parent-dir walk, no newest-anywhere fallback), or a single session id / `--output -` to override and extract just one. For Codex transcripts use `scripts/extract_codex_session_log.py` instead.

**Then describe any dumped images.** The extractor can't see images, so it dumps each pasted image to a tmp file and leaves a marker in the log:
`[Image dumped to `<path>` — description pending]`. For every such marker in the files just written, `Read` the image at `<path>`, then `Edit` the marker line to replace it with `[Image: <one- or two-sentence description>. Text: <any text visible in the image, or "none">]`. Skip this pass if no markers are present.