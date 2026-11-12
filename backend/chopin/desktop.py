"""Close only dedicated X11 Chopin Studio app windows after explicit shutdown."""
import logging
import os
import shutil
import subprocess

log = logging.getLogger(__name__)


def close_studio_windows():
    wmctrl = shutil.which('wmctrl') if os.environ.get('DISPLAY') else None
    if not wmctrl:
        return
    try:
        result = subprocess.run([wmctrl, '-lx'], capture_output=True, text=True, timeout=2, check=True)
        for line in result.stdout.splitlines():
            fields = line.split(None, 4)
            # Chrome app windows have a localhost WM_CLASS. Ordinary browser
            # windows, including tabs titled Chopin Studio, must stay open.
            if (len(fields) == 5 and fields[2].lower().startswith('127.0.0.1.')
                    and fields[4] == 'Chopin Studio'):
                subprocess.run([wmctrl, '-ic', fields[0]], timeout=2, check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        log.warning('Could not close the dedicated Chopin Studio window', exc_info=True)
