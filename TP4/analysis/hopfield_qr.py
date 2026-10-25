#!/usr/bin/env python3
"""Guarded driver of the Hopfield-on-QR experiments (HOP-04, HOP-05, D-01..D-11).

    .venv/bin/python analysis/hopfield_qr.py            # or: make hopfield-qr

Runs the protocol pre-registered in deliverables/05-hopfield-qr.md section 3, with every number
taken from analysis/hopfield_qr_select.py. Unlike Phase 4 (where the guard protected a *selection*
of letters), the five QR are fixed and given: what is guarded here is the experiment protocol
itself (D-01). The driver refuses to run unless the protocol commit is in place (the protocol
text, the guard code, scripts/qr.py and the five QR PNGs committed and unchanged) and the prepared
qr_pm1.csv was written from those same committed PNGs. The series are built in code from the
frozen constants, so no series file, flag or edit can change the design after the commit. Every
run of the neuron binary goes through analysis/hopfield.check_recall before anything is
aggregated; a failed run or a disagreement stops the driver and removes the output.

This plan builds ONLY the Hebb recall series (rule="hebb"), over both updates (async reference,
sync labelled comparison) and the ten frozen seeds, on the eleven-level 0..0.5 noise grid. Plan 04
adds the pseudo-inverse series on top of the same frozen grid; the energy-trace capture below is
written generically over "rule" so it needs no change when that series is added.

Writes under analysis/results/hopfield/qr/ (not versioned):
  - overlaps.json, qr_facts.json: input facts over the patterns alone (HOP-04, D-11a), independent
    of any network run.
  - recall.csv: pooled over the five QR and the ten seeds, per (update, noise) cell: recall_rate,
    the class-rate breakdown, mean_sweeps, mean_flips, the continuous mean |final overlap| with the
    pattern that was perturbed (D-03) and the mean final energy (D-09).
  - energy_trace.csv: the per-step energy of the traced trial (trace_trials=1) of the async
    reference update, one row per (rule, source, noise, step) - HOP-05's "energia por paso", not
    only the per-level final energy.
  - protocol.json: echo of the frozen design constants (no network quantity).
  - verdict.json: the D-02 threshold applied to the MEASURED Hebb async noise-0 recovery rate -
    never the predicted outcome, whatever the data shows (PROJECT.md: report the result as it comes
    out). The pinv fields are left null; Plan 04 fills them.
  - run.json: the rule identity, code_identity (git HEAD, dirty flag, sha256 of the network code and
    of the binary - not pinned by the pre-registration, but hopfield_qr_figures.py refuses to draw
    if these changed since the run, mirroring Phase 4's WR-02), the sweeps map and the per-series
    run counts.

numpy and the standard library only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import NamedTuple

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import hopfield  # noqa: E402
import hopfield_qr_select  # noqa: E402
import qr  # noqa: E402
import sweep  # noqa: E402

RESULTS_SUBDIR = Path("hopfield") / "qr"
RECALL_COLUMNS = ["rule", "update", "noise", "flipped", "n_trials", "recall_rate", "recall_sd_seeds",
                  "wrong_stored_rate", "inverse_rate", "mixture_rate", "other_rate", "cycle_rate", "mean_sweeps",
                  "mean_flips", "mean_final_overlap", "mean_final_energy"]
ENERGY_TRACE_COLUMNS = ["rule", "update", "source", "noise", "step", "energy"]
# The network code is not covered by the pre-registration guard (D-01 guards the protocol, scripts/qr.py and the
# five PNGs, not the Hopfield core). Its identity is recorded in run.json (mirrors Phase 4's WR-02) and
# hopfield_qr_figures.py refuses to draw if one of these files changed since the run. Paths relative to TP4 root.
# Deliberately excludes analysis/hopfield_qr_limits.py (Plan 05): that file does not exist at this plan's wave, and
# this recall run.json must not hash a missing file.
CODE_FILES = ("neuron/models/hopfield.c", "neuron/models/hopfield_core.c", "neuron/models/hopfield_core.h",
              "neuron/io/config.c", "analysis/hopfield.py", "analysis/hopfield_qr.py")

# Implementation parameters: not part of the frozen protocol (D-01..D-11 freeze the noise grid, trial/seed counts,
# updates, subset and verdict thresholds only). A generous sweep ceiling for N = 1369 so the dynamics are never cut
# artificially short, and the trace width HOP-05 needs ("energia por paso" of one picked trial per cell).
MAX_SWEEPS = 200
TRACE_TRIALS = 1
# energy_trace.csv has no seed column (rule, update, source, noise, step, energy): one seed's traced trial per
# (source, noise) cell, fixed by index to the first frozen seed - never chosen after looking at a curve - so the
# per-step sequence of a cell is never two different seeds' runs interleaved under the same key.
ENERGY_TRACE_SEED = hopfield_qr_select.SEEDS[0]


@dataclass(frozen=True)
class Design:
    """Every number of the experiment. default_design() fills it from analysis/hopfield_qr_select.py."""

    patterns_path: Path
    meta_path: Path
    max_sweeps: int
    noise_levels: tuple
    trials: int
    seeds: tuple
    updates: tuple
    subset: tuple
    trace_trials: int


def default_design() -> Design:
    """The design written in the protocol: the frozen constants of hopfield_qr_select, nothing else."""
    select = hopfield_qr_select
    return Design(
        patterns_path=qr.PREPARED_CSV,
        meta_path=qr.PREPARED_CSV.with_suffix(".meta.json"),
        max_sweeps=MAX_SWEEPS,
        noise_levels=tuple(select.NOISE_LEVELS),
        trials=select.TRIALS,
        seeds=tuple(select.SEEDS),
        updates=tuple(select.UPDATES),
        subset=tuple(select.SUBSET),
        trace_trials=TRACE_TRIALS,
    )


class Ran(NamedTuple):
    """One run of a series: its task, the run directory it was moved to and what check_recall recomputed in it."""

    task: sweep.Task
    dir: Path
    checked: dict


# ---------- writing ----------

def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([repr(row[c]) if isinstance(row[c], float) else row[c] for c in columns])


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _relative(path, results_dir: Path) -> str:
    """Relative to TP4 when the path lives there (the real run); otherwise relative to the results directory, so a
    run in a temporary directory writes no machine-specific path."""
    path = Path(path).resolve()
    try:
        return path.relative_to(TP_DIR).as_posix()
    except ValueError:
        return Path(os.path.relpath(path, Path(results_dir).resolve())).as_posix()


def _design_json(design: Design) -> dict:
    data = asdict(design)
    for key in ("patterns_path", "meta_path"):
        data[key] = _relative(data[key], TP_DIR)
    return data


def _dict_rows(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


# ---------- input facts over the patterns alone (HOP-04, D-11a) ----------

def overlap_matrix(P) -> np.ndarray:
    """The p x p integer dot-product matrix P P^T."""
    P = np.asarray(P, dtype=np.int64)
    return P @ P.T


def identical_fraction(P) -> float:
    """Fraction of the N pixels that hold the same value in every one of the p patterns."""
    P = np.asarray(P, dtype=np.int64)
    return float(np.all(P == P[0], axis=0).mean())


def min_pair_hamming(P) -> int:
    """Minimum Hamming distance over every pair of the p patterns."""
    P = np.asarray(P, dtype=np.int64)
    p = P.shape[0]
    return min(int((P[a] != P[b]).sum()) for a in range(p) for b in range(a + 1, p))


def overlaps_json(patterns) -> dict:
    """The 5x5 integer dot matrix, its /N overlaps and the max/mean |overlap| over the distinct pairs (HOP-04)."""
    P = np.asarray(patterns, dtype=np.int64)
    p, n = P.shape
    dots = overlap_matrix(P)
    overlaps = dots / n
    pairs = [abs(float(overlaps[a, b])) for a in range(p) for b in range(a + 1, p)]
    return {
        "n_pixels": n, "dots": dots.tolist(), "overlaps": overlaps.tolist(),
        "max_abs_overlap": max(pairs) if pairs else 0.0,
        "mean_abs_overlap": sum(pairs) / len(pairs) if pairs else 0.0,
    }


def qr_facts_json(patterns) -> dict:
    """The fraction of pixels identical in every pattern and the minimum pairwise Hamming distance (D-11a), the
    root cause of Hebb's expected failure on these correlated patterns."""
    P = np.asarray(patterns, dtype=np.int64)
    p, n = P.shape
    pair_hamming = [int((P[a] != P[b]).sum()) for a in range(p) for b in range(a + 1, p)]
    return {
        "n_pixels": n, "identical_fraction": identical_fraction(P), "min_pair_hamming": min_pair_hamming(P),
        "pair_hamming": pair_hamming,
    }


