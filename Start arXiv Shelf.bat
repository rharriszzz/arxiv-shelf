@echo off
setlocal
pushd "%~dp0"
rem A WSL checkout uses the Python already installed in that distribution.
echo %~dp0 | findstr /i /l /b /c:"\\wsl.localhost\" /c:"\\wsl$\" >nul
if not errorlevel 1 goto wsl
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    py -3.12 shelf.py --open-browser %*
    goto done
)
python -c "import sys; sys.exit(sys.version_info[:2] != (3, 12))" >nul 2>&1
if not errorlevel 1 (
    python shelf.py --open-browser %*
    goto done
)
echo Python 3.12 is required. Install Python or run this project from WSL.
goto done
:wsl
for /f "tokens=3 delims=\" %%D in ("%~dp0") do set "DISTRO=%%D"
wsl.exe -d "%DISTRO%" --cd "%~dp0." bash "./Start arXiv Shelf.sh" %*
:done
popd
pause
