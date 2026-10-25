#!/usr/bin/env python3
"""The only place where a result number becomes text of the informe (D-11).

    .venv/bin/python analysis/facts.py dump [--results DIR]

Every number that a generated sentence shows is read from analysis/results/** here and formatted once, with
the Spanish decimal comma: `dec`, `pct` and `integer` are the only formatters (they consolidate the helpers
that analysis/campaigns.py kept for its own report lines). `load_facts` returns flat display strings keyed
`group.name`; `fill` replaces the `{group.name}` tokens of a template with them (or with whatever the `wrap`
callback returns, which is how informe.py marks each number as a `data-fact` span). A missing result file or
an unknown key stops the build with the make command to run, never a blank number. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Callable

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

RESULTS_DIR = TP_DIR / "analysis" / "results"

# source name -> (path relative to the results directory, make step that writes it)
SOURCES: dict[str, tuple[str, str]] = {
    "som.contrast": ("som/profiles/pca_contrast.json", "som-profiles"),
    "som.selection": ("som/series_som_stage1/selection.json", "som-stage1"),
    "som.robustness": ("som/series_som_stage2/robustness.json", "som-stage2"),
}

TOKEN = re.compile(r"\{([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)\}")


# ---------- formatters ----------

def dec(value: float, digits: int) -> str:
    """Spanish decimals: comma instead of point; NaN is written n/d."""
    value = float(value)
    if math.isnan(value):
        return "n/d"
    return f"{value:.{digits}f}".replace(".", ",")


def pct(fraction: float, digits: int = 0) -> str:
    """A fraction as a percentage the way the fragments write it: number, one space, percent sign."""
    fraction = float(fraction)
    if math.isnan(fraction):
        return "n/d"
    return f"{dec(fraction * 100.0, digits)} %"


def integer(value: float) -> str:
    value = float(value)
    if math.isnan(value):
        return "n/d"
    return str(int(round(value)))


# ---------- sources ----------

def read_source(results_dir: Path, name: str) -> dict:
    """Load one JSON source; a missing file stops with the make command that writes it."""
    relative, step = SOURCES[name]
    path = Path(results_dir) / relative
    if not path.is_file():
        raise SystemExit(f"{path} not found; run `make results` (step {step})")
    return json.loads(path.read_text(encoding="utf-8"))


def load_facts(results_dir: Path = RESULTS_DIR) -> dict[str, str]:
    """Flat display strings of every fact the generated text may quote."""
    contrast = read_source(results_dir, "som.contrast")
    selection = read_source(results_dir, "som.selection")
    robustness = read_source(results_dir, "som.robustness")
    return {
        "som.r2_pc1": dec(contrast["r2_pc1"], 3),
        "som.p_r2_pc1": dec(contrast["p_r2_pc1"], 3),
        "som.r2_pc2": dec(contrast["r2_pc2"], 3),
        "som.p_r2_pc2": dec(contrast["p_r2_pc2"], 3),
        "som.chosen_k": integer(selection["chosen_k"]),
        "som.n_regions": integer(contrast["n_regions"]),
        "som.n_permutations": integer(contrast["n_permutations"]),
        "som.robust": "sí" if robustness["robust"] else "no",
    }


def fill(template: str, facts: dict[str, str], wrap: Callable[[str, str], str] | None = None) -> str:
    """Replace every {group.key} token by its value (or by wrap(key, value)); an unknown key stops the build."""

    def replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in facts:
            raise SystemExit(f"unknown fact key {key!r}; add it to facts.load_facts")
        value = facts[key]
        return wrap(key, value) if wrap is not None else value

    return TOKEN.sub(replace, template)


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    dump = sub.add_parser("dump", help="print the facts as sorted JSON")
    dump.add_argument("--results", type=Path, default=RESULTS_DIR)
    args = parser.parse_args(argv)
    if args.command == "dump":
        print(json.dumps(load_facts(args.results), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
