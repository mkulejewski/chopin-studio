"""Compatibility characterizations captured before domain/router extraction."""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chopin.app import create_app
from chopin.assessment import piece_assessment
from chopin.organisation import analyse_segment, organise, performance_notes
from chopin.progress import current_analyses
from chopin.retention import current_analysis
from chopin.store import Store
from test_practice import make_session, reference


def test_openapi_contract(tmp_path):
    with TestClient(create_app(tmp_path, hardware=False)) as client:
        expected = json.loads(
            (Path(__file__).parent / "fixtures/api_contract.json").read_text()
        )
        assert client.get("/openapi.json").json() == expected
        assert {
            "active",
            "saving",
            "shutting_down",
            "notes",
            "pedals",
            "devices",
        } <= client.get("/api/status").json().keys()
        assert {"pieces", "volumes"} == client.get("/api/library").json().keys()
        assert client.get("/api/sessions").json() == []
        assert client.get("/api/recordings").json()["takes"] == []
        assert len(client.get("/api/progress").json()) == 44


@pytest.fixture
def saved_analysis(tmp_path):
    store = Store(tmp_path)
    reference(store)
    sid = make_session(store)
    segment = organise(store, sid)[0]
    result = analyse_segment(store, segment)
    result["segment_snapshot"] = {
        k: segment[k]
        for k in ("piece_id", "start", "end", "revision", "complete", "discarded")
    }
    store.execute(
        "INSERT INTO analyses VALUES(?,?,?,?,?,?)",
        ("original", sid, segment["id"], "test", "2026-11-16", json.dumps(result)),
    )
    yield store, segment, result
    store.db.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("piece_id", "n9-2"),
        ("start", 0.1),
        ("end", 2),
        ("revision", 2),
        ("complete", 0),
        ("discarded", 1),
    ],
)
def test_snapshot_changes_withhold_current_evidence_without_changing_history(
    saved_analysis, field, value
):
    store, segment, result = saved_analysis
    original = store.query("SELECT * FROM analyses")
    store.execute(f"UPDATE segments SET {field}=? WHERE id=?", (value, segment["id"]))
    changed = store.query("SELECT * FROM segments WHERE id=?", (segment["id"],))[0]
    assert current_analysis(store, changed) == {}
    assert list(current_analyses(store, "n9-1")) == []
    assert piece_assessment(store, "n9-1")["latest_performance"] is None
    assert store.query("SELECT * FROM analyses") == original


def test_newer_stale_analysis_does_not_hide_older_current_result(saved_analysis):
    store, segment, result = saved_analysis
    wrong = {
        **result,
        "segment_snapshot": {**result["segment_snapshot"], "revision": 99},
    }
    store.execute(
        "INSERT INTO analyses VALUES(?,?,?,?,?,?)",
        (
            "new",
            segment["session_id"],
            segment["id"],
            "test",
            "2026-11-17",
            json.dumps(wrong),
        ),
    )
    assert current_analysis(store, segment) == json.loads(json.dumps(result))
    assert [row["id"] for row, _ in current_analyses(store, "n9-1")] == ["original"]
    assert (
        piece_assessment(store, "n9-1")["latest_performance"]["analysis_id"]
        == "original"
    )


def test_performance_projection_preserves_source_unknown_fields():
    events = [
        {
            "t": 0,
            "sequence": 99,
            "custom": {"x": "kept"},
            "message": {"type": "note_on", "channel": 2, "note": 60, "velocity": 87},
        },
        {
            "t": 1,
            "message": {"type": "note_off", "channel": 2, "note": 60, "velocity": 31},
        },
    ]
    original = json.dumps(events)
    note = performance_notes(iter(events))[0]
    assert (
        note["pitch"],
        note["duration"],
        note["release_velocity"],
        note["channel"],
    ) == (60, 1, 31, 2)
    assert json.dumps(events) == original


