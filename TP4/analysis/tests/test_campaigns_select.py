"""Tests of the pre-registered campaign selection rule (D-07..D-17): every term on synthetic creators, and the
rule_identity guard in temporary git repositories. No real creator is read here."""

from __future__ import annotations

import hashlib
import subprocess

import numpy as np
import pytest

import campaigns_select as cs
import pca
from creadores import Creadores

TOPIC_COLUMNS = [name for name, _ in cs.TOPICS]
LABELS = [label for _, label in cs.TOPICS]


def build(n, **columns):
    """Synthetic Creadores: ids INF001.., only the columns given (each a list of n numbers)."""
    names = list(columns)
    values = np.empty((n, len(names)), dtype=np.float64)
    for j, name in enumerate(names):
        if len(columns[name]) != n:
            raise ValueError(f"{name}: {len(columns[name])} values for {n} rows")
        values[:, j] = columns[name]
    ids = [f"INF{i + 1:03d}" for i in range(n)]
    return Creadores(ids=ids, names=[f"@c{i + 1}" for i in range(n)], columns=names, values=values)


def topic_columns(labels):
    """The four raw topic shares for creators whose dominant topic is the given label (80 for it, 20/3 else)."""
    columns = {name: [] for name in TOPIC_COLUMNS}
    for label in labels:
        for name, topic in cs.TOPICS:
            columns[name].append(80.0 if topic == label else 20.0 / 3)
    return columns


def depth_data():
    """Eight creators with distinct values in every depth column and in total_engagement_per_1000."""
    return build(
        8,
        content_tutorial_pct=[10, 20, 30, 40, 50, 60, 70, 95],
        saves_per_1000=[5, 1, 9, 3, 7, 2, 8, 4],
        average_watch_time_seconds=[12, 30, 18, 6, 24, 9, 15, 21],
        total_engagement_per_1000=[100, 40, 90, 20, 60, 70, 10, 50],
    )


def depth_scores(data):
    columns = [data.values[:, data.columns.index(c)] for c in cs.DEPTH_COLUMNS]
    z = [(c - c.mean()) / c.std(ddof=1) for c in columns]
    return (z[0] + z[1] + z[2]) / 3


def test_topics_match_pca():
    assert cs.TOPICS == pca.TOPICS
    assert cs.K == 5


def test_dominant_topics_argmax_and_tie_order():
    data = build(
        6,
        topic_football_pct=[50, 10, 10, 40, 10, 30],
        topic_makeup_pct=[20, 60, 10, 10, 10, 30],
        topic_dogs_pct=[20, 20, 70, 40, 45, 20],
        topic_art_pct=[10, 10, 10, 10, 35, 20],
    )
    assert cs.dominant_topics(data) == ["fútbol", "maquillaje", "perros", "fútbol", "perros", "fútbol"]
    # row 3: fútbol and perros tied at the top -> fútbol; row 5: fútbol and maquillaje tied -> fútbol (the first
    # of fútbol, maquillaje, perros, arte); row 4 is perros alone
    # perros and arte tied at the top -> perros
    tie = build(2, topic_football_pct=[10, 10], topic_makeup_pct=[10, 10], topic_dogs_pct=[40, 40],
                topic_art_pct=[40, 40])
    assert cs.dominant_topics(tie) == ["perros", "perros"]


def test_topic_members():
    data = build(5, **topic_columns(["perros", "fútbol", "perros", "arte", "perros"]))
    assert cs.topic_members(data, "perros") == [0, 2, 4]
    assert cs.topic_members(data, "fútbol") == [1]
    assert cs.topic_members(data, "maquillaje") == []
    with pytest.raises(ValueError):
        cs.topic_members(data, "cocina")


def test_alcance_descending():
    n = 8
    reach = [10, 90, 50, 70, 30, 80, 60, 20]
    data = build(n, **topic_columns(["fútbol"] * 7 + ["arte"]), estimated_argentina_reach=reach)
    oja = np.zeros(n)
    chosen = cs.shortlist(data, oja, "fútbol", "alcance")
    assert chosen == [1, 5, 3, 6, 2]  # reach 90, 80, 70, 60, 50; row 7 (arte, reach 20) is not a member
    assert len(chosen) == cs.K


