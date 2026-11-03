#!/usr/bin/env python3
"""Post-hoc experiment: Hebb on the varying pixels of the three most distinct QR (KD-9).

    .venv/bin/python analysis/hopfield_qr_masked.py        # or: make hopfield-qr-masked

The pre-registered protocol of deliverables/05-hopfield-qr.md section 3 found that Hebb recovers 0 % of the five QR
even without noise: they are too correlated. This driver runs a SECOND, clearly labelled experiment, designed AFTER
seeing that result (it is not part of the pre-registration and never changes its verdicts). It reduces the crosstalk
in two steps, both fixed by a deterministic rule written here:

  1. **Mask.** The pixels that hold the same value in all five QR (finder patterns, timing, format bits...) carry no
     information to tell the QR apart; they are removed and refilled afterwards from that common template. The
     network stores only the N' varying pixels (MASK_RULE).
  2. **Subset.** Of the ten triples of QR, the one with the smallest maximum |normalised dot product| between pairs
     over the full 1369 pixels (mean |dot| as the tie break, then the lowest indices) is kept (SUBSET_RULE).

Hebb runs on the C core (the same `neuron/build/neuron`, rule "hebb", synchronous update) over the frozen noise
grid, trials and seeds of hopfield_qr_select; the noise flips k = lround(level * N') of the N' stored pixels. Every
run is checked by analysis/hopfield.check_recall. A Hamming 1-NN baseline runs on the same masked patterns. An
ablation runs the four combinations (full or masked, 5 QR or the triple) at noise 0 only, to show which step is
needed for the stored patterns to be fixed points.

Like analysis/hopfield_qr_limits.py, it refuses to run unless hopfield_qr_select.rule_identity accepts the protocol
commit (the five PNGs and scripts/qr.py unchanged), and records its own code identity in run.json.

Writes under analysis/results/hopfield/qr_masked/ (not versioned):
  - selection.json: the mask (size, indices), the ranking of the ten triples and the chosen one.
  - masked_all.csv, masked_subset.csv: the five QR and the chosen triple on the N' varying pixels (network input).
  - overlaps.json: the normalised dot products of the chosen triple on the N' pixels.
  - ablation.json: stored patterns that are fixed points of Hebb, for the four combinations (C core, noise 0).
  - recall.csv, recovery_table.csv, energy_trace.csv: like analysis/hopfield_qr.py, rules "hebb" and "hamming".
  - run.json: rule identity of the protocol, code identity, design and run counts.

numpy and the standard library only.
"""

from __future__ import annotations

import argparse
import itertools
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import hopfield  # noqa: E402
import hopfield_qr  # noqa: E402
import hopfield_qr_select  # noqa: E402
import qr  # noqa: E402
import sweep  # noqa: E402

RESULTS_SUBDIR = Path("hopfield") / "qr_masked"
MASKED_CODE_FILES = ("analysis/hopfield_qr_masked.py", "analysis/hopfield_qr.py", "analysis/hopfield.py",
                     "neuron/models/hopfield.c", "neuron/models/hopfield_core.c", "neuron/models/hopfield_core.h",
                     "neuron/io/config.c")
SUBSET_SIZE = 3
MASK_RULE = "pixels that are not identical in all five QR (the common ones are refilled from the template)"
SUBSET_RULE = ("the triple with the smallest max |normalised dot product| between pairs over the full 1369 pixels; "
               "ties broken by the mean |dot|, then by the lowest indices")
RECOVERY_TABLE_COLUMNS = ["level", "hebb", "hamming"]
ABLATION = (  # (key, masked, uses the chosen triple)
    ("full_all", False, False),
    ("masked_all", True, False),
    ("full_subset", False, True),
    ("masked_subset", True, True),
)


# ---------- the mask and the subset, fixed by rule ----------

def varying_mask(P) -> np.ndarray:
    """Boolean mask of the pixels that do not hold the same value in every pattern (MASK_RULE)."""
    P = np.asarray(P, dtype=np.int64)
    return ~np.all(P == P[0], axis=0)


def _pair_overlaps(P, rows) -> list[float]:
    P = np.asarray(P, dtype=np.int64)
    n = P.shape[1]
    return [abs(float(P[a] @ P[b])) / n for a, b in itertools.combinations(rows, 2)]


