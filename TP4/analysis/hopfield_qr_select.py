#!/usr/bin/env python3
"""The pre-registered protocol of deliverables/05-hopfield-qr.md section 3 as code (HOP-05, D-01..D-11).

Unlike Phase 4 (where the guard protected a *selection* of letters), here the 5 QR are fixed and
given: there is no selection. What is pre-registered and guarded with a sha256 digest before the
network ever runs on the QR is the experiment protocol itself: the literal hypothesis, the success
criterion, the noise grid, the number of trials and seeds, the two numeric verdict thresholds (D-02),
and the Hamming tie-break rule. The protocol text, this module, scripts/qr.py and the five QR PNGs
are committed together by the user before any network run (D-01: once it runs, none of them changes).

The deliverable (RULE_FILE) is checked by marker digest only, NOT porcelain-clean: its result
sections (outside the markers) are written later by Plans 03-05 without tripping the guard, while
any change to the marker text itself changes the digest and refuses. rule_guard (porcelain-clean)
covers exactly the guard code, scripts/qr.py and the five PNGs.

This module never computes a network quantity (Hebb or pinv weights, fields, energies, fixed points,
recall rates); `report` prints the frozen design constants and the five PNG sha256 only.

    .venv/bin/python analysis/hopfield_qr_select.py report
    .venv/bin/python analysis/hopfield_qr_select.py identity
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import som_select  # noqa: E402

RULE_FILE = "deliverables/05-hopfield-qr.md"
SELECT_FILE = "analysis/hopfield_qr_select.py"  # this module: guarded and hashed together with the rule text (D-01)
QR_FILE = "scripts/qr.py"
# Fixed order (matches scripts/qr.py SOURCES): what the guard hashes and what the drivers index by
# subset [0, 1, 2, 3, 4].
PNG_FILES = (
    "datos/hopfield/beverages_menu_qr.png",
    "datos/hopfield/dessert_menu_qr.png",
    "datos/hopfield/food_menu_qr.png",
    "datos/hopfield/specials_menu_qr.png",
    "datos/hopfield/wine_menu_qr.png",
)
HEX40 = re.compile(r"[0-9a-f]{40}")

# ----------------------------------------------------------------------------------------------
# Design constants: the numbers written in the protocol (D-01, D-02, D-03, D-05, D-08)
# ----------------------------------------------------------------------------------------------

HYPOTHESIS = "Hebb no estabiliza los 5 QR correlacionados; la pseudo-inversa es el remedio"
NOISE_LEVELS = tuple(round(k * 0.05, 2) for k in range(11))  # 11 levels, 0 to 0.5 step 0.05 (D-05)
TRIALS = 30  # trials per noise level (D-05)
SEEDS = tuple(range(1, 11))  # seeds 1..10 (D-05)
UPDATES = ("async", "sync")  # async is the reference, sync the labelled comparison
SUBSET = (0, 1, 2, 3, 4)  # the five QR, scripts/qr.py SOURCES order
SUCCESS = "exact 1369-pixel match (|m| = 1 with the target); continuous mean final |m| also reported (D-03)"

# Numeric verdict thresholds (D-02), fixed before any run so the verdict is never adjusted after
# seeing the curve. Both are recovery rates at noise level 0 (the zero-noise stability test).
HEBB_FAIL_RECALL_AT_ZERO = 1.0  # Hebb FAILS if exact recovery at noise 0 is strictly below this
PINV_WORK_RECALL_AT_ZERO = 1.0  # pinv WORKS if exact recovery at noise 0 equals this (i.e. == 100%)

HAMMING_TIE_BREAK = "lowest index"  # 1-NN Hamming baseline tie-break (D-08)


# ----------------------------------------------------------------------------------------------
# Report: frozen protocol facts only (no network quantity)
# ----------------------------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def report(repo_dir: Path = TP_DIR) -> str:
    """Text lines: the literal hypothesis, the noise grid, trials, seeds, updates, the success
    criterion, both verdict thresholds worded legibly, the Hamming tie-break and the five PNG
    sha256. Bitmap/text facts only: no network quantity is computed here."""
    repo_dir = Path(repo_dir)
    lines = [f"hypothesis: {HYPOTHESIS}", ""]
    lines.append("noise grid (11 levels, 0 to 0.5 step 0.05): " + ", ".join(f"{level:.2f}" for level in NOISE_LEVELS))
    lines.append(f"trials per level: {TRIALS}")
    lines.append(f"seeds: {len(SEEDS)} ({SEEDS[0]}..{SEEDS[-1]})")
    lines.append("updates: " + ", ".join(UPDATES))
    lines.append(f"subset: {list(SUBSET)}")
    lines.append(f"success: {SUCCESS}")
    lines.append(f"Hebb fails: exact recovery at noise 0 < {HEBB_FAIL_RECALL_AT_ZERO * 100:.0f}%")
    lines.append(f"pinv works: exact recovery at noise 0 == {PINV_WORK_RECALL_AT_ZERO * 100:.0f}%")
    lines.append(f"Hamming baseline: 1-NN, ties broken by {HAMMING_TIE_BREAK}")
    lines.append("")
    lines.append("PNG sha256 (SOURCES order):")
    for path in PNG_FILES:
        lines.append(f"  {path}: {_sha256_file(repo_dir / path)}")
    return "\n".join(lines).rstrip("\n") + "\n"


# ----------------------------------------------------------------------------------------------
# "Committed before looking": the guard (D-01)
# ----------------------------------------------------------------------------------------------


def _git_stdout(args: list[str], repo_dir: Path) -> str:
    """Argument list, no shell, run in repo_dir (T-05-05)."""
    return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True,
                          check=True).stdout.strip()


def _added_commit(path: str, repo_dir: Path) -> str:
    """The one commit that added `path` (git log --diff-filter=A). Never added, or added more than
    once, is refused: the rule commit must be unambiguous."""
    out = _git_stdout(["log", "--diff-filter=A", "--format=%H", "--", path], repo_dir)
    if not HEX40.fullmatch(out):
        raise SystemExit(f"{path}: expected exactly one commit that added it, git reports {out!r} (D-01)")
    return out


def _is_ancestor(older: str, newer: str, repo_dir: Path) -> bool:
    result = subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=repo_dir,
                            capture_output=True, text=True)
    return result.returncode == 0


def rule_identity(repo_dir=TP_DIR) -> dict:
    """Refuse unless the guard code, scripts/qr.py and the five PNGs are committed, unchanged and
    porcelain-clean, the protocol text and this module were added in the same commit, scripts/qr.py
    and the five PNGs are in that commit or an ancestor, nothing guarded changed after it, and the
    deliverable's current marker digest equals the one at the rule commit. The deliverable
    (RULE_FILE) is deliberately NOT in the porcelain-clean guarded set: its result sections (outside
    the markers) may be edited uncommitted without tripping this guard; only its marker digest is
    checked. Returns the identity to record. Every refusal is a SystemExit ending in "(D-01)"."""
    repo_dir = Path(repo_dir).resolve()
    guarded = [SELECT_FILE, QR_FILE, *PNG_FILES]
    try:
        som_select.rule_guard(guarded, repo_dir)
    except SystemExit as error:
        raise SystemExit(f"{error}; Phase 5: the guard code, scripts/qr.py and the five QR PNGs must be "
                         "committed and unchanged (D-01)") from None

    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", RULE_FILE], cwd=repo_dir,
                             capture_output=True, text=True)
    if tracked.returncode != 0:
        raise SystemExit(f"{RULE_FILE}: the protocol text must be committed (D-01)")

    rule_commit = _added_commit(RULE_FILE, repo_dir)
    select_added = _added_commit(SELECT_FILE, repo_dir)
    if select_added != rule_commit:
        raise SystemExit(f"{SELECT_FILE} was added in commit {select_added}, not in the rule commit "
                         f"{rule_commit} that added {RULE_FILE} (D-01)")
    for path in (QR_FILE, *PNG_FILES):
        added = _added_commit(path, repo_dir)
        if not _is_ancestor(added, rule_commit, repo_dir):
            raise SystemExit(f"{path} was added in commit {added}, which is not the rule commit {rule_commit} "
                             "or an ancestor of it (D-01)")
    for path in guarded:
        last = _git_stdout(["log", "-1", "--format=%H", "--", path], repo_dir)
        if not HEX40.fullmatch(last) or not _is_ancestor(last, rule_commit, repo_dir):
            raise SystemExit(f"{path} changed in commit {last} after the rule commit {rule_commit} (D-01)")

    with tempfile.TemporaryDirectory() as folder:
        committed = Path(folder) / "rule.md"
        text = subprocess.run(["git", "show", f"{rule_commit}:./{RULE_FILE}"], cwd=repo_dir,
                              capture_output=True, check=True).stdout
        committed.write_bytes(text)
        committed_digest = som_select.rule_digest(committed)
    current_digest = som_select.rule_digest(repo_dir / RULE_FILE)
    if committed_digest != current_digest:
        raise SystemExit(f"the text between the markers of {RULE_FILE} differs from the one at the rule commit "
                         f"{rule_commit} (D-01)")
    return {
        "rule_commit": rule_commit,
        "rule_sha256": current_digest,
        "select_sha256": _sha256_file(repo_dir / SELECT_FILE),
        "qr_sha256": _sha256_file(repo_dir / QR_FILE),
        "png_sha256": {path: _sha256_file(repo_dir / path) for path in PNG_FILES},
    }


def require_same_rule(selection_path, repo_dir=TP_DIR) -> None:
    """Later steps run only on the protocol, guard code, scripts/qr.py and the five PNGs that the
    driver recorded (D-01)."""
    selection_path = Path(selection_path)
    repo_dir = Path(repo_dir)
    try:
        recorded = json.loads(selection_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"{selection_path}: cannot read the recorded identity (run the QR driver first): "
                         f"{error} (D-01)")
    current = {
        "rule_sha256": som_select.rule_digest(repo_dir / RULE_FILE),
        "select_sha256": _sha256_file(repo_dir / SELECT_FILE),
        "qr_sha256": _sha256_file(repo_dir / QR_FILE),
        "png_sha256": {path: _sha256_file(repo_dir / path) for path in PNG_FILES},
    }
    names = {"rule_sha256": "the protocol text", "select_sha256": SELECT_FILE,
             "qr_sha256": QR_FILE, "png_sha256": "the five QR PNGs"}
    for key, value in current.items():
        if recorded.get(key) != value:
            raise SystemExit(f"{names[key]} changed since the identity was recorded: "
                             f"{recorded.get(key)} != {value} (D-01)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("report", help="frozen protocol facts: hypothesis, noise grid, trials, seeds, "
                                        "verdict thresholds, PNG sha256 (no network quantity)")
    commands.add_parser("identity", help="print the rule identity, refusing unless the rule commit exists")
    args = parser.parse_args(argv)
    if args.command == "report":
        sys.stdout.write(report())
    else:
        print(json.dumps(rule_identity(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
