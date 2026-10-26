#!/usr/bin/env python3
"""The only place where a result number becomes text of the informe (D-11).

    .venv/bin/python analysis/facts.py dump [--results DIR]
    .venv/bin/python analysis/facts.py check [--results DIR] [--deliverables DIR]

Every number that a generated sentence shows is read from analysis/results/** here and formatted once, with
the Spanish decimal comma: `dec`, `pct` and `integer` are the only formatters (they consolidate the helpers
that analysis/campaigns.py kept for its own report lines). `load_facts` returns flat display strings keyed
`group.name`; `fill` replaces the `{group.name}` tokens of a template with them (or with whatever the `wrap`
callback returns, which is how informe.py marks each number as a `data-fact` span). A missing result file or
an unknown key stops the build with the make command to run, never a blank number. `DRIFT_PINS` ties the numbers
that the fragments of deliverables/ carry as hand-typed text to the results (D-12): `check_fragment_numbers` fills
each pin with the facts and looks the phrase up in its fragment, and the `check` subcommand exits 1 naming every
pin that no longer matches. Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
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
    "pca.decision": ("pca/audited/decision.json", "pca"),
    "pca.sensitivity": ("pca/sensitivity.json", "pca"),
    "pca.eigenvalues": ("pca/audited/eigenvalues.csv", "pca"),
    "som.contrast": ("som/profiles/pca_contrast.json", "som-profiles"),
    "som.selection": ("som/series_som_stage1/selection.json", "som-stage1"),
    "som.robustness": ("som/series_som_stage2/robustness.json", "som-stage2"),
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


def _som_facts(results_dir: Path) -> dict[str, str]:
    contrast = read_source(results_dir, "som.contrast")
    selection = read_source(results_dir, "som.selection")
    robustness = read_source(results_dir, "som.robustness")
    return {
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


def _oja_facts(results_dir: Path) -> dict[str, str]:
    comparison = read_source(results_dir, "oja.comparison")
    dispersion = read_source(results_dir, "oja.dispersion")
    evidence = read_source(results_dir, "oja.evidence")
    correlations = read_csv_source(results_dir, "oja.correlations")
    index = read_csv_source(results_dir, "oja.index")
    followers = next(row for row in correlations if row["target"] == "followers" and row["sign"] == "+1")
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
        row = next(
            r for r in comparison if r["campaign"] == campaign and r["objective"] == objective and r["list"] == "propia"
        )
        values[f"camp.{key}.objective"] = objective
        values[f"camp.{key}.top5"] = ", ".join(r["name"] for r in own[:5])
        values[f"camp.{key}.criterion"] = dec(row["criterion_mean"], 3)
        values[f"camp.{key}.cost_per_thousand_ar"] = dec(row["cost_per_thousand"], 2)
        values[f"camp.{key}.overlap_followers"] = integer(row["overlap_followers_global"])
        values[f"camp.{key}.overlap_followers_tema"] = integer(row["overlap_followers_tema"])
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

    def max_overlap(name: str) -> float:
        return max(abs(float(pair["overlap"])) for pair in selection[name]["pairs"])

    counts = {name: 0 for name in CLASS_NAMES}
    for seed in spurious["seeds_tried"]:
        for name, number in spurious["counts_by_seed"][str(seed)].items():
            counts[name] += int(number)
    trials = sum(counts.values())
    spurious_total = trials - counts["stored"]
    most_common = max((name for name in counts if name != "stored"), key=lambda name: counts[name])
    values = {
        "letters.n_pixels": integer(orthogonality["n_pixels"]),
        "letters.separated_set": str(selection["separated"]["letters"]),
        "letters.correlated_set": str(selection["correlated"]["letters"]),
        "letters.separated_max_overlap": dec(max_overlap("separated"), 2),
        "letters.correlated_max_overlap": dec(max_overlap("correlated"), 2),
        "letters.separated_min_margin": integer(min(orthogonality["separated"]["min_margin"])),
        "letters.p4_mean_stable_fraction": dec(capacity["p4_mean_stable_fraction"], 3),
        "letters.p4_all_stable_fraction": dec(capacity["p4_all_stable_fraction"], 3),
        "letters.spurious_class": CLASS_NAMES[most_common],
        "letters.spur_trials": str(trials),
        "letters.spur_total": str(spurious_total),
        "letters.spur_total_pct": pct(spurious_total / trials, 1),
    }
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
    first_shift = next(item for item in shift["shifts"] if int(item["shift"]) == 1)
    pinv_alive = [float(row["level"]) for row in table if float(row["pinv"]) > 0.0]
    pinv_full = [float(row["level"]) for row in table if abs(float(row["pinv"]) - 1.0) < 1e-12]
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
        "qr.noise_high": dec(max(pinv_alive), 2),
        "qr.majority_hamming_min": integer(min(majority["hamming_to_targets"])),
        "qr.majority_hamming_max": integer(max(majority["hamming_to_targets"])),
        "qr.n_noise_levels": str(len(table)),
        "qr.trials": integer(protocol["trials"]),
        "qr.n_seeds": str(len(protocol["seeds"])),
        "qr.shift1_query_hamming": integer(first_shift["query_hamming"]),
        "qr.shift1_recovered_hamming": integer(first_shift["recovered_hamming"]),
    }
    for level in (0.35, 0.40, 0.45, 0.50):
        row = _row_at(table, "level", level)
        label = f"{level:.2f}".replace(".", "_")
        values[f"qr.pinv_at_{label}"] = pct_short(row["pinv"], 1)
        values[f"qr.hamming_at_{label}"] = pct_short(row["hamming"], 1)
    return values


def load_facts(results_dir: Path = RESULTS_DIR) -> dict[str, str]:
    """Flat display strings of every fact the generated text may quote."""
    values: dict[str, str] = {}
    for part in (
        _pca_facts, _som_facts, _oja_facts, _campaign_facts, _maintenance_facts, _letters_facts, _qr_facts,
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