def test_cost_per_thousand_ascending_zero_reach_last():
    cost = cs.cost_per_thousand(np.array([100.0, 50.0, 30.0]), np.array([10000.0, 2000.0, 0.0]))
    assert cost[0] == pytest.approx(10.0)
    assert cost[1] == pytest.approx(25.0)
    assert np.isinf(cost[2])
    data = build(3, **topic_columns(["perros"] * 3), price_usd=[50, 30, 100],
                 estimated_argentina_reach=[2000, 0, 10000])
    assert cs.shortlist(data, np.zeros(3), "perros", "costo_por_mil") == [2, 0, 1]
    value, ascending, secondary = cs.criterion(data, "costo_por_mil")
    assert ascending is True and secondary is None and np.isinf(value[1])


def test_depth_mean_of_z_ddof1():
    data = depth_data()
    value, ascending, secondary = cs.criterion(data, "profundidad")
    assert ascending is False and secondary is None
    assert value == pytest.approx(depth_scores(data))
    # the z-scores use the mean and SD of all rows, not of the filter: a filter of a subset leaves them alone
    sub = build(8, **topic_columns(["arte"] * 4 + ["fútbol"] * 4),
                **{c: list(data.values[:, i]) for i, c in enumerate(data.columns)})
    assert cs.criterion(sub, "profundidad")[0] == pytest.approx(depth_scores(data))
    assert cs.zscores(data, "saves_per_1000") == pytest.approx(
        (data.values[:, 1] - data.values[:, 1].mean()) / data.values[:, 1].std(ddof=1))
    flat = build(3, saves_per_1000=[4, 4, 4])
    with pytest.raises(ValueError):
        cs.zscores(flat, "saves_per_1000")


def test_engagement_depth_half_and_half():
    data = depth_data()
    engagement = data.values[:, data.columns.index("total_engagement_per_1000")]
    z_engagement = (engagement - engagement.mean()) / engagement.std(ddof=1)
    value, ascending, secondary = cs.criterion(data, "engagement_profundidad")
    assert ascending is False and secondary is None
    assert value == pytest.approx(0.5 * z_engagement + 0.5 * depth_scores(data))


def test_discovery_trend_second_key():
    data = build(
        4,
        **topic_columns(["fútbol"] * 4),
        non_follower_reach_pct=[40.0, 55.0, 55.0, 30.0],
        trend_posts_pct=[10.0, 20.0, 35.0, 90.0],
    )
    value, ascending, secondary = cs.criterion(data, "descubrimiento")
    assert ascending is False
    assert value.tolist() == [40.0, 55.0, 55.0, 30.0]
    assert secondary.tolist() == [10.0, 20.0, 35.0, 90.0]
    # rows 1 and 2 tie on non_follower_reach_pct: the larger trend_posts_pct (row 2) goes first; the trend
    # value never lifts row 3 (trend 90) above a larger non_follower_reach_pct
    assert cs.shortlist(data, np.zeros(4), "fútbol", "descubrimiento") == [2, 1, 0, 3]


def test_tie_break_oja_then_creator_id():
    data = build(4, **topic_columns(["fútbol"] * 4), estimated_argentina_reach=[100.0, 100.0, 100.0, 100.0])
    oja = np.array([0.5, 0.9, 0.5, 0.1])
    # equal criterion: higher Oja index first (row 1), then equal Oja index 0.5 -> smaller creator_id (row 0, row 2)
    assert cs.shortlist(data, oja, "fútbol", "alcance") == [1, 0, 2, 3]
    # the same creator_id order when the Oja index is equal everywhere
    assert cs.shortlist(data, np.zeros(4), "fútbol", "alcance") == [0, 1, 2, 3]
    # creator_id is compared as the id string, not as the row position
    shuffled = Creadores(ids=["INF004", "INF003", "INF002", "INF001"], names=data.names, columns=data.columns,
                         values=data.values)
    assert cs.shortlist(shuffled, np.zeros(4), "fútbol", "alcance") == [3, 2, 1, 0]
    # the Oja index never outranks a different criterion value
    other = build(2, **topic_columns(["fútbol"] * 2), estimated_argentina_reach=[100.0, 101.0])
    assert cs.shortlist(other, np.array([0.99, -0.99]), "fútbol", "alcance") == [1, 0]


