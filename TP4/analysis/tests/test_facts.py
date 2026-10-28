"""Tests of the number formatters and the facts loader of the informe (D-11), on synthetic result trees."""

from __future__ import annotations

import json

import pytest

import facts
import informe


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header)] + [",".join(str(cell) for cell in row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def write_results(root, *, robust=False):
    """A results tree with minimal versions of every file facts.load_facts reads (values chosen to print round)."""
    write_csv(root / "eda/summary_stats.csv", ["variable", "skewness"],
              [["followers", 0.955], ["estimated_argentina_reach", 1.9712], ["average_caption_words", -0.28]])
    write_csv(root / "eda/strong_correlations.csv", ["variable_a", "variable_b", "r"], [
        ["average_reach", "average_video_views", 0.99728], ["average_impressions", "average_video_views", 0.988],
        ["average_reach", "average_impressions", 0.987], ["followers", "average_reach", 0.918],
        ["followers", "average_impressions", 0.912], ["followers", "average_video_views", 0.9064],
        ["price_usd", "price_ars", 1.0],
    ])
    write_csv(root / "eda/exact_dependencies.csv", ["relation", "max_abs_residual", "exact"],
              [[name, 0.0, "True"] for name in ("price_ars", "organic_posts_pct", "total_engagement_per_1000",
                                                "topic_sum_100", "content_sum_100")])
    write_csv(root / "som/profiles/zones.csv",
              ["neuron", "row", "col", "n", "topic", "median_followers", "median_price"],
              [[0, 0, 0, 5, "perros", 17062.0, 84.77], [1, 0, 1, 1, "perros", 5000.0, 10.0],
               [19, 3, 4, 3, "maquillaje", 638718.0, 6310.69], [18, 3, 3, 0, "", "nan", "nan"]])
    write_json(root / "pca/audited/decision.json", {
        "n_variables": 26, "k_80": 3, "explained_pc1": 0.5322, "explained_pc2": 0.0851,
        "min_eigenvalue": 0.00046018,
    })
    write_json(root / "pca/sensitivity.json", {
        "all31_sensitivity": {}, "abs_cos_pc1": 0.9999752, "spearman_pc1": -0.99817,
    })
    write_csv(root / "pca/audited/eigenvalues.csv", ["component", "eigenvalue", "explained", "cumulative"],
              [["PC1", 13.8, 0.5322, 0.5322], ["PC2", 2.2, 0.0851, 0.6173], ["PC3", 1.8, 0.0714, 0.8312]])
    prune_rows = [
        {"tau": tau, "n_kept": n, "kept": kept, "dropped": [{"dropped": d, "partner": "x", "abs_r": 0.9} for d in dropped],
         "k_80": k, "explained_pc1": pc1, "min_eigenvalue": lmin, "condition_number": cond}
        for tau, n, kept, dropped, k, pc1, lmin, cond in (
            (0.95, 22, ["followers", "estimated_argentina_reach", "comments_per_1000"], [], 6, 0.482, 0.0124, 856.4),
            (0.9, 20, ["followers", "estimated_argentina_reach", "comments_per_1000"], [], 6, 0.453, 0.0188, 483.0),
            (0.85, 20, ["followers", "estimated_argentina_reach", "comments_per_1000"], [], 6, 0.453, 0.0188, 483.0),
            (0.8, 17, ["followers", "estimated_argentina_reach", "comments_per_1000"], ["price_usd"], 7, 0.4, 0.0629, 108.0),
            (0.7, 15, ["estimated_argentina_reach", "comments_per_1000"], ["price_usd", "followers"], 7, 0.365, 0.1149, 48.0),
            (0.6, 12, ["comments_per_1000"], ["price_usd", "followers"], 6, 0.304, 0.1347, 27.0),
            (0.5, 9, ["monthly_posts"], ["price_usd", "followers"], 5, 0.278, 0.2192, 11.0),
        )
    ]
    write_json(root / "corr_prune/sensitivity.json", {"n_audited": 26, "rows": prune_rows})
    write_json(root / "som/profiles/pca_contrast.json", {
        "r2_pc1": 0.9613, "p_r2_pc1": 0.000999, "r2_pc2": 0.0552, "p_r2_pc2": 0.2667,
        "mantel_plane_rho": 0.599, "p_mantel_plane": 0.000999, "mantel_z26_rho": 0.6349,
        "edge_rho_pc1": 0.4808, "edge_rho_pc2": 0.2714, "n_edges": 29, "n_excluded_edges": 11,
        "n_regions": 1, "n_permutations": 1000,
    })
    write_json(root / "som/series_som_stage1/selection.json", {
        "outcome": "chosen", "chosen_k": 5, "qe_train_argmin_k": 8, "figure_seed": 4, "decided_by": "qe_loo",
    })
    write_json(root / "som/series_som_stage2/robustness.json", {
        "robust": robust, "failing_variants": [] if robust else ["a", "b"], "te_checked": True,
    })
    write_csv(root / "som/series_som_stage2/robustness.csv",
              ["label", "radius0", "eta0", "epochs", "te_mean", "passes_empty", "passes_creators"], [
        ["base", 2.5, 0.5, 260, 0.046, True, True], ["a", 5.0, 0.5, 260, 0.05600000000000001, True, True],
        ["b", 2.5, 0.25, 260, 0.06, True, True], ["c", 2.5, 0.5, 50, 0.052, True, True],
    ])
    # 5 x 5 map: the three highest walls each touch a neuron with one creator, and size and price grow towards the
    # bottom right (the sentences check_claims guards)
    write_csv(root / "som/figures/hits_members.csv", ["neuron", "row", "col", "hits", "creators"],
              [[n, n // 5, n % 5, 1 if n in (9, 11, 13) else 2, ""] for n in range(25)])
    write_csv(root / "som/profiles/high_u_edges.csv", ["edge_rank", "neuron_a", "neuron_b", "distance", "variable"],
              [[1, 9, 14, 3.67, "price_usd"], [2, 13, 14, 2.99, "price_usd"], [3, 11, 12, 2.98, "content_entertainment_pct"]])
    write_csv(root / "som/profiles/neuron_profiles.csv", ["group", "n", "followers", "price_usd"],
              [[n, 2, 10000 * (1 + n // 5 + n % 5), 100 * (1 + n // 5 + n % 5)] for n in range(25)])
    write_json(root / "oja/comparison.json", {"max_abs_diff": 0.00197})
    write_json(root / "oja/dispersion.json", {
        "n_seeds": 10, "n_abs_cos_above": 10, "min_pairwise_abs_cos": 0.99999932, "mean_pairwise_abs_cos": 0.99999978,
        "worst_seed": 6, "pivots": ["average_caption_words"], "pivot_margin": {"margin": 0.0027477},
    })
    write_json(root / "oja/evidence.json", {"maximum": {
        "+1": {"creator_id": "INF031", "name": "@mundo", "dominant_topic": "perros", "followers": 17062, "index": 6.703},
        "-1": {"creator_id": "INF045", "name": "@futbol", "dominant_topic": "fútbol", "followers": 493194, "index": 6.26},
    }})
    write_csv(root / "oja/evidence_correlations.csv", ["target", "sign", "pearson", "spearman"],
              [["followers", "+1", -0.87868, -0.92105], ["followers", "-1", 0.87868, 0.92105]])
    write_csv(root / "oja/index.csv", ["creator_id", "name", "oja_index"], [["INF001", "@a", 1.0], ["INF002", "@b", 2.0]])
    write_json(root / "campaigns/selection_identity.json", {
        "rule_commit": "a6212e89cdc654021cfda02d9d16237c8c21c332", "k": 5,
        "pairs": [{"campaign": "fútbol", "objective": "profundidad"}, {"campaign": "perros", "objective": "costo_por_mil"},
                  {"campaign": "maquillaje", "objective": "profundidad"},
                  {"campaign": "arte", "objective": "engagement_profundidad"}],
    })
    shortlist, comparison = [], []
    for campaign, objective in (("fútbol", "profundidad"), ("perros", "costo_por_mil"), ("maquillaje", "profundidad"),
                                ("arte", "engagement_profundidad")):
        for rank in range(6, 0, -1):  # written out of order: load_facts sorts by rank and keeps five
            shortlist.append([campaign, objective, "propia", rank, f"I{rank}", f"@{campaign}{rank}", 3.25])
        shortlist.append([campaign, objective, "followers_global", 1, "G1", "@global1", -5.69])
        comparison.append([campaign, objective, "propia", 5, 1, 2, 12.3456, 0.8826, 0.0, 1367.0])
        comparison.append([campaign, objective, "followers_global", 5, 5, 1, 25.7069, -1.1077, 0.2, 22657.0])
    comparison.append(["fútbol", "alcance", "propia", 5, 1, 3, 26.99, 1.0, 1.0, 14714.0])
    write_csv(root / "campaigns/shortlists.csv",
              ["campaign", "objective", "list", "rank", "creator_id", "name", "pc1"], shortlist)
    write_csv(root / "campaigns/comparison.csv", ["campaign", "objective", "list", "n", "overlap_followers_global",
                                                  "overlap_followers_tema", "cost_per_thousand", "criterion_mean",
                                                  "topic_dominant_share", "cost_total"], comparison)
    write_json(root / "maintenance/demo.json", {
        "bmu": {"row": 3, "col": 1, "distance": 1.3290},
        "drift": {"qe": 2.7238, "max": 3.6509, "p95": 3.5446, "percentile": 0.0, "drift": False},
        "oja_index": 0.2494, "oja_rank": 24,
    })
    write_json(root / "hopfield/letters/selection.json", {
        "separated": {"letters": "GRTV", "pairs": [{"overlap": -0.04}, {"overlap": 0.04}]},
        "correlated": {"letters": "HMNW", "pairs": [{"overlap": 0.68}, {"overlap": 0.84}]},
    })
    write_json(root / "hopfield/letters/orthogonality.json", {
        "n_pixels": 25, "separated": {"min_margin": [18, 18, 18, 18]}, "correlated": {"min_margin": [4, -30, -34, -34]},
    })
    write_csv(root / "hopfield/letters/recall.csv", ["set", "update", "noise", "flipped", "recall_rate"], [
        ["separated", "async", 0.12, 3, 0.99667], ["separated", "async", 0.24, 6, 0.847],
        ["separated", "async", 0.36, 9, 0.3233], ["separated", "sync", 0.12, 3, 1.0],
        ["correlated", "async", 0.12, 3, 0.25], ["correlated", "async", 0.24, 6, 0.25],
    ])
    write_json(root / "hopfield/letters/capacity.json", {
        "p4_n_stable_counts": {"0": 284, "1": 1687, "2": 2653, "3": 3073, "4": 7253},
        "p4_mean_stable_fraction": 0.75625, "p4_all_stable_fraction": 0.48515,
    })
    write_csv(root / "hopfield/letters/capacity_by_p.csv", ["p", "n_subsets", "exhaustive", "mean_stable_fraction"],
              [[1, 26, 1, 1.0], [2, 200, 0, 1.0], [3, 200, 0, 0.9177], [4, 200, 0, 0.7488], [6, 200, 0, 0.4247],
               [26, 1, 1, 0.1154]])
    write_json(root / "hopfield/letters/spurious.json", {
        "levels": [0.4, 0.44, 0.48], "seeds_tried": [1],
        "counts_by_seed": {"1": {"stored": 463, "inverse": 334, "mixture": 254, "other": 149}},
    })
    write_json(root / "hopfield/qr/verdict.json", {
        "hebb_exact_recovery_noise0_async": 0.0, "pinv_exact_recovery_noise0_async": 1.0,
    })
    write_json(root / "hopfield/qr/qr_facts.json", {"n_pixels": 1369, "identical_fraction": 0.6976, "min_pair_hamming": 96})
    write_json(root / "hopfield/qr/overlaps.json", {
        "dots": [[1] * 5] * 5, "max_abs_overlap": 0.8598, "mean_abs_overlap": 0.6701,
    })
    write_json(root / "hopfield/qr/protocol.json", {"trials": 30, "seeds": list(range(1, 11))})
    write_csv(root / "hopfield/qr/recovery_table.csv", ["level", "hebb", "pinv", "hamming"], [
        [0.0, 0.0, 1.0, 1.0], [0.3, 0.0, 1.0, 1.0], [0.35, 0.0, 0.99867, 1.0], [0.4, 0.0, 0.97333, 0.98533],
        [0.45, 0.0, 0.694, 0.81533], [0.5, 0.0, 0.0, 0.16667],
    ])
    write_json(root / "hopfield/qr_limits/majority.json", {"hamming_to_targets": [225, 225, 71, 103, 91]})
    write_json(root / "hopfield/qr_limits/shift.json", {"shifts": [
        {"shift": 1, "query_hamming": 741, "recovered_hamming": 1034}, {"shift": 2, "query_hamming": 699, "recovered_hamming": 1198},
    ]})
    return root


def test_dec_uses_decimal_comma():
    assert facts.dec(0.9613, 3) == "0,961"


def test_dec_writes_nan_as_nd():
    assert facts.dec(float("nan"), 2) == "n/d"


def test_pct_is_number_space_percent_sign():
    assert facts.pct(0.973, 1) == "97,3 %"
    assert facts.pct(0.5) == "50 %"


def test_integer_drops_the_decimal_part():
    assert facts.integer(5.0) == "5"
    assert facts.integer(1000) == "1000"


def test_load_facts_returns_display_strings(tmp_path):
    values = facts.load_facts(write_results(tmp_path))
    assert values["som.r2_pc1"] == "0,961"
    assert values["som.p_r2_pc1"] == "0,001"
    assert values["som.r2_pc2"] == "0,055"
    assert values["som.p_r2_pc2"] == "0,267"
    assert values["som.chosen_k"] == "5"
    assert values["som.n_regions"] == "1"
    assert values["som.n_permutations"] == "1000"
    assert values["som.robust"] == "no"


def test_load_facts_robust_true_is_si(tmp_path):
    assert facts.load_facts(write_results(tmp_path, robust=True))["som.robust"] == "sí"


def test_load_facts_missing_file_names_the_make_command(tmp_path):
    write_results(tmp_path)
    (tmp_path / "som" / "profiles" / "pca_contrast.json").unlink()
    with pytest.raises(SystemExit) as stop:
        facts.load_facts(tmp_path)
    assert "make results" in str(stop.value)
    assert "som-profiles" in str(stop.value)


def test_fill_substitutes_known_keys():
    assert facts.fill("R² {som.r2_pc1}", {"som.r2_pc1": "0,961"}) == "R² 0,961"


def test_fill_unknown_key_names_it():
    with pytest.raises(SystemExit) as stop:
        facts.fill("{som.nothing}", {"som.r2_pc1": "0,961"})
    assert "som.nothing" in str(stop.value)


def test_fill_wrap_emits_data_fact_span_and_escapes_the_value():
    out = facts.fill("x {som.r2_pc1} y", {"som.r2_pc1": "<b>"}, wrap=informe.fact_span)
    assert out == 'x <span class="fact" data-fact="som.r2_pc1">&lt;b&gt;</span> y'


def test_dump_prints_sorted_json(tmp_path, capsys):
    write_results(tmp_path)
    assert facts.main(["dump", "--results", str(tmp_path)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["som.chosen_k"] == "5"
    assert list(printed) == sorted(printed)


def test_pct_short_drops_decimals_of_whole_percentages():
    assert facts.pct_short(0.0) == "0 %"
    assert facts.pct_short(1.0) == "100 %"
    assert facts.pct_short(0.99867) == "99,9 %"
    assert facts.pct_short(0.694) == "69,4 %"


def test_read_csv_source_returns_dict_rows(tmp_path):
    write_results(tmp_path)
    rows = facts.read_csv_source(tmp_path, "qr.recovery")
    assert rows[0] == {"level": "0.0", "hebb": "0.0", "pinv": "1.0", "hamming": "1.0"}
    assert {row["pinv"] for row in rows if row["level"] == "0.45"} == {"0.694"}


def test_every_source_is_written_by_the_fixture(tmp_path):
    write_results(tmp_path)
    for name, (relative, _) in facts.SOURCES.items():
        assert (tmp_path / relative).is_file(), name


@pytest.mark.parametrize("name", sorted(facts.SOURCES))
def test_load_facts_names_make_results_and_the_step_for_any_missing_file(tmp_path, name):
    write_results(tmp_path)
    relative, step = facts.SOURCES[name]
    (tmp_path / relative).unlink()
    with pytest.raises(SystemExit) as stop:
        facts.load_facts(tmp_path)
    assert "make results" in str(stop.value)
    assert step in str(stop.value)


def test_load_facts_reads_the_values_of_every_phase(tmp_path):
    values = facts.load_facts(write_results(tmp_path))
    assert values["pca.k_80"] == "3" and values["pca.n_features"] == "26"
    assert values["pca.var_pc1"] == "53,2 %" and values["pca.cum_k80"] == "83,1 %"
    assert values["som.mantel_rho"] == "0,599" and values["som.n_failing_variants"] == "2"
    assert values["oja.corr_followers_pearson"] == "-0,879" and values["oja.corr_followers_spearman"] == "-0,921"
    assert values["oja.max_id"] == "INF031" and values["oja.max_followers"] == "17062"
    assert values["camp.rule_commit"] == "a6212e8" and values["camp.k"] == "5"
    assert values["maint.bmu"] == "(fila 3, col 1)" and values["maint.retrain"] == "no hace falta re-entrenar"
    assert values["letters.separated_set"] == "GRTV" and values["letters.correlated_max_overlap"] == "0,84"
    assert values["letters.spurious_class"] == "inverso" and values["letters.spur_total_pct"] == "61,4 %"
    assert values["qr.hebb_exact_noise0"] == "0 %" and values["qr.pinv_exact_noise0"] == "100 %"
    assert values["qr.pinv_at_0_45"] == "69,4 %" and values["qr.hamming_at_0_45"] == "81,5 %"
    assert values["qr.pinv_at_0_50"] == "0 %" and values["qr.hamming_at_0_50"] == "16,7 %"
    assert values["qr.noise_high"] == "0,45" and values["qr.pinv_last_full_noise"] == "0,30"
    assert values["qr.majority_hamming_min"] == "71" and values["qr.majority_hamming_max"] == "225"


def test_campaign_facts_take_the_first_five_by_rank_and_the_own_list(tmp_path):
    values = facts.load_facts(write_results(tmp_path))
    assert values["camp.futbol.top5"] == "@fútbol1, @fútbol2, @fútbol3, @fútbol4, @fútbol5"
    assert values["camp.perros.cost_per_thousand_ar"] == "12,35"
    assert values["camp.arte.criterion"] == "0,883"
    assert values["camp.perros.overlap_followers"] == "1" and values["camp.perros.overlap_followers_tema"] == "2"


def test_slide_facts_failing_variants_are_labelled_by_what_moved(tmp_path):
    values = facts.load_facts(write_results(tmp_path))
    assert values["som.fail_1.variant"] == "R0 = 5" and values["som.fail_1.te"] == "0,056"
    assert values["som.fail_2.variant"] == "η0 = 0,25" and values["som.fail_2.te"] == "0,060"
    assert "som.fail_3.variant" not in values


def test_slide_facts_robust_run_has_no_failing_variant_facts(tmp_path):
    values = facts.load_facts(write_results(tmp_path, robust=True))
    assert not [key for key in values if key.startswith("som.fail_")]


def test_slide_facts_cover_followers_cost_letters_recall_and_opposite_topic(tmp_path):
    values = facts.load_facts(write_results(tmp_path))
    assert values["camp.futbol.followers_global_cost_per_thousand_ar"] == "25,71"
    assert values["letters.separated_recall_k3"] == "99,7 %" and values["letters.separated_recall_k6"] == "84,7 %"
    assert values["letters.separated_recall_k9"] == "32,3 %" and values["letters.correlated_recall_k3"] == "25,0 %"
    assert values["letters.separated_n_stable"] == "4" and values["letters.correlated_n_stable"] == "1"
    assert values["oja.max_opposite_topic"] == "fútbol"


def test_campaign_objective_not_in_the_committed_pairs_stops(tmp_path):
    write_results(tmp_path)
    write_json(tmp_path / "campaigns/selection_identity.json", {"rule_commit": "abcdef0123", "k": 5, "pairs": []})
    with pytest.raises(SystemExit) as stop:
        facts.load_facts(tmp_path)
    assert "make results" in str(stop.value)


def test_recovery_level_without_a_row_stops(tmp_path):
    write_results(tmp_path)
    rows = [[0.0, 0.0, 1.0, 1.0], [0.5, 0.0, 0.0, 0.16667]]
    write_csv(tmp_path / "hopfield/qr/recovery_table.csv", ["level", "hebb", "pinv", "hamming"], rows)
    with pytest.raises(SystemExit) as stop:
        facts.load_facts(tmp_path)
    assert "hopfield-qr" in str(stop.value)


def test_typed_numbers_of_the_letter_slides_are_facts(tmp_path):
    values = facts.load_facts(write_results(tmp_path))
    assert (values["letters.flips_k3"], values["letters.flips_k6"], values["letters.flips_k9"]) == ("3", "6", "9")
    assert values["letters.set_size"] == "4" and values["letters.alphabet_size"] == "26"
    # lround(level x 25) for the levels 0,40, 0,44 and 0,48, as the C binary flips them
    assert values["letters.spur_flip_min"] == "10" and values["letters.spur_flip_max"] == "12"
    assert values["letters.draft_matching_glyphs"] == "25"


def test_noise_high_is_the_fixed_reporting_level_not_where_pinv_dies(tmp_path):
    write_results(tmp_path)
    # pinv still recovers something at 0,50: the high-noise facts must stay those of 0,45
    write_csv(tmp_path / "hopfield/qr/recovery_table.csv", ["level", "hebb", "pinv", "hamming"], [
        [0.0, 0.0, 1.0, 1.0], [0.3, 0.0, 1.0, 1.0], [0.35, 0.0, 0.99867, 1.0], [0.4, 0.0, 0.97333, 0.98533],
        [0.45, 0.0, 0.694, 0.81533], [0.5, 0.0, 0.01, 0.16667],
    ])
    values = facts.load_facts(tmp_path)
    assert values["qr.noise_high"] == "0,45"
    assert values["qr.pinv_at_high"] == values["qr.pinv_at_0_45"] == "69,4 %"
    assert values["qr.hamming_at_high"] == values["qr.hamming_at_0_45"] == "81,5 %"


def test_recovery_table_that_does_not_end_at_the_last_named_level_stops(tmp_path):
    write_results(tmp_path)
    rows = [[0.0, 0.0, 1.0, 1.0], [0.35, 0.0, 0.99867, 1.0], [0.4, 0.0, 0.97333, 0.98533],
            [0.45, 0.0, 0.694, 0.81533], [0.5, 0.0, 0.0, 0.16667], [0.55, 0.0, 0.0, 0.1]]
    write_csv(tmp_path / "hopfield/qr/recovery_table.csv", ["level", "hebb", "pinv", "hamming"], rows)
    with pytest.raises(SystemExit) as stop:
        facts.load_facts(tmp_path)
    assert "last" in str(stop.value)


def _drop_followers_row(root):
    write_csv(root / "oja/evidence_correlations.csv", ["target", "sign", "pearson", "spearman"],
              [["followers", "-1", 0.87868, 0.92105]])


def _drop_followers_global_rows(root):
    write_csv(root / "campaigns/comparison.csv", ["campaign", "objective", "list", "n", "overlap_followers_global",
                                                  "overlap_followers_tema", "cost_per_thousand", "criterion_mean"],
              [[campaign, objective, "propia", 5, 1, 2, 12.3456, 0.8826]
               for campaign, objective in facts.RECOMMENDED_OBJECTIVE.values()])


def _drop_shift_1(root):
    write_json(root / "hopfield/qr_limits/shift.json",
               {"shifts": [{"shift": 2, "query_hamming": 699, "recovered_hamming": 1198}]})


def _empty_majority(root):
    write_json(root / "hopfield/qr_limits/majority.json", {"hamming_to_targets": []})


def _pinv_never_full(root):
    write_csv(root / "hopfield/qr/recovery_table.csv", ["level", "hebb", "pinv", "hamming"], [
        [0.0, 0.0, 0.9, 1.0], [0.35, 0.0, 0.8, 1.0], [0.4, 0.0, 0.7, 0.98533], [0.45, 0.0, 0.6, 0.81533],
        [0.5, 0.0, 0.0, 0.16667],
    ])


@pytest.mark.parametrize("damage, step", [
    (_drop_followers_row, "oja"), (_drop_followers_global_rows, "campaigns"), (_drop_shift_1, "hopfield-qr-limits"),
    (_empty_majority, "hopfield-qr-limits"), (_pinv_never_full, "hopfield-qr"),
])
def test_a_partial_result_stops_with_the_make_step_not_a_bare_error(tmp_path, damage, step):
    write_results(tmp_path)
    damage(tmp_path)
    with pytest.raises(SystemExit) as stop:
        facts.load_facts(tmp_path)
    assert "make results" in str(stop.value) and step in str(stop.value)


def _pinv_above_hamming(root):
    write_csv(root / "hopfield/qr/recovery_table.csv", ["level", "hebb", "pinv", "hamming"], [
        [0.0, 0.0, 1.0, 1.0], [0.35, 0.0, 0.99867, 1.0], [0.4, 0.0, 0.99, 0.98533], [0.45, 0.0, 0.694, 0.81533],
        [0.5, 0.0, 0.0, 0.16667],
    ])


def _occupancy_fails(root):
    write_csv(root / "som/series_som_stage2/robustness.csv",
              ["label", "radius0", "eta0", "epochs", "te_mean", "passes_empty", "passes_creators"],
              [["base", 2.5, 0.5, 260, 0.046, True, True], ["a", 5.0, 0.5, 260, 0.056, False, True],
               ["b", 2.5, 0.25, 260, 0.06, True, True]])


def _decided_by_another_measure(root):
    write_json(root / "som/series_som_stage1/selection.json",
               {"outcome": "chosen", "chosen_k": 5, "qe_train_argmin_k": 8, "figure_seed": 4, "decided_by": "qe"})


def _high_walls_between_full_neurons(root):
    write_csv(root / "som/figures/hits_members.csv", ["neuron", "row", "col", "hits", "creators"],
              [[n, n // 5, n % 5, 2, ""] for n in range(25)])


def _price_falls_towards_the_bottom_right(root):
    write_csv(root / "som/profiles/neuron_profiles.csv", ["group", "n", "followers", "price_usd"],
              [[n, 2, 10000 * (1 + n // 5 + n % 5), 100 * (9 - n // 5 - n % 5)] for n in range(25)])


@pytest.mark.parametrize("damage, sentence", [
    (_pinv_above_hamming, "lookup de Hamming"), (_occupancy_fails, "ocupación"),
    (_decided_by_another_measure, "QE-LOO"), (_high_walls_between_full_neurons, "un solo creador"),
    (_price_falls_towards_the_bottom_right, "price_usd"),
])
def test_check_claims_stops_when_a_result_falsifies_a_sentence(tmp_path, damage, sentence):
    write_results(tmp_path)
    facts.check_claims(tmp_path)  # the fixture supports every sentence
    damage(tmp_path)
    with pytest.raises(SystemExit) as stop:
        facts.load_facts(tmp_path)
    assert sentence in str(stop.value)


# ---------- drift pins (D-12) ----------

def write_fragments(directory, pins, values):
    """One fragment per number holding every filled pin phrase (joined across a line break)."""
    directory.mkdir(parents=True, exist_ok=True)
    by_number: dict[int, list[str]] = {}
    for number, template in pins:
        by_number.setdefault(number, []).append(facts.fill(template, values))
    for number, phrases in by_number.items():
        (directory / f"{number:02d}-x.md").write_text("Texto.\n\n" + " y\n".join(phrases) + "\n", encoding="utf-8")


def test_drift_pins_are_at_least_25_with_at_least_3_per_fragment():
    counts = {number: 0 for number in range(1, 6)}
    for number, _ in facts.DRIFT_PINS:
        counts[number] += 1
    assert len(facts.DRIFT_PINS) >= 25
    assert all(count >= 3 for count in counts.values()), counts


def test_every_pin_has_a_placeholder_and_every_placeholder_is_a_loaded_fact(tmp_path):
    values = facts.load_facts(write_results(tmp_path))
    for number, template in facts.DRIFT_PINS:
        keys = facts.TOKEN.findall(template)
        assert keys, template
        assert all(key in values for key in keys), (number, template, [k for k in keys if k not in values])


def test_check_fragment_numbers_is_empty_when_every_phrase_is_present(tmp_path):
    values = facts.load_facts(write_results(tmp_path / "results"))
    write_fragments(tmp_path / "deliverables", facts.DRIFT_PINS, values)
    assert facts.check_fragment_numbers(values, tmp_path / "deliverables") == []


def test_check_fragment_numbers_collapses_whitespace_runs(tmp_path):
    values = {"a.b": "1"}
    (tmp_path / "01-x.md").write_text("R² de\n  1   y p", encoding="utf-8")
    assert facts.check_fragment_numbers(values, tmp_path, ((1, "R² de {a.b} y p"),)) == []


def test_check_fragment_numbers_names_the_fragment_phrase_and_filled_text(tmp_path):
    values = {"a.b": "2"}
    (tmp_path / "03-x.md").write_text("R² de 1 y p", encoding="utf-8")
    failures = facts.check_fragment_numbers(values, tmp_path, ((3, "R² de {a.b} y p"),))
    assert len(failures) == 1
    assert "fragment 3" in failures[0] and "R² de 2 y p" in failures[0] and "R² de {a.b} y p" in failures[0]


def test_check_fragment_numbers_reports_a_missing_fragment_and_an_unknown_key(tmp_path):
    (tmp_path / "01-x.md").write_text("texto", encoding="utf-8")
    failures = facts.check_fragment_numbers({"a.b": "1"}, tmp_path, ((2, "{a.b}"), (1, "{a.nada}")))
    assert len(failures) == 2
    assert "fragment 2" in failures[0] and "a.nada" in failures[1]


def test_check_prints_drift_ok_and_exits_0_on_a_matching_tree(tmp_path, capsys):
    results = write_results(tmp_path / "results")
    write_fragments(tmp_path / "deliverables", facts.DRIFT_PINS, facts.load_facts(results))
    code = facts.main(["check", "--results", str(results), "--deliverables", str(tmp_path / "deliverables")])
    assert code == 0
    assert capsys.readouterr().out.strip() == f"DRIFT_OK {len(facts.DRIFT_PINS)} pins"


def test_check_exits_1_and_lists_the_altered_phrase(tmp_path, capsys):
    results = write_results(tmp_path / "results")
    write_fragments(tmp_path / "deliverables", facts.DRIFT_PINS, facts.load_facts(results))
    target = tmp_path / "deliverables" / "02-x.md"
    text = target.read_text(encoding="utf-8")
    assert "R² de PC2 sobre la grilla: 0,055" in text
    target.write_text(text.replace("R² de PC2 sobre la grilla: 0,055", "R² de PC2 sobre la grilla: 0,056"), encoding="utf-8")
    code = facts.main(["check", "--results", str(results), "--deliverables", str(tmp_path / "deliverables")])
    out = capsys.readouterr().out
    assert code == 1
    assert "fragment 2" in out and "R² de PC2 sobre la grilla: 0,055" in out


def test_check_does_not_modify_the_fragments(tmp_path):
    results = write_results(tmp_path / "results")
    write_fragments(tmp_path / "deliverables", facts.DRIFT_PINS, facts.load_facts(results))
    before = {p.name: p.read_bytes() for p in (tmp_path / "deliverables").iterdir()}
    facts.main(["check", "--results", str(results), "--deliverables", str(tmp_path / "deliverables")])
    assert {p.name: p.read_bytes() for p in (tmp_path / "deliverables").iterdir()} == before


def test_facts_of_the_review_slides_eda_zones_capacity_and_campaign_evidence(tmp_path):
    values = facts.load_facts(write_results(tmp_path))
    assert values["eda.n_columns"] == "3" and values["eda.n_dropped"] == "5"
    assert values["eda.size_r_min"] == "0,91" and values["eda.size_r_max"] == "0,997"
    assert values["eda.max_skew"] == "1,97" and values["eda.max_skew_variable"] == "estimated_argentina_reach"
    assert values["som.n_stage2_variants"] == "3" and values["som.base_te"] == "0,046"
    assert values["som.passing_variants"] == "50 épocas"
    assert values["som.zone_small.cell"] == "(0,0)" and values["som.zone_large.topic"] == "maquillaje"
    assert values["letters.course_capacity"] == "3,75" and values["letters.stable_p4"] == "0,749"
    assert values["letters.capacity_last_p"] == "26" and values["qr.course_capacity"] == "205"
    assert values["qr.pinv_stored_energy"] == "−684,5"
    assert values["camp.futbol.followers_global_topic_share"] == "20 %"
    assert values["camp.futbol.cost_total"] == "1367" and values["camp.futbol.other_cost_total_min"] == "14714"
    assert values["camp.followers_global_pc1_mean"] == "-5,69" and values["camp.futbol.pc1_mean"] == "3,25"
