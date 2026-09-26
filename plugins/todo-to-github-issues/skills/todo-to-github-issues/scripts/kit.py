"""The sdd kit this skill leans on, and the checks that run before anything else.

The TODO.md format belongs to the kit (`templates/todo.md`, one variant per OUTPUT_LANG), and so
does its shape sensor (`tests/check-todo.sh`). This skill carries NO copy of either: it finds the
kit on the machine and calls it. So the kit is a hard requirement, checked on every run, and its
absence is reported with the command that installs it — never papered over by a local guess.

Keep this module importable by Python 3.7: the version check lives here, and a module that fails
to COMPILE on the old interpreter would die before it could say why (no walrus, no match).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

OPEN_MARKER = "<!-- sdd:open -->"
DECIDED_MARKER = "<!-- sdd:decided -->"
KIT_REPO = "https://github.com/j0ruge/sdd_agents"
KIT_DEFAULT = os.path.join("~", "repos", "sdd_agents")
MIN_PY = (3, 8)


def find_kit(env=None, which=shutil.which, home=None):
    """(kit root or None, how it was looked for). SDD_HOME wins and is never second-guessed: a
    wrong SDD_HOME is an error to report, not a hint to try somewhere else — silently using a
    different kit than the one the user named would measure the file against the wrong sensor."""
    env = os.environ if env is None else env
    home = os.path.expanduser("~") if home is None else home
    if env.get("SDD_HOME"):
        return (env["SDD_HOME"] if os.path.isdir(env["SDD_HOME"]) else None), "SDD_HOME=" + env["SDD_HOME"]
    sdd = which("sdd")
    if sdd:
        root = os.path.dirname(os.path.dirname(os.path.realpath(sdd)))
        if os.path.isfile(os.path.join(root, "tests", "check-todo.sh")):
            return root, "the `sdd` on PATH (" + sdd + ")"
    default = os.path.join(home, "repos", "sdd_agents")
    return (default if os.path.isdir(default) else None), "the default " + KIT_DEFAULT


def sensor_path(root):
    return os.path.join(root, "tests", "check-todo.sh")


def preflight(need_gh, need_kit):
    """Every requirement of the mode that is about to run, checked at once; all failures are
    reported together (fixing one to discover the next costs a round per missing tool), then
    exit 3. Returns the kit root when the mode needs it, else None."""
    fails = []
    if sys.version_info < MIN_PY:
        have = "{}.{}".format(*sys.version_info[:2])
        fails.append(f"Python {MIN_PY[0]}.{MIN_PY[1]}+ is required, this is {have} — run the script with a newer python3")
    for tool, hint in (("git", "install git (e.g. `sudo apt install git`)"),
                       ("bash", "install bash — the kit's sensor is a bash script")):
        if not shutil.which(tool):
            fails.append(f"`{tool}` not found on PATH — {hint}")
    if need_gh:
        if not shutil.which("gh"):
            fails.append("`gh` not found on PATH — install the GitHub CLI: https://cli.github.com")
        elif subprocess.run(["gh", "auth", "status", "--hostname", "github.com"],
                            capture_output=True, check=False).returncode != 0:
            fails.append("`gh` is not authenticated — run `gh auth login`")
    root = None
    if need_kit:
        root, how = find_kit()
        if root is None:
            fails.append(
                f"sdd kit not found (looked at {how}). This skill carries no copy of the TODO.md format\n"
                "      or of its shape sensor — it calls the kit's. Install it:\n"
                f"        git clone {KIT_REPO} ~/repos/sdd_agents\n"
                "      or point at an existing clone: export SDD_HOME=<path to the clone>")
        elif not os.access(sensor_path(root), os.R_OK):
            fails.append(f"the kit at {root} has no readable tests/check-todo.sh — is SDD_HOME the kit's root?")
        elif shutil.which("bash"):
            # Capability, not presence: a kit from before the two-section skeleton has the sensor
            # but not `--count`, and answers the probe with 96 (unknown option) instead of 93.
            rc = subprocess.run(["bash", sensor_path(root), "--count", os.path.join(root, ".no-such-file")],
                                capture_output=True, check=False).returncode
            if rc != 93:
                fails.append(f"the kit at {root} predates the TODO.md skeleton (its sensor has no --count) —\n"
                             f"      update it: git -C {root} pull")
    if fails:
        print("FAIL  requirements missing — nothing was run:", file=sys.stderr)
        for f in fails:
            print("  - " + f, file=sys.stderr)
        sys.exit(3)
    return root


def run_sensor(root, *args):
    """(rc, combined output) of the kit's shape sensor. Always via `bash`, like the kit's own
    suite, so a checkout without the exec bit does not become a false "sensor crashed"."""
    r = subprocess.run(["bash", sensor_path(root), *args], capture_output=True, text=True, check=False)
    return r.returncode, (r.stdout + r.stderr)


def open_marker_line(lines):
    """0-based index of the open marker sitting directly under a `## ` heading, or None. The
    heading text is never read: it is content in OUTPUT_LANG. Only the marker is the contract."""
    for i, line in enumerate(lines):
        if line.rstrip() == OPEN_MARKER and i > 0 and lines[i - 1].startswith("## "):
            return i
    return None
