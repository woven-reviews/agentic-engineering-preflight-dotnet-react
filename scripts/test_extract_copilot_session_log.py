#!/usr/bin/env python3
"""Minimal asserts for extract_copilot_session_log.

Run: python3 scripts/test_extract_copilot_session_log.py
"""

from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path

import extract_copilot_session_log as copilot_log
from extract_copilot_session_log import (
    Turn,
    _permissions_from_events,
    attribute_permissions,
    clean_user_text,
    format_decision,
    get_db_connection,
    get_session_by_id,
    get_session_turns,
    matching_sessions,
    render_session,
)

_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/ax6fN8A"
    "AAAASUVORK5CYII="
)


def test_copilot_noise_cleaning():
    assert clean_user_text("<system-notification>test</system-notification>") == ""
    assert clean_user_text("<bash-stdout>output</bash-stdout>") == ""
    assert (
        clean_user_text("Real text\n<system-reminder>ignore</system-reminder>\nMore text")
        == "Real text\n\nMore text"
    )


def test_copilot_permissions_join_approval_and_denial():
    lines = [
        json.dumps(
            {
                "type": "permission.requested",
                "timestamp": "2026-07-01T22:03:50Z",
                "data": {
                    "requestId": "r1",
                    "permissionRequest": {"kind": "shell", "fullCommandText": "pytest"},
                },
            }
        ),
        json.dumps(
            {
                "type": "permission.completed",
                "timestamp": "2026-07-01T22:04:04Z",
                "data": {"requestId": "r1", "result": {"kind": "approved"}},
            }
        ),
        json.dumps(
            {
                "type": "permission.requested",
                "timestamp": "2026-07-01T22:05:00Z",
                "data": {
                    "requestId": "r2",
                    "permissionRequest": {"kind": "write", "intention": "edit crud.py"},
                },
            }
        ),
        json.dumps(
            {
                "type": "permission.completed",
                "timestamp": "2026-07-01T22:05:30Z",
                "data": {
                    "requestId": "r2",
                    "result": {
                        "kind": "denied-interactively-by-user",
                        "feedback": "not like that",
                    },
                },
            }
        ),
    ]
    perms = _permissions_from_events(lines)
    assert [(p["tool"], p["decision"], p["feedback"]) for p in perms] == [
        ("pytest", "approved", ""),
        ("edit crud.py", "denied-interactively-by-user", "not like that"),
    ]


def test_copilot_permission_pending_when_no_completion():
    lines = [
        json.dumps(
            {
                "type": "permission.requested",
                "timestamp": "2026-07-01T22:05:00Z",
                "data": {
                    "requestId": "r3",
                    "permissionRequest": {"kind": "shell", "fullCommandText": "rm x"},
                },
            }
        )
    ]
    perms = _permissions_from_events(lines)
    assert perms == [
        {
            "tool": "rm x",
            "decision": "pending",
            "feedback": "",
            "timestamp": "2026-07-01T22:05:00Z",
        }
    ]


def test_copilot_format_decision():
    assert format_decision("approved") == "approved"
    assert format_decision("approved-for-location") == "approved"
    assert format_decision("denied-interactively-by-user") == "denied"
    assert format_decision("") == "unknown"


def test_copilot_attribute_permissions_by_timestamp():
    t0 = Turn("first", "", "2026-07-01T22:00:00Z", 0)
    t1 = Turn("second", "", "2026-07-01T22:10:00Z", 1)
    perms = [
        {"tool": "a", "decision": "approved", "feedback": "", "timestamp": "2026-07-01T22:05:00Z"},
        {"tool": "b", "decision": "denied", "feedback": "no", "timestamp": "2026-07-01T22:15:00Z"},
    ]
    attribute_permissions([t0, t1], perms)
    assert [p["tool"] for p in t0.permission_decisions] == ["a"]
    assert [p["tool"] for p in t1.permission_decisions] == ["b"]


