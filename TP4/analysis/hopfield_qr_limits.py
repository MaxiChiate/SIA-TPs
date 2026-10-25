#!/usr/bin/env python3
"""Correlation and shift-sensitivity evidence for the QR limitations (HOP-07, D-11a/D-11b).

    .venv/bin/python analysis/hopfield_qr_limits.py        # or: make hopfield-qr-limits

Two of the four HOP-07 limitation facets are computed here (the other two - the Hamming 1-NN
lookup curve and the Reed-Solomon error-correction argument - come from analysis/hopfield_qr.py's
recall.csv and from text alone, D-10/D-11):

  (a) **Correlation as the root cause of Hebb's failure (D-11a).** The pixel-wise majority of the
      five QR (sign of the per-pixel sum) is the common attractor Hebb's dynamics tends to collapse
      to; it differs from every one of the five stored QR by a positive Hamming distance, written to
      majority.json.
  (b) **Shift sensitivity of pixel-wise recall (D-11b).** A 1 px and a 2 px zero-padded shift of one
      stored QR, evolved under the pinv network by a by-hand numpy async forward run (this script's
      own implementation, not a library and not hopfield.py's trace-replay - PROJECT.md: Hopfield by
      hand), with the measured query and recovered Hamming distances to the source recorded in
      shift.json for each shift. The research predicts pixel-wise recovery breaks (recovered Hamming
      > 0), but the script never asserts it: whatever the data shows is a finding, reported honestly
      in the deliverable (D-02 / PROJECT.md's rule of reporting the result as it comes out).

Like analysis/hopfield_qr.py, this script refuses to run unless hopfield_qr_select.rule_identity
accepts the protocol commit (D-01): the protocol text, the guard code, scripts/qr.py and the five
QR PNGs must be committed and unchanged. Its own network code (this file and analysis/hopfield.py,
LIMITS_CODE_FILES) is not covered by that pre-registration guard; its identity is recorded in
run.json and analysis/hopfield_qr_figures.py refuses to draw the two limitation figures if it
changed since this run (mirrors Phase 4's WR-02 and this plan's own run.json for hopfield-qr).

Writes under analysis/results/hopfield/qr_limits/ (not versioned) - a DIRECTORY SEPARATE from
analysis/results/hopfield/qr/, which make hopfield-qr rmtrees on every re-run: keeping the
limitation outputs outside that scope means a recall rerun can never delete the inputs this
script's own figures and the deliverable cite.
  - majority.json: the pixel-wise majority attractor, its overlap and Hamming distance to each of
    the five QR.
  - shift.json: for a 1 px and a 2 px shift of one fixed QR (SHIFT_SOURCE, chosen by index before
    looking at any result), the measured query_hamming and recovered_hamming to the source, plus
    the by-hand runner's sweep/flip count; also the sanity check that the SAME runner keeps an
    unshifted stored QR fixed under pinv's W (agreeing with the C core's stored.csv fixed == 1),
    so the forward run is trustworthy before trusting its shift-demo output.
  - run.json: code_identity over LIMITS_CODE_FILES (git HEAD, dirty flag, per-file sha256) - no
    neuron binary is hashed here, since this script never calls the C core.

numpy and the standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import hopfield  # noqa: E402
import hopfield_qr_select  # noqa: E402
import qr  # noqa: E402
import sweep  # noqa: E402

RESULTS_SUBDIR = Path("hopfield") / "qr_limits"
# The limitation generators' own code (this file and the numpy control it calls into for pinv/fields):
# not part of the D-01 pre-registration guard, but recorded here so hopfield_qr_figures.py can refuse to
# draw the limitation figures on a changed implementation (mirrors hopfield_qr.py's CODE_FILES/WR-02).
LIMITS_CODE_FILES = ("analysis/hopfield_qr_limits.py", "analysis/hopfield.py")

MAX_SWEEPS = 200  # generous ceiling for N = 1369; an implementation parameter, not part of the protocol
# Fixed by index before looking at any result (same convention as hopfield_qr.py's ENERGY_TRACE_SEED and
# hopfield_qr_figures.py's ENERGY_LEVELS): which QR is shifted (the first, "beverages") and the seed of
# the by-hand async runner's sweep permutations.
SHIFT_SOURCE = 0
SHIFT_SEED = 1
SHIFT_PIXELS = (1, 2)
# The vacated edge of a zero-padded shift is light = -1 (documented edge convention, HOP-07 flagged
# assumption): shifting down-and-right by k pixels leaves the top k rows and left k columns light.
EDGE_CONVENTION = "zero-padded shift (down and right); the vacated edge is light = -1"


# ---------- writing ----------

def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _relative(path, base: Path) -> str:
    path = Path(path).resolve()
    try:
        return path.relative_to(TP_DIR).as_posix()
    except ValueError:
        return str(path)


# ---------- (a) the common Hebb attractor: pixel-wise majority (D-11a, Pitfall 1) ----------

def majority_attractor(P) -> np.ndarray:
    """The pixel-wise majority vote across the p patterns: the sign of the per-pixel sum, ties (an even
    p) broken to +1 (dark, the display polarity's "on" value) - not reached with the five real QR (p is
    odd), but defined for any p so the synthetic test fixtures stay well-posed too."""
    P = np.asarray(P, dtype=np.int64)
    total = P.sum(axis=0)
    return np.where(total >= 0, 1, -1).astype(np.int64)


def majority_json(P) -> dict:
    """The majority attractor plus its overlap and Hamming distance to every one of the p patterns (the
    research's prediction, Pitfall 1: this is the common attractor Hebb's dynamics collapses to, and it
    differs from every stored QR - the root cause of Hebb's failure on correlated patterns, D-11a)."""
    P = np.asarray(P, dtype=np.int64)
    p, n = P.shape
    majority = majority_attractor(P)
    overlap_to_targets = [float(majority @ P[a]) / n for a in range(p)]
    hamming_to_targets = [int((majority != P[a]).sum()) for a in range(p)]
    return {
        "n_pixels": n,
        "n_patterns": p,
        "majority": majority.tolist(),
        "overlap_to_targets": overlap_to_targets,
        "hamming_to_targets": hamming_to_targets,
    }


# ---------- our own by-hand asynchronous forward run (D-11b; PROJECT.md: Hopfield by hand) ----------

def by_hand_async_run(W, s0, seed: int, max_sweeps: int = MAX_SWEEPS) -> tuple[np.ndarray, int, int]:
    """Our own numpy implementation of the asynchronous dynamics - NOT hopfield.py's _replay_async, which
    only replays a trace the C core already saved; this one actually drives the network from a query we
    hand it, exactly like neuron/models/hopfield_core.c's hopfield_async_run (field = W s, kept
    incrementally after every flip; a neuron takes sign(h) or keeps its state when h == 0; a fresh
    permutation of the n neurons drawn from `seed` at the start of every sweep; stop on a sweep with no
    flips or at max_sweeps). Returns (final_state int64, sweeps, total_flips)."""
    W = np.asarray(W, dtype=np.float64)
    s = np.asarray(s0, dtype=np.float64).copy()
    n = s.shape[0]
    rng = np.random.default_rng(seed)
    h = hopfield.fields(W, s)
    flips_total = 0
    sweeps = 0
    for sweep in range(1, max_sweeps + 1):
        order = rng.permutation(n)
        flips_this_sweep = 0
        for i in order:
            if h[i] > hopfield.ENERGY_TOLERANCE:
                new = 1.0
            elif h[i] < -hopfield.ENERGY_TOLERANCE:
                new = -1.0
            else:
                new = s[i]
            if new != s[i]:
                delta = new - s[i]
                s[i] = new
                h += W[:, i] * delta  # W is symmetric for both hebb and pinv, so column i == row i
                flips_total += 1
                flips_this_sweep += 1
        sweeps = sweep
        if flips_this_sweep == 0:
            break
    return s.astype(np.int64), sweeps, flips_total


def _sanity_check_unshifted_fixed(P, W, source: int = SHIFT_SOURCE, seed: int = SHIFT_SEED) -> dict:
    """Runs by_hand_async_run on an UNSHIFTED stored QR: it must stay fixed (zero flips), agreeing with
    the C core's stored.csv fixed == 1 for pinv (D-07's exact-fixed-point property). This is what makes
    the shift demo below trustworthy - if the runner flipped an unshifted stored pattern, its shift
    results would not mean what they claim to mean."""
    P = np.asarray(P, dtype=np.int64)
    final, sweeps, flips = by_hand_async_run(W, P[source], seed=seed)
    if flips != 0 or not np.array_equal(final, P[source]):
        raise SystemExit(
            "hopfield_qr_limits: the by-hand async runner did not keep an UNSHIFTED stored QR fixed under "
            "pinv's W (disagrees with the C core's stored.csv fixed == 1); the runner is not trustworthy, "
            "refusing to report a shift result from it"
        )
    return {"sweeps": sweeps, "flips": flips}


# ---------- (b) the shift demo (D-11b, Pitfall 15) ----------

def shift_pattern(pattern_2d: np.ndarray, shift_px: int) -> np.ndarray:
    """Zero-padded shift of a (side, side) pm-one image down and to the right by shift_px pixels
    (EDGE_CONVENTION): the vacated top shift_px rows and left shift_px columns are set to light (-1)."""
    side = pattern_2d.shape[0]
    shifted = np.full_like(pattern_2d, -1)
    if shift_px < side:
        shifted[shift_px:, shift_px:] = pattern_2d[: side - shift_px, : side - shift_px]
    return shifted


def shift_json(P, source: int = SHIFT_SOURCE, pixels=SHIFT_PIXELS, seed: int = SHIFT_SEED,
               max_sweeps: int = MAX_SWEEPS) -> dict:
    """For each magnitude in `pixels`, shifts the source QR, runs it through by_hand_async_run under the
    pinv W and records the MEASURED Hamming distance of the shifted query to the source (query_hamming)
    and of the recovered state to the source (recovered_hamming) - never asserted to be positive; the
    research predicts the shift breaks pixel-wise recovery, but this function only measures (D-02 /
    PROJECT.md's honest-reporting rule, the same principle as the Hebb/pinv verdict in verdict.json). Also
    runs and records the sanity check that the SAME runner keeps an unshifted stored QR fixed (D-07)."""
    P = np.asarray(P, dtype=np.int64)
    p, n = P.shape
    side = int(round(n ** 0.5))
    if side * side != n:
        raise SystemExit(f"hopfield_qr_limits: n_pixels={n} is not a perfect square, cannot reshape to a grid")
    W = hopfield.pinv(P)
    sanity = _sanity_check_unshifted_fixed(P, W, source=source, seed=seed)

    base = P[source].reshape(side, side)
    shifts = []
    for shift_px in pixels:
        shifted_2d = shift_pattern(base, shift_px)
        shifted = shifted_2d.reshape(-1).astype(np.int64)
        query_hamming = int((shifted != P[source]).sum())
        recovered, sweeps, flips = by_hand_async_run(W, shifted, seed=seed, max_sweeps=max_sweeps)
        recovered_hamming = int((recovered != P[source]).sum())
        shifts.append({
            "shift": int(shift_px),
            "query_hamming": query_hamming,
            "recovered_hamming": recovered_hamming,
            "sweeps": sweeps,
            "flips": flips,
        })
    return {
        "source": source,
        "n_pixels": n,
        "edge_convention": EDGE_CONVENTION,
        "seed": seed,
        "sanity_unshifted_fixed": sanity,
        "shifts": shifts,
    }


# ---------- identity of the limitation generators' own code (mirrors hopfield_qr.py's WR-02) ----------

def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_file_hashes(repo_dir=TP_DIR) -> dict:
    repo_dir = Path(repo_dir)
    try:
        return {name: _sha256_file(repo_dir / name) for name in LIMITS_CODE_FILES}
    except OSError as error:
        raise SystemExit(f"cannot hash the limitation generators' code: {error}") from None


def _git_text(args: list[str], repo_dir: Path):
    try:
        done = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True)
    except OSError:
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def code_identity(repo_dir=TP_DIR) -> dict:
    """git HEAD, whether LIMITS_CODE_FILES differs from HEAD or is untracked (dirty), and the sha256 of
    each file - no neuron binary is hashed here, since this script never calls the C core."""
    repo_dir = Path(repo_dir)
    status = _git_text(["status", "--porcelain", "--untracked-files=all", "--", *LIMITS_CODE_FILES], repo_dir)
    return {
        "head": _git_text(["rev-parse", "HEAD"], repo_dir),
        "dirty": None if status is None else bool(status),
        "files": code_file_hashes(repo_dir),
    }


