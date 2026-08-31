@echo off
REM Run tests without activating the venv; print output only on failure.
setlocal

REM If venv python doesn't exist, create venv and install requirements
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv || (echo ERROR: failed to create venv & exit /b 1)

  echo Installing Python dependencies (may take a moment)...
  .\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel >nul 2>&1
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt >pytest_out.txt 2>&1
  if %ERRORLEVEL% neq 0 (
    type pytest_out.txt
    del pytest_out.txt
    exit /b %ERRORLEVEL%
  )
  del pytest_out.txt
)

REM Run the specific test file, capture stdout/stderr
.\.venv\Scripts\python.exe -m pytest tests/test_api.py >pytest_out.txt 2>&1

REM If tests failed, print the captured output and return pytest's exit code
if %ERRORLEVEL% neq 0 (
  type pytest_out.txt
  del pytest_out.txt
  exit /b %ERRORLEVEL%
)

REM Success: delete capture file and exit quietly with code 0
del pytest_out.txt >nul 2>&1
exit /b 0
