"""Desktop integration for macOS, Windows, and Windows-hosted WSL."""
import base64
import os
from pathlib import Path
import shutil
import subprocess
import sys
import webbrowser


def is_wsl():
    return sys.platform == 'linux' and ('WSL_DISTRO_NAME' in os.environ or
        'microsoft' in os.uname().release.lower())


def powershell(script):
    # EncodedCommand preserves Unicode and keeps paths out of shell syntax.
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                             '-EncodedCommand', encoded], capture_output=True,
                            timeout=20)
    if result.returncode:
        raise ValueError(result.stderr.decode('utf-8', errors='replace').strip() or
                         'Windows could not complete the desktop operation.')
    return result.stdout.decode('utf-8-sig').strip()


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def default_directory():
    if sys.platform == 'win32' or is_wsl():
        try:
            directory = powershell(
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                "$d = (Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders')."
                "'{374DE290-123F-4565-9164-39C4925E467B}'; "
                "if (!$d) { $d = Join-Path $env:USERPROFILE 'Downloads' }; "
                "[Environment]::ExpandEnvironmentVariables($d)")
            if is_wsl():
                directory = subprocess.check_output(['wslpath', '-u', directory], text=True).strip()
            return Path(directory)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise ValueError('Could not locate Windows Downloads. Use --directory PATH. ' + str(exc)) from exc
    return Path.home() / 'Downloads'


def open_windows(target, app=None):
    script = "$ErrorActionPreference = 'Stop'; $target = " + ps_literal(target) + '; '
    if app and app != 'Adobe Acrobat':
        script += "$reader = " + ps_literal(app) + '; '
        script += "if (!(Test-Path -LiteralPath $reader -PathType Leaf)) { throw 'PDF application not found. Check --acrobat-app.' }; "
    elif app:
        script += r"""$reader = @(
            "$env:ProgramFiles\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
            "${env:ProgramFiles(x86)}\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
            "${env:ProgramFiles(x86)}\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe"
        ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1; """
    else:
        script += '$reader = $null; '
    script += "if ($reader) { Start-Process -FilePath $reader -ArgumentList ('\"' + $target + '\"') } else { Start-Process -FilePath $target }"
    powershell(script)


def open_pdf(path, app):
    if sys.platform == 'darwin':
        result = subprocess.run(['open', '-a', app, str(path)], capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise ValueError(f'Could not open {app}. Check --acrobat-app. {result.stderr.strip()}')
    elif sys.platform == 'win32' or is_wsl():
        target = str(path)
        if is_wsl():
            target = subprocess.check_output(['wslpath', '-w', target], text=True).strip()
        open_windows(target, app)
    else:
        if not shutil.which('xdg-open'):
            raise ValueError('No desktop PDF opener is available. Use Browser preview.')
        subprocess.Popen(['xdg-open', str(path)])


def open_browser(url):
    if sys.platform == 'win32' or is_wsl():
        open_windows(url)
    else:
        webbrowser.open(url)
