"""Loader, variable audit and saved scaler of datos/creadores.csv (DATA-01, DATA-02, DATA-03).

Library only, no side effects on import. No dataframe library (D-06): `csv` parses and numpy does
the arithmetic. The audit rule (D-08, D-09) removes the 5 exact linear dependencies; the z-score is
direct, ddof = 1, with no log and no winsorizing (D-11). Written files hold no timestamp and no
absolute path, so a rerun reproduces them byte for byte (D-04).
"""

from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = TP_DIR / "datos" / "creadores.csv"
PREPARED_DIR = TP_DIR / "datos" / "prepared"

EXPECTED_ROWS = 50
EXPECTED_COLUMNS = 33
ID_COLUMNS = ("creator_id", "name")
COMPOSITION_PREFIXES = ("topic_", "content_")
EXACT_TOLERANCE = 1e-6

# Variables that are an exact function of another one (D-09): name -> (reason, reconstruct).
FIXED_DROPS = {
    "price_ars": ("dependencia lineal exacta con price_usd", "price_ars = 1500 * price_usd"),
    "organic_posts_pct": (
        "dependencia lineal exacta con sponsored_posts_pct",
        "organic_posts_pct = 100 - sponsored_posts_pct",
    ),
    "total_engagement_per_1000": (
        "dependencia lineal exacta: suma de las cuatro interacciones por mil",
        "total_engagement_per_1000 = likes_per_1000 + comments_per_1000"
        " + saves_per_1000 + shares_per_1000",
    ),
}

COMPOSITION_REASON = "composición que suma 100: menor varianza del grupo"
COMPOSITION_RECONSTRUCT = "100 - (suma de los otros tres)"

AUDITED_NOTE = (
    "Conjunto auditado: 31 variables menos las 5 dependencias lineales exactas (D-08, D-09)"
)
ALL31_NOTE = (
    "SENSIBILIDAD (DATA-05): las 31 columnas con z-score; incluye las 5 dependencias exactas, "
    "la matriz de correlación es singular (rango 26). No es el conjunto auditado."
)


@dataclass(frozen=True)
class Creadores:
    ids: list[str]
    names: list[str]
    columns: list[str]
    values: np.ndarray  # float64, shape (rows, len(columns))


@dataclass(frozen=True)
class DroppedVariable:
    name: str
    reason: str
    reconstruct: str


@dataclass(frozen=True)
class Audit:
    kept: list[str]
    dropped: list[DroppedVariable]


@dataclass(frozen=True)
class Scaler:
    features: list[str]
    mean: np.ndarray
    std: np.ndarray
    ddof: int = 1


def load_creadores(
    path: Path = RAW_PATH,
    expected_rows: int = EXPECTED_ROWS,
    expected_columns: int = EXPECTED_COLUMNS,
) -> Creadores:
    """Read the creators CSV and check it is exactly expected_rows x expected_columns."""
    with Path(path).open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    if not rows:
        raise ValueError(f"{path}: empty file")

    header = rows[0]
    data_rows = rows[1:]
    if len(data_rows) != expected_rows or len(header) != expected_columns:
        raise ValueError(
            f"{path}: expected {expected_rows} rows x {expected_columns} columns, "
            f"found {len(data_rows)} rows x {len(header)} columns"
        )
    if tuple(header[: len(ID_COLUMNS)]) != ID_COLUMNS:
        raise ValueError(f"{path}: the first columns must be {ID_COLUMNS}, found {header[:2]}")

    columns = header[len(ID_COLUMNS) :]
    ids: list[str] = []
    names: list[str] = []
    values = np.empty((len(data_rows), len(columns)), dtype=np.float64)
    for index, row in enumerate(data_rows):
        line_number = index + 2  # the header is line 1
        if len(row) != expected_columns:
            raise ValueError(
                f"{path}: line {line_number} has {len(row)} fields, expected {expected_columns}"
            )
        ids.append(row[0])
        names.append(row[1])
        for j, cell in enumerate(row[len(ID_COLUMNS) :]):
            try:
                number = float(cell)
            except ValueError:
                number = math.nan
            if not math.isfinite(number):
                raise ValueError(
                    f"{path}: line {line_number}, column {columns[j]!r}: "
                    f"not a finite number: {cell!r}"
                )
            values[index, j] = number
    return Creadores(ids=ids, names=names, columns=columns, values=values)


def _column(data: Creadores, name: str) -> np.ndarray:
    if name not in data.columns:
        raise ValueError(f"column {name!r} not found in creadores data")
    return data.values[:, data.columns.index(name)]


def _group(data: Creadores, prefix: str) -> list[str]:
    return [c for c in data.columns if c.startswith(prefix)]


def dependency_residuals(data: Creadores) -> dict[str, float]:
    """Max absolute residual of each of the 5 exact relations (D-08)."""
    col = lambda name: _column(data, name)  # noqa: E731
    engagement = sum(
        col(f"{kind}_per_1000") for kind in ("likes", "comments", "saves", "shares")
    )
    topics = sum(col(name) for name in _group(data, "topic_"))
    contents = sum(col(name) for name in _group(data, "content_"))
    return {
        "price_ars": float(np.max(np.abs(col("price_ars") - 1500.0 * col("price_usd")))),
        "organic_posts_pct": float(
            np.max(np.abs(col("organic_posts_pct") + col("sponsored_posts_pct") - 100.0))
        ),
        "total_engagement_per_1000": float(
            np.max(np.abs(col("total_engagement_per_1000") - engagement))
        ),
        "topic_sum_100": float(np.max(np.abs(topics - 100.0))),
        "content_sum_100": float(np.max(np.abs(contents - 100.0))),
    }