def rank_subsets(P, size: int = SUBSET_SIZE) -> list[dict]:
    """Every `size`-subset of the patterns with its max and mean |normalised dot| (full pixels), best first."""
    ranked = []
    for rows in itertools.combinations(range(np.asarray(P).shape[0]), size):
        pairs = _pair_overlaps(P, rows)
        ranked.append({"subset": list(rows), "max_abs_overlap": max(pairs), "mean_abs_overlap": sum(pairs) / len(pairs)})
    ranked.sort(key=lambda item: (round(item["max_abs_overlap"], 12), round(item["mean_abs_overlap"], 12),
                                  item["subset"]))
    return ranked


def reconstruct(masked_state, mask, template) -> np.ndarray:
    """A full QR from a state on the varying pixels: the common pixels come from the template."""
    full = np.asarray(template, dtype=np.int64).copy()
    full[np.asarray(mask, dtype=bool)] = np.asarray(masked_state, dtype=np.int64)
    return full


def selection_json(P) -> dict:
    P = np.asarray(P, dtype=np.int64)
    mask = varying_mask(P)
    ranked = rank_subsets(P)
    chosen = ranked[0]["subset"]
    masked = P[:, mask]
    labels = [name.removesuffix("_menu_qr.png") for name in qr.SOURCES]
    for item in ranked:
        item["names"] = [labels[i] for i in item["subset"]]
        masked_pairs = _pair_overlaps(masked, item["subset"])
        item["masked_max_abs_overlap"] = max(masked_pairs)
        item["masked_mean_abs_overlap"] = sum(masked_pairs) / len(masked_pairs)
    rebuilt = all(np.array_equal(reconstruct(masked[a], mask, P[0]), P[a]) for a in range(P.shape[0]))
    return {
        "mask_rule": MASK_RULE, "subset_rule": SUBSET_RULE,
        "n_pixels": int(P.shape[1]), "n_varying": int(mask.sum()), "n_common": int((~mask).sum()),
        "varying_indices": np.flatnonzero(mask).tolist(),
        "chosen": chosen, "chosen_names": [labels[i] for i in chosen],
        "masked_all_mean_abs_overlap": float(np.mean(_pair_overlaps(masked, range(P.shape[0])))),
        "masked_all_max_abs_overlap": float(max(_pair_overlaps(masked, range(P.shape[0])))),
        "reconstruction_exact": bool(rebuilt),
        "ranking": ranked,
    }


def write_patterns(path: Path, P) -> None:
    P = np.asarray(P, dtype=np.int64)
    with Path(path).open("w", encoding="utf-8", newline="") as file:
        file.write(",".join(f"p{j}" for j in range(P.shape[1])) + "\n")
        for row in P:
            file.write(",".join(str(int(v)) for v in row) + "\n")


# ---------- the runs ----------

def _design(patterns_path: Path, subset, noise_levels=None, trials=None, seeds=None, trace_trials=None):
    base = hopfield_qr.default_design()
    return replace(base, patterns_path=Path(patterns_path), meta_path=Path(patterns_path),
                   subset=tuple(subset),
                   noise_levels=tuple(base.noise_levels if noise_levels is None else noise_levels),
                   trials=base.trials if trials is None else trials,
                   seeds=tuple(base.seeds if seeds is None else seeds),
                   trace_trials=base.trace_trials if trace_trials is None else trace_trials)


def _series(name: str, design, out: Path) -> sweep.Series:
    base = hopfield_qr._recall_base(design, "hebb")
    return hopfield_qr._make_series(name, out, base, [sweep.Variant("hebb", {})], design.seeds)


def ablation_json(out: Path, paths: dict, chosen, workers=None) -> dict:
    """Stored patterns that are fixed points of Hebb (C core, metrics stored_fixed), noise 0, one seed."""
    result = {}
    for key, masked, use_subset in ABLATION:
        path = paths["masked_all"] if masked else paths["full"]
        subset = chosen if use_subset else range(5)
        design = _design(path, subset, noise_levels=(0.0,), trials=1, seeds=(1,), trace_trials=0)
        patterns = hopfield.load_patterns(path)
        ran = hopfield_qr.run_series(_series(f"ablation_{key}", design, out), out, patterns, workers)
        result[key] = {"masked": masked, "subset": list(subset), "n_pixels": int(patterns.shape[1]),
                       "n_patterns": len(list(subset)), "stored_fixed": hopfield_qr.stored_fixed_for(ran),
                       "recall_rate_noise0": hopfield_qr.aggregate_recall(design, ran)[0]["recall_rate"]}
    return result


