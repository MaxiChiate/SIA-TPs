"""Paired statistics for comparing two things measured on the same seeds (stdlib only).

An exact sign-flip permutation test over 2^n pairings, a percentile bootstrap, and Holm's correction for
testing several variants against the leader. plots_compare.py uses them on a series' variants (paired by
the network's seed) and robustness.py on models evaluated on the same noisy datasets (paired by the noise
seed). Kept apart from plots_compare.py so the latter's plotly import doesn't come along.
"""

from __future__ import annotations

import itertools
import random
import statistics

# Fixed so a reported interval is the same number every time the script runs
BOOTSTRAP_SEED = 20260907
BOOTSTRAP_RESAMPLES = 20000

# Above this many pairs, enumerating every sign flip stops being free (2^n), so the test samples the same
# null distribution instead
EXACT_PERMUTATION_LIMIT = 20


def permutation_p_value(differences: list[float]) -> tuple[float, bool]:
    """Two-sided p for "the sign of each difference was a coin flip".

    The null of a paired randomisation test: if the two variants were interchangeable, relabelling them
    within a seed would be equally likely, so each difference could have carried either sign. p is the
    share of the 2^n sign assignments whose mean is at least as extreme as the observed one. No normality
    assumption, which a few seeds couldn't check anyway.

    Returns `(p, exact)`; `exact` is False when n forced sampling.
    """
    n = len(differences)
    if n == 0:
        return 1.0, True
    observed = abs(statistics.fmean(differences))

    if n <= EXACT_PERMUTATION_LIMIT:
        extreme = sum(abs(statistics.fmean([s * d for s, d in zip(signs, differences)])) >= observed
                      for signs in itertools.product((1, -1), repeat=n))
        return extreme / 2 ** n, True

    rng = random.Random(BOOTSTRAP_SEED)
    extreme = sum(abs(statistics.fmean([d if rng.random() < 0.5 else -d for d in differences])) >= observed
                  for _ in range(BOOTSTRAP_RESAMPLES))
    return extreme / BOOTSTRAP_RESAMPLES, False


def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni, keeping the input order.

    Comparing k variants against the leader is k tests, and at p<0.05 each a false winner among them is
    likelier than not. Holm is the cheap correction that stays valid without assuming independence (the
    tests share the leader's runs).
    """
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    total = len(p_values)
    adjusted = [0.0] * total
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (total - rank) * p_values[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def bootstrap_interval(values: list[float], confidence: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean of `values`; only ever read as "does it clear zero"."""
    if len(values) < 2:
        return (values[0], values[0]) if values else (0.0, 0.0)
    rng = random.Random(BOOTSTRAP_SEED)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(BOOTSTRAP_RESAMPLES))
    tail = (1.0 - confidence) / 2.0
    return means[int(tail * len(means))], means[min(int((1.0 - tail) * len(means)), len(means) - 1)]
