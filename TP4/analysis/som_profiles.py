#!/usr/bin/env python3
"""Regions, raw-unit profiles and the PC1/PC2 contrast of the chosen Kohonen map (SOM-05).

    .venv/bin/python analysis/som_profiles.py [--stage1 DIR] [--out DIR]

The region rule and the contrast statistics are the ones committed in section 2 of deliverables/02-kohonen.md
(**Regiones.** and **Contraste con PC1/PC2.**) before any result was looked at: regions are the 4-adjacency
connected components of the occupied neurons after cutting every adjacent pair whose prototype distance exceeds
the 75th percentile of all adjacent-pair distances; a region with fewer than 2 creators is "no interpretable".
The contrast is R^2 of PC1 and PC2 on the BMU (row, col), a tie-aware Mantel-type Spearman between grid distances
and PC1-PC2 plane distances (the 26-D z distance as reference), and the edge-wise Spearman between U-matrix edges
and the PC1 and PC2 gaps, with 1 000 permutations from a generator seeded with 2026. Only the grid chosen by
the rule is profiled (D-14), and main refuses to start when the rule sha256 differs from the one stage 1 recorded.
numpy, matplotlib (through plots_style) and the standard library only (Phase 1 D-06).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import pca  # noqa: E402
import plots_style  # noqa: E402
import som  # noqa: E402
import som_figures  # noqa: E402
import som_stage  # noqa: E402
from creadores import load_creadores, scaler_from_meta  # noqa: E402

DEFAULT_STAGE1 = TP_DIR / "analysis" / "results" / "som" / "series_som_stage1"
DEFAULT_OUT = TP_DIR / "analysis" / "results" / "som" / "profiles"
RULE_FILE = TP_DIR / "deliverables" / "02-kohonen.md"

REGION_PERCENTILE = 75.0
MIN_MEMBERS = 2
PERMUTATION_SEED = 2026
N_PERMUTATIONS = 1000
PROFILE_COLUMNS = ("followers", "estimated_argentina_reach", "argentina_audience_pct",
                   "total_engagement_per_1000", "price_usd", "sponsored_posts_pct",
                   "topic_football_pct", "topic_makeup_pct", "topic_dogs_pct", "topic_art_pct")
KIND_PLANE_CLOSE = "plano_cerca_grilla_lejos"
KIND_PLANE_FAR = "plano_lejos_grilla_cerca"
CLOSE_QUANTILE = 25.0


@dataclass(frozen=True)
class RegionResult:
    labels: np.ndarray  # k^2 ints: region id, -1 for an empty neuron
    threshold: float
    cut: np.ndarray  # bool per adjacent pair (som.adjacent_pairs order): distance above the threshold
    sizes: np.ndarray  # creators per region
    interpretable: np.ndarray  # bool per region: sizes >= MIN_MEMBERS


# ---------- regions and profiles ----------

def regions(protos, hits, k: int, percentile: float = REGION_PERCENTILE) -> RegionResult:
    """The committed region rule. An adjacent pair joins two neurons when both are occupied and its prototype
    distance is at most the percentile (numpy linear) of the distances of all adjacent pairs; regions are the
    connected components of the occupied neurons, numbered by the smallest neuron index of each."""
    hits = np.asarray(hits)
    pairs = som.adjacent_pairs(k)
    distances = som.edge_distances(protos, k)
    threshold = float(np.percentile(distances, percentile))
    cut = distances > threshold
    neighbours: list[list[int]] = [[] for _ in range(k * k)]
    for (a, b), is_cut in zip(pairs, cut):
        if not is_cut and hits[a] > 0 and hits[b] > 0:
            neighbours[a].append(b)
            neighbours[b].append(a)
    labels = np.full(k * k, -1, dtype=np.int64)
    sizes: list[int] = []
    for start in range(k * k):
        if hits[start] == 0 or labels[start] != -1:
            continue
        region = len(sizes)
        labels[start] = region
        queue = deque([start])
        total = 0
        while queue:
            neuron = queue.popleft()
            total += int(hits[neuron])
            for other in neighbours[neuron]:
                if labels[other] == -1:
                    labels[other] = region
                    queue.append(other)
        sizes.append(total)
    sizes_array = np.array(sizes, dtype=np.int64)
    return RegionResult(labels, threshold, cut, sizes_array, sizes_array >= MIN_MEMBERS)


def profiles(group_of_creator, raw_values, columns) -> list[dict]:
    """One row per group id >= 0 (ascending): its creator count n and the mean of every column in the units of
    raw_values. Group -1 (creators with no group) is not profiled."""
    group_of_creator = np.asarray(group_of_creator)
    raw_values = np.asarray(raw_values, dtype=np.float64)
    rows = []
    for group in sorted(int(g) for g in set(group_of_creator.tolist()) if g >= 0):
        members = raw_values[group_of_creator == group]
        row = {"group": group, "n": int(len(members))}
        for index, name in enumerate(columns):
            row[name] = float(members[:, index].mean())
        rows.append(row)
    return rows


# ---------- PC1/PC2 contrast: statistics and permutation nulls ----------

def grid_r2(y, rows, cols) -> float:
    """R^2 of the least-squares fit of y on [1, row, col]."""
    y = np.asarray(y, dtype=np.float64)
    design = np.column_stack([np.ones(len(y)), np.asarray(rows, dtype=np.float64),
                              np.asarray(cols, dtype=np.float64)])
    coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - design @ coefficients
    total = float(np.sum((y - y.mean()) ** 2))
    if total == 0.0:
        return 0.0
    return 1.0 - float(np.sum(residual ** 2)) / total


def permutation_pvalue(observed: float, null) -> float:
    """One-sided permutation p-value with the observed value counted in: (1 + #(null >= observed)) / (1 + N)."""
    null = np.asarray(null)
    return (1.0 + float(np.sum(null >= observed))) / (1.0 + len(null))


def r2_null(y, rows, cols, rng, n: int = N_PERMUTATIONS) -> np.ndarray:
    """R^2 under n permutations of the (row, col) pairs among creators."""
    rows = np.asarray(rows)
    cols = np.asarray(cols)
    out = np.empty(n, dtype=np.float64)
    for index in range(n):
        order = rng.permutation(len(rows))
        out[index] = grid_r2(y, rows[order], cols[order])
    return out


def plane_distance_vector(points) -> np.ndarray:
    """Euclidean distance between every pair of creators in the given coordinates, upper triangle in the pair
    order of som.grid_distance_vector."""
    points = np.asarray(points, dtype=np.float64)
    i, j = np.triu_indices(len(points), 1)
    return np.sqrt(np.sum((points[i] - points[j]) ** 2, axis=1))


def mantel_null(bmu, k: int, plane_points, rng, n: int = N_PERMUTATIONS) -> np.ndarray:
    """Mantel-type null: the grid-distance vector stays fixed, the creator order of plane_points is permuted and
    the tie-aware Spearman between the two distance vectors is recomputed."""
    plane_points = np.asarray(plane_points, dtype=np.float64)
    grid = som.grid_distance_vector(bmu, k)
    full = np.sqrt(np.sum((plane_points[:, None, :] - plane_points[None, :, :]) ** 2, axis=2))
    i, j = np.triu_indices(len(plane_points), 1)
    out = np.empty(n, dtype=np.float64)
    for index in range(n):
        order = rng.permutation(len(plane_points))
        out[index] = som.spearman_ties(grid, full[order][:, order][i, j])
    return out


def _neuron_means(hits, bmu, values) -> np.ndarray:
    means = np.full(len(hits), np.nan)
    values = np.asarray(values, dtype=np.float64)
    for neuron in range(len(hits)):
        members = values[np.asarray(bmu) == neuron]
        if len(members):
            means[neuron] = float(members.mean())
    return means


def edge_contrast(protos, hits, bmu, k: int, pc) -> dict:
    """Edge-wise Spearman between the prototype distance of every adjacent pair of occupied neurons and the gap
    of the neuron-mean PC1, and of PC2, between its two neurons. Pairs touching an empty neuron are excluded
    and counted."""
    hits = np.asarray(hits)
    pc = np.asarray(pc, dtype=np.float64)
    pairs = som.adjacent_pairs(k)
    distances = som.edge_distances(protos, k)
    means = [_neuron_means(hits, bmu, pc[:, column]) for column in (0, 1)]
    keep = [index for index, (a, b) in enumerate(pairs) if hits[a] > 0 and hits[b] > 0]
    result = {"n_edges": len(keep), "n_excluded": len(pairs) - len(keep)}
    for name, neuron_mean in zip(("rho_pc1", "rho_pc2"), means):
        gaps = [abs(neuron_mean[pairs[i][0]] - neuron_mean[pairs[i][1]]) for i in keep]
        result[name] = som.spearman_ties(distances[keep], gaps)
    return result


# ---------- what the highest U-matrix edges are made of ----------

def high_u_edges(protos, hits, k: int, features, std, top_edges: int = 3, top_vars: int = 3) -> list[dict]:
    """The top_edges adjacent pairs of occupied neurons with the largest prototype distance (ties: pair order)
    and, per edge, the top_vars features by |delta z| (delta = prototype of the higher neuron minus the lower),
    each with delta z and delta raw = delta z * std of that feature."""
    hits = np.asarray(hits)
    protos = np.asarray(protos, dtype=np.float64)
    std = np.asarray(std, dtype=np.float64)
    pairs = som.adjacent_pairs(k)
    distances = som.edge_distances(protos, k)
    candidates = [index for index, (a, b) in enumerate(pairs) if hits[a] > 0 and hits[b] > 0]
    ranked = sorted(candidates, key=lambda index: (-distances[index], index))[:top_edges]
    edges = []
    for rank, index in enumerate(ranked, start=1):
        a, b = pairs[index]
        delta = protos[b] - protos[a]
        order = sorted(range(len(features)), key=lambda f: (-abs(delta[f]), f))[:top_vars]
        edges.append({
            "rank": rank, "neuron_a": a, "neuron_b": b, "distance": float(distances[index]),
            "variables": [{"variable": features[f], "delta_z": float(delta[f]),
                           "delta_raw": float(delta[f] * std[f])} for f in order],
        })
    return edges


def disagreements(bmu, k: int, plane_points, top: int = 3) -> list[dict]:
    """Creator pairs where the map and the PC1-PC2 plane tell different stories.

    KIND_PLANE_CLOSE: among the pairs whose plane distance is at most the 25th percentile of all pair distances,
    the `top` farthest apart on the grid (ties: smaller plane distance, then creator index).
    KIND_PLANE_FAR: among the pairs that share a neuron or are 4-adjacent (grid distance at most 1), the `top`
    farthest apart in the plane (ties: creator index). Creator indices follow the row order of plane_points."""
    plane = plane_distance_vector(plane_points)
    grid = som.grid_distance_vector(bmu, k)
    i, j = np.triu_indices(len(np.asarray(plane_points)), 1)
    order_index = np.arange(len(plane))  # upper-triangle order is (a, b) lexicographic: creator index order
    limit = float(np.percentile(plane, CLOSE_QUANTILE))
    close = [p for p in order_index if plane[p] <= limit]
    close.sort(key=lambda p: (-grid[p], plane[p], p))
    far = [p for p in order_index if grid[p] <= 1.0 + 1e-12]
    far.sort(key=lambda p: (-plane[p], p))
    rows = []
    for kind, chosen in ((KIND_PLANE_CLOSE, close[:top]), (KIND_PLANE_FAR, far[:top])):
        for p in chosen:
            rows.append({"kind": kind, "creator_a": int(i[p]), "creator_b": int(j[p]),
                         "plane_distance": float(plane[p]), "grid_distance": float(grid[p])})
    return rows