def changed_code_files(recorded: dict, repo_dir=TP_DIR) -> list[str]:
    """The LIMITS_CODE_FILES whose current sha256 is not the one in a recorded code_identity (all of them
    when nothing was recorded)."""
    files = recorded.get("files") if isinstance(recorded, dict) else None
    if not isinstance(files, dict):
        return list(LIMITS_CODE_FILES)
    current = code_file_hashes(repo_dir)
    return [name for name in LIMITS_CODE_FILES if files.get(name) != current[name]]


# ---------- the run ----------

def run(results_dir=sweep.RESULTS_DIR, repo_dir=TP_DIR, check_rule: bool = True) -> Path:
    results_dir = Path(results_dir)
    if check_rule:
        hopfield_qr_select.rule_identity(repo_dir)  # refuses on a changed protocol (D-01)

    patterns = hopfield.load_patterns(qr.PREPARED_CSV)

    out = results_dir / RESULTS_SUBDIR
    if out.exists():  # only THIS directory; analysis/results/hopfield/qr/ (make hopfield-qr) is never touched
        shutil.rmtree(out)
    out.mkdir(parents=True)
    try:
        _write_json(out / "majority.json", majority_json(patterns))
        _write_json(out / "shift.json", shift_json(patterns))
        _write_json(out / "run.json", {"code_identity": code_identity(repo_dir)})
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise
    print(f"hopfield-qr-limits -> {_relative(out, results_dir)}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