def test_legacy_database_initialization_preserves_user_fields_and_pages(tmp_path):
    db = sqlite3.connect(tmp_path / "studio.sqlite3")
    migration = Path(__file__).parents[1] / "backend/chopin/migrations/001_initial.sql"
    db.executescript(migration.read_text())
    db.execute(
        "INSERT INTO volumes(id,title,source,edition) VALUES('nocturnes','My volume','synthetic','test')"
    )
    db.execute(
        "INSERT INTO pieces(id,title,genre,opus,musical_key,volume_id,start_page,end_page,notes) VALUES('n9-1','My title','Nocturnes','9 No. 1','B-flat minor','nocturnes',10,14,'My notes')"
    )
    db.commit()
    db.close()
    store = Store(tmp_path)
    row = store.query("SELECT * FROM pieces WHERE id='n9-1'")[0]
    assert (row["title"], row["start_page"], row["end_page"], row["notes"]) == (
        "My title",
        10,
        14,
        "My notes",
    )
    assert len(store.query("SELECT id FROM pieces")) == 44
    assert len(store.query("SELECT id FROM volumes")) == 11
    store.execute(
        "UPDATE pieces SET mastery=1,notes='later',volume_id='schott' WHERE id='n9-1'"
    )
    store.db.close()
    reopened = Store(tmp_path)
    row = reopened.query("SELECT * FROM pieces WHERE id='n9-1'")[0]
    assert (row["mastery"], row["notes"], row["volume_id"]) == (1, "later", "schott")
    assert reopened.query("PRAGMA user_version")[0]["user_version"] == 7
    reopened.db.close()


@pytest.mark.parametrize(
    "change", ["source", "deleted", "quality", "edition", "notes", "reference_removed"]
)
def test_current_automatic_evidence_rejects_changed_source_or_reference(
    saved_analysis, change
):
    store, segment, result = saved_analysis
    before = store.query("SELECT * FROM analyses")
    if change == "source":
        store.execute(
            "UPDATE sessions SET status='incomplete' WHERE id=?",
            (segment["session_id"],),
        )
    elif change == "deleted":
        store.execute(
            "INSERT INTO recording_deletions(id,session_id,segment_id,start,end,scope,status,created) VALUES('d',?,?,0,1,'recording','done','now')",
            (segment["session_id"], segment["id"]),
        )
    elif change == "reference_removed":
        store.execute(
            "DELETE FROM symbolic_scores WHERE id=?", (result["reference_id"],)
        )
    else:
        value = {"quality": "provisional", "edition": "changed edition", "notes": "[]"}[
            change
        ]
        store.execute(
            f"UPDATE symbolic_scores SET {change}=? WHERE id=?",
            (value, result["reference_id"]),
        )
    assert list(current_analyses(store, "n9-1")) == []
    assert piece_assessment(store, "n9-1")["automatic_level"] is None
    # Retention can describe an incomplete source for manual audio review.
    assert bool(current_analysis(store, segment)) is (change == "source")
    assert store.query("SELECT * FROM analyses") == before


def test_retention_policy_keeps_discarded_take_evidence_separate(saved_analysis):
    store, segment, result = saved_analysis
    store.execute("UPDATE segments SET discarded=1 WHERE id=?", (segment["id"],))
    segment["discarded"] = 1
    result["segment_snapshot"]["discarded"] = 1
    store.execute("UPDATE analyses SET result=?", (json.dumps(result),))
    assert current_analysis(store, segment)
    assert list(current_analyses(store, "n9-1")) == []


