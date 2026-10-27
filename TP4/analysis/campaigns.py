#!/usr/bin/env python3
"""Campaign lists by the committed rule, two followers baselines and the comparison metrics (CAMP-01, CAMP-02).

    .venv/bin/python analysis/campaigns.py [--out DIR]

Applies the rule committed in section 4 of deliverables/03-oja-campanas.md through analysis/campaigns_select.py
(D-07..D-17). main calls campaigns_select.rule_identity before it reads or creates anything and refuses to run
(a SystemExit, nothing written) unless the rule text and that module were added in one commit and have not changed
since; the identity (rule commit, sha256 of the rule text, sha256 of the module) is recorded in
selection_identity.json and cited by the first line of report_campaigns.md.

For each of the six (campaign, objective) pairs it writes the own list and the two followers baselines, all with
k = 5 over datos/creadores.csv, and the D-17 metrics: overlap@5 with each baseline, the share of the list whose
dominant topic is the campaign's, total Argentine reach, total cost, cost per thousand Argentines (total cost over
total reach, a ratio of sums) and the list mean of the criterion. Whatever the rule produces is reported as it
came out (PROJECT Key Decisions).

Every chosen creator is then located, only to describe the lists (D-14, D-15): its neuron (row, col) in the
Phase 2 figure run of the chosen grid (k5-step), its Oja index and rank (analysis/results/oja/index.csv) and its
PC1 and PC2 scores (analysis/results/pca/audited/scores.csv). The per-variable means of each criterion go to
objective_metrics.csv, and two figures place the lists on the PC1-PC2 plane and on the SOM map. None of these
readings changes a list. numpy, matplotlib (through plots_style) and the standard library only (Phase 1 D-06).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import campaigns_select  # noqa: E402
import pca  # noqa: E402
import plots_style  # noqa: E402
import som  # noqa: E402
import som_figures  # noqa: E402
import som_stage  # noqa: E402
from creadores import load_creadores  # noqa: E402

DEFAULT_OUT = TP_DIR / "analysis" / "results" / "campaigns"
OJA_INDEX = TP_DIR / "analysis" / "results" / "oja" / "index.csv"
PCA_SCORES = TP_DIR / "analysis" / "results" / "pca" / "audited" / "scores.csv"
PCA_EIGENVALUES = TP_DIR / "analysis" / "results" / "pca" / "audited" / "eigenvalues.csv"
STAGE1 = TP_DIR / "analysis" / "results" / "som" / "series_som_stage1"
PHASE2_RULE_FILE = "deliverables/02-kohonen.md"

LIST_NAMES = ("propia", "followers_global", "followers_tema")
LIST_LABELS = {"propia": "propia", "followers_global": "followers global", "followers_tema": "followers en el tema"}

SHORTLIST_COLUMNS = ["campaign", "objective", "list", "rank", "creator_id", "name", "dominant_topic", "criterion",
                     "criterion_secondary", "followers", "estimated_argentina_reach", "price_usd",
                     "cost_per_thousand"]
READING_COLUMNS = ["oja_index", "oja_rank", "pc1", "pc2", "som_neuron", "som_row", "som_col"]
OBJECTIVE_METRICS_COLUMNS = ["campaign", "objective", "list", "variable", "mean"]
COMPARISON_COLUMNS = ["campaign", "objective", "list", "n", "overlap_followers_global", "overlap_followers_tema",
                      "topic_dominant_share", "topic_mean_pct", "reach_total", "cost_total", "cost_per_thousand",
                      "criterion_mean"]
TABLE_HEADER = ("| Campaña / objetivo | Lista | n | overlap@5 con followers global | overlap@5 con followers en el "
                "tema | Proporción con el tema como dominante | Media del share del tema (%) | Alcance argentino "
                "total | Costo total (USD) | USD por mil argentinos | Criterio (media de la lista) |")


# ----------------------------------------------------------------------------------------------
# Metrics of one list (D-17)
# ----------------------------------------------------------------------------------------------


def overlap(a, b) -> int:
    """Number of creator indices that appear in both lists (a creator present in each counts once)."""
    return len(set(a) & set(b))


def _column(data, name) -> np.ndarray:
    return data.values[:, data.columns.index(name)]


def list_metrics(members, data, campaign, objective) -> dict:
    """The D-17 numbers of one list: n, the share of members whose dominant topic is the campaign's, the mean raw
    share of the campaign's topic column, total Argentine reach, total cost, cost per thousand Argentines as
    total cost / total reach x 1000 (a ratio of sums) and the mean of the criterion in its own units. With no
    members the totals are 0 and every share, ratio and mean is NaN."""
    members = list(members)
    n = len(members)
    reach = _column(data, "estimated_argentina_reach")[members]
    price = _column(data, "price_usd")[members]
    reach_total = float(reach.sum())
    cost_total = float(price.sum())
    if n == 0:
        nan = math.nan
        return {"n": 0, "topic_dominant_share": nan, "topic_mean_pct": nan, "reach_total": reach_total,
                "cost_total": cost_total, "cost_per_thousand": nan, "criterion_mean": nan}
    labels = campaigns_select.dominant_topics(data)
    topic_column = {label: name for name, label in campaigns_select.TOPICS}[campaign]
    value, _ascending, _secondary = campaigns_select.criterion(data, objective)
    return {
        "n": n,
        "topic_dominant_share": sum(1 for i in members if labels[i] == campaign) / n,
        "topic_mean_pct": float(_column(data, topic_column)[members].mean()),
        "reach_total": reach_total,
        "cost_total": cost_total,
        "cost_per_thousand": float(campaigns_select.cost_per_thousand(cost_total, reach_total)),
        "criterion_mean": float(value[members].mean()),
    }


def objective_means(members, data, objective) -> dict:
    """{variable: list mean of the raw values} for every variable the objective's criterion uses, in
    campaigns_select.OBJECTIVE_COLUMNS order (D-17); NaN for each variable when the list is empty."""
    members = list(members)
    return {variable: float(_column(data, variable)[members].mean()) if members else math.nan
            for variable in campaigns_select.OBJECTIVE_COLUMNS[objective]}


def index_top_overlap(members, oja_index, k=campaigns_select.K) -> int:
    """How many members are among the k largest values of the Oja index (D-02 sign, exact ties by row order):
    the lists do not coincide with the top of the index (D-15)."""
    top = np.argsort(-np.asarray(oja_index, dtype=np.float64), kind="stable")[:k]
    return overlap(members, top.tolist())


# ----------------------------------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------------------------------


def _read_columns(path, ids, columns, hint) -> dict:
    """Named columns of a generated CSV, as strings; the creator_id order must be the one of datos/creadores.csv."""
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"{path} not found; run `{hint}`")
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    header, body = rows[0], rows[1:]
    for column in ("creator_id", *columns):
        if column not in header:
            raise SystemExit(f"{path}: no {column!r} column in the header {header[:6]}")
    if [row[header.index("creator_id")] for row in body] != list(ids):
        raise SystemExit(f"{path}: the creators are not the ones of datos/creadores.csv in the same order")
    return {column: [row[header.index(column)] for row in body] for column in columns}


def read_oja_index(path, ids) -> np.ndarray:
    """The oja_index column of analysis/results/oja/index.csv in the order of datos/creadores.csv (D-13)."""
    return np.array([float(v) for v in _read_columns(path, ids, ["oja_index"], "make oja")["oja_index"]],
                    dtype=np.float64)


def read_oja_rank(path, ids) -> np.ndarray:
    """rank_oja of index.csv (1 = the largest index with the D-02 sign)."""
    return np.array([int(v) for v in _read_columns(path, ids, ["rank_oja"], "make oja")["rank_oja"]],
                    dtype=np.int64)


def read_pc_scores(path, ids) -> np.ndarray:
    """PC1 and PC2 scores of the audited PCA, one row per creator in the order of datos/creadores.csv."""
    columns = _read_columns(path, ids, ["PC1", "PC2"], "make pca")
    return np.column_stack([[float(v) for v in columns["PC1"]], [float(v) for v in columns["PC2"]]])


def read_explained(path=PCA_EIGENVALUES) -> tuple[float, float]:
    """Explained variance fraction of PC1 and PC2 from eigenvalues.csv."""
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"{path} not found; run `make pca`")
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    by = {row["component"]: float(row["explained"]) for row in rows}
    if "PC1" not in by or "PC2" not in by:
        raise SystemExit(f"{path}: PC1 or PC2 missing")
    return by["PC1"], by["PC2"]


def read_som_bmu(stage1=STAGE1, ids=None):
    """(k, label, figure_seed, bmu) of the figure run of the chosen grid (D-14). Refuses without selection.json,
    when the Phase 2 rule changed since stage 1, when no grid was chosen, or when the run does not match the
    creators."""
    stage1 = Path(stage1)
    selection_path = stage1 / "selection.json"
    if not selection_path.is_file():
        raise SystemExit(f"{selection_path} not found; run `make som-stage1`")
    som_stage.require_same_rule(selection_path, TP_DIR / PHASE2_RULE_FILE)
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection.get("chosen_k") is None or selection.get("outcome") != "chosen":
        raise SystemExit(f"selection.json has no chosen grid (outcome {selection.get('outcome')!r}): "
                         "no creator is located on the map (D-14)")
    k = int(selection["chosen_k"])
    run = som.read_run(TP_DIR / selection["figure_run"])
    if run.k != k:
        raise SystemExit(f"figure run has grid_k {run.k}, selection.json chose k = {k}")
    _features, _z, meta = pca.read_prepared("creadores_zscore")
    if len(run.bmu) != len(meta["creator_id"]) or (ids is not None and list(ids) != list(meta["creator_id"])):
        raise SystemExit("the figure run and datos/creadores.csv list different creators")
    return k, str(selection["chosen_label"]), int(selection["figure_seed"]), run.bmu


# ----------------------------------------------------------------------------------------------
# Writers (byte-stable: repr floats, "\n" line ends)
# ----------------------------------------------------------------------------------------------


def _cell(value):
    if isinstance(value, (float, np.floating)):
        return repr(float(value))
    return value


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow([_cell(c) for c in row])


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _decimal(value: float, digits: int) -> str:
    """Spanish decimals for the report lines: comma instead of point; NaN is written n/d."""
    if math.isnan(value):
        return "n/d"
    return f"{value:.{digits}f}".replace(".", ",")


def _percent(value: float) -> str:
    return "n/d" if math.isnan(value) else f"{value * 100:.1f} %".replace(".", ",")


# ----------------------------------------------------------------------------------------------
# The six pairs, three lists each
# ----------------------------------------------------------------------------------------------


def build_entries(data, oja_index) -> list[dict]:
    """One entry per (campaign, objective, list) in the fixed order: CAMPAIGNS order, then propia,
    followers_global, followers_tema; each with its members in rank order and its D-17 metrics."""
    entries = []
    for campaign, objectives in campaigns_select.CAMPAIGNS:
        for objective in objectives:
            members = {
                "propia": campaigns_select.shortlist(data, oja_index, campaign, objective),
                "followers_global": campaigns_select.followers_global(data, oja_index),
                "followers_tema": campaigns_select.followers_in_topic(data, oja_index, campaign),
            }
            for name in LIST_NAMES:
                metrics = list_metrics(members[name], data, campaign, objective)
                metrics["overlap_followers_global"] = overlap(members[name], members["followers_global"])
                metrics["overlap_followers_tema"] = overlap(members[name], members["followers_tema"])
                entries.append({"campaign": campaign, "objective": objective, "list": name,
                                "members": members[name], "metrics": metrics})
    return entries


def shortlist_rows(entries, data, reading) -> list[list]:
    """One row per member in rank order; `reading` holds the per-creator arrays that only describe the lists:
    oja_index, oja_rank, pc (n x 2) and bmu with the grid side k (D-14, D-15)."""
    k = reading["k"]
    labels = campaigns_select.dominant_topics(data)
    followers = _column(data, "followers")
    reach = _column(data, "estimated_argentina_reach")
    price = _column(data, "price_usd")
    unit_cost = campaigns_select.cost_per_thousand(price, reach)
    criteria = {objective: campaigns_select.criterion(data, objective) for objective in campaigns_select.OBJECTIVES}
    rows = []
    for entry in entries:
        value, _ascending, secondary = criteria[entry["objective"]]
        for rank, i in enumerate(entry["members"], start=1):
            rows.append([entry["campaign"], entry["objective"], entry["list"], rank, data.ids[i], data.names[i],
                         labels[i], float(value[i]), "" if secondary is None else float(secondary[i]),
                         float(followers[i]), float(reach[i]), float(price[i]), float(unit_cost[i]),
                         float(reading["oja_index"][i]), int(reading["oja_rank"][i]),
                         float(reading["pc"][i, 0]), float(reading["pc"][i, 1]), int(reading["bmu"][i]),
                         int(reading["bmu"][i]) // k, int(reading["bmu"][i]) % k])
    return rows


def comparison_rows(entries) -> list[list]:
    return [[e["campaign"], e["objective"], e["list"], *(e["metrics"][c] for c in COMPARISON_COLUMNS[3:])]
            for e in entries]


def report_campaigns_lines(identity, entries, data) -> list[str]:
    lines = [f"- Commit de la regla: {identity['rule_commit'][:12]} (sha256 del texto entre marcadores: "
             f"{identity['rule_sha256'][:12]})"]
    for e in entries:
        names = ", ".join(data.names[i] for i in e["members"]) or "(lista vacía)"
        lines.append(f"- {e['campaign']} / {e['objective']} — {LIST_LABELS[e['list']]}: {names}")
    lines.append("")
    lines.append(TABLE_HEADER)
    lines.append("|" + "---|" * 11)
    for e in entries:
        m = e["metrics"]
        lines.append("| " + " | ".join([
            f"{e['campaign']} / {e['objective']}", LIST_LABELS[e["list"]], str(m["n"]),
            str(m["overlap_followers_global"]), str(m["overlap_followers_tema"]),
            _percent(m["topic_dominant_share"]), _decimal(m["topic_mean_pct"], 1),
            f"{round(m['reach_total']):d}", f"{round(m['cost_total']):d}", _decimal(m["cost_per_thousand"], 2),
            _decimal(m["criterion_mean"], 3)]) + " |")
    return lines


def objective_metrics_rows(entries, data) -> list[list]:
    return [[e["campaign"], e["objective"], e["list"], variable, mean]
            for e in entries for variable, mean in objective_means(e["members"], data, e["objective"]).items()]


def criterion_means_lines(entries, data) -> list[str]:
    """One bullet per list with the means of the raw variables its criterion uses (D-17)."""
    lines = []
    for e in entries:
        means = objective_means(e["members"], data, e["objective"])
        text = "; ".join(f"{variable} {_decimal(mean, 3)}" for variable, mean in means.items())
        lines.append(f"- {e['campaign']} / {e['objective']} — {LIST_LABELS[e['list']]}, medias del criterio: {text}")
    return lines


def _reading_bullet(label, members, oja_index, oja_rank, pc, bmu, k) -> str:
    n = len(members)
    ranks = ", ".join(str(int(oja_rank[i])) for i in members) or "ninguno"
    neurons = ", ".join(f"({int(bmu[i]) // k}, {int(bmu[i]) % k})" for i in members) or "ninguna"
    pc1 = _decimal(float(pc[members, 0].mean()), 2) if n else "n/d"
    pc2 = _decimal(float(pc[members, 1].mean()), 2) if n else "n/d"
    return (f"- {label}: {index_top_overlap(members, oja_index)} de {n} en el top 5 del índice de Oja; rangos del "
            f"índice (1 = máximo): {ranks}; PC1 media {pc1}; PC2 media {pc2}; neuronas (fila, col): {neurons}")


def report_reading_lines(entries, oja_index, oja_rank, pc, bmu, k) -> list[str]:
    """Kohonen, Oja and PCA reading of every own list, then of the followers-global baseline of each campaign."""
    lines = [_reading_bullet(f"{e['campaign']} / {e['objective']}", e["members"], oja_index, oja_rank, pc, bmu, k)
             for e in entries if e["list"] == "propia"]
    for campaign, _objectives in campaigns_select.CAMPAIGNS:
        first = next(e for e in entries if e["campaign"] == campaign and e["list"] == "followers_global")
        lines.append(_reading_bullet(f"{campaign}, línea base followers global", first["members"], oja_index,
                                     oja_rank, pc, bmu, k))
    return lines


# ----------------------------------------------------------------------------------------------
# Figures (D-14, D-15: they describe the lists, they never choose them)
# ----------------------------------------------------------------------------------------------

MARKERS = ("o", "s", "^")


def _own_groups(entries, campaign) -> list[tuple[str, list[int]]]:
    return [(e["objective"], e["members"]) for e in entries if e["campaign"] == campaign and e["list"] == "propia"]


def _global_members(entries, campaign) -> list[int]:
    return next(e["members"] for e in entries if e["campaign"] == campaign and e["list"] == "followers_global")


def plot_shortlists_biplot(entries, pc, explained, out_stem) -> None:
    """2 x 2 figure, one panel per campaign: every creator as a grey point on PC1 (x) and PC2 (y), the campaign's
    own list or lists as filled markers (one colour and shape per objective), the global followers baseline as
    hollow black markers."""
    plt = plots_style.apply_style()
    slide = plots_style.variant() == "slide"
    fig, axes = plt.subplots(2, 2, figsize=plots_style.figsize((11.5, 9.4)), sharex=True, sharey=True)
    objectives = [objective for _campaign, objectives in campaigns_select.CAMPAIGNS for objective in objectives]
    colors = plots_style.palette_for(objectives)
    for ax, (campaign, _objs) in zip(axes.ravel(), campaigns_select.CAMPAIGNS):
        ax.axhline(0, color=plots_style.GRID, linewidth=1, zorder=0)
        ax.axvline(0, color=plots_style.GRID, linewidth=1, zorder=0)
        ax.scatter(pc[:, 0], pc[:, 1], s=26, color="#c9c8c3", zorder=1, label="50 creadores" if slide else "los 50 creadores")
        base = _global_members(entries, campaign)
        ax.scatter(pc[base, 0], pc[base, 1], s=170, facecolors="none", edgecolors="black", linewidths=1.6,
                   zorder=3, label="base: followers" if slide else "línea base: followers global")
        for index, (objective, members) in enumerate(_own_groups(entries, campaign)):
            ax.scatter(pc[members, 0], pc[members, 1], s=70, marker=MARKERS[index % len(MARKERS)],
                       color=colors[objective], edgecolor=plots_style.SURFACE, linewidth=1.2, zorder=4,
                       label=objective if slide else f"lista propia: {objective}")
        ax.set_title(campaign, fontsize=plots_style.fontsize(11), loc="left")
        if slide:  # a legend over the points hides them: it sits to the right of its panel, own lists by name
            ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=plots_style.fontsize(7.5),
                      frameon=False, borderaxespad=0.0)
        else:
            ax.legend(loc="best", fontsize=plots_style.fontsize(7.5), frameon=True, facecolor=plots_style.SURFACE)
    for ax in axes[1]:
        ax.set_xlabel(f"PC1 ({_decimal(explained[0] * 100, 1)} %)")
    for ax in axes[:, 0]:
        ax.set_ylabel(f"PC2 ({_decimal(explained[1] * 100, 1)} %)")
    plots_style.suptitle(fig, "Listas por campaña sobre el plano PC1-PC2", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=plots_style.rect((0, 0.07, 1, 0.96)))
    plots_style.caption(fig, "Misma orientación que la sección 5 del fragmento de la Fase 1 (el coeficiente de mayor "
                           "valor absoluto de cada componente es positivo). La posición describe las listas; no "
                           "decide quién entra a ninguna (D-15).", width=140)
    plots_style.save_figure(fig, out_stem)


def plot_shortlists_som(entries, bmu, k, label, seed, out_stem) -> None:
    """2 x 2 figure, one k x k grid per campaign: the hits of the figure run as a light shading and, in each
    neuron, the number of the campaign's own-list creators it holds (football: the union of its three lists)."""
    plt = plots_style.apply_style()
    hits = np.bincount(np.asarray(bmu, dtype=np.int64), minlength=k * k)
    slide = plots_style.variant() == "slide"
    # slide: the four grids in a row (square cells fill the 2.6:1 box); report: 2 x 2
    fig, axes = plt.subplots(1 if slide else 2, 4 if slide else 2, figsize=plots_style.figsize((10.4, 10.4)))
    cmap = plt.get_cmap("Blues")
    top = max(int(hits.max()), 1)
    for ax, (campaign, _objs) in zip(axes.ravel(), campaigns_select.CAMPAIGNS):
        chosen = sorted({i for _objective, members in _own_groups(entries, campaign) for i in members})
        counts = np.bincount(np.asarray([bmu[i] for i in chosen], dtype=np.int64), minlength=k * k)
        for neuron in range(k * k):
            row, col = divmod(neuron, k)
            shade = 0.45 * hits[neuron] / top
            ax.add_patch(plt.Rectangle((col - 0.5, row - 0.5), 1, 1, facecolor=cmap(shade) if hits[neuron] else
                                       plots_style.SURFACE, edgecolor=plots_style.GRID, linewidth=1.0))
            if counts[neuron] > 0:
                ax.text(col, row, str(int(counts[neuron])), ha="center", va="center",
                        fontsize=plots_style.fontsize(15), fontweight="bold", color=plots_style.TEXT_PRIMARY)
        som_figures._grid_axes(ax, k)
        ax.set_aspect("equal")
        if slide:
            ax.set_title(f"{campaign}\n{len(chosen)} de la lista propia", fontsize=plots_style.fontsize(8),
                         loc="left")
        else:
            ax.set_title(f"{campaign}: {len(chosen)} creadores de la lista propia", fontsize=10, loc="left")
    plots_style.suptitle(fig, f"Listas por campaña sobre el mapa SOM {k} x {k}", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=plots_style.rect((0, 0.07, 1, 0.96)))
    plots_style.caption(fig, f"Kohonen solo describe (D-14): la neurona no cambia la selección; la orientación del "
                           f"mapa es arbitraria; k = {k} ({label}), seed {seed} de las figuras. El sombreado es "
                           "la cantidad de creadores de cada neurona y el número, los creadores de la lista "
                           "propia de la campaña (fútbol: la unión de sus tres listas).", width=125)
    plots_style.save_figure(fig, out_stem)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Campaign lists by the committed rule and the followers baselines.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="output folder (default: analysis/results/campaigns)")
    args = parser.parse_args(argv)
    out: Path = args.out

    # D-07: the rule is checked before anything is read or created; a SystemExit leaves nothing behind.
    identity = campaigns_select.rule_identity()

    data = load_creadores()
    oja_index = read_oja_index(OJA_INDEX, data.ids)
    oja_rank = read_oja_rank(OJA_INDEX, data.ids)
    pc = read_pc_scores(PCA_SCORES, data.ids)
    explained = read_explained()
    k, label, seed, bmu = read_som_bmu(STAGE1, data.ids)
    entries = build_entries(data, oja_index)
    reading = {"oja_index": oja_index, "oja_rank": oja_rank, "pc": pc, "bmu": bmu, "k": k}

    out.mkdir(parents=True, exist_ok=True)
    pairs = [{"campaign": campaign, "objective": objective}
             for campaign, objectives in campaigns_select.CAMPAIGNS for objective in objectives]
    (out / "selection_identity.json").write_text(
        json.dumps({**identity, "k": campaigns_select.K, "pairs": pairs}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    _write_csv(out / "shortlists.csv", SHORTLIST_COLUMNS + READING_COLUMNS, shortlist_rows(entries, data, reading))
    _write_csv(out / "comparison.csv", COMPARISON_COLUMNS, comparison_rows(entries))
    _write_csv(out / "objective_metrics.csv", OBJECTIVE_METRICS_COLUMNS, objective_metrics_rows(entries, data))
    _write_lines(out / "report_campaigns.md", [*report_campaigns_lines(identity, entries, data), "",
                                               *criterion_means_lines(entries, data)])
    _write_lines(out / "report_reading.md", report_reading_lines(entries, oja_index, oja_rank, pc, bmu, k))
    for _ in plots_style.iter_variants():  # report, then slide (D-08): the data above is computed once
        plot_shortlists_biplot(entries, pc, explained, out / "shortlists_biplot")
        plot_shortlists_som(entries, bmu, k, label, seed, out / "shortlists_som")
    print(f"campaigns -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
