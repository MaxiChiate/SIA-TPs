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
came out (PROJECT Key Decisions). numpy, matplotlib (through plots_style) and the standard library only
(Phase 1 D-06).
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
from creadores import load_creadores  # noqa: E402

DEFAULT_OUT = TP_DIR / "analysis" / "results" / "campaigns"
OJA_INDEX = TP_DIR / "analysis" / "results" / "oja" / "index.csv"
PCA_SCORES = TP_DIR / "analysis" / "results" / "pca" / "audited" / "scores.csv"
STAGE1 = TP_DIR / "analysis" / "results" / "som" / "series_som_stage1"
PHASE2_RULE_FILE = "deliverables/02-kohonen.md"

LIST_NAMES = ("propia", "followers_global", "followers_tema")
LIST_LABELS = {"propia": "propia", "followers_global": "followers global", "followers_tema": "followers en el tema"}

SHORTLIST_COLUMNS = ["campaign", "objective", "list", "rank", "creator_id", "name", "dominant_topic", "criterion",
                     "criterion_secondary", "followers", "estimated_argentina_reach", "price_usd",
                     "cost_per_thousand"]
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


def objective_means(members, data, objective):
    raise NotImplementedError  # RED stub of plan 03-05, Task 2


def index_top_overlap(members, oja_index, k=campaigns_select.K):
    raise NotImplementedError  # RED stub of plan 03-05, Task 2


# ----------------------------------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------------------------------


def read_oja_index(path, ids) -> np.ndarray:
    """The oja_index column of analysis/results/oja/index.csv in the order of datos/creadores.csv (D-13)."""
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"{path} not found; run `make oja`")
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    header, body = rows[0], rows[1:]
    for column in ("creator_id", "oja_index"):
        if column not in header:
            raise SystemExit(f"{path}: no {column!r} column in the header {header}")
    if [row[header.index("creator_id")] for row in body] != list(ids):
        raise SystemExit(f"{path}: the creators are not the ones of datos/creadores.csv in the same order")
    return np.array([float(row[header.index("oja_index")]) for row in body], dtype=np.float64)


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


def shortlist_rows(entries, data) -> list[list]:
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
                         float(followers[i]), float(reach[i]), float(price[i]), float(unit_cost[i])])
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
    entries = build_entries(data, oja_index)

    out.mkdir(parents=True, exist_ok=True)
    pairs = [{"campaign": campaign, "objective": objective}
             for campaign, objectives in campaigns_select.CAMPAIGNS for objective in objectives]
    (out / "selection_identity.json").write_text(
        json.dumps({**identity, "k": campaigns_select.K, "pairs": pairs}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    _write_csv(out / "shortlists.csv", SHORTLIST_COLUMNS, shortlist_rows(entries, data))
    _write_csv(out / "comparison.csv", COMPARISON_COLUMNS, comparison_rows(entries))
    _write_lines(out / "report_campaigns.md", report_campaigns_lines(identity, entries, data))
    print(f"campaigns -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