def test_copilot_db_operations():
    """Test database operations with a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        test_db = Path(tf.name)

    try:
        # Create test database
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Create schema
        cursor.execute("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                cwd TEXT,
                repository TEXT,
                branch TEXT,
                summary TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE TABLE turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                turn_index INTEGER NOT NULL,
                user_message TEXT,
                assistant_response TEXT,
                timestamp TEXT DEFAULT (datetime('now')),
                UNIQUE(session_id, turn_index)
            )
        """)

        cursor.execute("""
            CREATE TABLE session_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                file_path TEXT NOT NULL,
                tool_name TEXT,
                turn_index INTEGER,
                first_seen_at TEXT DEFAULT (datetime('now')),
                UNIQUE(session_id, file_path)
            )
        """)

        cursor.execute("""
            CREATE TABLE session_refs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                ref_type TEXT NOT NULL,
                ref_value TEXT NOT NULL,
                turn_index INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE TABLE checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                checkpoint_number INTEGER NOT NULL,
                title TEXT,
                overview TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(session_id, checkpoint_number)
            )
        """)

        # Insert test data
        test_cwd = str(Path.cwd())
        cursor.execute(
            """
            INSERT INTO sessions (id, cwd, repository, branch, summary, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "test-session-1",
                test_cwd,
                "test/repo",
                "main",
                "Test session",
                "2026-01-01T12:00:00Z",
                "2026-01-01T12:30:00Z",
            ),
        )

        cursor.execute(
            """
            INSERT INTO turns (session_id, turn_index, user_message, assistant_response, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                "test-session-1",
                0,
                "Hello, can you help?",
                "Of course! What do you need?",
                "2026-01-01T12:00:05Z",
            ),
        )

        cursor.execute(
            """
            INSERT INTO turns (session_id, turn_index, user_message, assistant_response, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                "test-session-1",
                1,
                "Create a test file",
                "I'll create that for you.",
                "2026-01-01T12:10:00Z",
            ),
        )

        cursor.execute(
            """
            INSERT INTO session_files (session_id, file_path, tool_name, turn_index)
            VALUES (?, ?, ?, ?)
        """,
            ("test-session-1", "/tmp/test.py", "create", 1),
        )

        cursor.execute(
            """
            INSERT INTO session_refs (session_id, ref_type, ref_value, turn_index)
            VALUES (?, ?, ?, ?)
        """,
            ("test-session-1", "commit", "abc123", 1),
        )

        conn.commit()
        conn.close()

        # Test database operations
        conn = get_db_connection(test_db)

        # Test session retrieval
        session = get_session_by_id(conn, "test-session-1")
        assert session is not None
        assert session["id"] == "test-session-1"
        assert session["repository"] == "test/repo"
        assert session["summary"] == "Test session"

        # Test turns retrieval
        turns = get_session_turns(conn, "test-session-1")
        assert len(turns) == 2
        assert turns[0]["user_message"] == "Hello, can you help?"
        assert turns[1]["assistant_response"] == "I'll create that for you."

        # Test matching sessions
        sessions = matching_sessions(conn, Path.cwd(), strict=False)
        assert len(sessions) >= 1
        found = any(s["id"] == "test-session-1" for s in sessions)
        assert found

        # Test render
        markdown = render_session(conn, session)
        assert "test-session-1" in markdown
        assert "test/repo" in markdown
        assert "Hello, can you help?" in markdown
        assert "## Summary - user inputs" in markdown
        assert "# Full turn-by-turn detail" in markdown
        assert "Turn 1 -" in markdown
        assert "Turn 2 -" in markdown
        assert "/tmp/test.py" in markdown
        assert "- create -> /tmp/test.py" in markdown
        assert "abc123" in markdown

        conn.close()

    finally:
        # Cleanup
        test_db.unlink()


def test_copilot_prefix_matching():
    """Test that session ID prefix matching works."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        test_db = Path(tf.name)

    try:
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                cwd TEXT,
                repository TEXT,
                branch TEXT,
                summary TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        cursor.execute(
            """
            INSERT INTO sessions (id, cwd, repository, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                "6c7682e8-3849-4784-b7f2-92f3617212ff",
                str(Path.cwd()),
                "test/repo",
                "2026-01-01T12:00:00Z",
                "2026-01-01T12:00:00Z",
            ),
        )

        conn.commit()
        conn.close()

        conn = get_db_connection(test_db)

        # Test full ID
        session = get_session_by_id(conn, "6c7682e8-3849-4784-b7f2-92f3617212ff")
        assert session is not None

        # Test prefix
        session = get_session_by_id(conn, "6c7682e8")
        assert session is not None
        assert session["id"] == "6c7682e8-3849-4784-b7f2-92f3617212ff"

        conn.close()

    finally:
        test_db.unlink()


def test_copilot_image_reference_without_attachment_is_flagged():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        test_db = Path(tf.name)

    try:
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                cwd TEXT,
                repository TEXT,
                branch TEXT,
                summary TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                turn_index INTEGER NOT NULL,
                user_message TEXT,
                assistant_response TEXT,
                timestamp TEXT
            )
        """)
        cursor.execute("CREATE TABLE session_files (session_id TEXT, file_path TEXT, tool_name TEXT, turn_index INTEGER, first_seen_at TEXT)")
        cursor.execute("CREATE TABLE session_refs (session_id TEXT, ref_type TEXT, ref_value TEXT, turn_index INTEGER, created_at TEXT)")
        cursor.execute("CREATE TABLE checkpoints (session_id TEXT, checkpoint_number INTEGER, title TEXT, overview TEXT, created_at TEXT)")

        cursor.execute(
            "INSERT INTO sessions (id, cwd, repository, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("img-session", str(Path.cwd()), "test/repo", "2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO turns (session_id, turn_index, user_message, assistant_response, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                "img-session",
                0,
                "[image: copilot-image-test.png] please summarize",
                "Done",
                "2026-01-01T12:00:05Z",
            ),
        )
        conn.commit()
        conn.close()

        conn = get_db_connection(test_db)
        session = get_session_by_id(conn, "img-session")
        assert session is not None
        markdown = render_session(conn, session)
        assert "source file unavailable; description pending" in markdown
        conn.close()
    finally:
        test_db.unlink()


def test_copilot_image_attachment_is_dumped_to_marker_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        test_db = Path(tf.name)

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "copilot-image-test.png"
        img_path.write_bytes(base64.b64decode(_PNG_B64))

        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    cwd TEXT,
                    repository TEXT,
                    branch TEXT,
                    summary TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    turn_index INTEGER NOT NULL,
                    user_message TEXT,
                    assistant_response TEXT,
                    timestamp TEXT
                )
            """)
            cursor.execute("CREATE TABLE session_files (session_id TEXT, file_path TEXT, tool_name TEXT, turn_index INTEGER, first_seen_at TEXT)")
            cursor.execute("CREATE TABLE session_refs (session_id TEXT, ref_type TEXT, ref_value TEXT, turn_index INTEGER, created_at TEXT)")
            cursor.execute("CREATE TABLE checkpoints (session_id TEXT, checkpoint_number INTEGER, title TEXT, overview TEXT, created_at TEXT)")
            cursor.execute("CREATE TABLE attachments (session_id TEXT, display_name TEXT, path TEXT, type TEXT)")

            cursor.execute(
                "INSERT INTO sessions (id, cwd, repository, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                ("img-session-2", str(Path.cwd()), "test/repo", "2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z"),
            )
            cursor.execute(
                "INSERT INTO turns (session_id, turn_index, user_message, assistant_response, timestamp) VALUES (?, ?, ?, ?, ?)",
                (
                    "img-session-2",
                    0,
                    "[image: copilot-image-test.png] please summarize",
                    "Done",
                    "2026-01-01T12:00:05Z",
                ),
            )
            cursor.execute(
                "INSERT INTO attachments (session_id, display_name, path, type) VALUES (?, ?, ?, ?)",
                ("img-session-2", "copilot-image-test.png", str(img_path), "image/png"),
            )
            conn.commit()
            conn.close()

            conn = get_db_connection(test_db)
            session = get_session_by_id(conn, "img-session-2")
            assert session is not None
            markdown = render_session(conn, session)
            conn.close()

            marker = re.search(r"\[Image dumped to `([^`]+)` — description pending\]", markdown)
            assert marker is not None
            dumped = Path(marker.group(1))
            assert dumped.exists()
            dumped.unlink()
        finally:
            test_db.unlink()


def test_copilot_image_attachment_from_state_events_is_dumped_to_marker_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        test_db = Path(tf.name)

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "copilot-image-test.png"
        img_path.write_bytes(base64.b64decode(_PNG_B64))

        state_root = Path(tmpdir) / "state-root"
        session_dir = state_root / "img-session-3"
        session_dir.mkdir(parents=True, exist_ok=True)
        events_path = session_dir / "events.jsonl"
        events_path.write_text(
            json.dumps(
                {
                    "type": "user.message",
                    "data": {
                        "content": "[image: copilot-image-test.png] please summarize",
                        "attachments": [
                            {
                                "type": "file",
                                "path": str(img_path),
                                "displayName": "copilot-image-test.png",
                                "mimeType": "image/png",
                            }
                        ],
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )

        original_root = copilot_log.COPILOT_STATE_ROOT
        copilot_log.COPILOT_STATE_ROOT = state_root
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    cwd TEXT,
                    repository TEXT,
                    branch TEXT,
                    summary TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    turn_index INTEGER NOT NULL,
                    user_message TEXT,
                    assistant_response TEXT,
                    timestamp TEXT
                )
            """)
            cursor.execute("CREATE TABLE session_files (session_id TEXT, file_path TEXT, tool_name TEXT, turn_index INTEGER, first_seen_at TEXT)")
            cursor.execute("CREATE TABLE session_refs (session_id TEXT, ref_type TEXT, ref_value TEXT, turn_index INTEGER, created_at TEXT)")
            cursor.execute("CREATE TABLE checkpoints (session_id TEXT, checkpoint_number INTEGER, title TEXT, overview TEXT, created_at TEXT)")

            cursor.execute(
                "INSERT INTO sessions (id, cwd, repository, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                ("img-session-3", str(Path.cwd()), "test/repo", "2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z"),
            )
            cursor.execute(
                "INSERT INTO turns (session_id, turn_index, user_message, assistant_response, timestamp) VALUES (?, ?, ?, ?, ?)",
                (
                    "img-session-3",
                    0,
                    "[image: copilot-image-test.png] please summarize",
                    "Done",
                    "2026-01-01T12:00:05Z",
                ),
            )
            conn.commit()
            conn.close()

            conn = get_db_connection(test_db)
            session = get_session_by_id(conn, "img-session-3")
            assert session is not None
            markdown = render_session(conn, session)
            conn.close()

            marker = re.search(r"\[Image dumped to `([^`]+)` — description pending\]", markdown)
            assert marker is not None
            dumped = Path(marker.group(1))
            assert dumped.exists()
            dumped.unlink()
        finally:
            copilot_log.COPILOT_STATE_ROOT = original_root
            test_db.unlink()


if __name__ == "__main__":
    test_copilot_noise_cleaning()
    print("✓ test_copilot_noise_cleaning")

    test_copilot_db_operations()
    print("✓ test_copilot_db_operations")

    test_copilot_prefix_matching()
    print("✓ test_copilot_prefix_matching")

    test_copilot_image_reference_without_attachment_is_flagged()
    print("✓ test_copilot_image_reference_without_attachment_is_flagged")

    test_copilot_image_attachment_is_dumped_to_marker_path()
    print("✓ test_copilot_image_attachment_is_dumped_to_marker_path")

    test_copilot_image_attachment_from_state_events_is_dumped_to_marker_path()
    print("✓ test_copilot_image_attachment_from_state_events_is_dumped_to_marker_path")

    test_copilot_permissions_join_approval_and_denial()
    print("✓ test_copilot_permissions_join_approval_and_denial")

    test_copilot_permission_pending_when_no_completion()
    print("✓ test_copilot_permission_pending_when_no_completion")

    test_copilot_format_decision()
    print("✓ test_copilot_format_decision")

    test_copilot_attribute_permissions_by_timestamp()
    print("✓ test_copilot_attribute_permissions_by_timestamp")

    print("\nAll tests passed!")