def audit_variables(data: Creadores) -> Audit:
    """Choose the variables that enter PCA, SOM and Oja (D-08, D-09, D-10).

    Drops price_ars, organic_posts_pct, total_engagement_per_1000 and, in each composition group
    (topic_*, content_*), the member with the lowest sample variance in original units. Near
    redundant variables are kept. Stops if any of the 5 dependencies stops being exact.
    """
    for relation, residual in dependency_residuals(data).items():
        if residual > EXACT_TOLERANCE:
            raise ValueError(
                f"dependency {relation} is no longer exact: max residual {residual:.3g} "
                f"> {EXACT_TOLERANCE:g}; the audit rule assumes exact dependencies"
            )

    dropped = [
        DroppedVariable(name, reason, reconstruct)
        for name, (reason, reconstruct) in FIXED_DROPS.items()
    ]
    for prefix in COMPOSITION_PREFIXES:
        members = _group(data, prefix)
        variances = [float(np.var(_column(data, name), ddof=1)) for name in members]
        lowest = members[int(np.argmin(variances))]
        dropped.append(DroppedVariable(lowest, COMPOSITION_REASON, COMPOSITION_RECONSTRUCT))

    dropped_names = {d.name for d in dropped}
    kept = [c for c in data.columns if c not in dropped_names]
    return Audit(kept=kept, dropped=dropped)


def fit_scaler(data: Creadores, features: list[str]) -> Scaler:
    """Mean and sample std (ddof = 1) of the given features, in original units (D-11)."""
    columns = np.column_stack([_column(data, name) for name in features])
    mean = columns.mean(axis=0)
    std = columns.std(axis=0, ddof=1)
    zero = [name for name, s in zip(features, std) if s == 0.0]
    if zero:
        raise ValueError(f"zero standard deviation, cannot z-score: {zero}")
    return Scaler(features=list(features), mean=mean, std=std, ddof=1)


def transform(scaler: Scaler, values: np.ndarray) -> np.ndarray:
    """z = (x - mean) / std for a 2-D array whose columns follow scaler.features."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != len(scaler.features):
        raise ValueError(
            f"expected a 2-D array with {len(scaler.features)} columns, got shape {values.shape}"
        )
    return (values - scaler.mean) / scaler.std


def load_meta(path: Path) -> dict:
    """Read a .meta.json written by write_prepared."""
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def _atomic_write(path: Path, text: str) -> None:
    """Write via a temporary file in the same folder, then os.replace: readers never see half."""
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", newline="", encoding="utf-8") as file:
            file.write(text)
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def zscore_csv_text(features: list[str], z: np.ndarray) -> str:
    """CSV text with repr(float) values (C strtod reads the exact double), "\\n" line ends."""
    lines = [",".join(features)]
    for row in z:
        lines.append(",".join(repr(float(v)) for v in row))
    return "\n".join(lines) + "\n"


def _relative_source(source: Path) -> str:
    try:
        return Path(source).resolve().relative_to(TP_DIR).as_posix()
    except ValueError:
        return Path(source).name


def write_prepared(
    out_dir: Path,
    stem: str,
    variant: str,
    note: str,
    data: Creadores,
    scaler: Scaler,
    dropped: list[DroppedVariable],
    source: Path = RAW_PATH,
) -> tuple[Path, Path]:
    """Write {stem}.csv (z-scored matrix) and {stem}.meta.json (scaler and provenance)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    index = [data.columns.index(name) for name in scaler.features]
    z = transform(scaler, data.values[:, index])
    meta = {
        "variant": variant,
        "note": note,
        "source": _relative_source(source),
        "n_rows": len(data.ids),
        "ddof": scaler.ddof,
        "features": list(scaler.features),
        "mean": [float(v) for v in scaler.mean],
        "std": [float(v) for v in scaler.std],
        "dropped": [
            {"name": d.name, "reason": d.reason, "reconstruct": d.reconstruct} for d in dropped
        ],
        "creator_id": list(data.ids),
        "name": list(data.names),
    }
    csv_path = out_dir / f"{stem}.csv"
    meta_path = out_dir / f"{stem}.meta.json"
    _atomic_write(csv_path, zscore_csv_text(scaler.features, z))
    _atomic_write(meta_path, json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return csv_path, meta_path


def prepare(source: Path = RAW_PATH, out_dir: Path = PREPARED_DIR) -> tuple[Audit, list[Path]]:
    """Write the audited variant and the all-31 sensitivity variant; return audit and 4 paths."""
    data = load_creadores(source)
    audit = audit_variables(data)
    audited = write_prepared(
        out_dir,
        "creadores_zscore",
        "audited",
        AUDITED_NOTE,
        data,
        fit_scaler(data, audit.kept),
        audit.dropped,
        source,
    )
    all31 = write_prepared(
        out_dir,
        "creadores_zscore_all31",
        "all31_sensitivity",
        ALL31_NOTE,
        data,
        fit_scaler(data, data.columns),
        [],
        source,
    )
    return audit, [*audited, *all31]