def test_failed_timeline_write_rolls_back_history_and_keep_protection(tmp_path):
    app = create_app(tmp_path, hardware=False)
    store = app.state.store
    reference(store)
    sid = make_session(store)
    segment = organise(store, sid)[0]
    store.execute(
        "INSERT INTO recording_choices(segment_id,choice) VALUES(?,'keep')",
        (segment["id"],),
    )
    before = {
        name: store.query("SELECT * FROM " + name)
        for name in ("segments", "segment_history", "recording_choices")
    }
    store.execute(
        "CREATE TRIGGER reject_test_edit BEFORE INSERT ON segments WHEN NEW.label='force failure' BEGIN SELECT RAISE(ABORT,'synthetic write failure'); END"
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        edited = {**segment, "label": "force failure"}
        response = client.put(
            f"/api/sessions/{sid}/segments",
            json={"segments": [edited], "expected_revision": segment["revision"]},
        )
        assert response.status_code == 500
        for name, rows in before.items():
            assert store.query("SELECT * FROM " + name) == rows
        assert store.db.in_transaction is False


def test_store_transactions_support_nested_rollback(tmp_path):
    store = Store(tmp_path)
    with store.transaction():
        store.set_setting("outer", True)
        with pytest.raises(RuntimeError):
            with store.transaction():
                store.set_setting("inner", True)
                raise RuntimeError("synthetic failure")
        assert store.setting("inner") is None
        store.set_setting("after", True)
    assert store.setting("outer") is True and store.setting("after") is True
    with pytest.raises(RuntimeError):
        with store.transaction():
            store.set_setting("outer", False)
            raise RuntimeError("rollback")
    assert store.setting("outer") is True
    store.db.close()


def test_seeded_database_repairs_original_ids_without_overwriting_existing_rows(
    tmp_path,
):
    store = Store(tmp_path)
    store.execute("DELETE FROM pieces WHERE id='n72-1'")
    store.execute(
        "UPDATE pieces SET title='My title',mastery=1,notes='unchanged' WHERE id='e25-1'"
    )
    store.db.close()
    store = Store(tmp_path)
    assert len(store.query("SELECT * FROM pieces")) == 44
    assert store.query("SELECT title,mastery,notes FROM pieces WHERE id='e25-1'")[
        0
    ] == {"title": "My title", "mastery": 1, "notes": "unchanged"}
    store.db.close()


def test_comparison_json_response_preserves_complete_domain_payload(tmp_path):
    from chopin.passages import compare_passages

    app = create_app(tmp_path, hardware=False)
    store = app.state.store
    reference(store)
    segments = [organise(store, make_session(store))[0] for _ in range(2)]
    a, b = [analyse_segment(store, segment) for segment in segments]
    raw = [
        (store.root / "sessions" / s["session_id"] / "events.jsonl").read_bytes()
        for s in segments
    ]
    with TestClient(app) as client:
        response = client.get(
            "/api/comparison",
            params={"left": segments[0]["id"], "right": segments[1]["id"]},
        )
        assert (
            response.status_code == 200
            and response.headers["content-type"] == "application/json"
        )
        payload = response.json()
        for side, segment, analysis in zip(("left", "right"), segments, (a, b)):
            assert payload[side] == json.loads(
                json.dumps({"segment": segment, "analysis": analysis})
            )
        assert payload["aligned"] == json.loads(json.dumps(compare_passages(a, b)))
        assert [
            (store.root / "sessions" / s["session_id"] / "events.jsonl").read_bytes()
            for s in segments
        ] == raw


def test_overview_reuses_evidence_without_stale_cross_request_cache(saved_analysis):
    from chopin.progress import progress_overview, piece_progress

    store, segment, result = saved_analysis
    overview = next(row for row in progress_overview(store) if row["id"] == "n9-1")
    assert overview["machine"] == piece_assessment(store, "n9-1")
    assert overview["practice"] == piece_progress(store, "n9-1")
    store.execute(
        "UPDATE segments SET revision=revision+1 WHERE id=?", (segment["id"],)
    )
    changed = next(row for row in progress_overview(store) if row["id"] == "n9-1")
    assert (
        changed["machine"]["latest_performance"] is None
        and changed["practice"]["measures"] == []
    )


def test_hardware_disabled_server_does_not_enumerate_physical_outputs(
    tmp_path, monkeypatch
):
    import mido

    def forbidden():
        raise AssertionError("Physical output discovery is forbidden in this fixture")

    monkeypatch.setattr(mido, "get_output_names", forbidden)
    with TestClient(create_app(tmp_path, hardware=False)) as client:
        assert client.get("/api/audio/hardware").json()["ports"] == []
