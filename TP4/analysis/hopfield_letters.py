#!/usr/bin/env python3
"""Guarded driver of the Hopfield letters experiments (HOP-02, HOP-03, D-04).

    .venv/bin/python analysis/hopfield_letters.py            # or: make hopfield-letters

Runs the experiments pre-registered in deliverables/04-hopfield-letras.md section 3, with every number taken from
analysis/hopfield_select.py. It refuses to run unless the rule commit is in place (the rule text, the selection
code, the alphabet and the converter committed and unchanged) and the prepared alphabet was written from the
committed one (D-04). The series are built in code from the frozen constants, so no series file, flag or edit can
change the design after the commit. Every run of the neuron binary goes through analysis/hopfield.py before
anything is aggregated; a failed run or a disagreement stops the driver and removes the output. What that check
recomputes is narrower than "every trial": W, stored.csv, overlaps and the capacity stability columns of every run,
and the step-by-step replay of the traced recall trials (one per letter and level) and of every spurious-search
trial. The class, convergence, sweeps, flips and correct columns of the other recall trials, and the capacity
recall_rate and mean_sweeps, are only range- and consistency-checked (see the docstring of analysis/hopfield.py).
The network code that produced a run (git HEAD, a dirty flag, sha256 of the C core, the driver, the config reader
and the numpy control, and of the binary) is recorded in run.json as code_identity; it is not pinned by the rule
guard, and hopfield_figures.py refuses to draw if those files changed since the run (WR-02).

Writes under analysis/results/hopfield/letters/ (not versioned): selection.json, run.json (with code_identity) and
sweeps/<series>/.
numpy and the standard library only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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
import hopfield_select  # noqa: E402
import letters  # noqa: E402
import sweep  # noqa: E402

RESULTS_SUBDIR = Path("hopfield") / "letters"
SET_NAMES = ("separated", "correlated")
RECALL_COLUMNS = ["set", "update", "noise", "flipped", "n_trials", "recall_rate", "recall_sd_seeds",
                  "wrong_stored_rate", "inverse_rate", "mixture_rate", "other_rate", "cycle_rate", "mean_sweeps",
                  "mean_flips", "mean_final_overlap"]
PATTERN_COLUMNS = ["set", "update", "letter", "noise", "flipped", "n_trials", "recall_rate"]
# The network code is not covered by the pre-registration guard. Its identity is recorded in run.json (WR-02) and
# hopfield_figures.py refuses to draw if one of these files changed since the run. Paths relative to the TP4 root.
CODE_FILES = ("neuron/models/hopfield.c", "neuron/models/hopfield_core.c", "neuron/models/hopfield_core.h",
              "neuron/io/config.c", "analysis/hopfield.py", "analysis/hopfield_letters.py")


@dataclass(frozen=True)
class Design:
    """Every number of the experiment. default_design() fills it from analysis/hopfield_select.py."""

    patterns_path: Path
    meta_path: Path
    letters: str
    max_sweeps: int
    recall_levels: tuple
    recall_trials: int
    seeds: tuple
    updates: tuple
    trace_trials: int
    capacity_p: int
    capacity_level: float
    capacity_trials: int
    capacity_p_range: tuple
    capacity_samples: int
    capacity_near_zero: float
    capacity_p_limit: int
    spurious_levels: tuple
    spurious_trials: int
    spurious_seeds: tuple
    spurious_update: str


def default_design() -> Design:
    """The design written in the rule: the constants of the frozen hopfield_select module, nothing else."""
    select = hopfield_select
    return Design(
        patterns_path=letters.PREPARED_CSV,
        meta_path=letters.PREPARED_CSV.with_suffix(".meta.json"),
        letters=letters.LETTERS,
        max_sweeps=select.MAX_SWEEPS,
        recall_levels=tuple(select.RECALL_LEVELS),
        recall_trials=select.RECALL_TRIALS,
        seeds=tuple(select.SEEDS),
        updates=tuple(select.UPDATES),
        trace_trials=select.TRACE_TRIALS,
        capacity_p=select.CAPACITY_P,
        capacity_level=select.CAPACITY_LEVEL,
        capacity_trials=select.CAPACITY_TRIALS,
        capacity_p_range=tuple(select.CAPACITY_P_RANGE),
        capacity_samples=select.CAPACITY_SAMPLES,
        capacity_near_zero=select.CAPACITY_NEAR_ZERO,
        capacity_p_limit=select.CAPACITY_P_LIMIT,
        spurious_levels=tuple(select.SPURIOUS_LEVELS),
        spurious_trials=select.SPURIOUS_TRIALS,
        spurious_seeds=tuple(select.SPURIOUS_SEEDS),
        spurious_update=select.SPURIOUS_UPDATE,
    )


class Ran(NamedTuple):
    """One run of a series: its task, the run directory it was moved to and what check_recall or
    check_capacity recomputed in it."""

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
    """Relative to TP4 when the path lives there (the real run); otherwise relative to the results directory,
    so a run in a temporary directory writes no machine-specific path."""
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


# ---------- series, built in code from the frozen constants ----------

def _input_path(design: Design) -> str:
    return os.path.relpath(Path(design.patterns_path).resolve(), sweep.NEURON_DIR)


def _recall_base(design: Design, subset: list[int]) -> dict:
    return {
        "model": "hopfield", "seed": 1, "input": _input_path(design), "task": "recall", "rule": "hebb",
        "update": "async", "max_sweeps": design.max_sweeps, "trials": design.recall_trials,
        "noise_levels": list(design.recall_levels), "subset": subset, "trace_trials": design.trace_trials,
    }


def _capacity_base(design: Design) -> dict:
    """Built from scratch: sweep.plan cannot delete keys and the capacity task refuses subset and trace_trials."""
    return {
        "model": "hopfield", "seed": 1, "input": _input_path(design), "task": "capacity", "rule": "hebb",
        "update": "async", "max_sweeps": design.max_sweeps, "trials": design.capacity_trials,
        "noise_levels": [design.capacity_level], "p": design.capacity_p, "n_subsets": 0,
    }


def _make_series(name: str, out: Path, base: dict, variants: list[sweep.Variant], seeds) -> sweep.Series:
    return sweep.Series(name=name, path=out / "sweeps" / name / "series.json", base_config=base, shared={},
                        varied=None, variants=variants, seeds=list(seeds), workers=os.cpu_count() or 1)


def recall_series(design: Design, sets: dict, out: Path, set_names=SET_NAMES, updates=None) -> sweep.Series:
    updates = design.updates if updates is None else updates
    variants = [sweep.Variant(f"{name}-{update}", {"subset": [int(i) for i in sets[name]], "update": update})
                for name in set_names for update in updates]
    return _make_series("recall", out, _recall_base(design, [int(i) for i in sets[set_names[0]]]), variants,
                        design.seeds)


def run_series(series: sweep.Series, out: Path, patterns, workers=None, kind="recall") -> list[Ran]:
    """Run every (variant, seed) of the series, stop on any failure, and check every run with analysis/hopfield.py
    (what that recomputes and what it only range-checks is in its docstring)."""
    sweep_dir = out / "sweeps" / series.name
    sweep_dir.mkdir(parents=True, exist_ok=True)
    _write_json(sweep_dir / "base_config.json", series.base_config)
    spec = {"_comment": "generated by analysis/hopfield_letters.py from the constants of analysis/hopfield_select.py",
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
            checker = hopfield.check_recall if kind == "recall" else hopfield.check_capacity
            ran.append(Ran(task, run_dir, checker(run_dir, patterns)))
        except hopfield.HopfieldCheckError as error:
            raise SystemExit(f"series {series.name}: run {task.name} disagrees with numpy: {error}")
    return ran


# ---------- aggregation ----------

def _set_and_update(task: sweep.Task) -> tuple[str, str]:
    name, update = task.label.split("-", 1)
    return name, update


def aggregate_recall(design: Design, ran: list[Ran], out: Path, set_names=SET_NAMES, updates=None) -> dict:
    """recall.csv and recall_by_pattern.csv: pooled over the seeds, from the trials.csv of every run."""
    updates = design.updates if updates is None else updates
    cells: dict = {}
    for item in ran:
        header, table = hopfield.read_table(item.dir / "trials.csv")
        cells.setdefault(_set_and_update(item.task), []).append((header, table))

    summary, by_pattern = [], []
    for name in set_names:
        for update in updates:
            tables = cells[(name, update)]
            for level in design.recall_levels:
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
                own = np.take_along_axis(data[:, [column[f"m_{b}"] for b in range(sum(
                    1 for c in column if c.startswith("m_")))]], pattern.astype(int)[:, None], axis=1)
                summary.append({
                    "set": name, "update": update, "noise": float(level),
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
                    "mean_final_overlap": float(own.mean()),
                })
                for source_row in sorted({int(v) for v in data[:, column["source_row"]]}):
                    mine = data[data[:, column["source_row"]] == source_row]
                    by_pattern.append({
                        "set": name, "update": update, "letter": design.letters[source_row],
                        "noise": float(level), "flipped": int(mine[0, column["flipped"]]),
                        "n_trials": int(mine.shape[0]), "recall_rate": float(mine[:, column["correct"]].mean()),
                    })
    _write_csv(out / "recall.csv", RECALL_COLUMNS, summary)
    _write_csv(out / "recall_by_pattern.csv", PATTERN_COLUMNS, by_pattern)
    return {"recall_rows": len(summary), "recall_by_pattern_rows": len(by_pattern)}


def capacity_series(design: Design, n_rows: int, out: Path, name: str, ps=None) -> sweep.Series:
    """capacity_p4 (ps None): the single exhaustive variant "p4". Otherwise one variant "p<p>" per p, every
    subset when C(n_rows, p) <= capacity_samples and capacity_samples random subsets per seed otherwise."""
    if ps is None:
        variants = [sweep.Variant(f"p{design.capacity_p}", {"p": design.capacity_p, "n_subsets": 0})]
    else:
        variants = [sweep.Variant(f"p{p}", {"p": p, "n_subsets": 0 if math.comb(n_rows, p) <= design.capacity_samples
                                            else design.capacity_samples}) for p in ps]
    return _make_series(name, out, _capacity_base(design), variants, design.seeds)


class CapacityGroup(NamedTuple):
    """The runs of one p of the capacity curve: exhaustive when every subset was taken, extension 1 for a p
    added by the written rule."""

    p: int
    exhaustive: bool
    extension: int
    ran: list


def _capacity_groups(series: sweep.Series, ran: list[Ran], extension: int) -> list[CapacityGroup]:
    groups = []
    for variant_index, variant in enumerate(series.variants):
        mine = [item for item in ran if item.task.variant == variant_index]
        groups.append(CapacityGroup(int(variant.overrides["p"]), variant.overrides["n_subsets"] == 0, extension,
                                    mine))
    return groups


def _capacity_tables(ran: list[Ran]) -> list[tuple]:
    return [hopfield.read_table(item.dir / "capacity.csv") for item in sorted(ran, key=lambda i: i.task.seed)]


def _group_stats(group: CapacityGroup) -> dict:
    """Per-seed means of the stable fraction and of the recall rate, pooled counts of fully stable subsets."""
    stable, recall, rows, all_stable = [], [], [], 0
    for header, table in _capacity_tables(group.ran):
        column = {c: i for i, c in enumerate(header)}
        stable.append(float(table[:, column["stable_fraction"]].mean()))
        recall.append(float(table[:, column["recall_rate"]].mean()))
        rows.append(int(table.shape[0]))
        all_stable += int((table[:, column["n_stable"]] == group.p).sum())
    if len(set(rows)) != 1:
        raise SystemExit(f"p = {group.p}: the seeds drew different numbers of subsets: {rows}")
    return {"n_subsets": rows[0], "n_seeds": len(rows), "mean_stable_fraction": float(np.mean(stable)),
            "sd_stable_fraction": float(np.std(stable)), "mean_recall_rate": float(np.mean(recall)),
            "sd_recall_rate": float(np.std(recall)), "all_stable_fraction": all_stable / (sum(rows))}


def _aggregate_p4(design: Design, ran: list[Ran], out: Path) -> list[dict]:
    """capacity_p4.csv: one row per subset, joined over the seeds. Whether a subset is stable cannot depend on
    the seed, so every column but the recall ones must be identical across seeds."""
    tables = _capacity_tables(ran)
    header = tables[0][0]
    stack = np.stack([table for _h, table in tables])
    column = {c: i for i, c in enumerate(header)}
    for name in header:
        if name in ("recall_rate", "mean_sweeps"):
            continue
        if not np.all(stack[:, :, column[name]] == stack[0, :, column[name]]):
            raise SystemExit(f"capacity_p4: column {name} differs between seeds; the stability of a subset "
                             "cannot depend on the seed")
    recall = stack[:, :, column["recall_rate"]]
    rows = []
    for r in range(stack.shape[1]):
        idx = [int(stack[0, r, column[f"idx_{c}"]]) for c in range(design.capacity_p)]
        row = {"subset": int(stack[0, r, column["subset"]])}
        row.update({f"idx_{c}": idx[c] for c in range(design.capacity_p)})
        row.update({
            "letters": "".join(design.letters[i] for i in idx),
            "max_abs_overlap": float(stack[0, r, column["max_abs_overlap"]]),
            "mean_abs_overlap": float(stack[0, r, column["mean_abs_overlap"]]),
            "n_stable": int(stack[0, r, column["n_stable"]]),
            "stable_fraction": float(stack[0, r, column["stable_fraction"]]),
            "min_margin": int(stack[0, r, column["min_margin"]]),
            "recall_rate_mean": float(recall[:, r].mean()),
            "recall_rate_sd": float(recall[:, r].std()),
        })
        rows.append(row)
    columns = (["subset"] + [f"idx_{c}" for c in range(design.capacity_p)]
               + ["letters", "max_abs_overlap", "mean_abs_overlap", "n_stable", "stable_fraction", "min_margin",
                  "recall_rate_mean", "recall_rate_sd"])
    _write_csv(out / "capacity_p4.csv", columns, rows)
    return rows


def aggregate_capacity(design: Design, p4_ran: list[Ran], groups: list[CapacityGroup], sets: dict, out: Path,
                       n_pixels: int) -> dict:
    """capacity_p4.csv, capacity_by_p.csv and capacity.json (D-05)."""
    p4_rows = _aggregate_p4(design, p4_ran, out)
    by_p, last_fraction = [], None
    for group in sorted(groups, key=lambda g: g.p):
        stats = _group_stats(group)
        by_p.append({"p": group.p, "n_subsets": stats["n_subsets"], "exhaustive": int(group.exhaustive),
                     "n_seeds": stats["n_seeds"], "mean_stable_fraction": stats["mean_stable_fraction"],
                     "sd_stable_fraction": stats["sd_stable_fraction"],
                     "all_stable_fraction": stats["all_stable_fraction"],
                     "mean_recall_rate": stats["mean_recall_rate"], "sd_recall_rate": stats["sd_recall_rate"],
                     "extension": group.extension})
        last_fraction = stats["mean_stable_fraction"]
    _write_csv(out / "capacity_by_p.csv",
               ["p", "n_subsets", "exhaustive", "n_seeds", "mean_stable_fraction", "sd_stable_fraction",
                "all_stable_fraction", "mean_recall_rate", "sd_recall_rate", "extension"], by_p)

    counts: dict = {}
    for row in p4_rows:
        counts[row["n_stable"]] = counts.get(row["n_stable"], 0) + 1
    by_indices = {tuple(row[f"idx_{c}"] for c in range(design.capacity_p)): row for row in p4_rows}
    p_last = by_p[-1]["p"]
    capacity = {
        "n_pixels": n_pixels,
        "p4_subsets": len(p4_rows),
        "p4_n_stable_counts": {str(k): counts[k] for k in sorted(counts)},
        "p4_mean_stable_fraction": float(np.mean([row["stable_fraction"] for row in p4_rows])),
        "p4_all_stable_fraction": float(np.mean([row["n_stable"] == design.capacity_p for row in p4_rows])),
        "p4_sets": {name: by_indices.get(tuple(int(i) for i in sets[name])) for name in SET_NAMES},
        "p_extension": {"near_zero": design.capacity_near_zero, "p_limit": design.capacity_p_limit,
                        "p_last": p_last, "extended": any(g.extension for g in groups),
                        "near_zero_reached": last_fraction <= design.capacity_near_zero},
        "orders_of_magnitude": {f"{ref:g}N": ref * n_pixels for ref in hopfield_select.CAPACITY_REFERENCES},
    }
    _write_json(out / "capacity.json", capacity)
    return {"p4_rows": len(p4_rows), "p_values": [row["p"] for row in by_p]}


# ---------- orthogonality ----------

def orthogonality(design: Design, patterns, sets: dict) -> dict:
    """Both sets: integer dot products, overlaps, the cross term of every pixel, the margins N - p + cross
    term, which letters are fixed points and the energy of each stored letter (D-06)."""
    n = patterns.shape[1]
    report = {"n_pixels": n}
    for name in SET_NAMES:
        indices = [int(i) for i in sets[name]]
        P = patterns[indices]
        p = len(indices)
        dots = P @ P.T
        cross = hopfield.cross_terms(P)
        margin = n - p + cross
        W = hopfield.hebb(P)
        min_margin, wrong = hopfield.margins(W, P)
        if not np.array_equal(margin.min(axis=1), min_margin) or not np.array_equal((margin < 0).sum(axis=1), wrong):
            raise SystemExit(f"{name}: N - p + cross term disagrees with the margins of the Hebb matrix")
        report[name] = {
            "indices": indices, "letters": [design.letters[i] for i in indices],
            "dots": dots.tolist(), "overlaps": (dots / n).tolist(), "cross_terms": cross.tolist(),
            "margins": margin.tolist(), "min_margin": [int(v) for v in min_margin],
            "wrong_pixels": [int(v) for v in wrong], "fixed": [bool(v == 0) for v in wrong],
            "stored_energies": [hopfield.energy(W, P[a]) for a in range(p)],
        }
    return report


# ---------- the pre-registered spurious-state search (HOP-03) ----------

def spurious_series(design: Design, sets: dict, out: Path, seed: int) -> sweep.Series:
    """Very noisy queries of the separated set, every trial traced, one seed."""
    subset = [int(i) for i in sets["separated"]]
    base = _recall_base(design, subset)
    base.update({"update": design.spurious_update, "noise_levels": list(design.spurious_levels),
                 "trials": design.spurious_trials, "trace_trials": design.spurious_trials})
    variants = [sweep.Variant(f"separated-{design.spurious_update}",
                              {"subset": subset, "update": design.spurious_update})]
    return _make_series(f"spurious_seed{seed}", out, base, variants, [seed])


def _dict_rows(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _spurious_pick(design: Design, patterns, subset: list[int], seed: int, run_dir: Path, row: dict,
                   results_dir: Path) -> dict:
    """The query, the final state, the energy trace and the overlaps of one picked trial, with its class,
    energies and fixed-point status recomputed in numpy; a disagreement with trials.csv stops the run."""
    P = patterns[subset]
    W = hopfield.hebb(P)
    trial = int(float(row["trial"]))
    _h, states = hopfield.read_table(run_dir / "states.csv")
    _h, trace = hopfield.read_table(run_dir / "trace.csv")
    mine = states[states[:, 0] == trial]
    if mine.shape[0] != 2 or mine[0, 1] != 0 or mine[1, 1] != 1:
        raise SystemExit(f"{run_dir.name}: trial {trial} has no query and final rows in states.csv")
    query = mine[0, 2:].astype(np.int64)
    final = mine[1, 2:].astype(np.int64)
    energies = [float(v) for v in trace[trace[:, 0] == trial][:, 5]]
    code, match, sign = hopfield.classify(P, final)
    e_start, e_final = float(row["e_start"]), float(row["e_final"])
    problems = []
    if code != int(float(row["class"])):
        problems.append(f"class {code} != {row['class']}")
    if abs(hopfield.energy(W, query) - e_start) > hopfield.ENERGY_TOLERANCE:
        problems.append("e_start")
    if abs(hopfield.energy(W, final) - e_final) > hopfield.ENERGY_TOLERANCE:
        problems.append("e_final")
    if not energies or energies[0] != e_start or energies[-1] != e_final:
        problems.append("energy trace")
    fixed = hopfield.is_fixed(W, final)
    if int(float(row["converged"])) == 1 and not fixed:
        problems.append("converged but not a fixed point")
    if problems:
        raise SystemExit(f"{run_dir.name} trial {trial}: numpy disagrees with trials.csv: {', '.join(problems)}")
    used = [slot for slot in range(3) if match[slot] >= 0]
    return {
        "seed": seed, "run": _relative(run_dir, results_dir), "trial": trial,
        "letter": design.letters[int(float(row["source_row"]))], "noise": float(row["noise"]),
        "flipped": int(float(row["flipped"])), "query": [int(v) for v in query], "final": [int(v) for v in final],
        "overlaps": [float(row[f"m_{b}"]) for b in range(len(subset))], "class": hopfield_select.CLASS_NAMES[code],
        "match_letters": [design.letters[subset[match[slot]]] for slot in used],
        "signs": [int(sign[slot]) for slot in used], "converged": int(float(row["converged"])),
        "sweeps": int(float(row["sweeps"])), "e_start": e_start, "e_final": e_final, "energy_trace": energies,
        "is_fixed": bool(fixed),
    }


def spurious_report(design: Design, sets: dict, patterns, out: Path, results_dir: Path, workers=None) -> dict:
    """Seeds in the order of the rule; the first converged trial of each of inverse, mixture and other, over the
    seeds in order; stop at the first seed whose trials hold a converged mixture or other state. Writes
    spurious.json and returns {"seeds_tried", "trials"}."""
    subset = [int(i) for i in sets["separated"]]
    W = hopfield.hebb(patterns[subset])
    picks: dict = {}
    seeds_tried, counts, converged_counts, checked = [], {}, {}, 0
    for seed in design.spurious_seeds:
        ran = run_series(spurious_series(design, sets, out, seed), out, patterns, workers)
        checked += ran[0].checked["trials"]
        rows = _dict_rows(ran[0].dir / "trials.csv")
        seeds_tried.append(seed)
        codes = [int(float(row["class"])) for row in rows]
        done = [int(float(row["converged"])) == 1 for row in rows]
        counts[str(seed)] = {name: codes.count(code) for code, name in enumerate(hopfield_select.CLASS_NAMES)}
        converged_counts[str(seed)] = {name: sum(1 for c, d in zip(codes, done) if c == code and d)
                                       for code, name in enumerate(hopfield_select.CLASS_NAMES)}
        for code, row in hopfield_select.pick_spurious(rows).items():
            picks.setdefault(code, (seed, ran[0].dir, row))
        if not hopfield_select.spurious_needs_next_seed(rows):
            break
    report = {
        "update": design.spurious_update, "levels": list(design.spurious_levels),
        "trials_per_level_and_letter": design.spurious_trials, "seeds_tried": seeds_tried,
        "counts_by_seed": counts, "converged_by_seed": converged_counts,
        "found_target": any(code in (2, 3) for code in picks),
        "stored_letters": [design.letters[i] for i in subset],
        "stored_energies": [hopfield.energy(W, patterns[i]) for i in subset],
        "picks": {hopfield_select.CLASS_NAMES[code]: _spurious_pick(design, patterns, subset, seed, run_dir, row,
                                                                      results_dir)
                  for code, (seed, run_dir, row) in sorted(picks.items())},
    }
    _write_json(out / "spurious.json", report)
    return {"seeds_tried": seeds_tried, "trials": checked}


# ---------- identity of the network code (WR-02) ----------

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
    (dirty), the sha256 of each file and the sha256 of the neuron binary that ran. head and dirty are None when
    repo_dir is not a git checkout; the file hashes are what hopfield_figures.py compares."""
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
    """The CODE_FILES whose current sha256 is not the one in a recorded code_identity (all of them when
    nothing was recorded)."""
    files = recorded.get("files") if isinstance(recorded, dict) else None
    if not isinstance(files, dict):
        return list(CODE_FILES)
    current = code_file_hashes(repo_dir)
    return [name for name in CODE_FILES if files.get(name) != current[name]]


