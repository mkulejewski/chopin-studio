#!/usr/bin/env python3
"""Desktop entry point: one backend, independent of browser lifetime."""
import argparse
import fcntl
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser


def studio_windows(wmctrl):
    """Identify only this localhost app window, never ordinary Chrome tabs."""
    try:
        result = subprocess.run([wmctrl, '-lx'], capture_output=True, text=True, timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        return []
    windows = []
    for line in result.stdout.splitlines():
        fields = line.split(None, 4)
        if (len(fields) == 5 and fields[2].lower().startswith('127.0.0.1.')
                and fields[4] == 'Chopin Studio'):
            windows.append(fields[0])
    return windows


def maximize_frontend(wmctrl, previous):
    # Chrome can forward --app to an existing browser and ignore startup flags.
    # Prefer a newly created app window; reuse an existing one only after waiting.
    target = None
    for _ in range(20):
        windows = studio_windows(wmctrl)
        fresh = [ident for ident in windows if ident not in previous]
        if fresh:
            target = fresh[-1]
            break
        time.sleep(.2)
    if target is None:
        windows = studio_windows(wmctrl)
        target = windows[-1] if windows else None
    if target:
        # Repeat after window creation settles in case Chrome restores old bounds.
        for attempt in range(2):
            try:
                subprocess.run([wmctrl, '-ir', target, '-b', 'add,maximized_vert,maximized_horz'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                return
            if attempt == 0:time.sleep(.25)


def open_frontend(fullscreen=False):
    url = 'http://127.0.0.1:8765'
    browser = next((shutil.which(x) for x in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable') if shutil.which(x)), None)
    if browser:
        options = ['--start-fullscreen'] if fullscreen else ['--start-maximized']
        wmctrl = shutil.which('wmctrl') if os.environ.get('DISPLAY') and not fullscreen else None
        previous = set(studio_windows(wmctrl)) if wmctrl else set()
        subprocess.Popen([browser, *options, '--app=' + url], start_new_session=True)
        if wmctrl:maximize_frontend(wmctrl, previous)
    else:
        webbrowser.open(url)


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
        open_frontend(args.fullscreen)
    return 0

if __name__=='__main__':sys.exit(main())