# ---------- series, built in code from the frozen constants ----------

def _input_path(design: Design) -> str:
    return os.path.relpath(Path(design.patterns_path).resolve(), sweep.NEURON_DIR)


def _recall_base(design: Design) -> dict:
    return {
        "model": "hopfield", "seed": 1, "input": _input_path(design), "task": "recall", "rule": "hebb",
        "update": "async", "max_sweeps": design.max_sweeps, "trials": design.trials,
        "noise_levels": list(design.noise_levels), "subset": list(design.subset),
        "trace_trials": design.trace_trials,
    }


def _make_series(name: str, out: Path, base: dict, variants: list[sweep.Variant], seeds) -> sweep.Series:
    return sweep.Series(name=name, path=out / "sweeps" / name / "series.json", base_config=base, shared={},
                        varied=None, variants=variants, seeds=list(seeds), workers=os.cpu_count() or 1)


def recall_series(design: Design, out: Path, updates=None) -> sweep.Series:
    """One variant per update, labelled by the update itself ("async"/"sync")."""
    updates = design.updates if updates is None else updates
    variants = [sweep.Variant(update, {"update": update}) for update in updates]
    return _make_series("recall_hebb", out, _recall_base(design), variants, design.seeds)


def run_series(series: sweep.Series, out: Path, patterns, workers=None) -> list[Ran]:
    """Run every (variant, seed) of the series, stop on any failure, and check every run with
    analysis/hopfield.check_recall (a disagreement removes nothing by itself - run() removes the whole output on
    any failure)."""
    sweep_dir = out / "sweeps" / series.name
    sweep_dir.mkdir(parents=True, exist_ok=True)
    _write_json(sweep_dir / "base_config.json", series.base_config)
    spec = {"_comment": "generated by analysis/hopfield_qr.py from the frozen constants of "
                        "analysis/hopfield_qr_select.py",
            "base_config": "base_config.json", "seeds": series.seeds,
            "variants": [{"label": v.label, "set": v.overrides} for v in series.variants]}
    _write_json(series.path, spec)
    sweep.write_plan(series, sweep_dir / "plan.json")
    sweep.build_binary()
    tasks = sweep.plan(series)
    varied = sweep.varied_keys(series)
    rows = sweep.run_all(tasks, sweep_dir, workers or os.cpu_count() or 1, varied)
    sweep.write_summary(rows, sweep_dir / "summary.csv", varied)
    for row in rows:
        if row["status"] != "ok":
            raise SystemExit(f"series {series.name}: run {row['run']} failed: {row['status']}")
    ran = []
    for task in tasks:
        run_dir = sweep_dir / "runs" / task.name
        try:
            ran.append(Ran(task, run_dir, hopfield.check_recall(run_dir, patterns)))
        except hopfield.HopfieldCheckError as error:
            raise SystemExit(f"series {series.name}: run {task.name} disagrees with numpy: {error}")
    return ran


