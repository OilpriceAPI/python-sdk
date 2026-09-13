"""Guard against committing a developer virtualenv to version control.

Virtualenv launchers, activation scripts and ``pyvenv.cfg`` are machine-specific
build artifacts, not SDK source. They bloat clones, leak absolute paths from a
developer's machine, and can be mistaken for runnable interpreters. This test
asserts none of them are tracked by git.

See https://github.com/OilpriceAPI/python-sdk/issues/106.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

# Files that only ever exist inside a virtual environment.
VENV_MARKER_NAMES = {
    "pyvenv.cfg",
    "activate",
    "activate.csh",
    "activate.fish",
    "Activate.ps1",
}

# Directory names that, at the repository root, denote a virtual environment.
VENV_DIR_NAMES = {
    "build-env",
    "venv",
    ".venv",
    "env",
    "ENV",
    "virtualenv",
}


def tracked_files() -> list[str]:
    """Return every path tracked by git, or skip if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover
        pytest.skip(f"git is not available for this checkout: {exc}")
    return [p for p in result.stdout.decode("utf-8").split("\0") if p]


def test_no_virtualenv_directory_is_tracked() -> None:
    """No file under a virtualenv directory may be tracked."""
    files = tracked_files()
    assert files, "expected git ls-files to report tracked files"

    offenders = sorted(
        path
        for path in files
        if path.split("/", 1)[0] in VENV_DIR_NAMES
    )
    assert not offenders, (
        f"{len(offenders)} virtualenv file(s) are tracked in git. "
        "Virtual environments are machine-specific build artifacts and must not "
        "be committed. Remove them with `git rm -r --cached <dir>` and confirm "
        f".gitignore covers them. Offenders: {offenders[:10]}"
    )


def test_no_virtualenv_marker_files_are_tracked() -> None:
    """No pyvenv.cfg or shell activation script may be tracked anywhere."""
    offenders = sorted(
        path
        for path in tracked_files()
        if path.rsplit("/", 1)[-1] in VENV_MARKER_NAMES
    )
    assert not offenders, (
        "virtualenv marker files are tracked in git and must be removed: "
        f"{offenders}"
    )


def test_gitignore_excludes_the_build_env_directory() -> None:
    """A recreated developer environment must not be re-added by `git add`."""
    probe = "build-env/bin/pip"
    result = subprocess.run(
        ["git", "check-ignore", "-v", probe],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{probe!r} is not ignored by .gitignore, so recreating the developer "
        "environment would re-add it to version control. "
        f"git check-ignore said: {result.stdout or result.stderr!r}"
    )
