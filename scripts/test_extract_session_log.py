#!/usr/bin/env python3
"""Minimal asserts for the option-question parsing in extract_session_log.

Run: python3 scripts/test_extract_session_log.py
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

from extract_session_log import (
    Turn,
    _candidate_project_dirs,
    _parse_chosen,
    build_turns,
    clean_user_text,
    dump_images,
    parse_permission_denial,
    permission_denials_from_result,
    render,
)

# 1x1 transparent PNG.
_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9"
    "awAAAABJRU5ErkJggg=="
)

OPTS = [
    {"label": "section", "description": "a"},
    {"label": "manufacturer_part_no", "description": "b"},
    {"label": "Neither", "description": "c"},
]


def test_single_choice():
    res = 'Your questions have been answered: "Q"="section". continue.'
    val, chosen = _parse_chosen("Q", OPTS, res)
    assert val == "section", val
    assert [o["label"] for o in chosen] == ["section"]


def test_multiselect_comma():
    res = '"Q"="section, manufacturer_part_no". continue.'
    val, chosen = _parse_chosen("Q", OPTS, res)
    assert [o["label"] for o in chosen] == ["section", "manufacturer_part_no"], chosen


def test_permission_denial_bare():
    c = (
        "The user doesn't want to proceed with this tool use. The tool use was "
        "rejected (eg. if it was a file edit, the new_string was NOT written to "
        "the file). STOP what you are doing and wait for the user to tell you how "
        "to proceed.\n\nNote: The user's next message may contain a correction."
    )
    assert parse_permission_denial(c) == ""


def test_permission_denial_with_message():
    c = (
        "Permission for this tool use was denied. The tool use was rejected (eg. "
        "if it was a file edit, the new_string was NOT written to the file). The "
        "user said:\nWe need a new branch for this"
    )
    assert parse_permission_denial(c) == "We need a new branch for this"


def test_plan_rejection_reason_is_a_message():
    # Plan mode words the same thing differently when a plan is sent back.
    c = (
        "The user doesn't want to proceed with this tool use. The tool use was "
        "rejected. The user provided the following reason for the rejection:\n"
        "wrong table, use line_items\n\nNote: The user's next message may contain "
        "a correction."
    )
    assert parse_permission_denial(c) == "wrong table, use line_items"


def test_permission_denial_ignores_normal_result():
    assert parse_permission_denial("42 files changed") is None
    assert parse_permission_denial("error: file not found") is None


def test_permission_denials_from_result_names_tool():
    entry = {
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_1",
                    "is_error": True,
                    "content": (
                        "Permission for this tool use was denied. The tool use "
                        "was rejected. The user said:\nno"
                    ),
                }
            ]
        }
    }
    out = permission_denials_from_result(entry, {"toolu_1": "Bash — rm -rf build"})
    assert out == [{"tool": "Bash — rm -rf build", "message": "no"}]


def test_custom_answer_matches_no_option():
    res = '"Q"="something the user typed". continue.'
    val, chosen = _parse_chosen("Q", OPTS, res)
    assert val == "something the user typed"
    assert chosen == []


def test_multi_question_anchors_on_its_own_text():
    res = '"Q1"="section", "Q2"="Neither". continue.'
    _, c1 = _parse_chosen("Q1", OPTS, res)
    _, c2 = _parse_chosen("Q2", OPTS, res)
    assert [o["label"] for o in c1] == ["section"], c1
    assert [o["label"] for o in c2] == ["Neither"], c2


def test_task_notification_is_stripped_to_empty():
    assert clean_user_text("<task-notification>\nstuff\n</task-notification>") == ""


def test_bash_output_is_stripped_to_empty():
    msg = "<bash-stdout>some output</bash-stdout><bash-stderr>a warning</bash-stderr>"
    assert clean_user_text(msg) == ""


def test_bash_input_survives_cleaning_for_detection():
    # The command itself must NOT be stripped; build_turns extracts it.
    assert (
        clean_user_text("<bash-input>ls -la</bash-input>")
        == "<bash-input>ls -la</bash-input>"
    )


def test_strict_candidate_dirs_skip_parents():
    cwd = Path("/Users/me/work/app/sub")
    loose = list(_candidate_project_dirs(cwd, strict=False))
    strict = list(_candidate_project_dirs(cwd, strict=True))
    assert len(strict) == 1  # only the cwd itself
    assert len(loose) > 1  # cwd + parents
    assert strict[0] == loose[0]


def test_dump_images_writes_file_and_marker():
    turn = Turn("look at this", None)
    turn.images = [{"type": "base64", "media_type": "image/png", "data": _PNG_B64}]
    dump_dir = Path(tempfile.mkdtemp())
    written = dump_images([turn], "sess123", dump_dir=dump_dir)
    assert len(written) == 1
    p = written[0]
    assert p.exists() and p.name == "sess123_turn1_img1.png"
    assert p.read_bytes() == base64.b64decode(_PNG_B64)
    assert "description pending" in turn.user_text
    assert str(p) in turn.user_text


def test_dump_images_noop_without_images():
    turn = Turn("no images here", None)
    dump_dir = Path(tempfile.mkdtemp())
    assert dump_images([turn], "s", dump_dir=dump_dir) == []
    assert turn.user_text == "no images here"


def _plan_entries(result_text: str, plan: str = "# Plan\n\nStep one."):
    return [
        {
            "type": "user",
            "timestamp": "2026-01-01T00:00:00Z",
            "message": {"content": "build it"},
        },
        {
            "type": "assistant",
            "timestamp": "2026-01-01T00:00:01Z",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_plan",
                        "name": "ExitPlanMode",
                        "input": {"plan": plan},
                    }
                ]
            },
        },
        {
            "type": "user",
            "timestamp": "2026-01-01T00:00:02Z",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_plan",
                        "content": result_text,
                    }
                ]
            },
        },
    ]


def test_plan_approved_is_captured():
    turns, _ = build_turns(
        _plan_entries(
            "User has approved your plan. You can now start coding.\n\n"
            "## Approved Plan (edited by user):\n# Plan\n\nStep one."
        )
    )
    (plan,) = turns[0].plans
    assert plan["plan"] == "# Plan\n\nStep one."
    assert plan["decision"] == "approved"
    # Unchanged plan echoed back under the "edited" heading is not an edit.
    assert plan["edited_plan"] == ""
    # The plan is rendered as its own block, not as a tool bullet.
    assert turns[0].tool_bullets == []
    assert turns[0].result_notes == []


def test_plan_approved_with_edit_keeps_final_version():
    turns, _ = build_turns(
        _plan_entries(
            "User has approved your plan.\n\n"
            "## Approved Plan (edited by user):\n# Plan\n\nStep one, but smaller."
        )
    )
    (plan,) = turns[0].plans
    assert plan["decision"] == "approved"
    assert plan["edited_plan"] == "# Plan\n\nStep one, but smaller."


def test_plan_rejection_reason_is_captured_and_rendered():
    # The wording the harness actually uses when a plan is sent back in plan mode.
    turns, _ = build_turns(
        _plan_entries(
            "The user doesn't want to proceed with this tool use. The tool use "
            "was rejected (eg. if it was a file edit, the new_string was NOT "
            "written to the file). STOP what you are doing and wait for the user "
            "to tell you how to proceed. The user provided the following reason "
            "for the rejection:\nwrong table, use line_items\nand keep it in one "
            "migration\n\nNote: The user's next message may contain a correction."
        )
    )
    (plan,) = turns[0].plans
    assert plan["decision"] == "rejected"
    assert plan["message"] == "wrong table, use line_items\nand keep it in one migration"
    # Routed to the plan record, not the generic permission-denial list.
    assert turns[0].permission_denials == []
    md = render(turns, [], "proj", None)
    assert "> wrong table, use line_items" in md
    assert "> and keep it in one migration" in md


def test_plan_without_result_is_marked_undecided():
    entries = _plan_entries("")[:2]
    (plan,) = build_turns(entries)[0][0].plans
    assert plan["decision"] == "no decision recorded"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all passed")
