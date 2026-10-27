#!/usr/bin/env python3
"""The only place where a result number becomes text of the informe (D-11).

    .venv/bin/python analysis/facts.py dump [--results DIR]
    .venv/bin/python analysis/facts.py check [--results DIR] [--deliverables DIR]

Every number that a generated sentence shows is read from analysis/results/** here and formatted once, with
the Spanish decimal comma: `dec`, `pct` and `integer` are the only formatters (they consolidate the helpers
that analysis/campaigns.py kept for its own report lines). `load_facts` returns flat display strings keyed
`group.name`; `fill` replaces the `{group.name}` tokens of a template with them (or with whatever the `wrap`
callback returns, which is how informe.py marks each number as a `data-fact` span). A missing result file or
an unknown key stops the build with the make command to run, never a blank number. `check_claims` stops it too
when a result no longer supports one of the few sentences that state a result without a number. `DRIFT_PINS` ties
the numbers that the fragments of deliverables/ carry as hand-typed text to the results (D-12):
`check_fragment_numbers` fills each pin with the facts and looks the phrase up in its fragment, and the `check`
subcommand exits 1 naming every pin that no longer matches. Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Callable

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

RESULTS_DIR = TP_DIR / "analysis" / "results"

# source name -> (path relative to the results directory, make step that writes it)
SOURCES: dict[str, tuple[str, str]] = {
    "eda.summary": ("eda/summary_stats.csv", "eda"),
    "eda.strong": ("eda/strong_correlations.csv", "eda"),
    "eda.dependencies": ("eda/exact_dependencies.csv", "eda"),
    "pca.decision": ("pca/audited/decision.json", "pca"),
    "pca.sensitivity": ("pca/sensitivity.json", "pca"),
    "pca.eigenvalues": ("pca/audited/eigenvalues.csv", "pca"),
    "som.contrast": ("som/profiles/pca_contrast.json", "som-profiles"),
    "som.selection": ("som/series_som_stage1/selection.json", "som-stage1"),
    "som.robustness": ("som/series_som_stage2/robustness.json", "som-stage2"),
    "som.robustness_table": ("som/series_som_stage2/robustness.csv", "som-stage2"),
    "som.hits": ("som/figures/hits_members.csv", "som-figures"),
    "som.high_u_edges": ("som/profiles/high_u_edges.csv", "som-profiles"),
    "som.neuron_profiles": ("som/profiles/neuron_profiles.csv", "som-profiles"),
    "som.zones": ("som/profiles/zones.csv", "som-profiles"),
    "oja.comparison": ("oja/comparison.json", "oja"),
    "oja.dispersion": ("oja/dispersion.json", "oja"),
    "oja.evidence": ("oja/evidence.json", "oja"),
    "oja.correlations": ("oja/evidence_correlations.csv", "oja"),
    "oja.index": ("oja/index.csv", "oja"),
    "camp.identity": ("campaigns/selection_identity.json", "campaigns"),
    "camp.shortlists": ("campaigns/shortlists.csv", "campaigns"),
    "camp.comparison": ("campaigns/comparison.csv", "campaigns"),
    "maint.demo": ("maintenance/demo.json", "maintenance"),
    "letters.selection": ("hopfield/letters/selection.json", "hopfield-letters"),
    "letters.orthogonality": ("hopfield/letters/orthogonality.json", "hopfield-letters"),
    "letters.capacity": ("hopfield/letters/capacity.json", "hopfield-letters"),
    "letters.capacity_by_p": ("hopfield/letters/capacity_by_p.csv", "hopfield-letters"),
    "letters.recall": ("hopfield/letters/recall.csv", "hopfield-letters"),
    "letters.spurious": ("hopfield/letters/spurious.json", "hopfield-letters"),
    "qr.verdict": ("hopfield/qr/verdict.json", "hopfield-qr"),
    "qr.facts": ("hopfield/qr/qr_facts.json", "hopfield-qr"),
    "qr.overlaps": ("hopfield/qr/overlaps.json", "hopfield-qr"),
    "qr.protocol": ("hopfield/qr/protocol.json", "hopfield-qr"),
    "qr.recovery": ("hopfield/qr/recovery_table.csv", "hopfield-qr"),
    "qr.majority": ("hopfield/qr_limits/majority.json", "hopfield-qr-limits"),
    "qr.shift": ("hopfield/qr_limits/shift.json", "hopfield-qr-limits"),
}

# The objective the informe recommends for each campaign (section 5 of deliverables/03-oja-campanas.md): the
# committed shortlist whose handles, cost and criterion the camp.<campaign>.* facts report. campaign key ->
# (name in the CSV files, objective). load_facts checks each pair against campaigns/selection_identity.json.
RECOMMENDED_OBJECTIVE: dict[str, tuple[str, str]] = {
    "futbol": ("fútbol", "profundidad"),
    "perros": ("perros", "costo_por_mil"),
    "maquillaje": ("maquillaje", "profundidad"),
    "arte": ("arte", "engagement_profundidad"),
}

# Spanish names of the final classes of a Hopfield trial (spurious.json keys).
CLASS_NAMES = {"stored": "almacenado", "inverse": "inverso", "mixture": "mezcla", "other": "otro"}

# Flipped pixels of the letter recall rates the texts quote; each letters.flips_k<n> is read from the recall row it names.
LETTER_RECALL_FLIPS = (3, 6, 9)
# The disclosure of fragment 04 (D-04b): glyphs of the alphabet that match the discarded draft. It is not a result of
# any run, so it is a constant here and a drift pin ties it to the fragment's own sentence.
DRAFT_MATCHING_GLYPHS = 25

# QR noise levels the texts name. QR_HIGH_NOISE is the level they call "ruido alto", a fixed reporting level and not
# the last level where pinv recovers anything; QR_LAST_NOISE is what the slide notes call "el último nivel", and
# load_facts stops if the recovery table ends anywhere else.
QR_REPORTED_LEVELS = (0.35, 0.40, 0.45, 0.50)
QR_HIGH_NOISE, QR_LAST_NOISE = 0.45, 0.50

# The size block of the EDA slide: the four size variables whose pairwise correlations the slide quotes.
SIZE_BLOCK = ("followers", "average_reach", "average_impressions", "average_video_views")
# The capacity reference of the course slides (3 - Modelo de Hopfield, "Limitaciones": p <= 0,15 N), quoted as an
# order of magnitude and never as a threshold (fragment 04, section 6).
COURSE_CAPACITY_RATIO = 0.15

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


def pct_short(fraction: float, digits: int = 1) -> str:
    """Like `pct`, but a whole percentage drops its decimals (0 % and 100 %, as the recovery prose writes them)."""
    fraction = float(fraction)
    if math.isnan(fraction):
        return "n/d"
    value = round(fraction * 100.0, digits)
    if value == int(value):
        return f"{int(value)} %"
    return f"{dec(value, digits)} %"


def integer(value: float) -> str:
    value = float(value)
    if math.isnan(value):
        return "n/d"
    return str(int(round(value)))


# ---------- sources ----------

def _source_path(results_dir: Path, name: str) -> Path:
    relative, step = SOURCES[name]
    path = Path(results_dir) / relative
    if not path.is_file():
        raise SystemExit(f"{path} not found; run `make results` (step {step})")
    return path


def read_source(results_dir: Path, name: str) -> dict:
    """Load one JSON source; a missing file stops with the make command that writes it."""
    return json.loads(_source_path(results_dir, name).read_text(encoding="utf-8"))


def read_csv_source(results_dir: Path, name: str) -> list[dict[str, str]]:
    """Load one CSV source as a list of dicts (csv module, no pandas); a missing file stops like read_source."""
    with _source_path(results_dir, name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _row_at(rows: list[dict[str, str]], column: str, level: float) -> dict[str, str]:
    """The CSV row whose `column` equals `level` (the noise grid is exact decimals, compared with a tolerance)."""
    for row in rows:
        if abs(float(row[column]) - level) < 1e-9:
            return row
    raise SystemExit(f"no row with {column} = {level} in the recovery table; run `make results` (step hopfield-qr)")


def _first(items: list[dict], condition: Callable[[dict], bool], what: str, step: str) -> dict:
    """The first item that meets `condition`; none stops the build with the make step to run, as `_row_at` does."""
    for item in items:
        if condition(item):
            return item
    raise SystemExit(f"no {what}; run `make results` (step {step})")


def _nonempty(values: list[float], what: str, step: str) -> list[float]:
    """`values` itself, so that max()/min() on an empty list stops with the make step instead of a ValueError."""
    if not values:
        raise SystemExit(f"no {what}; run `make results` (step {step})")
    return values


def _eda_facts(results_dir: Path) -> dict[str, str]:
    summary = read_csv_source(results_dir, "eda.summary")
    strong = read_csv_source(results_dir, "eda.strong")
    dependencies = read_csv_source(results_dir, "eda.dependencies")
    block = [abs(float(row["r"])) for row in strong
             if row["variable_a"] in SIZE_BLOCK and row["variable_b"] in SIZE_BLOCK]
    pairs = len(SIZE_BLOCK) * (len(SIZE_BLOCK) - 1) // 2
    if len(block) != pairs:
        raise SystemExit(f"strong_correlations.csv has {len(block)} of the {pairs} size-block pairs; "
                         "run `make results` (step eda)")
    skewest = max(summary, key=lambda row: abs(float(row["skewness"])))
    return {
        "eda.n_columns": str(len(summary)),
        "eda.n_dropped": str(sum(1 for row in dependencies if row["exact"] == "True")),
        "eda.size_r_min": dec(min(block), 2),
        "eda.size_r_max": dec(max(block), 3),
        "eda.max_skew": dec(abs(float(skewest["skewness"])), 2),
        "eda.max_skew_variable": skewest["variable"],
    }


def _pca_facts(results_dir: Path) -> dict[str, str]:
    decision = read_source(results_dir, "pca.decision")
    sensitivity = read_source(results_dir, "pca.sensitivity")
    eigenvalues = read_csv_source(results_dir, "pca.eigenvalues")
    k_80 = int(decision["k_80"])
    return {
        "pca.n_features": integer(decision["n_variables"]),
        "pca.k_80": integer(k_80),
        "pca.kaiser": integer(decision["kaiser"]),
        "pca.var_pc1": pct(decision["explained_pc1"], 1),
        "pca.var_pc2": pct(decision["explained_pc2"], 1),
        "pca.cum_k80": pct(eigenvalues[k_80 - 1]["cumulative"], 1),
        "pca.min_eigenvalue": dec(decision["min_eigenvalue"], 5),
        "pca.kaiser_all31": integer(sensitivity["all31_sensitivity"]["kaiser"]),
        "pca.abs_cos_pc1": dec(sensitivity["abs_cos_pc1"], 5),
        "pca.abs_spearman_pc1": dec(abs(sensitivity["spearman_pc1"]), 4),
    }


def _number(value: float) -> str:
    """A parameter value without trailing zeros (5 and not 5,00; 0,25; 0,9)."""
    text = dec(value, 2)
    return text.rstrip("0").rstrip(",") if "," in text else text


def _variant_label(row: dict[str, str], base: dict[str, str]) -> str:
    """What a stage-2 variant moved from the baseline: R0, eta0 or the number of epochs."""
    if float(row["radius0"]) != float(base["radius0"]):
        return f"R0 = {_number(row['radius0'])}"
    if float(row["eta0"]) != float(base["eta0"]):
        return f"η0 = {_number(row['eta0'])}"
    return f"{integer(row['epochs'])} épocas"


def _som_facts(results_dir: Path) -> dict[str, str]:
    contrast = read_source(results_dir, "som.contrast")
    selection = read_source(results_dir, "som.selection")
    robustness = read_source(results_dir, "som.robustness")
    table = {row["label"]: row for row in read_csv_source(results_dir, "som.robustness_table")}
    values = {
        "som.r2_pc1": dec(contrast["r2_pc1"], 3),
        "som.r2_pc1_pct": pct(contrast["r2_pc1"], 1),
        "som.p_r2_pc1": dec(contrast["p_r2_pc1"], 3),
        "som.r2_pc2": dec(contrast["r2_pc2"], 3),
        "som.p_r2_pc2": dec(contrast["p_r2_pc2"], 3),
        "som.mantel_rho": dec(contrast["mantel_plane_rho"], 3),
        "som.p_mantel": dec(contrast["p_mantel_plane"], 3),
        "som.mantel_z26_rho": dec(contrast["mantel_z26_rho"], 3),
        "som.edge_rho_pc1": dec(contrast["edge_rho_pc1"], 3),
        "som.edge_rho_pc2": dec(contrast["edge_rho_pc2"], 3),
        "som.n_edges": integer(contrast["n_edges"]),
        "som.n_excluded_edges": integer(contrast["n_excluded_edges"]),
        "som.chosen_k": integer(selection["chosen_k"]),
        "som.qe_train_argmin_k": integer(selection["qe_train_argmin_k"]),
        "som.figure_seed": integer(selection["figure_seed"]),
        "som.n_regions": integer(contrast["n_regions"]),
        "som.n_permutations": integer(contrast["n_permutations"]),
        "som.robust": "sí" if robustness["robust"] else "no",
        "som.n_failing_variants": str(len(robustness["failing_variants"])),
    }
    # One pair of facts per stage-2 variant that failed the TE filter, in the order robustness.json lists them
    # (the slide of the failed variants reads som.fail_1 ... som.fail_N).
    for position, label in enumerate(robustness["failing_variants"], start=1):
        if label not in table or "base" not in table:
            raise SystemExit(f"stage-2 variant {label!r} is not in robustness.csv; run `make results` (step som-stage2)")
        values[f"som.fail_{position}.variant"] = _variant_label(table[label], table["base"])
        values[f"som.fail_{position}.te"] = dec(table[label]["te_mean"], 3)
    base = table["base"]
    variants = [label for label in table if label != "base"]
    passing = [label for label in variants if label not in robustness["failing_variants"]]
    values.update({
        "som.n_stage2_variants": str(len(variants)),
        "som.base_radius0": _number(base["radius0"]),
        "som.base_eta0": _number(base["eta0"]),
        "som.base_epochs": integer(base["epochs"]),
        "som.base_te": dec(base["te_mean"], 3),
        "som.passing_variants": "; ".join(_variant_label(table[label], base) for label in passing),
    })
    # Zones of the zones figure: the occupied neurons with at least 2 creators that have the smallest and the largest
    # median followers (the two ends of the size axis the slide reads).
    zones = [row for row in read_csv_source(results_dir, "som.zones") if int(row["n"]) >= 2]
    zones = _nonempty(zones, "neuron with 2 or more creators in zones.csv", "som-profiles")
    for name, row in (("small", min(zones, key=lambda r: float(r["median_followers"]))),
                      ("large", max(zones, key=lambda r: float(r["median_followers"])))):
        values[f"som.zone_{name}.cell"] = f"({row['row']},{row['col']})"
        values[f"som.zone_{name}.n"] = integer(row["n"])
        values[f"som.zone_{name}.topic"] = row["topic"]
        values[f"som.zone_{name}.followers"] = integer(row["median_followers"])
        values[f"som.zone_{name}.price"] = integer(row["median_price"])
    return values


def _oja_facts(results_dir: Path) -> dict[str, str]:
    comparison = read_source(results_dir, "oja.comparison")
    dispersion = read_source(results_dir, "oja.dispersion")
    evidence = read_source(results_dir, "oja.evidence")
    correlations = read_csv_source(results_dir, "oja.correlations")
    index = read_csv_source(results_dir, "oja.index")
    followers = _first(
        correlations, lambda row: row["target"] == "followers" and row["sign"] == "+1",
        "followers/+1 row in oja/evidence_correlations.csv", "oja",
    )
    top, top_opposite = evidence["maximum"]["+1"], evidence["maximum"]["-1"]
    return {
        "oja.n_seeds": integer(dispersion["n_seeds"]),
        "oja.n_creators": str(len(index)),
        "oja.n_abs_cos_above": integer(dispersion["n_abs_cos_above"]),
        "oja.abs_cos_min": dec(dispersion["min_pairwise_abs_cos"], 7),
        "oja.abs_cos_mean": dec(dispersion["mean_pairwise_abs_cos"], 7),
        "oja.worst_seed": integer(dispersion["worst_seed"]),
        "oja.pivot": ", ".join(dispersion["pivots"]),
        "oja.pivot_margin": dec(dispersion["pivot_margin"]["margin"], 5),
        "oja.max_abs_diff": dec(comparison["max_abs_diff"], 4),
        "oja.corr_followers_pearson": dec(followers["pearson"], 3),
        "oja.corr_followers_spearman": dec(followers["spearman"], 3),
        "oja.max_id": str(top["creator_id"]),
        "oja.max_name": str(top["name"]),
        "oja.max_topic": str(top["dominant_topic"]),
        "oja.max_followers": integer(top["followers"]),
        "oja.max_index": dec(top["index"], 2),
        "oja.max_opposite_id": str(top_opposite["creator_id"]),
        "oja.max_opposite_name": str(top_opposite["name"]),
        "oja.max_opposite_followers": integer(top_opposite["followers"]),
        "oja.max_opposite_topic": str(top_opposite["dominant_topic"]),
    }


def _campaign_facts(results_dir: Path) -> dict[str, str]:
    identity = read_source(results_dir, "camp.identity")
    shortlists = read_csv_source(results_dir, "camp.shortlists")
    comparison = read_csv_source(results_dir, "camp.comparison")
    committed = {(pair["campaign"], pair["objective"]) for pair in identity["pairs"]}
    values = {"camp.k": integer(identity["k"]), "camp.rule_commit": str(identity["rule_commit"])[:7]}
    for key, (campaign, objective) in RECOMMENDED_OBJECTIVE.items():
        if (campaign, objective) not in committed:
            raise SystemExit(
                f"campaign {campaign}/{objective} is not in campaigns/selection_identity.json; "
                "run `make results` (step campaigns)"
            )
        own = [r for r in shortlists if r["campaign"] == campaign and r["objective"] == objective and r["list"] == "propia"]
        own.sort(key=lambda r: int(r["rank"]))
        row = _first(
            comparison, lambda r: r["campaign"] == campaign and r["objective"] == objective and r["list"] == "propia",
            f"{campaign}/{objective} own-list row in campaigns/comparison.csv", "campaigns",
        )
        values[f"camp.{key}.objective"] = objective
        values[f"camp.{key}.top5"] = ", ".join(r["name"] for r in own[:5])
        values[f"camp.{key}.criterion"] = dec(row["criterion_mean"], 3)
        values[f"camp.{key}.cost_per_thousand_ar"] = dec(row["cost_per_thousand"], 2)
        values[f"camp.{key}.overlap_followers"] = integer(row["overlap_followers_global"])
        values[f"camp.{key}.overlap_followers_tema"] = integer(row["overlap_followers_tema"])
        baseline = _first(
            comparison,
            lambda r: r["campaign"] == campaign and r["objective"] == objective and r["list"] == "followers_global",
            f"{campaign}/{objective} followers_global row in campaigns/comparison.csv", "campaigns",
        )
        values[f"camp.{key}.followers_global_cost_per_thousand_ar"] = dec(baseline["cost_per_thousand"], 2)
        values[f"camp.{key}.followers_global_topic_share"] = pct(baseline["topic_dominant_share"], 0)
        values[f"camp.{key}.cost_total"] = integer(row["cost_total"])
        values[f"camp.{key}.pc1_mean"] = dec(statistics.mean(float(r["pc1"]) for r in own), 2)
    global_rows = [r for r in shortlists if r["list"] == "followers_global"]
    seen: dict[str, float] = {}
    for r in global_rows:
        seen[r["creator_id"]] = float(r["pc1"])
    values["camp.followers_global_pc1_mean"] = dec(statistics.mean(seen.values()), 2)
    futbol_costs = [float(r["cost_total"]) for r in comparison if r["campaign"] == "fútbol" and r["list"] == "propia"]
    values["camp.futbol.other_cost_total_min"] = integer(sorted(futbol_costs)[1] if len(futbol_costs) > 1 else futbol_costs[0])
    return values


def _maintenance_facts(results_dir: Path) -> dict[str, str]:
    demo = read_source(results_dir, "maint.demo")
    return {
        "maint.bmu": f"(fila {integer(demo['bmu']['row'])}, col {integer(demo['bmu']['col'])})",
        "maint.distance": dec(demo["bmu"]["distance"], 3),
        "maint.qe": dec(demo["drift"]["qe"], 3),
        "maint.max_training_distance": dec(demo["drift"]["max"], 3),
        "maint.p95": dec(demo["drift"]["p95"], 3),
        "maint.retrain": "hace falta re-entrenar" if demo["drift"]["drift"] else "no hace falta re-entrenar",
        "maint.oja_index": dec(demo["oja_index"], 3),
        "maint.index_place": integer(demo["oja_rank"]),
    }


def _letters_facts(results_dir: Path) -> dict[str, str]:
    selection = read_source(results_dir, "letters.selection")
    orthogonality = read_source(results_dir, "letters.orthogonality")
    capacity = read_source(results_dir, "letters.capacity")
    spurious = read_source(results_dir, "letters.spurious")
    recall = read_csv_source(results_dir, "letters.recall")

    def recall_row(name: str, flipped: int) -> dict[str, str]:
        return _first(
            recall, lambda r: r["set"] == name and r["update"] == "async" and int(r["flipped"]) == flipped,
            f"async recall row of the {name} set with {flipped} flipped pixels", "hopfield-letters",
        )

    def recall_rate(name: str, flipped: int) -> str:
        # Half-up on the decimal text, as the fragment rounds its 3-decimal rates: 0,3225 is 32,3 %, not 32,2 %.
        percent = (Decimal(recall_row(name, flipped)["recall_rate"]) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{percent} %".replace(".", ",")

    def max_overlap(name: str) -> float:
        return max(abs(float(pair["overlap"])) for pair in selection[name]["pairs"])

    counts = {name: 0 for name in CLASS_NAMES}
    for seed in spurious["seeds_tried"]:
        for name, number in spurious["counts_by_seed"][str(seed)].items():
            counts[name] += int(number)
    trials = sum(counts.values())
    spurious_total = trials - counts["stored"]
    most_common = max((name for name in counts if name != "stored"), key=lambda name: counts[name])
    set_size = len(selection["separated"]["letters"])
    if len(selection["correlated"]["letters"]) != set_size:
        raise SystemExit("the separated and correlated letter sets differ in size; run `make results` (step hopfield-letters)")
    n_pixels = int(orthogonality["n_pixels"])
    # p = 1 is enumerated exhaustively: one subset per letter of the alphabet.
    singles = _first(read_csv_source(results_dir, "letters.capacity_by_p"),
                     lambda r: int(r["p"]) == 1 and r["exhaustive"] == "1", "exhaustive p = 1 row in capacity_by_p.csv",
                     "hopfield-letters")
    # The C binary flips lround(level x N) pixels per trial (neuron/models/hopfield.c); floor(x + 0.5) is the same
    # for positive x.
    spurious_flips = [math.floor(float(level) * n_pixels + 0.5)
                      for level in _nonempty(spurious["levels"], "noise level in spurious.json", "hopfield-letters")]
    values = {
        "letters.n_pixels": integer(n_pixels),
        "letters.set_size": str(set_size),
        "letters.alphabet_size": integer(singles["n_subsets"]),
        "letters.draft_matching_glyphs": str(DRAFT_MATCHING_GLYPHS),
        "letters.spur_flip_min": str(min(spurious_flips)),
        "letters.spur_flip_max": str(max(spurious_flips)),
        "letters.separated_set": str(selection["separated"]["letters"]),
        "letters.correlated_set": str(selection["correlated"]["letters"]),
        "letters.separated_max_overlap": dec(max_overlap("separated"), 2),
        "letters.correlated_max_overlap": dec(max_overlap("correlated"), 2),
        "letters.separated_min_margin": integer(min(orthogonality["separated"]["min_margin"])),
        "letters.separated_n_stable": str(sum(1 for margin in orthogonality["separated"]["min_margin"] if margin >= 0)),
        "letters.correlated_n_stable": str(sum(1 for margin in orthogonality["correlated"]["min_margin"] if margin >= 0)),
        "letters.correlated_recall_k3": recall_rate("correlated", 3),
        "letters.p4_mean_stable_fraction": dec(capacity["p4_mean_stable_fraction"], 3),
        "letters.p4_all_stable_fraction": dec(capacity["p4_all_stable_fraction"], 3),
        "letters.spurious_class": CLASS_NAMES[most_common],
        "letters.spur_trials": str(trials),
        "letters.spur_total": str(spurious_total),
        "letters.spur_total_pct": pct(spurious_total / trials, 1),
    }
    by_p = {int(r["p"]): r for r in read_csv_source(results_dir, "letters.capacity_by_p")}
    for p in (3, 4, 6):
        values[f"letters.stable_p{p}"] = dec(by_p[p]["mean_stable_fraction"], 3)
    last_p = max(by_p)
    values["letters.capacity_last_p"] = str(last_p)
    values["letters.stable_last_p"] = dec(by_p[last_p]["mean_stable_fraction"], 3)
    values["letters.course_capacity_ratio"] = dec(COURSE_CAPACITY_RATIO, 2)
    values["letters.course_capacity"] = dec(COURSE_CAPACITY_RATIO * n_pixels, 2)
    for flipped in LETTER_RECALL_FLIPS:
        values[f"letters.separated_recall_k{flipped}"] = recall_rate("separated", flipped)
        values[f"letters.flips_k{flipped}"] = integer(recall_row("separated", flipped)["flipped"])
    for n_stable in range(5):
        values[f"letters.p4_stable_{n_stable}"] = integer(capacity["p4_n_stable_counts"][str(n_stable)])
    for name in CLASS_NAMES:
        values[f"letters.spur_{name}"] = str(counts[name])
        values[f"letters.spur_{name}_pct"] = pct(counts[name] / trials, 1)
    return values


def _qr_facts(results_dir: Path) -> dict[str, str]:
    verdict = read_source(results_dir, "qr.verdict")
    pair_facts = read_source(results_dir, "qr.facts")
    overlaps = read_source(results_dir, "qr.overlaps")
    protocol = read_source(results_dir, "qr.protocol")
    majority = read_source(results_dir, "qr.majority")
    shift = read_source(results_dir, "qr.shift")
    table = read_csv_source(results_dir, "qr.recovery")
    first_shift = _first(shift["shifts"], lambda item: int(item["shift"]) == 1, "shift of 1 pixel in shift.json",
                         "hopfield-qr-limits")
    pinv_full = _nonempty([float(row["level"]) for row in table if abs(float(row["pinv"]) - 1.0) < 1e-12],
                          "noise level where pinv recovers every QR", "hopfield-qr")
    hamming_to_targets = _nonempty(majority["hamming_to_targets"], "Hamming distance in majority.json",
                                   "hopfield-qr-limits")
    last_level = max(_nonempty([float(row["level"]) for row in table], "row in recovery_table.csv", "hopfield-qr"))
    if abs(last_level - QR_LAST_NOISE) > 1e-9:
        raise SystemExit(f"the recovery table ends at noise {last_level}, but the texts call {QR_LAST_NOISE} the last "
                         "level; update QR_LAST_NOISE and the texts that name it")
    high = _row_at(table, "level", QR_HIGH_NOISE)
    values = {
        "qr.n_qr": str(len(overlaps["dots"])),
        "qr.n_pixels": integer(pair_facts["n_pixels"]),
        "qr.mean_abs_overlap": dec(overlaps["mean_abs_overlap"], 2),
        "qr.max_abs_overlap": dec(overlaps["max_abs_overlap"], 2),
        "qr.identical_fraction": pct(pair_facts["identical_fraction"], 1),
        "qr.min_pair_hamming": integer(pair_facts["min_pair_hamming"]),
        "qr.hebb_exact_noise0": pct_short(verdict["hebb_exact_recovery_noise0_async"], 1),
        "qr.pinv_exact_noise0": pct_short(verdict["pinv_exact_recovery_noise0_async"], 1),
        "qr.pinv_last_full_noise": dec(max(pinv_full), 2),
        "qr.noise_high": dec(QR_HIGH_NOISE, 2),
        "qr.pinv_at_high": pct_short(high["pinv"], 1),
        "qr.hamming_at_high": pct_short(high["hamming"], 1),
        "qr.majority_hamming_min": integer(min(hamming_to_targets)),
        "qr.majority_hamming_max": integer(max(hamming_to_targets)),
        "qr.n_noise_levels": str(len(table)),
        "qr.trials": integer(protocol["trials"]),
        "qr.n_seeds": str(len(protocol["seeds"])),
        "qr.shift1_query_hamming": integer(first_shift["query_hamming"]),
        "qr.shift1_recovered_hamming": integer(first_shift["recovered_hamming"]),
        # 0,15 N of the course for the QR network, and the energy of a stored QR under the projection rule:
        # W xi = xi, so E = -1/2 xi.xi = -N/2.
        "qr.course_capacity": integer(math.floor(COURSE_CAPACITY_RATIO * float(pair_facts["n_pixels"]))),
        "qr.pinv_stored_energy": dec(-float(pair_facts["n_pixels"]) / 2, 1).replace("-", "−"),
    }
    for level in QR_REPORTED_LEVELS:
        row = _row_at(table, "level", level)
        label = f"{level:.2f}".replace(".", "_")
        values[f"qr.pinv_at_{label}"] = pct_short(row["pinv"], 1)
        values[f"qr.hamming_at_{label}"] = pct_short(row["hamming"], 1)
    return values


def check_claims(results_dir: Path = RESULTS_DIR) -> None:
    """Stop the build when a result no longer supports a sentence that the slides or the informe state as plain text.

    The drift pins guard numbers; these sentences carry no number, so a regenerated result could falsify them with
    the build still green. Each check names the sentence it guards.
    """
    results_dir = Path(results_dir)
    failed: list[str] = []
    table = read_csv_source(results_dir, "qr.recovery")
    if any(float(row["pinv"]) > float(row["hamming"]) for row in table):
        failed.append("QR: «un lookup de Hamming iguala o supera a la pseudo-inversa» (pinv > Hamming at some level)")
    robustness = read_csv_source(results_dir, "som.robustness_table")
    if not all(row["passes_empty"] == "True" and row["passes_creators"] == "True" for row in robustness):
        failed.append("SOM: «la ocupación de las neuronas no se degrada» (a stage-2 variant fails an occupancy filter)")
    selection = read_source(results_dir, "som.selection")
    if selection.get("decided_by") != "qe_loo":
        failed.append("SOM: «entre las grillas que pasan gana el menor QE-LOO» (selection.json decided_by is not qe_loo)")
    hits = {int(row["neuron"]): int(row["hits"]) for row in read_csv_source(results_dir, "som.hits")}
    edges = {
        int(row["edge_rank"]): (int(row["neuron_a"]), int(row["neuron_b"]))
        for row in read_csv_source(results_dir, "som.high_u_edges")
    }
    if any(rank not in edges or min(hits[n] for n in edges[rank]) != 1 for rank in (1, 2, 3)):
        failed.append("SOM: «en las tres paredes más altas hay una neurona con un solo creador»")
    k = int(selection["chosen_k"])
    profiles = read_csv_source(results_dir, "som.neuron_profiles")
    diagonal = [int(row["group"]) // k + int(row["group"]) % k for row in profiles]
    for column in ("price_usd", "followers"):
        if statistics.correlation(diagonal, [float(row[column]) for row in profiles]) <= 0:
            failed.append(f"SOM: «chicos y baratos arriba a la izquierda, grandes y caros abajo a la derecha» "
                          f"({column} does not grow with row + col)")
    if failed:
        raise SystemExit("a sentence of the slides or the informe no longer holds:\n- " + "\n- ".join(failed))


def load_facts(results_dir: Path = RESULTS_DIR) -> dict[str, str]:
    """Flat display strings of every fact the generated text may quote; check_claims runs first."""
    check_claims(Path(results_dir))
    values: dict[str, str] = {}
    for part in (
        _eda_facts, _pca_facts, _som_facts, _oja_facts, _campaign_facts, _maintenance_facts, _letters_facts, _qr_facts,
    ):
        values.update(part(Path(results_dir)))
    return values


def fill(template: str, facts: dict[str, str], wrap: Callable[[str, str], str] | None = None) -> str:
    """Replace every {group.key} token by its value (or by wrap(key, value)); an unknown key stops the build."""

    def replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in facts:
            raise SystemExit(f"unknown fact key {key!r}; add it to facts.load_facts")
        value = facts[key]
        return wrap(key, value) if wrap is not None else value

    return TOKEN.sub(replace, template)


# ---------- drift pins (D-12) ----------

# (fragment number, template): a short phrase copied from the fragment with each number replaced by the
# {group.key} fact it must equal. check_fragment_numbers fills the template and searches it in the fragment.
DRIFT_PINS: tuple[tuple[int, str], ...] = (
    # 1: datos y PCA
    (1, "El conjunto auditado queda en {pca.n_features} variables"),
    (1, "Componentes para el 80 % de la varianza: {pca.k_80}"),
    (1, "Componentes con autovalor > 1 (Kaiser): {pca.kaiser}"),
    (1, "La PCA muestra que {pca.k_80} componentes de {pca.n_features} retendrían {pca.cum_k80} de la varianza"),
    (1, "PC1 ({pca.var_pc1})"),
    (1, "PC2 ({pca.var_pc2})"),
    (1, "Kaiser pasa de {pca.kaiser} a {pca.kaiser_all31}"),
    (1, "(abs(cos) {pca.abs_cos_pc1}) ni como orden de los creadores (Spearman en valor absoluto {pca.abs_spearman_pc1})"),
    (1, "ningún autovalor nulo, el menor es {pca.min_eigenvalue}"),
    # 2: Kohonen
    (2, "- Grilla elegida: k = {som.chosen_k}"),
    (2, "R² de PC1 sobre la grilla: {som.r2_pc1} (p = {som.p_r2_pc1})"),
    (2, "R² de PC2 sobre la grilla: {som.r2_pc2} (p = {som.p_r2_pc2})"),
    (2, "Mantel grilla vs plano PC1-PC2: rho = {som.mantel_rho} (p = {som.p_mantel})"),
    (2, "Mantel grilla vs distancia en las 26 variables (referencia): rho = {som.mantel_z26_rho}"),
    (2, "explica el {som.r2_pc1_pct} de la variación de PC1"),
    (2, "con seed {som.figure_seed}, que es el medoide de estabilidad"),
    (2, "rho de Spearman {som.edge_rho_pc1} y con la de PC2 con {som.edge_rho_pc2} ({som.n_edges} aristas; las otras {som.n_excluded_edges} tocan"),
    (2, "con {som.n_permutations} permutaciones de un generador sembrado con 2026"),
    # 3: Oja y campañas
    (3, "Pearson {oja.corr_followers_pearson} y Spearman {oja.corr_followers_spearman} con `followers`"),
    (3, "(Spearman de {oja.corr_followers_spearman} con `followers` con el signo de D-02)"),
    (3, "Seeds con abs(cos(w, v1)) > 0,99: {oja.n_abs_cos_above} de {oja.n_seeds}."),
    (3, "abs(cos) entre pares de seeds: mínimo {oja.abs_cos_min}, media {oja.abs_cos_mean}."),
    (3, "pivote de todas: {oja.pivot}."),
    (3, "Los dos más grandes de PC1 difieren en {oja.pivot_margin} en valor absoluto"),
    (3, "Máximo con el signo de D-02: {oja.max_id} ({oja.max_name}), tema dominante {oja.max_topic}, {oja.max_followers} followers"),
    (3, "Máximo con el signo opuesto: {oja.max_opposite_id} ({oja.max_opposite_name}), tema dominante fútbol, {oja.max_opposite_followers} followers"),
    (3, "Commit de la regla: {camp.rule_commit}"),
    (3, "Las dos líneas base usan k = {camp.k} igual que las listas propias"),
    (3, "fútbol / profundidad — propia: {camp.futbol.top5}"),
    (3, "perros / costo_por_mil — propia: {camp.perros.top5}"),
    (3, "maquillaje / profundidad — propia: {camp.maquillaje.top5}"),
    (3, "arte / engagement_profundidad — propia: {camp.arte.top5}"),
    (3, "con USD {camp.futbol.cost_per_thousand_ar} por mil, el costo por mil más alto"),
    (3, "(USD {camp.perros.cost_per_thousand_ar} por mil)"),
    (3, "| {camp.perros.cost_per_thousand_ar} | {camp.perros.criterion} |"),
    (3, "(USD {camp.maquillaje.cost_per_thousand_ar} por mil)"),
    (3, "(USD {camp.arte.cost_per_thousand_ar} por mil)"),
    (3, "Comparte {camp.perros.overlap_followers_tema} de 5 con la línea base dentro del tema"),
    (3, "y {camp.perros.overlap_followers} de 5 con la global"),
    (3, "a distancia {maint.distance} de su vector"),
    (3, "es {maint.bmu} a distancia"),
    (3, "máximo {maint.max_training_distance}, percentil 95 {maint.p95}"),
    (3, "Veredicto de deriva: {maint.retrain} (la distancia"),
    (3, "índice de Oja {maint.oja_index} con el w guardado y ocuparía el lugar {maint.index_place} entre los 50 creadores"),
    # 4: Hopfield, letras
    (4, "N = {letters.n_pixels} (cada letra es un vector de {letters.n_pixels} valores"),
    (4, "el margen mínimo de cada letra es {letters.separated_min_margin}, a {letters.separated_min_margin} unidades de cero"),
    (4, "{letters.separated_set} está en el primer valor (máximo {letters.separated_max_overlap})"),
    (4, "{letters.correlated_set} está en el último (máximo {letters.correlated_max_overlap})"),
    (4, "Hay {letters.p4_stable_0}, {letters.p4_stable_1}, {letters.p4_stable_2}, {letters.p4_stable_3} y {letters.p4_stable_4} subconjuntos con 0, 1, 2, 3 y 4 letras estables"),
    (4, "{letters.p4_stable_4} ({letters.p4_all_stable_fraction}) las tienen todas estables y la fracción estable media es {letters.p4_mean_stable_fraction}"),
    (4, "almacenado {letters.spur_stored} ({letters.spur_stored_pct}), inverso {letters.spur_inverse} ({letters.spur_inverse_pct}), mezcla {letters.spur_mixture} ({letters.spur_mixture_pct}) y otro {letters.spur_other} ({letters.spur_other_pct})"),
    (4, "seguida por el {letters.spurious_class}, la mezcla y el otro"),
    (4, "({letters.spur_total} de {letters.spur_trials}, {letters.spur_total_pct})"),
    (4, "{letters.draft_matching_glyphs} de sus {letters.alphabet_size} glifos coinciden con los del borrador"),
    # 5: Hopfield, QR
    (5, "el máximo |solapamiento| entre pares es {qr.max_abs_overlap}"),
    (5, "y la media es {qr.mean_abs_overlap}; todos"),
    (5, "el {qr.identical_fraction} de los {qr.n_pixels} píxeles es idéntico en los {qr.n_qr} QR a la vez"),
    (5, "la distancia de Hamming mínima entre un par es {qr.min_pair_hamming}"),
    (5, "{qr.n_noise_levels} niveles de 0 a 0,5 en pasos de 0,05"),
    (5, "{qr.trials} ensayos por nivel y seeds 1 a {qr.n_seeds}"),
    (5, "la tasa exacta es {qr.hebb_exact_noise0} en los {qr.n_noise_levels} niveles de ruido"),
    (5, "(`pinv_stored_fixed_noise0_async = {qr.n_qr}`)"),
    (5, "por entre {qr.majority_hamming_min} y {qr.majority_hamming_max} píxeles"),
    (5, "pinv sostiene el {qr.pinv_exact_noise0} de recuperación exacta hasta el nivel {qr.pinv_last_full_noise}"),
    (5, "cae apenas a {qr.pinv_at_0_35} en 0,35, a {qr.pinv_at_0_40} en 0,40, a {qr.pinv_at_0_45} en 0,45 y colapsa a {qr.pinv_at_0_50} en 0,50"),
    (5, "({qr.hamming_at_0_40} contra {qr.pinv_at_0_40})"),
    (5, "{qr.hamming_at_0_45} contra {qr.pinv_at_0_45} en el nivel 0,45, y {qr.hamming_at_0_50} contra {qr.pinv_at_0_50} en el nivel 0,50"),
    (5, "la distancia de Hamming de la consulta a la fuente ya es {qr.shift1_query_hamming} de {qr.n_pixels}"),
    (5, "queda a {qr.shift1_recovered_hamming} píxeles"),
)


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def check_fragment_numbers(
    facts: dict[str, str],
    deliverables_dir: Path = TP_DIR / "deliverables",
    pins: tuple[tuple[int, str], ...] = DRIFT_PINS,
) -> list[str]:
    """One message per pin whose filled phrase is not in its fragment (whitespace runs collapsed); [] when none drifted.

    Reads each fragment once and never writes. A pin with an unknown key or a missing fragment is reported as a failure.
    """
    texts: dict[int, str | None] = {}
    failures: list[str] = []
    for number, template in pins:
        if number not in texts:
            found = sorted(Path(deliverables_dir).glob(f"{number:02d}-*.md"))
            texts[number] = _collapse(found[0].read_text(encoding="utf-8")) if found else None
        text = texts[number]
        if text is None:
            failures.append(f"fragment {number}: no file {number:02d}-*.md in {deliverables_dir}")
            continue
        try:
            filled = _collapse(fill(template, facts))
        except SystemExit as error:
            failures.append(f"fragment {number}: pin {template!r}: {error}")
            continue
        if filled not in text:
            failures.append(f"fragment {number}: phrase not found: {filled!r} (pin {template!r})")
    return failures


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    dump = sub.add_parser("dump", help="print the facts as sorted JSON")
    dump.add_argument("--results", type=Path, default=RESULTS_DIR)
    check = sub.add_parser("check", help="verify that the numbers pinned in the fragments equal the results (D-12)")
    check.add_argument("--results", type=Path, default=RESULTS_DIR)
    check.add_argument("--deliverables", type=Path, default=TP_DIR / "deliverables")
    args = parser.parse_args(argv)
    if args.command == "dump":
        print(json.dumps(load_facts(args.results), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    failures = check_fragment_numbers(load_facts(args.results), args.deliverables)
    if failures:
        print(f"DRIFT {len(failures)} of {len(DRIFT_PINS)} pins")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print(f"DRIFT_OK {len(DRIFT_PINS)} pins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