def test_shortlist_fewer_than_k_not_padded():
    topics = ["arte"] * 3 + ["fútbol"] * 6 + ["perros"]
    n = len(topics)
    data = build(n, **topic_columns(topics), estimated_argentina_reach=[float(10 * (i + 1)) for i in range(n)],
                 price_usd=[5.0] * n, followers=[float(1000 - i) for i in range(n)])
    oja = np.zeros(n)
    own = cs.shortlist(data, oja, "arte", "alcance")
    assert own == [2, 1, 0]
    assert all(topics[i] == "arte" for i in own)
    in_topic = cs.followers_in_topic(data, oja, "arte")
    assert in_topic == [0, 1, 2]
    assert all(topics[i] == "arte" for i in in_topic)
    assert cs.shortlist(data, oja, "maquillaje", "alcance") == []
    assert cs.followers_in_topic(data, oja, "maquillaje") == []
    assert len(cs.shortlist(data, oja, "fútbol", "alcance")) == cs.K


def test_followers_baselines():
    topics = ["fútbol", "arte", "fútbol", "perros", "arte", "fútbol", "fútbol", "arte", "fútbol", "fútbol"]
    followers = [900.0, 1000.0, 300.0, 800.0, 700.0, 600.0, 200.0, 500.0, 400.0, 100.0]
    n = len(topics)
    data = build(n, **topic_columns(topics), followers=followers)
    oja = np.zeros(n)
    # global: the 5 largest followers, topics ignored (rows 1, 0, 3, 4, 5)
    assert cs.followers_global(data, oja) == [1, 0, 3, 4, 5]
    # inside fútbol: rows 0 (900), 5 (600), 8 (400), 2 (300), 6 (200)
    assert cs.followers_in_topic(data, oja, "fútbol") == [0, 5, 8, 2, 6]
    # an equal-followers pair uses the D-13 tie-break: higher Oja index first, then the smaller creator_id
    tied = build(3, **topic_columns(["fútbol"] * 3), followers=[500.0, 500.0, 500.0])
    assert cs.followers_global(tied, np.array([0.2, 0.7, 0.2])) == [1, 0, 2]
    assert cs.followers_in_topic(tied, np.array([0.2, 0.7, 0.2]), "fútbol") == [1, 0, 2]


def test_campaigns_table():
    assert cs.K == 5
    pairs = [(campaign, objective) for campaign, objectives in cs.CAMPAIGNS for objective in objectives]
    assert pairs == [
        ("fútbol", "alcance"),
        ("fútbol", "descubrimiento"),
        ("fútbol", "profundidad"),
        ("perros", "costo_por_mil"),
        ("maquillaje", "profundidad"),
        ("arte", "engagement_profundidad"),
    ]
    assert set(objective for _, objective in pairs) <= set(cs.OBJECTIVES)
    assert set(cs.OBJECTIVE_COLUMNS) == set(cs.OBJECTIVES)
    assert cs.OBJECTIVE_COLUMNS["descubrimiento"] == ("non_follower_reach_pct", "trend_posts_pct")
    assert cs.OBJECTIVE_COLUMNS["costo_por_mil"] == ("price_usd", "estimated_argentina_reach")
    assert cs.DEPTH_COLUMNS == ("content_tutorial_pct", "saves_per_1000", "average_watch_time_seconds")
    assert cs.ENGAGEMENT_COLUMN == "total_engagement_per_1000"


# ----------------------------------------------------------------------------------------------
# rule_identity, in temporary git repositories
# ----------------------------------------------------------------------------------------------


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                           *args], cwd=repo, check=True, capture_output=True, text=True)


RULE_TEXT = f"# Fase 3\n\n## 4. Regla\n\n{cs.RULE_START}\nk = 5\n**Alcance.** regla\n{cs.RULE_END}\n"