# ---------- aggregation (HOP-05, D-03, D-09) ----------

def aggregate_recall(design: Design, ran: list[Ran], out: Path, rule: str = "hebb", updates=None) -> dict:
    """recall.csv: pooled over the five QR and the seeds, from the trials.csv of every run. mean_final_overlap is
    the mean of the ABSOLUTE final overlap |m| with the pattern that was perturbed (D-03), not a signed mean."""
    updates = design.updates if updates is None else updates
    p = len(design.subset)
    cells: dict = {}
    for item in ran:
        header, table = hopfield.read_table(item.dir / "trials.csv")
        cells.setdefault(item.task.label, []).append((header, table))

    summary = []
    for update in updates:
        tables = cells[update]
        for level in design.noise_levels:
            per_seed, parts = [], []
            for header, table in tables:
                column = {c: i for i, c in enumerate(header)}
                part = table[np.abs(table[:, column["noise"]] - level) < 1e-9]
                parts.append((column, part))
                per_seed.append(float(part[:, column["correct"]].mean()))
            column = parts[0][0]
            data = np.concatenate([part for _c, part in parts])
            klass = data[:, column["class"]]
            pattern = data[:, column["pattern"]]
            own_overlap = np.take_along_axis(data[:, [column[f"m_{b}"] for b in range(p)]],
                                             pattern.astype(int)[:, None], axis=1)
            summary.append({
                "rule": rule, "update": update, "noise": float(level),
                "flipped": int(data[0, column["flipped"]]), "n_trials": int(data.shape[0]),
                "recall_rate": float(data[:, column["correct"]].mean()),
                "recall_sd_seeds": float(np.std(per_seed)),
                "wrong_stored_rate": float(((klass == hopfield.CLASS_STORED)
                                            & (data[:, column["match_a"]] != pattern)).mean()),
                "inverse_rate": float((klass == hopfield.CLASS_INVERSE).mean()),
                "mixture_rate": float((klass == hopfield.CLASS_MIXTURE).mean()),
                "other_rate": float((klass == hopfield.CLASS_OTHER).mean()),
                "cycle_rate": float((data[:, column["cycle"]] > 0).mean()),
                "mean_sweeps": float(data[:, column["sweeps"]].mean()),
                "mean_flips": float(data[:, column["flips"]].mean()),
                "mean_final_overlap": float(np.abs(own_overlap).mean()),
                "mean_final_energy": float(data[:, column["e_final"]].mean()),
            })
    _write_csv(out / "recall.csv", RECALL_COLUMNS, summary)
    return {"recall_rows": len(summary)}


