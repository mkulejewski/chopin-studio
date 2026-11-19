"""Conservative MIDI evidence and optional, explicitly confirmed profiles."""

from dataclasses import asdict, dataclass, field
from typing import Literal

from .platform.interfaces import MidiMessage

Support = Literal["supported", "unsupported", "unknown"]
CONTROLLER_FEATURES = {66: "sostenuto", 67: "soft_pedal", 88: "cc88"}
FEATURES = (
    "midi_input", "midi_output", "note_on_velocity", "cc88", "note_off_velocity",
    "continuous_sustain", "binary_sustain", "sostenuto", "soft_pedal",
)


@dataclass
class InstrumentProfile:
    """Per-port settings. Unknown is the default for each unconfirmed feature."""

    identity: str | None = None
    manufacturer: str | None = None
    confirmed: dict[str, Support] = field(default_factory=dict)
    controllers: dict[int, Support] = field(default_factory=dict)
    release_velocity_range: tuple[int, int] | None = None


@dataclass
class MidiEvidence:
    features: set[str] = field(default_factory=set)
    controllers: set[int] = field(default_factory=set)

    release_values: set[int] = field(default_factory=set)

    def observe(self, message: MidiMessage):
        self.features.add("midi_input")
        kind = message["type"]
        if kind == "note_on" and message["velocity"]:
            self.features.add("note_on_velocity")
        elif kind == "note_off":
            self.release_values.add(message["velocity"])
            # A fixed default (often 0 or 64) does not demonstrate release sensing.
            if len(self.release_values) > 1:
                self.features.add("note_off_velocity")
        elif kind == "control_change":
            controller = message["control"]
            self.controllers.add(controller)
            feature = CONTROLLER_FEATURES.get(controller)
            if feature:
                self.features.add(feature)
            if controller == 64 and 0 < message["value"] < 127:
                self.features.add("continuous_sustain")

    def describe(self, profile: InstrumentProfile):
        return {
            **asdict(profile),
            "observed": sorted(self.features),
            "observed_controllers": sorted(self.controllers),
            "observed_release_values": sorted(self.release_values),
            "support": {
                name: profile.confirmed.get(
                    name, "supported" if name in self.features else "unknown",
                )
                for name in FEATURES
            },
        }


def load_profile(store, port):
    data = store.setting("midi_capabilities:" + port, {})
    bounds = data.get("release_velocity_range")
    return InstrumentProfile(
        identity=data.get("identity"), manufacturer=data.get("manufacturer"),
        confirmed=data.get("confirmed", {}),
        controllers={int(key): value for key, value in data.get("controllers", {}).items()},
        release_velocity_range=tuple(bounds) if bounds is not None else None,
    )


def save_profile(store, port, profile: InstrumentProfile):
    if profile.confirmed.keys() - set(FEATURES):
        raise ValueError("Unknown MIDI capability")
    bounds = profile.release_velocity_range
    if bounds is not None and not 0 <= bounds[0] <= bounds[1] <= 127:
        raise ValueError("Release calibration must give the minimum before the maximum")
    store.set_setting("midi_capabilities:" + port, asdict(profile))
