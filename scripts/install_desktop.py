"""Install a user-scoped desktop shortcut. Never writes system directories."""
import os
from pathlib import Path
import shutil

root=Path(__file__).resolve().parents[1]
data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
applications=data/'applications'
applications.mkdir(parents=True,exist_ok=True)
icon=data/'icons/hicolor/scalable/apps/chopin-studio.svg'
icon.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(root/'frontend/public/icon.svg',icon)

def quote(value):
    return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')+'"'

entry=f'''[Desktop Entry]
Type=Application
Name=Chopin Studio
Comment=Your local piano practice workstation
Exec={quote(root/'.venv/bin/python')} {quote(root/'scripts/launch.py')}
Icon=chopin-studio
Terminal=false
Categories=AudioVideo;Music;
StartupNotify=true
Actions=Fullscreen;

[Desktop Action Fullscreen]
Name=Open fullscreen
Exec={quote(root/'.venv/bin/python')} {quote(root/'scripts/launch.py')} --fullscreen
'''
(applications/'chopin-studio.desktop').write_text(entry)
print('Desktop launcher installed:',applications/'chopin-studio.desktop')
