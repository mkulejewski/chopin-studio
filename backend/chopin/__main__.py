import logging
import fcntl
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

import uvicorn
from .app import create_app
from .store import data_root

root = data_root()
root.mkdir(parents=True, exist_ok=True)
instance_lock = (root / "backend.lock").open("a")
try:
    fcntl.flock(instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit("Chopin Studio is already running for this data directory")

log_root = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'chopin-studio'
log_root.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), RotatingFileHandler(log_root / 'studio.log', maxBytes=2_000_000, backupCount=3)], format='%(asctime)s %(levelname)s %(name)s: %(message)s')
def request_shutdown():
    server.should_exit = True


app = create_app(hardware=os.environ.get('CHOPIN_NO_HARDWARE') != '1', shutdown=request_shutdown)
server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=int(os.environ.get('CHOPIN_PORT', '8765'))))
server.run()
