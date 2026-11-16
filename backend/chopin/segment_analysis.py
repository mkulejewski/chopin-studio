"""Offline, derived analysis of an immutable captured performance."""

import statistics
from collections import Counter, defaultdict
from .midi_files import journal_events
from .performance import performance_notes, groups
from .recognition import Recognizer, VERSION


def analyse_segment(store, segment):
    diagnostics = Counter()
    observed = performance_notes(
        journal_events(
            store.root / "sessions" / segment["session_id"] / "events.jsonl"
        ),
        diagnostics,
    )
    observed = [n for n in observed if segment["start"] <= n["onset"] < segment["end"]]
    reference = (
        store.query(
            "SELECT * FROM symbolic_scores WHERE piece_id=? ORDER BY quality DESC",
            (segment["piece_id"],),
        )
        if segment["piece_id"]
        else []
    )
    velocities = [n["velocity"] for n in observed]
    result = {
        "version": VERSION,
        "notes": len(observed),
        "velocity_mean": statistics.mean(velocities) if velocities else None,
        "midi_resolution": dict(diagnostics),
        "observations": [],
        "accuracy": None,
        "notice": "No verified score alignment. Descriptive measurements only.",
    }
    from .microphone import analyse_audio

    try:
        result["audio"] = analyse_audio(
            store.root / "sessions" / segment["session_id"], segment, observed
        )
    except Exception as exc:
        result["audio"] = {
            "available": False,
            "notice": "Audio analysis failed: " + str(exc),
        }
    capture = store.query(
        "SELECT status,error FROM sessions WHERE id=?", (segment["session_id"],)
    )
    if capture and (
        capture[0]["error"] or capture[0]["status"] not in ("saved", "imported")
    ):
        presence = result.get("audio", {}).get("piano_presence")
        if presence:
            presence.update(
                status="uncertain",
                auto_discard=False,
                notice="Capture integrity needs review; microphone audio retained.",
            )
    if not reference:
        return result
    recognizer = Recognizer(reference)
    match = recognizer.match(observed)
    result["match"] = match
    if not match.get("reference_id"):
        return result
    ref = next(r for r in recognizer.references if r["id"] == match["reference_id"])
    from .analysis_selection import reference_identity

    result["reference_revision"] = reference_identity(ref).revision
    og = groups(observed)
    rg = ref["groups"]
    evidence = []
    correct = 0
    expected = 0
    tempo = []
    for a, b in match.get("pairs", []):
        if a >= len(og) or b >= len(rg):
            continue
        actual = og[a]["pitches"]
        wanted = rg[b]["pitches"]
        correct += len(actual & wanted)
        expected += len(wanted)
        for kind, pitches in [("missing", wanted - actual), ("extra", actual - wanted)]:
            for pitch in sorted(pitches):
                evidence.append(
                    {
                        "id": f"{segment['id']}:{a}:{kind}:{pitch}",
                        "kind": kind,
                        "pitch": pitch,
                        "measure": rg[b]["measure"],
                        "time": og[a]["onset"],
                        "confidence": match["confidence"],
                        "expected": sorted(wanted),
                        "observed": sorted(actual),
                        "uncertainty": "Ornaments, repeats, voice allocation and edition differences require review.",
                    }
                )
        tempo.append(
            {
                "time": og[a]["onset"],
                "beat": rg[b]["onset"],
                "measure": rg[b]["measure"],
            }
        )
    paired_observed = {a for a, b in match.get("pairs", [])}
    paired_reference = {b for a, b in match.get("pairs", [])}
    # Compact score-relative note groups for the review overlay. Keep unaligned
    # played groups separate: an uncertain alignment is not proof of extra notes.
    paired_by_reference = {b: a for a, b in match.get("pairs", [])}
    from .symbolic import annotate_reference_staves, annotate_reference_rhythm

    source = store.root / "references" / ref.get("filename", "")
    score_notes = annotate_reference_rhythm(
        annotate_reference_staves(ref["note_data"], source), source
    )
    result["key_fifths"] = next(
        (n["key_fifths"] for n in score_notes if n.get("key_fifths") is not None), None
    )
    comparison = []
    for index in range(match["reference_start"], min(match["reference_end"], len(rg))):
        played = (
            og[paired_by_reference[index]] if index in paired_by_reference else None
        )
        comparison.append(
            {
                "measure": rg[index]["measure"],
                "beat": rg[index]["onset"],
                "key_fifths": next(
                    (
                        score_notes[j]["key_fifths"]
                        for j in rg[index]["indices"]
                        if score_notes[j].get("key_fifths") is not None
                    ),
                    None,
                ),
                "time": played["onset"] if played else None,
                "expected": sorted(rg[index]["pitches"]),
                "observed": sorted(played["pitches"]) if played else [],
                "score_notes": [
                    {
                        key: score_notes[j].get(key)
                        for key in (
                            "pitch",
                            "spelling",
                            "key_fifths",
                            "duration",
                            "staff",
                            "voice",
                            "part",
                            "grace",
                            "display_staff",
                            "staff_source",
                            "clef_sign",
                            "beam_group",
                            "beaming_source",
                            "beat_group_size",
                            "measure_start",
                            "dynamic",
                            "dynamic_velocity",
                            "role",
                        )
                    }
                    for j in rg[index]["indices"]
                ],
                "played_notes": [
                    {
                        key: observed[j].get(key)
                        for key in (
                            "pitch",
                            "onset",
                            "duration",
                            "channel",
                            "velocity",
                            "velocity_14",
                            "release_velocity",
                            "release_velocity_14",
                            "release_source",
                            "released",
                        )
                    }
                    for j in played["indices"]
                ]
                if played
                else [],
            }
        )
    result["note_comparison"] = comparison
    result["unaligned_played_groups"] = sum(
        index not in paired_observed for index in range(len(og))
    )
    for index in range(match["reference_start"], min(match["reference_end"], len(rg))):
        if index not in paired_reference:
            for pitch in rg[index]["pitches"]:
                evidence.append(
                    {
                        "id": f"{segment['id']}:unmatched:{index}:{pitch}",
                        "kind": "unmatched_expected_group",
                        "pitch": pitch,
                        "measure": rg[index]["measure"],
                        "time": None,
                        "confidence": match["confidence"],
                        "expected": sorted(rg[index]["pitches"]),
                        "observed": [],
                        "uncertainty": "Could be omission, repeat structure or alignment ambiguity; no exact observed timestamp exists.",
                    }
                )
    voice_velocities = defaultdict(list)
    for a, b in match.get("pairs", []):
        for observed_index in og[a]["indices"]:
            note = observed[observed_index]
            candidates = [
                ref["note_data"][j]
                for j in rg[b]["indices"]
                if ref["note_data"][j]["pitch"] == note["pitch"]
            ]
            if len(candidates) == 1:
                source_note = candidates[0]
                voice_velocities[
                    f"part {source_note.get('part', 0)} / staff {source_note.get('staff', '?')} / voice {source_note.get('voice', '?')}"
                ].append(note["velocity"])
    pedal_events = [
        e
        for e in journal_events(
            store.root / "sessions" / segment["session_id"] / "events.jsonl"
        )
        if segment["start"] <= e["t"] < segment["end"]
        and e.get("message", {}).get("type") == "control_change"
        and e["message"].get("control") == 64
    ]
    values = [e["message"]["value"] for e in pedal_events]
    pedal_changes = sum(a >= 64 > b or a < 64 <= b for a, b in zip(values, values[1:]))
    result.update(
        {
            "observations": evidence[:5000],
            "observations_truncated": len(evidence) > 5000,
            "alignment": tempo,
            "reference_id": ref["id"],
            "reference_quality": ref["quality"],
            "voice_velocity": {
                voice: {"mean": statistics.mean(velocities), "count": len(velocities)}
                for voice, velocities in voice_velocities.items()
            },
            "pedal": {
                "messages": len(values),
                "threshold_crossings": pedal_changes,
                "partial_values": sum(0 < v < 127 for v in values),
                "notice": "Controller positions only, not proof of acoustic clearing or blurring.",
            },
            "ornaments": {
                "reference_grace_notes": sum(
                    bool(n.get("grace")) for n in ref["note_data"]
                ),
                "treatment": "Grace-note durations are retained; trills and free ornaments are not classified reliably and may appear as uncertain mismatches.",
            },
            "notice": "Experimental edit alignment. Ornaments and repeated passages can be ambiguous. Review note evidence; MIDI velocity is not loudness.",
        }
    )
    # Accuracy remains withheld: ornaments, unmatched groups and edition variants
    # are not yet resolved robustly enough for a defensible percentage.
    result["matched_pitch_count"] = correct
    from .assessment import assess

    result["assessment"] = assess(store, segment, ref, match, og, rg, correct)
    from .tempo import infer_tempo

    result["tempo"] = infer_tempo(observed, ref, match)
    result["tempo_curve"] = result["tempo"]["curve"]
    from .musical_comparison import musical_review

    result["musical_review"] = musical_review(
        comparison,
        ref["quality"],
        0 if match.get("location_ambiguous") else match["confidence"],
    )
    judgements = {
        (g["time"], g["measure"], side, int(pitch)): item
        for g in comparison
        for side, items in g["musical_context"].items()
        for pitch, item in items.items()
    }
    for observation in result["observations"]:
        side = "observed" if observation["kind"] == "extra" else "expected"
        observation["musical_judgement"] = judgements.get(
            (observation["time"], observation["measure"], side, observation["pitch"])
        )
    from .passages import passage_analysis

    result["passages"] = passage_analysis(
        comparison,
        list(
            journal_events(
                store.root / "sessions" / segment["session_id"] / "events.jsonl"
            )
        ),
        segment,
        result,
        store.setting("voicing:" + segment["piece_id"], {}),
    )
    return result
