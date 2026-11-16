"""Device preferences, pedal commands and explicit simulated input routes."""

import logging
import threading
import time

import mido

from ..midi_files import journal_events

log = logging.getLogger(__name__)


from fastapi import APIRouter

from .models import Settings, Simulation


def router(store, recorder, midi, simulation, session_folder):
    app = APIRouter()

    @app.get("/api/settings")
    def get_settings():
        return {
            key: store.setting(key, value)
            for key, value in Settings().model_dump().items()
        }

    @app.put("/api/settings")
    def save_settings(settings: Settings):
        previous_device = store.setting("preferred_device", "")
        with store.transaction():
            for key, value in settings.model_dump().items():
                store.set_setting(key, value)
        recorder.pedal_enabled = settings.pedal_enabled
        recorder.pedal_controller = settings.pedal_controller
        recorder.pedal_down = None
        if midi and previous_device != settings.preferred_device:
            midi.reconnect.set()
        return {"ok": True}

    @app.post("/api/devices/reconnect")
    def reconnect():
        if midi:
            midi.reconnect.set()
        return {"ok": True}

    @app.get("/api/page-commands")
    def page_commands(after: float = 0):
        return recorder.commands(after)

    @app.post("/api/simulation/start")
    def simulate(config: Simulation):
        if simulation["running"]:
            raise ValueError("Simulation is already running")
        if midi and midi.connected:
            raise ValueError(
                "Disconnect the piano before simulated input to avoid mixing performances"
            )
        path = (
            session_folder(config.session_id) / "events.jsonl"
            if config.session_id
            else None
        )
        simulation["running"] = True
        simulation["cancel"].clear()
        with recorder.lock:
            if recorder.active:
                recorder.simulated_recording = True
        recorder.mark("simulation_started", {"source_session": config.session_id})

        def run():
            try:
                if path:
                    events = journal_events(path)
                else:
                    # Synthetic scale only; never pretend this is a Chopin reference.
                    events = (
                        {
                            "t": i * 0.35 + off,
                            "message": mido.Message(
                                kind, note=note, velocity=velocity
                            ).dict(),
                        }
                        for i, note in enumerate([60, 62, 64, 65, 67, 69, 71, 72] * 3)
                        for off, kind, velocity in [
                            (0, "note_on", 64 + i % 20),
                            (0.25, "note_off", 0),
                        ]
                    )
                epoch = time.monotonic()
                for event in events:
                    if "message" not in event:
                        continue
                    delay = max(
                        0, event["t"] / config.speed - (time.monotonic() - epoch)
                    )
                    if simulation["cancel"].wait(delay):
                        break
                    recorder.receive(mido.Message.from_dict(event["message"]))
                for channel in range(16):
                    recorder.receive(
                        mido.Message(
                            "control_change", channel=channel, control=123, value=0
                        )
                    )
            except Exception:
                log.exception("Simulation failed")
            finally:
                simulation["running"] = False
                recorder.mark("simulation_ended", {})

        threading.Thread(target=run, daemon=True, name="midi-simulation").start()
        return {"ok": True}

    @app.post("/api/simulation/stop")
    def stop_simulation():
        simulation["cancel"].set()
        return {"ok": True}

    return app
