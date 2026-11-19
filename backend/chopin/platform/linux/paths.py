"""Linux XDG conventions. Resolving a path does not open or create it."""

import os
from pathlib import Path


def data_root():
    xdg_data = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    return Path(os.environ.get('CHOPIN_DATA_DIR', xdg_data / 'chopin-studio'))


def state_root():
    return Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'chopin-studio'
