@echo off
setlocal
set "GIT_DESK_PROJECT_DIR=%~dp0"
set "GIT_DESK_BUILD_DIR=%GIT_DESK_PROJECT_DIR%.build\windows"
set "GIT_DESK_OUTPUT_DIR=%GIT_DESK_PROJECT_DIR%dist\windows-x86_64"
py -3 -c "import sys, tkinter; assert sys.platform == 'win32' and sys.maxsize > 2**32, 'Use 64-bit Windows Python'"
if errorlevel 1 goto :failed
py -3 -m venv "%GIT_DESK_BUILD_DIR%\venv"
if errorlevel 1 goto :failed
set "GIT_DESK_PYTHON=%GIT_DESK_BUILD_DIR%\venv\Scripts\python.exe"
"%GIT_DESK_PYTHON%" -m pip install --disable-pip-version-check PyInstaller==6.22.3
if errorlevel 1 goto :failed
set "PYINSTALLER_CONFIG_DIR=%GIT_DESK_BUILD_DIR%\cache"
rem Keep piped stdout for Git askpass, while hiding our console on double-click.
"%GIT_DESK_PYTHON%" -m PyInstaller --noconfirm --clean --onefile --console --hide-console hide-early --name GitDesk --distpath "%GIT_DESK_OUTPUT_DIR%" --workpath "%GIT_DESK_BUILD_DIR%\work" --specpath "%GIT_DESK_BUILD_DIR%" "%GIT_DESK_PROJECT_DIR%git_gui.py"
if errorlevel 1 goto :failed
"%GIT_DESK_PYTHON%" "%GIT_DESK_PROJECT_DIR%packaging\windows\package_windows.py"
if errorlevel 1 goto :failed
echo Ready: %GIT_DESK_OUTPUT_DIR%\GitDesk.exe
exit /b 0
:failed
echo Build failed. Install 64-bit Python with Tcl/Tk and the py launcher enabled.
exit /b 1
