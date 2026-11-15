"""Ordered, one-shot CC88 decoding on derived data; raw capture stays untouched."""
from collections import Counter

REALTIME = {'clock', 'start', 'continue', 'stop', 'active_sensing'}


def velocity_events(events, diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else Counter()
    pending = {}
    previous_time = None
    for event in events:
        if event.get('kind') == 'capture_loss':
            diagnostics['interrupted_prefixes'] += len(pending)
            pending.clear()
        msg = event.get('message')
        if not msg:
            yield event
            continue
        timestamp = event['t']
        if previous_time is not None and timestamp < previous_time:
            diagnostics['out_of_order_events'] += 1
            pending.clear()
        previous_time = timestamp
        channel = msg.get('channel', 0)
        kind = msg['type']
        prefix = pending.pop(channel, None) if kind not in REALTIME else None
        if kind == 'control_change' and msg.get('control') == 88:
            diagnostics['prefixes'] += 1
            if prefix is not None: diagnostics['replaced_prefixes'] += 1
            pending[channel] = (timestamp, msg['value'])
        elif kind in ('note_on', 'note_off'):
            # No reverse lookup or timestamp coincidence pairing. A prefix is
            # consumed once, on its channel, in received order. A stale prefix
            # after a long interruption is withheld rather than guessed.
            valid = prefix is not None and 0 <= timestamp-prefix[0] <= 1
            field = 'velocity_14' if kind == 'note_on' and msg.get('velocity', 0) else 'release_velocity_14'
            event = {**event, field: (msg.get('velocity', 0) << 7) | prefix[1] if valid else None}
            if valid: diagnostics['paired_prefixes'] += 1
            elif prefix is not None: diagnostics['stale_prefixes'] += 1
        elif prefix is not None:
            diagnostics['interrupted_prefixes'] += 1
        if kind not in REALTIME and 'channel' not in msg:
            diagnostics['interrupted_prefixes'] += len(pending)
            pending.clear()
        yield event
    diagnostics['orphan_prefixes'] += len(pending)
