"""The pre-registered campaign selection rule as code (CAMP-01, CAMP-02, D-07..D-17).

The rule is written in Spanish in deliverables/03-oja-campanas.md section 4, between the markers
`<!-- regla:inicio -->` and `<!-- regla:fin -->`. This module is its executable twin: k, the topic order, the
criterion columns, the composite weights and the tie-break repeat the numbers of that text. The text, this file
and its tests are committed together, before any list is computed (D-07: once a list is seen, none of them
changes). `rule_identity` makes "committed before looking" mechanical: later steps refuse to run on a rule that
was not added in one commit with its code, on code that changed since, or on a changed rule text.

Pure functions over a `Creadores` object (scripts/creadores.py), a per-row Oja index array and numpy; the standard
library for the git checks. Nothing here reads a file of results: the Oja index is an argument, and it enters
only as the exact-tie breaker of D-13. Price, the SOM neuron and the PCA scores never decide who enters a list
(D-12, D-14, D-15).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

from som_select import RULE_END, RULE_START, rule_digest  # noqa: E402,F401

K = 5  # D-09: five creators per list and per strategy

# Same columns, labels and order as analysis/pca.py (a test keeps them equal); defined here so the committed
# rule cannot change through another module.
TOPICS = (
    ("topic_football_pct", "fútbol"),
    ("topic_makeup_pct", "maquillaje"),
    ("topic_dogs_pct", "perros"),
    ("topic_art_pct", "arte"),
)

DEPTH_COLUMNS = ("content_tutorial_pct", "saves_per_1000", "average_watch_time_seconds")
ENGAGEMENT_COLUMN = "total_engagement_per_1000"

OBJECTIVES = ("alcance", "descubrimiento", "profundidad", "costo_por_mil", "engagement_profundidad")
OBJECTIVE_COLUMNS = {
    "alcance": ("estimated_argentina_reach",),
    "descubrimiento": ("non_follower_reach_pct", "trend_posts_pct"),
    "profundidad": DEPTH_COLUMNS,
    "costo_por_mil": ("price_usd", "estimated_argentina_reach"),
    "engagement_profundidad": (ENGAGEMENT_COLUMN, *DEPTH_COLUMNS),
}
CAMPAIGNS = (
    ("fútbol", ("alcance", "descubrimiento", "profundidad")),
    ("perros", ("costo_por_mil",)),
    ("maquillaje", ("profundidad",)),
    ("arte", ("engagement_profundidad",)),
)

RULE_FILE = "deliverables/03-oja-campanas.md"
SELECT_FILE = "analysis/campaigns_select.py"  # this module: guarded and hashed together with the rule text (D-07)

_HEX40 = re.compile(r"[0-9a-f]{40}")


# ----------------------------------------------------------------------------------------------
# The rule (D-08..D-16)
# ----------------------------------------------------------------------------------------------


def _column(data, name) -> np.ndarray:
    if name not in data.columns:
        raise ValueError(f"column {name!r} not found in the creators data")
    return data.values[:, data.columns.index(name)]


def dominant_topics(data) -> list[str]:
    """Label of the largest raw topic share of each creator; an exact tie goes to the first label in TOPICS."""
    shares = np.column_stack([_column(data, name) for name, _ in TOPICS])
    return [TOPICS[int(np.argmax(row))][1] for row in shares]


def topic_members(data, campaign) -> list[int]:
    """Row indices, in row order, of the creators whose dominant topic is the campaign's (the filter)."""
    if campaign not in [label for _, label in TOPICS]:
        raise ValueError(f"unknown campaign {campaign!r}")
    return [i for i, label in enumerate(dominant_topics(data)) if label == campaign]


def zscores(data, column) -> np.ndarray:
    """(x - mean) / SD of the raw values over all rows (ddof = 1), never inside a filter."""
    x = _column(data, column)
    std = float(np.std(x, ddof=1))
    if std == 0.0:
        raise ValueError(f"{column}: zero standard deviation, cannot z-score")
    return (x - float(np.mean(x))) / std


def cost_per_thousand(price, reach) -> np.ndarray:
    """price / reach x 1000 element-wise; a reach <= 0 is an infinite cost (it ranks last)."""
    price = np.asarray(price, dtype=np.float64)
    reach = np.asarray(reach, dtype=np.float64)
    cost = np.full(price.shape, np.inf)
    positive = reach > 0
    cost[positive] = price[positive] / reach[positive] * 1000.0
    return cost


def _depth(data) -> np.ndarray:
    return sum(zscores(data, column) for column in DEPTH_COLUMNS) / len(DEPTH_COLUMNS)


def criterion(data, objective):
    """(value, ascending, secondary) of one objective, in the criterion's own units, one value per row.

    alcance: reach, descending. descubrimiento: non_follower_reach_pct descending, trend_posts_pct is the second
    key. profundidad: mean of the three depth z-scores. costo_por_mil: ascending. engagement_profundidad:
    1/2 z(total_engagement_per_1000) + 1/2 the depth score.
    """
    if objective == "alcance":
        return _column(data, "estimated_argentina_reach").copy(), False, None
    if objective == "descubrimiento":
        return (_column(data, "non_follower_reach_pct").copy(), False,
                _column(data, "trend_posts_pct").copy())
    if objective == "profundidad":
        return _depth(data), False, None
    if objective == "costo_por_mil":
        return (cost_per_thousand(_column(data, "price_usd"), _column(data, "estimated_argentina_reach")),
                True, None)
    if objective == "engagement_profundidad":
        return 0.5 * zscores(data, ENGAGEMENT_COLUMN) + 0.5 * _depth(data), False, None
    raise ValueError(f"unknown objective {objective!r}")


