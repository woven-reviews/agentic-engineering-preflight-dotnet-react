---
name: extract-codex-session-logs
description: Manual-only helper for exporting all Codex session logs for the python_rfp_manager repo by running scripts/extract_codex_session_log.py with --all, then replacing dumped-image markers with brief image descriptions. Use only when explicitly invoked as $extract-codex-session-logs or selected from the skills UI.
---

# Extract Codex Session Logs

Run the Codex session-log extractor for every Codex transcript associated with the `python_rfp_manager` app repo, then describe any pasted images that were dumped by the extractor.

1. Set the command working directory to the `python_rfp_manager` repo root, the directory containing `scripts/extract_codex_session_log.py`.
2. Run:

```bash
python3 scripts/extract_codex_session_log.py --all
```

3. If the user supplied extra arguments after invoking the skill, append them after `--all`. Common supported arguments are `--output DIR`, `--sessions-root DIR`, and `--strict` (only export sessions started in this exact directory — no parent/descendant cwd overlap, no newest-anywhere fallback).
4. Record the files written from the command output, then complete the image description pass below before sending the final report.

## Image Description Pass

The extractor is mechanical and cannot describe images itself. When a pasted image is present, it dumps the image to a temp file and writes this stable marker into the generated markdown:

```markdown
[Image dumped to `<path>` — description pending]
```

After extraction, inspect the generated `codex_session_log_*.md` files that were just written. For every marker line:

1. Extract the image path between the backticks.
2. Inspect that local image with an image-capable viewer/tool.
3. Replace every occurrence of that same marker in the generated markdown with:

```markdown
[Image: <one- or two-sentence description>. Text: <visible text in the image, or "none">]
```

Use the same replacement for repeated occurrences of the same image, such as one in the summary and one in the full detail. Keep descriptions brief and factual. Include only text that is visibly present in the image.

If image inspection is not available, do not silently leave the task as complete. Report that the extractor wrote pending image markers and that image descriptions could not be generated in this run.