def energy_trace_rows(ran: list[Ran], rule: str, seed: int = ENERGY_TRACE_SEED) -> list[dict]:
    """The per-step energy of the traced trial (t = 0 of each (source, noise) cell, trace_trials = 1) of the async
    reference update, ONE fixed seed only (HOP-05 "energia por paso"): the file has no seed column, so mixing
    several seeds' traces under the same (source, noise) key would interleave independent sequences and could look
    non-monotonic even though every single run's async energy never rises. Written generically over `rule` so a
    later pinv series (Plan 04) appends its own rows with no change here."""
    rows = []
    for item in ran:
        if item.task.label != "async" or item.task.seed != seed:
            continue
        config = hopfield.read_config(item.dir)
        subset = [int(v) for v in config["subset"]]
        levels = [float(v) for v in config["noise_levels"]]
        trials_per_cell = int(config["trials"])
        trace: dict[int, list[dict]] = {}
        for row in _dict_rows(item.dir / "trace.csv"):
            trace.setdefault(int(row["trial"]), []).append(row)
        for a in range(len(subset)):
            for l, level in enumerate(levels):
                trial = (a * len(levels) + l) * trials_per_cell  # first (t = 0) trial of the (a, l) cell
                for row in sorted(trace.get(trial, ()), key=lambda r: int(r["step"])):
                    rows.append({"rule": rule, "update": "async", "source": subset[a], "noise": level,
                                "step": int(row["step"]), "energy": float(row["energy"])})
    return rows