# ---------- the run ----------

def _check_prepared_alphabet(design: Design, identity: dict, repo_dir: Path) -> None:
    """The prepared CSV must come from the committed alphabet (T-04-12): the digest in its meta file and the
    patterns themselves are compared with the committed alphabet."""
    stale = (f"{design.patterns_path.name} was not written from the committed alphabet; run make letters (D-04)")
    try:
        meta = json.loads(Path(design.meta_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SystemExit(f"{Path(design.meta_path).name}: cannot read it; {stale}") from None
    if meta.get("source_sha256") != identity["alphabet_sha256"]:
        raise SystemExit(f"datos/prepared/{Path(design.meta_path).name}: {stale}")
    try:
        committed = letters.load_alphabet(Path(repo_dir) / hopfield_select.ALPHABET_FILE).patterns
        prepared = hopfield.load_patterns(design.patterns_path)
    except (OSError, ValueError) as error:
        raise SystemExit(f"{design.patterns_path.name}: {error}; {stale}") from None
    if committed.shape != prepared.shape or not np.array_equal(committed, prepared):
        raise SystemExit(f"{design.patterns_path.name} differs from the committed alphabet; run make letters (D-04)")


def _selection(design: Design, patterns, sets: dict, identity: dict) -> dict:
    n = patterns.shape[1]
    dots = hopfield_select.pair_dots(patterns)
    histogram = hopfield_select.max_abs_histogram(patterns)
    ties = {"separated": {"subsets_with_key": sets["ties_separated"]},
            "correlated": {"subsets_with_max": sets["ties_correlated_max"],
                           "subsets_with_key": sets["ties_correlated_key"]}}
    chosen = {}
    for name in SET_NAMES:
        combo = [int(i) for i in sets[name]]
        pairs = []
        for a in range(len(combo)):
            for b in range(a + 1, len(combo)):
                d = int(dots[combo[a], combo[b]])
                pairs.append({"pair": design.letters[combo[a]] + design.letters[combo[b]], "dot": d,
                              "overlap": d / n})
        key = sets[f"{name}_key"]
        chosen[name] = {"indices": combo, "letters": "".join(design.letters[i] for i in combo), "pairs": pairs,
                        "max_abs_dot": int(key[0]), "sum_abs_dot": int(key[1]), "ties": ties[name]}
    return {
        **identity,
        "patterns_path": _relative(design.patterns_path, TP_DIR),
        **chosen,
        "max_abs_overlap_histogram": [
            {"max_abs_dot": int(peak), "max_abs_overlap": peak / n, "n_subsets": int(count),
             "sets": [name for name in SET_NAMES if chosen[name]["max_abs_dot"] == peak]}
            for peak, count in histogram.items()],
    }


def run(results_dir=sweep.RESULTS_DIR, design=None, repo_dir=TP_DIR, check_rule=True, workers=None) -> Path:
    design = default_design() if design is None else design
    results_dir = Path(results_dir)
    identity = dict.fromkeys(("rule_commit", "rule_sha256", "select_sha256", "alphabet_sha256", "letters_sha256"))
    if check_rule:
        identity = hopfield_select.rule_identity(repo_dir)
        _check_prepared_alphabet(design, identity, Path(repo_dir))

    patterns = hopfield.load_patterns(design.patterns_path)
    if design.capacity_p_limit > patterns.shape[0]:
        raise SystemExit(f"capacity_p_limit {design.capacity_p_limit} exceeds the {patterns.shape[0]} patterns")
    if len(design.letters) != patterns.shape[0]:
        raise SystemExit(f"{len(design.letters)} letter names for {patterns.shape[0]} patterns")

    out = results_dir / RESULTS_SUBDIR
    if out.exists():  # a failed re-run must not leave an old aggregate next to new runs
        shutil.rmtree(out)
    out.mkdir(parents=True)
    try:
        sets = hopfield_select.select_sets(patterns)
        _write_json(out / "selection.json", _selection(design, patterns, sets, identity))

        _write_json(out / "orthogonality.json", orthogonality(design, patterns, sets))

        recall = recall_series(design, sets, out)
        recall_ran = run_series(recall, out, patterns, workers)
        aggregate_recall(design, recall_ran, out)

        n_rows, n_pixels = patterns.shape
        p4 = capacity_series(design, n_rows, out, "capacity_p4")
        p4_ran = run_series(p4, out, patterns, workers, kind="capacity")
        by_p = capacity_series(design, n_rows, out, "capacity_by_p", ps=design.capacity_p_range)
        by_p_ran = run_series(by_p, out, patterns, workers, kind="capacity")
        groups = _capacity_groups(by_p, by_p_ran, 0)
        series_runs = {"recall": len(recall_ran), "capacity_p4": len(p4_ran), "capacity_by_p": len(by_p_ran)}
        sweeps = ["recall", "capacity_p4", "capacity_by_p"]
        # The written extension (D-05): one p at a time from the last p of the range, while the frozen rule says so
        p = design.capacity_p_range[-1]
        while hopfield_select.capacity_needs_next_p(p, _group_stats(groups[-1])["mean_stable_fraction"],
                                                    design.capacity_near_zero, design.capacity_p_limit):
            p += 1
            name = f"capacity_by_p_p{p}"
            extra = capacity_series(design, n_rows, out, name, ps=[p])
            extra_ran = run_series(extra, out, patterns, workers, kind="capacity")
            groups += _capacity_groups(extra, extra_ran, 1)
            series_runs[name] = len(extra_ran)
            sweeps.append(name)
        capacity = aggregate_capacity(design, p4_ran, groups, sets, out, n_pixels)
        spurious = spurious_report(design, sets, patterns, out, results_dir, workers)
        for seed in spurious["seeds_tried"]:
            series_runs[f"spurious_seed{seed}"] = 1
            sweeps.append(f"spurious_seed{seed}")

        _write_json(out / "run.json", {
            **identity, "code_identity": code_identity(repo_dir), "design": _design_json(design),
            "sweeps": {name: _relative(out / "sweeps" / name, results_dir) for name in sweeps},
            "runs": series_runs,
            "spurious_seeds_tried": spurious["seeds_tried"],
            # Name kept so run.json keeps its shape: counts the trials that went through check_recall, of which
            # only the traced ones are replayed; the rest are range- and consistency-checked (WR-01).
            "cross_checked_trials": sum(item.checked["trials"] for item in recall_ran) + spurious["trials"],
            "cross_checked_capacity_rows": sum(item.checked["rows"] for item in p4_ran + by_p_ran
                                               + [r for g in groups if g.extension for r in g.ran]),
            "capacity_p_values": capacity["p_values"],
        })
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise
    print(f"hopfield-letters -> {_relative(out, results_dir)}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workers", type=int, help="parallel runs (default: every core)")
    args = parser.parse_args(argv)
    run(workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
