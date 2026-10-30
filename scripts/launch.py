#!/usr/bin/env python3
"""Desktop entry point: one backend, independent of browser lifetime."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fullscreen', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'chopin-studio'
    state.mkdir(parents=True, exist_ok=True)
    # Launcher lock avoids two simultaneous desktop clicks spawning competing services.
    with (state/'launcher.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        def available():
            try:
                with urllib.request.urlopen('http://127.0.0.1:8765/api/status', timeout=1) as response:
                    data=json.load(response)
                    return 'active' in data and 'pedals' in data
            except Exception:
                return False
        if not available():
            with (state/'launcher.log').open('a') as output:
                subprocess.Popen([str(root/'.venv/bin/python'), '-m', 'chopin'],cwd=root,
                                 stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            for _ in range(60):
                if available():break
                time.sleep(.25)
            else:
                message=f'Chopin Studio could not start. See {state}/launcher.log'
                subprocess.run(['zenity','--error','--text',message], check=False) if __import__('shutil').which('zenity') else print(message,file=sys.stderr)
                return 1
    if not args.no_browser:
        if args.fullscreen:
            import shutil
            browser=next((shutil.which(x) for x in ('chromium','chromium-browser','google-chrome') if shutil.which(x)),None)
            if browser:
                subprocess.Popen([browser,'--start-fullscreen','--app=http://127.0.0.1:8765'])
                return 0
        webbrowser.open('http://127.0.0.1:8765')
    return 0

if __name__=='__main__':sys.exit(main())
