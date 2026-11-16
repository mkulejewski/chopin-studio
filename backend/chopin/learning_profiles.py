"""Versioned Learning profile persistence, independent of recorder control."""

import copy
import json
from .learning_definition import DEFAULTS


def load_profile(store, bundle):
    rows = store.query(
        "SELECT * FROM learning_profiles WHERE piece_id=?", (bundle["piece_id"],)
    )
    if rows:
        state = json.loads(rows[0]["state"])
        if rows[0]["revision"] == bundle["revision"]:
            state["config"] = {**DEFAULTS, **state["config"]}
            state.setdefault("corrections", [])
            state.setdefault("hand", "both")
            state.setdefault("hand_progress", {})
            return state
        # Retain old attempts; a new source requires fresh progress and rules.
    fresh = {
        "config": dict(DEFAULTS),
        "chunks": bundle["chunks"],
        "variants": [],
        "corrections": [],
        "stage_index": 0,
        "streak": 0,
        "completed": [],
        "generation": 0,
        "hand": "both",
        "hand_progress": {},
    }
    if rows and rows[0]["revision"] == bundle.get("previous_revision"):
        # Scan-study judgements cannot become verified pitch evidence. Keep
        # the entire previous profile as historical data, including custom
        # chunks/rules and every hand's progress; retain routine preferences.
        fresh["previous_profile"] = {
            "revision": rows[0]["revision"],
            "state": copy.deepcopy(state),
        }
        fresh["config"] = {**DEFAULTS, **state["config"]}
        fresh["hand"] = state.get("hand", "both")
        fresh["generation"] = state.get("generation", 0) + 1
    return fresh


def save_profile(store, bundle, profile):
    store.execute(
        "INSERT OR REPLACE INTO learning_profiles VALUES(?,?,?)",
        (bundle["piece_id"], bundle["revision"], json.dumps(profile)),
    )
