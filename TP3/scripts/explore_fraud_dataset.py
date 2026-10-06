"""Exploratory analysis of the raw fraud dataset (stdlib only). Prints a plain-text report.

Covers what the statement asks before modelling: column ranges, composition, cleanliness, how
the BigModel probability is distributed, and which columns relate to it.
flagged_fraud is read only to describe the data; it is never a model input.
"""

from __future__ import annotations

import csv
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "neuron" / "data" / "fraud_dataset.csv"

TARGET = "big_model_fraud_probability"
LABEL = "flagged_fraud"
QUANTILES = [0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99]


@dataclass(frozen=True)
class Dataset:
    header: list[str]
    rows: list[list[float]]

    def column(self, name: str) -> list[float]:
        index = self.header.index(name)
        return [row[index] for row in self.rows]

    @property
    def inputs(self) -> list[str]:
        return [name for name in self.header if name not in (TARGET, LABEL)]


def load(path: Path) -> tuple[Dataset, int]:
    """Returns the parsed dataset and the count of cells that were empty or not numeric."""
    bad_cells = 0
    rows: list[list[float]] = []
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        for raw in reader:
            row: list[float] = []
            for cell in raw:
                try:
                    row.append(float(cell))
                except ValueError:
                    row.append(float("nan"))
                    bad_cells += 1
            rows.append(row)
    return Dataset(header, rows), bad_cells


def quantile(sorted_values: list[float], q: float) -> float:
    position = q * (len(sorted_values) - 1)
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2
        i = j + 1
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float:
    return statistics.correlation(xs, ys)


def spearman(xs: list[float], ys: list[float]) -> float:
    return statistics.correlation(rank(xs), rank(ys))


def outliers_iqr(values: list[float]) -> int:
    ordered = sorted(values)
    q1, q3 = quantile(ordered, 0.25), quantile(ordered, 0.75)
    fence = 1.5 * (q3 - q1)
    return sum(1 for v in values if v < q1 - fence or v > q3 + fence)


def print_columns(data: Dataset) -> None:
    print("\n== Columnas (rango, centro, dispersión, outliers por IQR 1.5x)")
    print(f"{'columna':32}{'min':>14}{'p50':>14}{'media':>14}{'std':>14}{'max':>14}{'distintos':>10}{'outl.':>7}")
    for name in data.header:
        values = data.column(name)
        ordered = sorted(values)
        print(
            f"{name:32}{ordered[0]:14.4g}{quantile(ordered, 0.5):14.4g}{statistics.fmean(values):14.4g}"
            f"{statistics.pstdev(values):14.4g}{ordered[-1]:14.4g}{len(set(values)):10d}{outliers_iqr(values):7d}"
        )


def print_cleanliness(data: Dataset, bad_cells: int) -> None:
    duplicates = len(data.rows) - len({tuple(row) for row in data.rows})
    without_target = len({tuple(r[:-2] + r[-1:]) for r in data.rows})
    print(f"\n== Limpieza\nfilas: {len(data.rows)}  celdas vacías o no numéricas: {bad_cells}  filas duplicadas: {duplicates}")
    print(f"filas distintas ignorando la probabilidad de BigModel: {without_target}")
    for name in ("amount_usd", "quantity_purchased", "session_duration_seconds", "days_since_last_purchase",
                 "time_since_last_login_s", "account_age_days", "items_viewed_before_purchase"):
        values = data.column(name)
        print(f"{name:32} negativos: {sum(v < 0 for v in values):5d}  ceros: {sum(v == 0 for v in values):5d}")
    target = data.column(TARGET)
    print(f"{TARGET} fuera de [0, 1]: {sum(v < 0 or v > 1 for v in target)}")


def print_composition(data: Dataset) -> None:
    labels = data.column(LABEL)
    fraud = sum(labels)
    stamps = data.column("timestamp")
    low, high = (datetime.fromtimestamp(int(f(stamps)), timezone.utc) for f in (min, max))
    print(f"\n== Composición\n{LABEL}=1: {int(fraud)} de {len(labels)} ({100 * fraud / len(labels):.2f} %)")
    print(f"timestamp: de {low:%Y-%m-%d} a {high:%Y-%m-%d}")
    resolutions = Counter(int(v) for v in data.column("device_screen_resolution"))
    print(f"device_screen_resolution: {len(resolutions)} valores distintos, los más comunes:")
    for value, count in resolutions.most_common(6):
        print(f"  {value:>10d} px  {count:5d} filas")
    quantities = Counter(int(v) for v in data.column("quantity_purchased"))
    print(f"quantity_purchased: {dict(sorted(quantities.items()))}")


def print_target(data: Dataset) -> None:
    target = data.column(TARGET)
    ordered = sorted(target)
    print(f"\n== {TARGET}")
    print("cuantiles: " + "  ".join(f"p{int(q * 100)}={quantile(ordered, q):.4f}" for q in QUANTILES))
    bins = Counter(min(int(v * 10), 9) for v in target)
    for b in range(10):
        bar = "#" * round(60 * bins[b] / len(target))
        print(f"  [{b / 10:.1f}, {(b + 1) / 10:.1f}) {bins[b]:5d} {bar}")
    labels = data.column(LABEL)
    for flag in (0, 1):
        subset = [t for t, l in zip(target, labels) if l == flag]
        if subset:
            print(f"con {LABEL}={flag}: n={len(subset)}  media={statistics.fmean(subset):.4f}  mediana={statistics.median(subset):.4f}")
    print("\numbral -> filas por encima / de ellas con flagged_fraud=1")
    for threshold in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        above = [l for t, l in zip(target, labels) if t >= threshold]
        print(f"  {threshold:.1f}: {len(above):5d} / {int(sum(above)):5d}")


def print_relations(data: Dataset) -> None:
    target, labels = data.column(TARGET), data.column(LABEL)
    print("\n== Relación de cada entrada con la probabilidad de BigModel y con flagged_fraud")
    print(f"{'columna':32}{'pearson':>10}{'spearman':>10}{'pearson/flag':>14}")
    for name in data.inputs:
        values = data.column(name)
        print(f"{name:32}{pearson(values, target):10.3f}{spearman(values, target):10.3f}{pearson(values, labels):14.3f}")
    print("\ncorrelación entre entradas con |r| > 0.5:")
    names, found = data.inputs, False
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            r = pearson(data.column(a), data.column(b))
            if abs(r) > 0.5:
                found = True
                print(f"  {a} ~ {b}: {r:.3f}")
    if not found:
        print("  ninguna")


def main() -> None:
    data, bad_cells = load(DATA_PATH)
    print(f"{DATA_PATH.name}: {len(data.rows)} filas x {len(data.header)} columnas")
    print_cleanliness(data, bad_cells)
    print_columns(data)
    print_composition(data)
    print_target(data)
    print_relations(data)


if __name__ == "__main__":
    main()
