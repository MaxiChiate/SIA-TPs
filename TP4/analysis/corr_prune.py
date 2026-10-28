"""Sensitivity of the PCA to pruning correlated variables by a threshold on |r| (a team decision, not course theory).

Run from TP4/ with `make corr-prune` (or `.venv/bin/python analysis/corr_prune.py`). It starts from the 26
audited variables (datos/prepared/creadores_zscore.csv, the same file pca.py reads) and, for each threshold tau,
prunes iteratively: take the pair with the largest |r| >= tau and drop the variable of that pair with the larger
mean |r| against the variables still in the set (a tie drops the one with the larger column index). It repeats until
no pair reaches tau. Then it runs the same PCA as pca.py on what is left.

Only the sensitivity table is produced: SOM, Oja and the campaigns are not rerun with any tau. Writes
analysis/results/corr_prune/sensitivity.csv and sensitivity.json (not versioned).

numpy only (D-06).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

from pca import k_by_variance, pca_eigh, read_prepared  # noqa: E402

DEFAULT_OUT_DIR = TP_DIR / "analysis" / "results" / "corr_prune"
THRESHOLDS = (0.95, 0.90, 0.85, 0.80, 0.70, 0.60, 0.50)
PREPARED_STEM = "creadores_zscore"


def prune(z: np.ndarray, threshold: float) -> tuple[list[int], list[dict]]:
    """Indices of the columns that stay and, in order, the drops (dropped, partner, |r| of the pair)."""
    keep = list(range(z.shape[1]))
    drops: list[dict] = []
    while len(keep) > 1:
        corr = np.abs(np.corrcoef(z[:, keep], rowvar=False))
        np.fill_diagonal(corr, 0.0)
        flat = int(np.argmax(corr))
        i, j = divmod(flat, len(keep))
        if corr[i, j] < threshold:
            break
        # i < j on the first hit of argmax over the upper-left scan only when corr is symmetric; fix the order
        i, j = min(i, j), max(i, j)
        mean_i = corr[i].sum() / (len(keep) - 1)
        mean_j = corr[j].sum() / (len(keep) - 1)
        out, partner = (i, j) if mean_i > mean_j else (j, i)
        drops.append({"dropped": keep[out], "partner": keep[partner], "abs_r": float(corr[i, j])})
        keep.pop(out)
    return keep, drops


def sensitivity(z: np.ndarray, features: list[str], thresholds=THRESHOLDS) -> list[dict]:
    rows = []
    for tau in thresholds:
        keep, drops = prune(z, tau)
        names = [features[k] for k in keep]
        result = pca_eigh(z[:, keep], names)
        eigenvalues = result.eigenvalues
        rows.append(
            {
                "tau": tau,
                "n_kept": len(keep),
                "kept": names,
                "dropped": [
                    {"dropped": features[d["dropped"]], "partner": features[d["partner"]], "abs_r": d["abs_r"]}
                    for d in drops
                ],
                "k_80": k_by_variance(result),
                "explained_pc1": float(result.explained[0]),
                "min_eigenvalue": float(eigenvalues[-1]),
                "condition_number": float(eigenvalues[0] / eigenvalues[-1]),
            }
        )
    return rows


def write_outputs(out: Path, rows: list[dict], n_audited: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "sensitivity.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["tau", "n_kept", "k_80", "explained_pc1", "min_eigenvalue", "condition_number"])
        for row in rows:
            writer.writerow(
                [
                    repr(row["tau"]), row["n_kept"], row["k_80"], repr(row["explained_pc1"]),
                    repr(row["min_eigenvalue"]), repr(row["condition_number"]),
                ]
            )
    payload = {"n_audited": n_audited, "rule": "iterative, drop the larger mean |r| of the most correlated pair", "rows": rows}
    (out / "sensitivity.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    features, z, _meta = read_prepared(PREPARED_STEM)
    rows = sensitivity(z, features)
    write_outputs(args.out, rows, len(features))
    for row in rows:
        print(
            f"tau {row['tau']:.2f}: {row['n_kept']:2d} variables, k80 {row['k_80']}, "
            f"PC1 {row['explained_pc1']:.1%}, lambda_min {row['min_eigenvalue']:.4f}, "
            f"cond {row['condition_number']:.0f}"
        )
    print(f"corr_prune -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