# ---------- the pre-registered verdict, applied to the measured data (D-02) ----------

def protocol_json(design: Design) -> dict:
    """Echo of the frozen design constants (hopfield_qr_select); no network quantity."""
    select = hopfield_qr_select
    return {
        "hypothesis": select.HYPOTHESIS,
        "noise_levels": list(design.noise_levels),
        "trials": design.trials,
        "seeds": list(design.seeds),
        "updates": list(design.updates),
        "subset": list(design.subset),
        "success": select.SUCCESS,
        "hebb_fail_recall_at_zero": select.HEBB_FAIL_RECALL_AT_ZERO,
        "pinv_work_recall_at_zero": select.PINV_WORK_RECALL_AT_ZERO,
        "hamming_tie_break": select.HAMMING_TIE_BREAK,
        "max_sweeps": design.max_sweeps,
        "trace_trials": design.trace_trials,
    }


def verdict_json(out: Path) -> dict:
    """hebb_fails: the frozen D-02 threshold (exact recovery at noise 0 async < 100%) APPLIED to the measured
    recall.csv value - never hard-coded to the predicted outcome. The pinv fields are left null; Plan 04 fills
    them once the pinv series runs."""
    rows = _dict_rows(out / "recall.csv")
    ref = [r for r in rows if r["rule"] == "hebb" and r["update"] == "async" and abs(float(r["noise"])) < 1e-9]
    if not ref:
        raise SystemExit("recall.csv: no hebb async noise-0 row to derive the verdict from (D-02)")
    measured = float(ref[0]["recall_rate"])
    threshold = hopfield_qr_select.HEBB_FAIL_RECALL_AT_ZERO
    hebb_fails = measured < threshold
    return {
        "hebb_exact_recovery_noise0_async": measured,
        "hebb_fails": hebb_fails,
        "hebb_rule": f"Hebb fails if exact recovery at noise 0 (async) < {threshold * 100:.0f}% (D-02); "
                     f"measured {measured * 100:.2f}%",
        "pinv_exact_recovery_noise0_async": None,
        "pinv_works": None,
        "pinv_rule": None,
    }


# ---------- identity of the network code (mirrors Phase 4's WR-02) ----------

def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_file_hashes(repo_dir=TP_DIR) -> dict:
    """sha256 of every file of CODE_FILES, read from repo_dir. A missing file is an error, not a silent gap."""
    repo_dir = Path(repo_dir)
    try:
        return {name: _sha256_file(repo_dir / name) for name in CODE_FILES}
    except OSError as error:
        raise SystemExit(f"cannot hash the network code: {error}") from None


def _git_text(args: list[str], repo_dir: Path):
    """Argument list, no shell. None when git cannot answer (not a repository, git missing)."""
    try:
        done = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True)
    except OSError:
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def code_identity(repo_dir=TP_DIR, binary=sweep.BINARY) -> dict:
    """Which network code produced a run: git HEAD, whether any CODE_FILES differs from HEAD or is untracked
    (dirty), the sha256 of each file and the sha256 of the neuron binary that ran."""
    repo_dir = Path(repo_dir)
    status = _git_text(["status", "--porcelain", "--untracked-files=all", "--", *CODE_FILES], repo_dir)
    try:
        binary_sha256 = _sha256_file(binary)
    except OSError as error:
        raise SystemExit(f"cannot hash the neuron binary: {error}") from None
    return {
        "head": _git_text(["rev-parse", "HEAD"], repo_dir),
        "dirty": None if status is None else bool(status),
        "files": code_file_hashes(repo_dir),
        "binary_sha256": binary_sha256,
    }