def rank(members, value, ascending, secondary, oja_index, ids) -> list[int]:
    """The members ordered by the criterion, then the second key, then the higher Oja index, then the smaller
    creator_id (D-13); the Oja index and the id only break exact ties."""

    def key(i):
        main = value[i] if ascending else -value[i]
        second = 0.0 if secondary is None else -secondary[i]
        return (main, second, -oja_index[i], ids[i])

    return sorted(members, key=key)


def shortlist(data, oja_index, campaign, objective, k=K) -> list[int]:
    """The first k creators of the campaign's filter under the objective; fewer when the filter is smaller,
    never padded with another topic (D-09)."""
    value, ascending, secondary = criterion(data, objective)
    return rank(topic_members(data, campaign), value, ascending, secondary, oja_index, data.ids)[:k]


def followers_global(data, oja_index, k=K) -> list[int]:
    """Baseline (a): the k largest followers among all creators, same tie-break (D-16)."""
    followers = _column(data, "followers")
    return rank(list(range(len(data.ids))), followers, False, None, oja_index, data.ids)[:k]


def followers_in_topic(data, oja_index, campaign, k=K) -> list[int]:
    """Baseline (b): the k largest followers inside the campaign's filter, same tie-break (D-16)."""
    followers = _column(data, "followers")
    return rank(topic_members(data, campaign), followers, False, None, oja_index, data.ids)[:k]


# ----------------------------------------------------------------------------------------------
# "Committed before looking": the identity of the rule (D-07)
# ----------------------------------------------------------------------------------------------


def _git(args, repo_dir) -> subprocess.CompletedProcess:
    """Argument list, no shell, run in repo_dir; stdout kept as bytes so a file at a commit is exact."""
    return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True)


def _out(result) -> str:
    return result.stdout.decode("utf-8", errors="replace").strip()


def _added_commit(path, repo_dir) -> str:
    result = _git(["log", "--diff-filter=A", "--format=%H", "--", path], repo_dir)
    commit = _out(result)
    if result.returncode != 0 or not _HEX40.fullmatch(commit):
        raise SystemExit(f"{path}: expected exactly one commit that added it, git reports {commit!r} (D-07)")
    return commit


def rule_identity(repo_dir=TP_DIR, rule_file=RULE_FILE, select_file=SELECT_FILE) -> dict:
    """Refuse unless the rule text and this module were added in one commit, the module has not changed since
    and the text between the markers is the one of that commit; return the identity to record.

    Text outside the markers may change (sections 1-3 and 5-7 are added later). Each refusal is a SystemExit
    that names the file.
    """
    repo_dir = Path(repo_dir)
    for path in (rule_file, select_file):
        if _git(["ls-files", "--error-unmatch", "--", path], repo_dir).returncode != 0:
            raise SystemExit(f"{path}: untracked; the rule text and its code must be committed before a list "
                             "is computed (D-07)")
    status = _git(["status", "--porcelain", "--", select_file], repo_dir)
    if status.returncode != 0 or _out(status):
        raise SystemExit(f"{select_file}: has uncommitted changes since the rule commit (D-07)")

    rule_commit = _added_commit(rule_file, repo_dir)
    select_commit = _added_commit(select_file, repo_dir)
    if select_commit != rule_commit:
        raise SystemExit(f"{select_file} was added in commit {select_commit}, not in the rule commit "
                         f"{rule_commit} that added {rule_file} (D-07)")
    later = _git(["log", "--format=%H", f"{rule_commit}..HEAD", "--", select_file], repo_dir)
    if later.returncode != 0 or _out(later):
        raise SystemExit(f"{select_file}: changed in a commit after the rule commit {rule_commit} (D-07)")

    shown = _git(["show", f"{rule_commit}:./{rule_file}"], repo_dir)
    if shown.returncode != 0:
        raise SystemExit(f"{rule_file}: cannot read it at the rule commit {rule_commit} (D-07)")
    with tempfile.TemporaryDirectory() as folder:
        committed = Path(folder) / "rule.md"
        committed.write_bytes(shown.stdout)
        try:
            at_commit = rule_digest(committed)
        except ValueError as error:
            raise SystemExit(f"{rule_file}: the rule commit has no usable rule text: {error} (D-07)")
    try:
        current = rule_digest(repo_dir / rule_file)
    except (OSError, ValueError) as error:
        raise SystemExit(f"{rule_file}: the working file has no usable rule text: {error} (D-07)")
    if current != at_commit:
        raise SystemExit(f"{rule_file}: the text between the markers changed since the rule commit "
                         f"{rule_commit}: {at_commit} != {current} (D-07)")
    return {
        "rule_commit": rule_commit,
        "rule_sha256": current,
        "select_sha256": hashlib.sha256((repo_dir / select_file).read_bytes()).hexdigest(),
    }
