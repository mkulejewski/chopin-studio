"""Device preferences, pedal commands and explicit simulated input routes."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ..midi_capabilities import FEATURES, InstrumentProfile, MidiEvidence, Support, load_profile, save_profile
from .models import Settings, Simulation


class Capabilities(BaseModel):
    identity: str | None = Field(default=None, max_length=300)
    manufacturer: str | None = Field(default=None, max_length=300)
    confirmed: dict[str, Support] = Field(default_factory=dict, max_length=len(FEATURES))
    controllers: dict[Annotated[int, Field(ge=0, le=127)], Support] = Field(default_factory=dict, max_length=128)
    release_velocity_range: tuple[Annotated[int, Field(ge=0, le=127)], Annotated[int, Field(ge=0, le=127)]] | None = None


Port = Annotated[str, Query(min_length=1, max_length=300)]


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
        recorder.set_pedal_preferences(settings.pedal_enabled, settings.pedal_controller)
        if midi and previous_device != settings.preferred_device:
            midi.request_reconnect()
        return {"ok": True}

    @app.post("/api/devices/reconnect")
    def reconnect():
        if midi:
            midi.request_reconnect()
        return {"ok": True}

    def describe(port):
        profile = midi.profile(port) if midi else MidiEvidence().describe(load_profile(store, port))
        return {"port": port, **profile}

    @app.get("/api/devices/capabilities")
    def device_capabilities(port: Port):
        return describe(port)

    @app.put("/api/devices/capabilities")
    def confirm_device_capabilities(port: Port, capabilities: Capabilities):
        save_profile(store, port, InstrumentProfile(**capabilities.model_dump()))
        return describe(port)

    @app.get("/api/page-commands")
    def page_commands(after: float = 0):
        return recorder.commands(after)

    @app.post("/api/simulation/start")
    def simulate(config: Simulation):
        path = session_folder(config.session_id) / "events.jsonl" if config.session_id else None
        simulation.start(path=path, source_session=config.session_id, speed=config.speed)
        return {"ok": True}

    @app.post("/api/simulation/stop")
    def stop_simulation():
        simulation.stop()
        return {"ok": True}

    return app
