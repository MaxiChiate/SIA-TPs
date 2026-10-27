"""The pre-registered grid-selection rule of the Kohonen map as code (SOM-03, D-10..D-15).

The rule is written in Spanish in deliverables/02-kohonen.md section 2, between the markers
`<!-- regla:inicio -->` and `<!-- regla:fin -->`. This module is its executable twin: the thresholds,
the filters, `select_grid` and the stage-2 ladders repeat the numbers of that text. The text, this file
and analysis/series_som_stage1.json are committed together, before any trained SOM runs on the creators'
data (D-10: once stage 1 runs, none of them changes). `rule_guard` and `rule_digest` make "committed
before looking" mechanical: later steps refuse to run on an untracked or modified rule.

Pure functions over plain dicts, numpy and the standard library only (D-06, Phase 1). There is no fallback
switch: with nothing eligible the rule chooses no grid (D-14: occupancy is never relaxed).
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

# D-11, D-12, D-14: filter thresholds, compared to means over the seeds of per-seed values.
TE_MAX = 0.05  # excluded when mean TE > TE_MAX
EMPTY_MAX = 0.20  # excluded when mean empty fraction > EMPTY_MAX
CREATORS_MIN = 2.0  # excluded when mean creators per occupied neuron < CREATORS_MIN

RULE_FILE = "deliverables/02-kohonen.md"
SELECT_FILE = "analysis/som_select.py"  # this module: guarded and hashed together with the rule text (D-10)
RULE_START = "<!-- regla:inicio -->"
RULE_END = "<!-- regla:fin -->"
STAGE1_SERIES = "analysis/series_som_stage1.json"
STAGE2_SERIES = "analysis/series_som_stage2.json"

# D-06, D-08: the stage-2 baseline on the chosen k (step); radius0 = max(1, k / 2) is computed per k.
BASELINE = {"neighborhood": "step", "radius_final": 1.0, "eta0": 0.5, "eta_final": 0.01, "epochs": 260}
ETA0_LADDER = (0.1, 0.25, 0.9)
EPOCHS_LADDER = (50, 130, 520, 1040)
SEEDS = tuple(range(1, 11))

MEASURES = ("qe", "te", "empty_fraction", "creators_per_occupied", "qe_loo")
CONFIG_KEYS = (("grid_k", int), ("neighborhood", str), ("radius0", float), ("radius_final", float),
               ("eta0", float), ("eta_final", float), ("epochs", int))


# ----------------------------------------------------------------------------------------------
# Aggregation over seeds
# ----------------------------------------------------------------------------------------------


def aggregate(summary_rows, loo_by_seed_rows, stability_by_label) -> list[dict]:
    """One row per configuration (label), in first-appearance order.

    summary_rows: csv.DictReader rows of a sweep summary.csv (one per seed run).
    loo_by_seed_rows: rows of loo_by_seed.csv (label, seed, qe_loo): each seed's mean over its 50 folds.
    stability_by_label: label -> (stability, nan_pairs).

    Every measure is computed per seed first and then summarised over the seeds: mean and sample SD
    (ddof 1). Creators per occupied neuron is the mean of the per-seed ratios n / occupied, never
    n / mean occupied. Any run whose status is not "ok" stops the selection (nothing is chosen from
    partial data).
    """
    loo = {}
    for row in loo_by_seed_rows:
        loo[(row["label"], int(row["seed"]))] = float(row["qe_loo"])

    per_label: dict[str, dict[int, dict]] = {}
    for row in summary_rows:
        if row["status"] != "ok":
            raise ValueError(f'run {row["run"]} did not finish ok: {row["status"]}')
        label, seed = row["label"], int(row["seed"])
        seeds = per_label.setdefault(label, {})
        if seed in seeds:
            raise ValueError(f"{label}: seed {seed} appears twice in the summary")
        if (label, seed) not in loo:
            raise ValueError(f"{label}: seed {seed} has no QE-LOO in loo_by_seed")
        seeds[seed] = row

    result = []
    for label, seeds in per_label.items():
        if len(seeds) < 2:
            raise ValueError(f"{label}: {len(seeds)} seed(s); the SD (ddof 1) needs at least 2")
        if label not in stability_by_label:
            raise ValueError(f"{label}: no stability given")
        ordered = [seeds[seed] for seed in sorted(seeds)]
        values = {
            "qe": [float(r["qe"]) for r in ordered],
            "te": [float(r["te"]) for r in ordered],
            "empty_fraction": [float(r["empty_fraction"]) for r in ordered],
            "creators_per_occupied": [float(r["n_samples"]) / float(r["occupied_neurons"]) for r in ordered],
            "qe_loo": [loo[(label, seed)] for seed in sorted(seeds)],
        }
        first = ordered[0]
        entry = {"label": label, "n_seeds": len(seeds)}
        for key, cast in CONFIG_KEYS:
            entry[key] = cast(first[key])
        for name in MEASURES:
            entry[f"{name}_mean"] = float(np.mean(values[name]))
            entry[f"{name}_sd"] = float(np.std(values[name], ddof=1))
        stability, nan_pairs = stability_by_label[label]
        entry["stability"] = float(stability)
        entry["nan_pairs"] = int(nan_pairs)
        result.append(entry)
    return result


# ----------------------------------------------------------------------------------------------
# The rule (D-11..D-15)
# ----------------------------------------------------------------------------------------------


def passes_filters(row) -> dict:
    """The three filters on one aggregated row; True means the grid is not excluded by that filter."""
    return {
        "te": row["te_mean"] <= TE_MAX,
        "empty": row["empty_fraction_mean"] <= EMPTY_MAX,
        "creators": row["creators_per_occupied_mean"] >= CREATORS_MIN,
    }


def _report(row) -> dict:
    flags = passes_filters(row)
    return {
        "k": int(row["grid_k"]),
        "label": row["label"],
        "passes_te": bool(flags["te"]),
        "passes_empty": bool(flags["empty"]),
        "passes_creators": bool(flags["creators"]),
        "qe_mean": row["qe_mean"],
        "qe_loo_mean": row["qe_loo_mean"],
        "qe_loo_sd": row["qe_loo_sd"],
        "te_mean": row["te_mean"],
        "empty_fraction_mean": row["empty_fraction_mean"],
        "creators_per_occupied_mean": row["creators_per_occupied_mean"],
        "stability": row["stability"],
    }


def select_grid(rows) -> dict:
    """Apply D-11..D-14 to the step rows; the gaussian rows are reported and never decide (D-11).

    1. Exclude mean TE > TE_MAX, mean empty fraction > EMPTY_MAX and mean creators per occupied neuron
       < CREATORS_MIN. If nothing is left, drop only the TE filter (D-14). If still nothing is left,
       no grid is chosen: outcome "no_eligible_grid" (the occupancy filters are never relaxed).
    2. The winner has the lowest mean QE-LOO (smaller k on an exact tie).
    3. The band is the winner plus every eligible row whose mean QE-LOO exceeds the winner's by strictly
       less than the winner's SD of per-seed QE-LOO. Inside the band the highest stability wins; equal
       stability goes to the smaller k.
    Training QE never decides; the k with the lowest mean training QE is reported (D-15).
    """
    step = [row for row in rows if row["neighborhood"] == "step"]
    gaussian = [row for row in rows if row["neighborhood"] == "gaussian"]
    if not step:
        raise ValueError("select_grid needs at least one step row")
    ks = [int(row["grid_k"]) for row in step]
    if len(set(ks)) != len(ks):
        raise ValueError("select_grid needs one step row per k")
    step = sorted(step, key=lambda row: int(row["grid_k"]))

    eligible = [row for row in step if all(passes_filters(row).values())]
    te_filter_dropped = False
    if not eligible:
        te_filter_dropped = True
        eligible = [row for row in step if passes_filters(row)["empty"] and passes_filters(row)["creators"]]

    qe_train_argmin_k = int(min(step, key=lambda row: (row["qe_mean"], int(row["grid_k"])))["grid_k"])
    result = {
        "outcome": "no_eligible_grid",
        "chosen_k": None,
        "chosen_label": None,
        "decided_by": None,
        "te_filter_dropped": te_filter_dropped,
        "winner_by_qe_loo": None,
        "tie_band": [],
        "per_k": [_report(row) for row in step],
        "gaussian": [_report(row) for row in sorted(gaussian, key=lambda row: int(row["grid_k"]))],
        "qe_train_argmin_k": qe_train_argmin_k,
        "thresholds": {"te_max": TE_MAX, "empty_max": EMPTY_MAX, "creators_min": CREATORS_MIN},
    }
    if not eligible:
        return result

    winner = min(eligible, key=lambda row: (row["qe_loo_mean"], int(row["grid_k"])))
    band = [winner] + [row for row in eligible if row is not winner
                       and row["qe_loo_mean"] - winner["qe_loo_mean"] < winner["qe_loo_sd"]]
    band.sort(key=lambda row: int(row["grid_k"]))
    if len(band) == 1:
        chosen, decided_by = winner, "qe_loo"
    else:
        best = max(row["stability"] for row in band)
        tied = [row for row in band if row["stability"] == best]
        chosen = tied[0]  # band is sorted by k, so the first tied row is the smallest k
        decided_by = "stability" if len(tied) == 1 else "smallest_k"
    result.update({
        "outcome": "chosen",
        "chosen_k": int(chosen["grid_k"]),
        "chosen_label": chosen["label"],
        "decided_by": decided_by,
        "winner_by_qe_loo": int(winner["grid_k"]),
        "tie_band": [int(row["grid_k"]) for row in band],
    })
    return result


# ----------------------------------------------------------------------------------------------
# "Committed before looking": digest and guard (D-10)
# ----------------------------------------------------------------------------------------------


def rule_digest(path) -> str:
    """sha256 of the text strictly between the two markers; the file needs exactly one of each."""
    text = Path(path).read_bytes().decode("utf-8")
    if text.count(RULE_START) != 1 or text.count(RULE_END) != 1:
        raise ValueError(f"{path}: needs exactly one {RULE_START} and one {RULE_END}")
    start = text.index(RULE_START) + len(RULE_START)
    end = text.index(RULE_END)
    if end < start:
        raise ValueError(f"{path}: {RULE_END} comes before {RULE_START}")
    return hashlib.sha256(text[start:end].encode("utf-8")).hexdigest()


def _git(args, repo_dir):
    return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True)


def rule_guard(paths, repo_dir=TP_DIR) -> str:
    """Refuse unless every path is tracked and has no uncommitted change; return the last commit hash.

    git calls are argument lists run in repo_dir, with no shell (T-02-09).
    """
    message = ": the pre-registered rule and its series must be committed and unchanged before a stage runs (D-10)"
    for path in paths:
        tracked = _git(["ls-files", "--error-unmatch", "--", str(path)], repo_dir)
        if tracked.returncode != 0:
            raise SystemExit(f"{path}{message}")
        status = _git(["status", "--porcelain", "--", str(path)], repo_dir)
        if status.returncode != 0 or status.stdout.strip():
            raise SystemExit(f"{path}{message}")
    log = _git(["log", "-1", "--format=%H", "--", *[str(path) for path in paths]], repo_dir)
    commit = log.stdout.strip()
    if log.returncode != 0 or len(commit) != 40:
        raise SystemExit(f"{', '.join(str(p) for p in paths)}{message}")
    return commit


# ----------------------------------------------------------------------------------------------
# Stage 2 (D-06): generated from the pre-registered ladders alone
# ----------------------------------------------------------------------------------------------


def radius0_ladder(k: int) -> list[float]:
    """radius0 values of stage 2: max(1, k / 4) and k, without the baseline max(1, k / 2)."""
    return sorted({max(1.0, k / 4), float(k)} - {max(1.0, k / 2)})


def stage2_series(k: int) -> dict:
    """The stage-2 series on the chosen k: the baseline plus variants that each change exactly one of
    radius0, eta0 or epochs."""
    base = {**BASELINE, "grid_k": k, "radius0": max(1.0, k / 2)}
    variants = [{"label": "base", "set": {}}]
    variants += [{"label": f"radius0-{v:g}", "set": {"radius0": v}} for v in radius0_ladder(k)]
    variants += [{"label": f"eta0-{v:g}", "set": {"eta0": v}} for v in ETA0_LADDER if v != base["eta0"]]
    variants += [{"label": f"epochs-{v}", "set": {"epochs": v}} for v in EPOCHS_LADDER if v != base["epochs"]]
    return {
        "_comment": "Stage 2 (D-06): generated from the ladders of deliverables/02-kohonen.md section 2 for "
                    "the chosen k; committed before it runs",
        "base_config": "../neuron/config.json.kohonen.example",
        "set": base,
        "seeds": list(SEEDS),
        "variants": variants,
    }
