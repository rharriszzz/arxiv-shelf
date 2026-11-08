@echo off
setlocal
pushd "%~dp0"
rem WSL checkouts use the Python 3.14 launcher inside that distribution.
set "SHELF_DIR=%~dp0"
if /i "%SHELF_DIR:~0,16%"=="\\wsl.localhost\" goto wsl
if /i "%SHELF_DIR:~0,7%"=="\\wsl$\" goto wsl
".venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info[:2] != (3, 14))" >nul 2>&1
if not errorlevel 1 goto venv
py -3.14 -c "import sys; sys.exit(sys.version_info[:2] != (3, 14))" >nul 2>&1
if not errorlevel 1 goto py
python -c "import sys; sys.exit(sys.version_info[:2] != (3, 14))" >nul 2>&1
if not errorlevel 1 goto python
echo Python 3.14 is required. Install Python 3.14 from https://www.python.org/downloads/ and create .venv as described in README.md.
set "SHELF_EXIT=1"
goto finish
:venv
".venv\Scripts\python.exe" shelf.py --open-browser %*
goto done
:py
py -3.14 shelf.py --open-browser %*
goto done
:python
python shelf.py --open-browser %*
goto done
:wsl
for /f "tokens=2 delims=\" %%D in ("%~dp0") do set "DISTRO=%%D"
rem WSL distribution names are passed without literal surrounding quotes.
wsl.exe -d %DISTRO% --cd "%~dp0." bash "./Start arXiv Shelf.sh" %*
:done
set "SHELF_EXIT=%errorlevel%"
:finish
popd
pause
exit /b %SHELF_EXIT%
