---
phase: "02"
slug: "kohonen-som"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-21"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| config.json -> kohonen.c | grid_k, epochs, radii and rates decide allocation sizes, loop bounds and divisions | numeric config, local, non-sensitive |
| prepared CSV -> kohonen.c | row and column counts index the sample and prototype arrays | z-scored creator features, non-sensitive |
| series JSON -> som_loo.py -> neuron binary | config values from a file become a child process's config | numeric config, local |
| temporary directories | thousands of short-lived run directories on disk | intermediate run files |
| run files -> analysis/som.py | Python trusts the C files' headers and shapes | CSV / JSON run outputs |
| human decision -> rule text | the checkpoint answer becomes part of a pre-registration that later steps enforce | selection rule (integrity-critical) |
| git working tree -> rule_guard | the guard trusts git's view of what is committed | commit hashes, file state |
| committed rule -> stage driver / figures / profiles | every later step must run against the committed, unchanged rule | rule sha256, select_sha256 |
| stage-1 results -> stage-2 series | the only value allowed to flow is the chosen k | integer k |
| figures / profiles -> report reader | visual encodings and creator names leave the analysis folder in the report | public course data (creator names) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Denial of service / Tampering | read_params in kohonen.c (grid_k, epochs) | medium | mitigate | `neuron/models/kohonen.c:49,61` range checks 2 <= grid_k <= GRID_K_MAX (32), 1 <= epochs <= EPOCHS_MAX (100000) before allocation; `steps` is `long long` (l.88); sizes cast to `size_t` | closed |
| T-02-02 | Tampering (memory safety) | pick_prototypes when k^2 > n | high | mitigate | `neuron/models/kohonen.c:105-107` `order[neuron % n]` with `rng_shuffle` at every wrap; `make -C neuron debug` builds with `-fsanitize=address,undefined` (`neuron/Makefile:63-66`) | closed |
| T-02-03 | Tampering (integrity of numbers) | schedules, gaussian kernel, occupancy ratios | medium | mitigate | `kohonen.c:74-85` eta0 in (0,1), 0 < eta_final <= eta0, radius_final bounds (gaussian > 0); radius clamp `fmax(..., radius_final)` (l.170); `m.occupied > 0` guard (l.400); non-finite written as `null` (`neuron/io/results.c:116-121`) | closed |
| T-02-04 | Tampering | read_run in analysis/som.py | low | mitigate | `analysis/som.py:71-109` header, neuron count and `row * k + col` numbering mismatches raise ValueError | closed |
| T-02-05 | Elevation of privilege (command injection) | som.run_binary called by run_loo | medium | mitigate | `analysis/som.py:172` `subprocess.run([BINARY, "config.json"], cwd=cwd)`, argument list, no shell; no `shell=True` anywhere in `analysis/` | closed |
| T-02-06 | Tampering (filesystem) | temporary training directories | low | mitigate | `analysis/som_loo.py:65` `tempfile.TemporaryDirectory(dir=tmp_root)`; `shutil.rmtree(tmp_root)` at l.113 and l.127 | closed |
| T-02-07 | Denial of service | about 7 000 trainings per stage-1 series | low | accept | bounded `ThreadPoolExecutor` (`analysis/som_loo.py:105`); see Accepted Risks Log AR-02-01 | closed |
| T-02-08 | Repudiation / Tampering | deliverables/02-kohonen.md section 2, analysis/series_som_stage1.json, analysis/som_select.py | high | mitigate | `analysis/som_select.py:214-230` `rule_digest` (sha256 between markers) and `rule_guard` refuse uncommitted / modified files; `analysis/som_stage.py:70-97` `rule_identity` records rule_commit, rule_sha256, select_commit, select_sha256 | closed |
| T-02-09 | Elevation of privilege (command injection) | git calls in rule_guard | low | mitigate | `analysis/som_select.py:227`, `analysis/som_stage.py:57` `subprocess.run(["git", *args], cwd=repo_dir)`, argument lists, no shell | closed |
| T-02-10 | Tampering / Repudiation | analysis/series_som_stage2.json and the rule section | high | mitigate | `analysis/som_stage.py:270` stage-2 file derived only from `som_select.stage2_series(chosen_k)`; l.66-90 rule-commit checks; `require_same_rule` (l.101-113) compares rule and selection-code sha256 with selection.json | closed |
| T-02-11 | Tampering (integrity of results) | run_stage aggregation | medium | mitigate | `analysis/som_stage.py:178` raises SystemExit when any run fails, before aggregate/selection are written; covered by `analysis/tests/test_som_stage.py:120` `test_run_stage_failure_stops` | closed |
| T-02-12 | Tampering (path) | run directories named from variant labels | low | mitigate | `analysis/sweep.py:72` slug `re.sub(r"[^A-Za-z0-9.]+", "-", label)`; unique-label check `som_stage.py:163` | closed |
| T-02-13 | Repudiation / Tampering | figure run choice in som_figures.main | medium | mitigate | `analysis/som_figures.py:328-336` `require_same_rule` first, run taken only from `selection["figure_run"]`; caption prints k, schedule, seed (l.353) | closed |
| T-02-14 | Tampering (misleading output) | plot_map, plot_planes | low | mitigate | `analysis/som_figures.py:136` U colour range [U.min(), U.max()]; empty neurons hatched (l.130, l.142) and NaN (l.74); shared symmetric z scale `vmin=-limit, vmax=limit` (l.170-177) | closed |
| T-02-15 | Tampering (integrity of results) | permutation nulls in som_profiles | low | mitigate | `analysis/som_profiles.py:376` single `np.random.default_rng(PERMUTATION_SEED)`; seed and count recorded (l.421); byte-identical reruns confirmed in 02-VERIFICATION.md | closed |
| T-02-16 | Information disclosure | creator names in CSVs and the report | low | accept | names come from the tracked course file `datos/creadores.csv`; see Accepted Risks Log AR-02-02 | closed |
| T-02-17 | Repudiation / Tampering | region threshold and contrast choices | medium | mitigate | `analysis/som_profiles.py:44-47` constants mirror the committed rule; `main` calls `require_same_rule` before computing (l.349) | closed |
| T-02-SC | Tampering | pip install of analysis/requirements.txt | high | mitigate | `analysis/requirements.txt` unchanged since Phase 1 commit 7781979 (four exact pins); no new package in plans 02-01..02-06 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-07 | About 7 000 trainings of ~20 ms each through a bounded thread pool; minutes of local compute, not a resource risk | plan 02-02 threat model | 2026-10-21 |
| AR-02-02 | T-02-16 | Creator names come from the course-provided, already tracked `datos/creadores.csv`; no new personal data is created or joined | plan 02-06 threat model | 2026-10-21 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-21 | 18 | 18 | 0 | /gsd-secure-phase (L1 grep verification, orchestrator) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-21
