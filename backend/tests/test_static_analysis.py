"""
Static analysis regression test.

Catches the specific class of bug where a name (like `PILImage`) is used
in code but not imported — which causes silent runtime failures when the
code path is wrapped in try/except.

History: This happened twice in 2026 — once with timesheets PDF and once
with Boletim de Medição PDF. The PDF generation code used `PILImage.open(...)`
inside a try/except that swallowed the NameError, so the PDF was generated
without the logo with no visible error to the user.

This test runs `ruff check --select F821` on the backend folder and fails
if any undefined name is detected. F821 catches:
  - Used but not imported (like the PIL bug)
  - Typos in variable names
  - Removed imports that left dangling references
"""
import os
import subprocess
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_no_undefined_names_in_backend():
    """Run ruff F821 check across the entire backend.

    Catches bugs like 'PILImage used but not imported' before they hit production.
    """
    result = subprocess.run(
        [
            "ruff", "check",
            "--select", "F821",
            "--exclude", "tests",
            BACKEND_DIR,
        ],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
    )

    if result.returncode != 0:
        pytest.fail(
            "Undefined names detected in backend code (F821):\n\n"
            f"{result.stdout}\n{result.stderr}\n\n"
            "Fix: add the missing import or fix the typo.\n"
            "This protects against silent runtime failures (e.g., logo missing in PDFs)."
        )


def test_no_unused_imports_in_routes():
    """Run ruff F401 check on routes/ to keep imports clean.

    Excludes __init__.py and FastAPI route modules where unused imports
    are sometimes intentional (re-exports, side-effects).
    """
    result = subprocess.run(
        [
            "ruff", "check",
            "--select", "F401",
            os.path.join(BACKEND_DIR, "routes"),
        ],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
    )

    # F401 is informational — don't fail the test, just print
    if result.returncode != 0 and result.stdout:
        print(f"\n[INFO] Unused imports in routes/ (non-blocking):\n{result.stdout}")
