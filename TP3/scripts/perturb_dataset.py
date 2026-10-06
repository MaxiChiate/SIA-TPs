"""Perturbs the inputs of a prepared CSV and leaves its outputs alone (stdlib only).

Works on any dataset the network reads: the input columns are every column but the zeta* ones at the end
(none: just the last one), as io/dataset.c reads them. For the Exercises 2 and 3 optionals it adds noise to the
generalization images; nothing here knows they are images.

    python3 scripts/perturb_dataset.py data/digits_test_prepared.csv data/digits_test_g0.2_s1.csv --gaussian 0.2 --seed 1 --clip 0 1

--gaussian σ adds N(0, σ²) to every input. With the same --seed every σ draws the same standard normals, so two
noise levels of one seed are the same noise scaled: the accuracy-vs-σ curve of a seed doesn't jump from one
pattern to another. --clip MIN MAX then clamps the inputs to the range real samples live in (pixels: 0 1).
Other perturbations (salt and pepper, occluding a block) go next to gaussian() without touching the rest.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

NEURON_DIR = Path(__file__).resolve().parent.parent / "neuron"

Perturbation = Callable[[list[float]], list[float]]


@dataclass(frozen=True)
class Table:
    header: list[str]
    n_inputs: int
    rows: list[list[str]]


def n_input_columns(header: list[str]) -> int:
    n_outputs = 0
    while n_outputs < len(header) and header[len(header) - 1 - n_outputs].startswith("zeta"):
        n_outputs += 1
    return len(header) - max(n_outputs, 1)


def load(path: Path) -> Table:
    with path.open(newline="") as file:
        reader = csv.reader(file)
        header = next(reader)
        return Table(header, n_input_columns(header), list(reader))


def gaussian(sigma: float, rng: random.Random) -> Perturbation:
    return lambda inputs: [x + sigma * rng.gauss(0.0, 1.0) for x in inputs]


def clip(low: float, high: float) -> Perturbation:
    return lambda inputs: [min(high, max(low, x)) for x in inputs]


def perturbed(table: Table, perturbations: list[Perturbation]) -> list[list[str]]:
    """Rows in the same order; outputs kept as written. repr keeps a float exact, so σ 0 changes nothing."""
    out = []
    for row in table.rows:
        inputs = [float(value) for value in row[:table.n_inputs]]
        for perturbation in perturbations:
            inputs = perturbation(inputs)
        out.append([repr(x) for x in inputs] + row[table.n_inputs:])
    return out


def write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def perturb(table: Table, out: Path, seed: int, sigma: float = 0.0, clip_range: tuple[float, float] | None = None) -> None:
    """One perturbed copy of table; robustness.py calls this once per (σ, seed)."""
    rng = random.Random(seed)
    perturbations = [gaussian(sigma, rng)] if sigma > 0 else []
    if clip_range is not None:
        perturbations.append(clip(*clip_range))
    write(out, table.header, perturbed(table, perturbations))


def resolve(name: str) -> Path:
    """As given if it exists, else relative to neuron/ (where data/ lives)."""
    path = Path(name)
    return path if path.exists() or path.is_absolute() else NEURON_DIR / name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", help="prepared CSV; relative paths also resolve from neuron/")
    parser.add_argument("out", help="perturbed CSV; relative paths also resolve from neuron/")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--gaussian", type=float, default=0.0, metavar="SIGMA", help="standard deviation of the noise added to every input")
    parser.add_argument("--clip", type=float, nargs=2, metavar=("MIN", "MAX"), help="clamp the inputs after the noise")
    args = parser.parse_args()
    if args.gaussian < 0:
        parser.error("--gaussian can't be negative")
    out = Path(args.out) if Path(args.out).is_absolute() or Path(args.out).parent.exists() else NEURON_DIR / args.out
    perturb(load(resolve(args.dataset)), out, args.seed, args.gaussian, tuple(args.clip) if args.clip else None)
    print(out)


if __name__ == "__main__":
    main()
