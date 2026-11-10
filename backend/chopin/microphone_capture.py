"""Supervise ALSA until the backend exits, including after an unclean exit.

Polling the parent process avoids PR_SET_PDEATHSIG's creating-thread semantics:
FastAPI may retire the worker thread that launched a long-running recording.
"""
import os
import signal
import subprocess
import sys


def main():
    parent = int(sys.argv[1])
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    if os.getppid() != parent:
        return 1
    process = subprocess.Popen(sys.argv[2:], stdin=subprocess.DEVNULL)
    try:
        while process.poll() is None:
            if stopping or os.getppid() != parent:
                process.send_signal(signal.SIGINT)
                try:
                    return process.wait(3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    return process.wait()
            try:
                return process.wait(.2)
            except subprocess.TimeoutExpired:
                pass
        return process.returncode
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


if __name__ == '__main__':
    raise SystemExit(main())