def changed_code_files(recorded: dict, repo_dir=TP_DIR) -> list[str]:
    """The CODE_FILES whose current sha256 is not the one in a recorded code_identity (all of them when nothing
    was recorded)."""
    files = recorded.get("files") if isinstance(recorded, dict) else None
    if not isinstance(files, dict):
        return list(CODE_FILES)
    current = code_file_hashes(repo_dir)
    return [name for name in CODE_FILES if files.get(name) != current[name]]


# ---------- the run ----------

def _check_prepared_qr(design: Design, identity: dict, repo_dir: Path) -> None:
    """The prepared CSV must come from the committed PNGs (T-05-06): the per-PNG digest in its meta file and the
    patterns themselves are compared with the committed PNGs."""
    stale = f"{design.patterns_path.name} was not written from the committed PNGs; run make qr (D-01)"
    try:
        meta = json.loads(Path(design.meta_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SystemExit(f"{Path(design.meta_path).name}: cannot read it; {stale}") from None
    source_sha256 = meta.get("source_sha256", {})
    for name, path in zip(qr.SOURCES, hopfield_qr_select.PNG_FILES):
        if source_sha256.get(name) != identity["png_sha256"].get(path):
            raise SystemExit(f"datos/prepared/{Path(design.meta_path).name}: {stale}")
    try:
        committed = qr.load_qr_set(Path(repo_dir) / "datos" / "hopfield").patterns
        prepared = hopfield.load_patterns(design.patterns_path)
    except (OSError, ValueError) as error:
        raise SystemExit(f"{design.patterns_path.name}: {error}; {stale}") from None
    if committed.shape != prepared.shape or not np.array_equal(committed, prepared):
        raise SystemExit(f"{design.patterns_path.name} differs from the committed PNGs; run make qr (D-01)")


def run(results_dir=sweep.RESULTS_DIR, design=None, repo_dir=TP_DIR, check_rule=True, workers=None) -> Path:
    design = default_design() if design is None else design
    results_dir = Path(results_dir)
    identity = dict.fromkeys(("rule_commit", "rule_sha256", "select_sha256", "qr_sha256", "png_sha256"))
    if check_rule:
        identity = hopfield_qr_select.rule_identity(repo_dir)
        _check_prepared_qr(design, identity, Path(repo_dir))

    patterns = hopfield.load_patterns(design.patterns_path)
    if len(design.subset) != patterns.shape[0]:
        raise SystemExit(f"subset has {len(design.subset)} entries for {patterns.shape[0]} patterns")

    out = results_dir / RESULTS_SUBDIR
    if out.exists():  # a failed re-run must not leave an old aggregate next to new runs; never touches qr_limits/
        shutil.rmtree(out)
    out.mkdir(parents=True)
    try:
        _write_json(out / "overlaps.json", overlaps_json(patterns))
        _write_json(out / "qr_facts.json", qr_facts_json(patterns))

        recall = recall_series(design, out)
        recall_ran = run_series(recall, out, patterns, workers)
        aggregate_recall(design, recall_ran, out)
        _write_csv(out / "energy_trace.csv", ENERGY_TRACE_COLUMNS, energy_trace_rows(recall_ran, "hebb"))

        _write_json(out / "protocol.json", protocol_json(design))
        _write_json(out / "verdict.json", verdict_json(out))

        _write_json(out / "run.json", {
            **identity, "code_identity": code_identity(repo_dir), "design": _design_json(design),
            "sweeps": {"recall_hebb": _relative(out / "sweeps" / "recall_hebb", results_dir)},
            "runs": {"recall_hebb": len(recall_ran)},
            "cross_checked_trials": sum(item.checked["trials"] for item in recall_ran),
        })
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise
    print(f"hopfield-qr -> {_relative(out, results_dir)}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workers", type=int, help="parallel runs (default: every core)")
    args = parser.parse_args(argv)
    run(workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
