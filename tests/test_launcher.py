"""Desktop fallback must target only Chopin Studio's app window."""
from types import SimpleNamespace

from scripts import launch


def test_window_filter_does_not_target_regular_browser_tabs(monkeypatch):
    output = ('0x1 0 google-chrome.Google-chrome host Chopin Studio\n'
              '0x2 0 127.0.0.1.Google-chrome host Other localhost app\n'
              '0x3 0 127.0.0.1.Google-chrome host Chopin Studio\n')
    monkeypatch.setattr(launch.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=output))
    assert launch.studio_windows('/usr/bin/wmctrl') == ['0x3']


def test_maximization_prefers_new_app_window_and_reapplies_after_restore(monkeypatch):
    calls=[]
    monkeypatch.setattr(launch, 'studio_windows', lambda _: ['0xold', '0xnew'])
    monkeypatch.setattr(launch.time, 'sleep', lambda _: None)
    monkeypatch.setattr(launch.subprocess, 'run', lambda cmd, **kwargs: calls.append(cmd))
    launch.maximize_frontend('/usr/bin/wmctrl', {'0xold'})
    assert calls == [['/usr/bin/wmctrl', '-ir', '0xnew', '-b', 'add,maximized_vert,maximized_horz']]*2


def test_reused_window_is_maximized_when_chrome_does_not_create_another(monkeypatch):
    calls=[]
    monkeypatch.setattr(launch, 'studio_windows', lambda _: ['0xold'])
    monkeypatch.setattr(launch.time, 'sleep', lambda _: None)
    monkeypatch.setattr(launch.subprocess, 'run', lambda cmd, **kwargs: calls.append(cmd))
    launch.maximize_frontend('/usr/bin/wmctrl', {'0xold'})
    assert all(cmd[2] == '0xold' for cmd in calls) and len(calls) == 2


def test_explicit_fullscreen_keeps_its_launch_flag_and_skips_maximize(monkeypatch):
    calls=[]
    monkeypatch.setattr(launch.shutil, 'which', lambda name: '/usr/bin/google-chrome' if name=='google-chrome' else None)
    monkeypatch.setenv('DISPLAY', ':0')
    monkeypatch.setattr(launch.subprocess, 'Popen', lambda cmd, **kwargs: calls.append(cmd))
    monkeypatch.setattr(launch, 'maximize_frontend', lambda *a: (_ for _ in ()).throw(AssertionError('must not maximize fullscreen')))
    launch.open_frontend(fullscreen=True)
    assert calls == [['/usr/bin/google-chrome', '--start-fullscreen', '--app=http://127.0.0.1:8765']]


def test_default_launch_keeps_maximized_flag_and_applies_window_fallback(monkeypatch):
    launches=[];maximizations=[]
    paths={'google-chrome':'/usr/bin/google-chrome','wmctrl':'/usr/bin/wmctrl'}
    monkeypatch.setattr(launch.shutil,'which',lambda name:paths.get(name))
    monkeypatch.setenv('DISPLAY',':0')
    monkeypatch.setattr(launch,'studio_windows',lambda _:['0xold'])
    monkeypatch.setattr(launch.subprocess,'Popen',lambda cmd,**kwargs:launches.append(cmd))
    monkeypatch.setattr(launch,'maximize_frontend',lambda wmctrl,previous:maximizations.append((wmctrl,previous)))
    launch.open_frontend()
    assert launches==[['/usr/bin/google-chrome','--start-maximized','--app=http://127.0.0.1:8765']]
    assert maximizations==[('/usr/bin/wmctrl',{'0xold'})]
