from types import SimpleNamespace
from chopin.platform.linux.desktop import close_studio_windows


def test_close_targets_only_dedicated_studio_app_windows(monkeypatch):
    calls = []
    monkeypatch.setenv('DISPLAY', ':0')
    monkeypatch.setattr('chopin.platform.linux.desktop.shutil.which', lambda _: '/usr/bin/wmctrl')
    listing = ('0x1 0 google-chrome.Google-chrome host Chopin Studio\n'
               '0x2 0 127.0.0.1.Google-chrome host Other localhost app\n'
               '0x3 0 127.0.0.1.Google-chrome host Chopin Studio\n'
               '0x4 0 127.0.0.1.Google-chrome host Chopin Studio\n')
    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout=listing)
    monkeypatch.setattr('chopin.platform.linux.desktop.subprocess.run', run)
    close_studio_windows()
    assert calls == [['/usr/bin/wmctrl', '-lx'], ['/usr/bin/wmctrl', '-ic', '0x3'], ['/usr/bin/wmctrl', '-ic', '0x4']]


def test_without_x11_does_not_touch_windows(monkeypatch):
    monkeypatch.delenv('DISPLAY', raising=False)
    monkeypatch.setattr('chopin.platform.linux.desktop.subprocess.run', lambda *a, **k: (_ for _ in ()).throw(AssertionError('must not invoke wmctrl')))
    close_studio_windows()
