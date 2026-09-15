---
name: extract-copilot-session-logs
description: Manual-only helper for exporting all GitHub Copilot CLI session logs for the python_rfp_manager repo by running scripts/extract_copilot_session_log.py with --all, then replacing dumped-image markers with brief image descriptions. Use only when explicitly invoked as $extract-copilot-session-logs or selected from the skills UI.
---

# Extract Copilot Session Logs

Run the Copilot session-log extractor for every Copilot CLI session associated with the `python_rfp_manager` app repo, then describe any pasted images that were dumped by the extractor.

1. Set the command working directory to the `python_rfp_manager` repo root, the directory containing `scripts/extract_copilot_session_log.py`.
2. Run:

```bash
python3 scripts/extract_copilot_session_log.py --all
```

3. If the user supplied extra arguments after invoking the skill, append them after `--all`. Common supported arguments are `--output DIR`, `--db PATH`, and `--strict` (only export sessions started in this exact directory — no parent/descendant cwd overlap, no newest-anywhere fallback).
4. Record the files written from the command output, then complete the image description pass below before sending the final report.

## Image Description Pass

The extractor is mechanical and cannot describe images itself. When a pasted image is present and the image file is available, it dumps the image to a temp file and writes this stable marker into the generated markdown:

```markdown
[Image dumped to `<path>` — description pending]
```

After extraction, inspect the generated `copilot_session_log_*.md` files that were just written. For every dumped-image marker line:

1. Extract the image path between the backticks.
2. Inspect that local image with an image-capable viewer/tool.
3. Replace every occurrence of that same marker in the generated markdown with:

```markdown
[Image: <one- or two-sentence description>. Text: <visible text in the image, or "none">]
```

Use the same replacement for repeated occurrences of the same image, such as one in the summary and one in the full detail. Keep descriptions brief and factual. Include only text that is visibly present in the image.

Also scan for unresolved image references, which indicate Copilot recorded an image mention but no readable source file path:

```markdown
[Image referenced as `<name>` — source file unavailable; description pending]
```

and raw inline Copilot tokens:

```markdown
[image: <name>]
```

If either unresolved form is present, do not claim image descriptions are complete. Report exactly which logs still contain unresolved image references and that descriptions could not be generated for those references in this run.

If image inspection is not available, do not silently leave the task as complete. Report that pending image markers were found and image descriptions could not be generated in this run.