def make_repo(tmp_path, same_commit=True):
    git(tmp_path, "init", "-q")
    (tmp_path / "deliverables").mkdir()
    (tmp_path / "analysis").mkdir()
    rule = tmp_path / cs.RULE_FILE
    select = tmp_path / cs.SELECT_FILE
    rule.write_text(RULE_TEXT, encoding="utf-8")
    select.write_text("K = 5\n", encoding="utf-8")
    if same_commit:
        git(tmp_path, "add", cs.RULE_FILE, cs.SELECT_FILE)
        git(tmp_path, "commit", "-q", "-m", "rule")
    else:
        git(tmp_path, "add", cs.RULE_FILE)
        git(tmp_path, "commit", "-q", "-m", "rule text")
        git(tmp_path, "add", cs.SELECT_FILE)
        git(tmp_path, "commit", "-q", "-m", "rule code")
    return rule, select


def test_rule_identity_accepts_and_ignores_text_outside_markers(tmp_path):
    rule, select = make_repo(tmp_path)
    head = git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    identity = cs.rule_identity(tmp_path)
    assert set(identity) == {"rule_commit", "rule_sha256", "select_sha256"}
    assert identity["rule_commit"] == head and len(identity["rule_commit"]) == 40
    between = RULE_TEXT.split(cs.RULE_START)[1].split(cs.RULE_END)[0]
    assert identity["rule_sha256"] == hashlib.sha256(between.encode("utf-8")).hexdigest()
    assert identity["select_sha256"] == hashlib.sha256(select.read_bytes()).hexdigest()
    # sections added later, outside the markers (committed or not), do not matter
    rule.write_text(RULE_TEXT + "\n## 5. Resultados\n\ntexto nuevo\n", encoding="utf-8")
    assert cs.rule_identity(tmp_path) == identity
    git(tmp_path, "add", cs.RULE_FILE)
    git(tmp_path, "commit", "-q", "-m", "results")
    assert cs.rule_identity(tmp_path) == identity


def test_rule_identity_refuses_changed_rule_text(tmp_path):
    rule, _ = make_repo(tmp_path)
    rule.write_text(RULE_TEXT.replace("k = 5", "k = 6"), encoding="utf-8")
    with pytest.raises(SystemExit) as refused:
        cs.rule_identity(tmp_path)
    assert cs.RULE_FILE in str(refused.value)
    # committing the changed text does not launder it
    git(tmp_path, "add", cs.RULE_FILE)
    git(tmp_path, "commit", "-q", "-m", "changed rule")
    with pytest.raises(SystemExit) as refused_committed:
        cs.rule_identity(tmp_path)
    assert cs.RULE_FILE in str(refused_committed.value)


def test_rule_identity_refuses_changed_select_file(tmp_path):
    _, select = make_repo(tmp_path)
    select.write_text("K = 6\n", encoding="utf-8")
    with pytest.raises(SystemExit) as uncommitted:
        cs.rule_identity(tmp_path)
    assert cs.SELECT_FILE in str(uncommitted.value)
    git(tmp_path, "add", cs.SELECT_FILE)
    git(tmp_path, "commit", "-q", "-m", "changed code")
    with pytest.raises(SystemExit) as later_commit:
        cs.rule_identity(tmp_path)
    assert cs.SELECT_FILE in str(later_commit.value)


def test_rule_identity_refuses_split_commit(tmp_path):
    make_repo(tmp_path, same_commit=False)
    with pytest.raises(SystemExit) as refused:
        cs.rule_identity(tmp_path)
    assert cs.SELECT_FILE in str(refused.value)


def test_rule_identity_refuses_untracked(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "deliverables").mkdir()
    (tmp_path / "analysis").mkdir()
    (tmp_path / cs.RULE_FILE).write_text(RULE_TEXT, encoding="utf-8")
    (tmp_path / cs.SELECT_FILE).write_text("K = 5\n", encoding="utf-8")
    with pytest.raises(SystemExit) as refused:
        cs.rule_identity(tmp_path)
    assert cs.RULE_FILE in str(refused.value)