def run(results_dir=sweep.RESULTS_DIR, repo_dir=TP_DIR, check_rule: bool = True, patterns_path=None,
        workers=None) -> Path:
    results_dir = Path(results_dir)
    identity = dict.fromkeys(("rule_commit", "rule_sha256", "select_sha256", "qr_sha256", "png_sha256"))
    if check_rule:
        identity = hopfield_qr_select.rule_identity(repo_dir)
        hopfield_qr._check_prepared_qr(hopfield_qr.default_design(), identity, Path(repo_dir))
    full_path = Path(patterns_path) if patterns_path is not None else qr.PREPARED_CSV
    P = hopfield.load_patterns(full_path)

    out = results_dir / RESULTS_SUBDIR
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    try:
        selection = selection_json(P)
        hopfield_qr._write_json(out / "selection.json", selection)
        mask = np.zeros(P.shape[1], dtype=bool)
        mask[selection["varying_indices"]] = True
        chosen = selection["chosen"]
        masked_all, masked_subset = P[:, mask], P[chosen][:, mask]
        write_patterns(out / "masked_all.csv", masked_all)
        write_patterns(out / "masked_subset.csv", masked_subset)
        hopfield_qr._write_json(out / "overlaps.json", hopfield_qr.overlaps_json(masked_subset))

        ablation = ablation_json(out, {"full": full_path, "masked_all": out / "masked_all.csv"}, chosen, workers)
        hopfield_qr._write_json(out / "ablation.json", ablation)

        design = _design(out / "masked_subset.csv", range(len(chosen)))
        ran = hopfield_qr.run_series(_series("recall_hebb", design, out), out, masked_subset, workers)
        rows = hopfield_qr.aggregate_recall(design, ran, rule="hebb") + hopfield_qr.hamming_rows(design, masked_subset)
        hopfield_qr._write_csv(out / "recall.csv", hopfield_qr.RECALL_COLUMNS, rows)
        by_key = {(r["rule"], round(r["noise"], 10)): r["recall_rate"] for r in rows}
        table = [{"level": float(level), "hebb": by_key[("hebb", round(float(level), 10))],
                  "hamming": by_key[("hamming", round(float(level), 10))]} for level in design.noise_levels]
        hopfield_qr._write_csv(out / "recovery_table.csv", RECOVERY_TABLE_COLUMNS, table)
        energy = hopfield_qr.energy_trace_rows(ran, "hebb")
        for row in energy:  # the source column names the QR by its row in qr_pm1.csv, not in the triple
            row["source"] = chosen[row["source"]]
        hopfield_qr._write_csv(out / "energy_trace.csv", hopfield_qr.ENERGY_TRACE_COLUMNS, energy)

        hopfield_qr._write_json(out / "run.json", {
            **identity, "code_identity": code_identity(repo_dir),
            "design": {"noise_levels": list(design.noise_levels), "trials": design.trials,
                       "seeds": list(design.seeds), "max_sweeps": design.max_sweeps, "subset": chosen,
                       "n_pixels": int(mask.sum())},
            "runs": {"recall_hebb": len(ran), "ablation": len(ABLATION)},
            "cross_checked_trials": sum(item.checked["trials"] for item in ran),
        })
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise
    print(f"hopfield-qr-masked -> {hopfield_qr._relative(out, results_dir)}")
    return out


# ---------- identity of this experiment's code ----------

def code_identity(repo_dir=TP_DIR) -> dict:
    repo_dir = Path(repo_dir)
    status = hopfield_qr._git_text(["status", "--porcelain", "--untracked-files=all", "--", *MASKED_CODE_FILES],
                                   repo_dir)
    return {"head": hopfield_qr._git_text(["rev-parse", "HEAD"], repo_dir),
            "dirty": None if status is None else bool(status),
            "files": code_file_hashes(repo_dir)}


def code_file_hashes(repo_dir=TP_DIR) -> dict:
    try:
        return {name: hopfield_qr._sha256_file(Path(repo_dir) / name) for name in MASKED_CODE_FILES}
    except OSError as error:
        raise SystemExit(f"cannot hash the masked experiment's code: {error}") from None


def changed_code_files(recorded: dict, repo_dir=TP_DIR) -> list[str]:
    files = recorded.get("files") if isinstance(recorded, dict) else None
    if not isinstance(files, dict):
        return list(MASKED_CODE_FILES)
    current = code_file_hashes(repo_dir)
    return [name for name in MASKED_CODE_FILES if files.get(name) != current[name]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workers", type=int, help="parallel runs (default: every core)")
    args = parser.parse_args(argv)
    run(workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
