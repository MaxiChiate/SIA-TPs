# Pitfalls Research

**Domain:** Academic unsupervised-learning / associative-memory assignment (Kohonen SOM + PCA + Oja on a 50x31 tabular dataset; Hopfield on 37x37 QR codes and 5x5 letters), C core + Python analysis
**Researched:** 2026-10-20
**Confidence:** HIGH for dataset facts and the Hopfield/Oja/SOM behaviours measured below; MEDIUM for literature claims (capacity figures, rule names) which come from training knowledge plus secondary web summaries

**How this was researched.** Besides the literature, every quantitative claim tagged "(measured)" was reproduced with throwaway numpy prototypes on the real files (`datos/creadores.csv`, `datos/hopfield/*.png`). Those prototypes live in the session scratchpad, not in the repo. They are a reference to check the real C implementation against, not deliverables. The implementation must reproduce these numbers or explain why not.

**Phase labels used below** (a suggestion; the roadmap may rename them): **P1** Data foundation (parser, EDA, feature audit, PCA) / **P2** Kohonen / **P3** Oja index vs PC1 / **P4** Campaign decisions and maintenance / **P5** Hopfield letters 5x5 / **P6** Hopfield QR 37x37 / **P7** Slides + report (Artifact).

---

## Critical Pitfalls

### Pitfall 1: Hopfield with plain Hebb on the five QRs does not work at all, and the capacity rule of thumb hides it

**What goes wrong:** With the standard Hebbian rule `W = (1/N) sum xi xi^T`, zero diagonal, the five QR patterns are NOT even fixed points of the network, so even a noise-free query changes. (measured) Of 35 noise runs at every noise level from 5% to 50% (async and sync), exact recovery was 0%. All 200 random starts ended in the same spurious state, the pixel-wise majority of the five QRs. A noisy "beverages" query returned something closest to "food".

**Why it happens:** The five QRs are highly correlated. (measured) The normalized overlaps (xi_a . xi_b / N) are 0.58 to 0.86, 69.8% of the 1369 pixels are identical in all five patterns (finder patterns, timing patterns, same version and format layout), and the minimum pairwise Hamming distance is only 96 of 1369 pixels (7%). The cross-talk term `sum_{nu != mu} xi_i^nu (xi^nu . xi^mu)/N` is then of the same size as the signal. The 0.138N capacity (P/N = 5/1369 = 0.004, "far below the limit") is derived for independent random patterns and says nothing about correlated ones. Students check P/N, see it is small, and are surprised.

**How to avoid:**
- Make "noise = 0 stability test" the first test of every Hopfield run: each stored pattern must be a fixed point. If it is not, stop and report it. Do not move on to noise sweeps.
- Report the Hebbian result honestly as the answer to "limitations of the use case" (correlation, not capacity, is the limit), then show a fix as a clearly labelled second experiment.
- Fix that was measured to work: the pseudo-inverse / projection rule `W = Xi^T (Xi Xi^T)^-1 Xi` (Personnaz / Kanter-Sompolinsky). (measured) All 5 patterns became fixed points, with 100% exact recovery up to 30% i.i.d. flips and 96% at 40%. It needs linear independence and P < N, and it is not local or incremental. Keep that trade-off in the write-up.
- Fix that was measured NOT to work: mean-centering the patterns before Hebb (covariance rule) gave 0% recovery. Do not waste a phase on it, or if tried, report it as negative.
- Do not "tune until it works" on Hebb by cherry-picking noise levels or trials.

**Warning signs:** The network "converges" in 2 sweeps for every noise level (measured 2.0 to 2.8 sweeps) and the final state looks the same for different queries. Energy plateaus at the same value regardless of the query. Hamming distance of the output to the target does not fall as noise falls.

**Phase to address:** P6 (QR). The stability-at-zero-noise check also belongs in P5 so the habit is in place.

---

### Pitfall 2: PCA (or SOM, or Oja) on unstandardized data

**What goes wrong:** (measured) On raw data PC1 explains 99.7% of variance and its loading vector is `price_ars = 1.0`, everything else about 0. A SOM on raw data spends 84% of its codebook spread on `price_ars` and simply sorts creators by price. Oja on raw data overflows to NaN.

**Why it happens:** The variables span 6 orders of magnitude: `price_ars` up to 9.5e6, `followers` up to 7.8e5, `comments_per_1000` around 0.8 to 7. The covariance matrix is dominated by units, not structure.

**How to avoid:** Standardize (z-score) every variable that enters PCA, SOM and Oja, using one `ddof` convention everywhere (1 is natural; state it, because the choice rescales covariance by n/(n-1)). Store the per-column mean and std. They are needed later for the maintenance question (new creators must be projected with the same scaler). Report PCA on the correlation matrix, not covariance. Consider `log10` for the skewed size family (followers, reach, impressions, video views, prices, estimated reach; skew up to 2.0); (measured) log lifts PC1 from 48% to 52%, a small effect, so decide once, document, and do not over-engineer.

**Warning signs:** PC1 loading concentrated on one variable; scree plot with PC1 above 95%; U-matrix gradient aligned to a single price-like variable.

**Phase to address:** P1 (decided there, reused by P2 and P3).

---

### Pitfall 3: Collinear and exactly dependent derived variables are fed in without being audited

**What goes wrong:** The covariance matrix is singular, and the "size" concept is counted many times over. (measured) The 31 columns have rank 26: five exact linear dependencies.
1. `price_ars = 1500 * price_usd` (r = 1.000)
2. `organic_posts_pct = 100 - sponsored_posts_pct` (r = -1.000)
3. `total_engagement_per_1000 = likes + comments + saves + shares` (exact)
4. the four `topic_*_pct` sum to 100 for every creator
5. the four `content_*_pct` sum to 100 for every creator

Dropping the first three still leaves rank 25 of 27, because the two compositions remain. In addition, `estimated_argentina_reach = average_reach * argentina_audience_pct / 100` is a nonlinear product (not rank-deficient, r = 0.87 with reach), `followers` / `average_reach` / `average_impressions` / `average_video_views` / `price_usd` are mutually correlated at 0.82 to 0.997, and `video_posts_pct` / `short_form_posts_pct` / `trend_posts_pct` at 0.95 to 0.97.

Consequences: 5 near-zero eigenvalues (about 1e-16) whose eigenvectors are numerical noise; Kaiser/scree counts and "components for 80%" are polluted; any code that inverts the covariance or whitens divides by about 0; and PC1 plus the SOM main axis become an inflated "size" axis (7+ near-duplicate variables vs 4 topic variables) that can hide the topic structure the campaigns need.

**Why it happens:** The CSV looks like 31 independent features. The derived-variable relations are stated in prose in the statement, not in the data.

**How to avoid:** In P1, write an explicit feature audit table (variable, role: raw / derived / composition / identifier, keep / drop, reason). At minimum drop `price_ars`, `organic_posts_pct`, `total_engagement_per_1000` (or keep the total and drop the four components; pick one), drop one component of each composition (or use a log-ratio transform), and decide on `estimated_argentina_reach`. Check that the retained matrix is full rank (print `matrix_rank` and the smallest eigenvalue). Keep derived metrics for the decision layer (P4), not as model inputs. Tension with the statement: the Kohonen bullet says "en terminos de todas sus variables", but section 1 of the statement explicitly asks to "seleccionar que variables seran utilizadas". Resolve it by treating the P1 selection as the "all variables" set and running all-31-z-scored as a labelled sensitivity check. Do not silently drop.

**Warning signs:** Eigenvalues printed as 1e-16 or negative; `np.linalg.inv` or Cholesky errors; two biplot arrows exactly overlapping; PC1 loadings equal for `price_usd` and `price_ars`.

**Phase to address:** P1.

---

### Pitfall 4: Parsing `creadores.csv` drops the last creator (the project says 49; there are 50)

**What goes wrong:** (measured) The file has 50 creator rows and no trailing newline. A line-count or `\n`-count based reader gives 49. `PROJECT.md` already states "49 creadores". A C parser that sizes arrays from the newline count, or a `while (fgets(...))` that checks a terminator, silently loses `@...` row 50, and every downstream number (PCA, hit map, the 50 vs 49 in the report) is off by one.

**Why it happens:** Last line without `\n`; hand-written CSV parsing in C.

**How to avoid:** Count rows by parsing, not by counting newlines. Assert `n_rows == 50` and `n_cols == 33` (31 numeric plus id and name) after load, and fail loudly otherwise. Fix the "49" in `PROJECT.md`. Verify the checksum of the two numeric columns against a Python pandas read. Handle quoted names defensively (names are `@handles`, none quoted today).

**Warning signs:** Last creator absent from the hit map or the ranking; pandas and C disagree on `n`.

**Phase to address:** P1 (before anything is built on the data).

---

### Pitfall 5: Choosing the SOM grid by minimizing quantization error on 50 samples

**What goes wrong:** (measured, z-scored, 5 seeds) quantization error (QE) falls monotonically with grid size: 4.00 (2x2), 3.17 (4x4), 2.86 (5x5), 2.24 (8x8), 1.96 (10x10), 1.69 (12x12). "Choose the grid with the best QE" therefore picks the biggest grid. At 8x8 there are already more neurons than creators (0.78 creators per neuron, 38 of 64 occupied); at 10x10 only 42 of 100 neurons are occupied. The map memorizes individual creators and the U-matrix shows walls that are just empty neurons. The folk rule 5*sqrt(N) neurons gives about 35, i.e. 1.4 creators per neuron, which is already too fine for 50 samples.

**Why it happens:** QE is a training error; there is no test set, and the statement says "evaluando la performance del modelo" without defining the metric. Topographic error (TE) is about 0.00 to 0.02 at every size here, so it does not discriminate either.

**How to avoid:** Define the selection criterion in advance and use several together: QE, TE, occupied-neuron fraction, mean creators per neuron (aim for about 2 to 5), interpretability of the U-matrix, and seed stability. Search a small grid (2x2 to 6x6, probably 3x3 to 5x5 wins). The only honest generalization estimate with n=50 is leave-one-out or k-fold QE (train on 49, measure the BMU distance of the held-out creator), so use that for the "performance" justification and note it is an estimate on 50 points. Report the full QE-vs-grid curve (do not pick on the elbow by eye alone) and say explicitly that QE alone would pick the largest grid.

**Warning signs:** Best grid in the sweep is the largest tried; over 30% of neurons empty; singleton neurons everywhere; "justified by lowest QE" in the report.

**Phase to address:** P2.

---

### Pitfall 6: Reading the U-matrix, hit map and "regions" naively

**What goes wrong:** (a) Treating high U-matrix distance as "bad neurons" instead of cluster boundaries (high distance between neighbouring neurons = the codebook jumps there, meaning dissimilar profiles on each side; low = homogeneous region). (b) Interpreting walls caused by empty or interpolating neurons as real cluster boundaries. (c) Describing a region from two or three members. (d) Comparing "top-left of the map" across runs: SOM orientation (rotation / reflection) is arbitrary and changes with the seed. (e) Declaring that the SOM "coincides with the biplot" by eye. (f) Claiming the clusters "validate" topics when topic variables are among the inputs (circular; (measured) 43 of 50 creators already have one topic above 50%, with dominant-topic counts 15 / 11 / 13 / 11 for football / makeup / dogs / art).

**Why it happens:** Small grid, small n, no ground-truth labels, and the statement's own phrasing ("coinciden con los perfiles observados en PC1 y PC2?") invites a yes.

**How to avoid:** Always show hit map plus U-matrix plus component planes (one heatmap per selected variable) together. Describe a neuron or region with de-standardized means of its assigned creators (raw units), not just codebook z-values, and flag neurons with fewer than 2 members. Quantify the PCA comparison: correlation between grid coordinates (or BMU codebook) and PC1/PC2 scores, and between neuron-mean PC1 scores and U-matrix position. Report where they disagree, since a nonlinear map can legitimately separate what PC1/PC2 mix. Keep a fixed seed for the figures in the deliverable, and state that orientation is arbitrary. Check stability across seeds with co-assignment agreement of creator pairs (measured at k=4 about 0.96, but the "all different" baseline is about 0.88, so it is only mildly informative; use a chance-adjusted version).

**Warning signs:** Region names such as "premium zone" with 1 creator behind them; conclusions that change when the seed changes; U-matrix colour scale truncated.

**Phase to address:** P2 (analysis), P7 (figure choices).

---

### Pitfall 7: Learning-rate and radius schedules that never order the map, or that hit a zero radius

**What goes wrong:** The map twists (folds) or stays disordered when the neighbourhood radius shrinks too fast or starts too small; with sigma reaching 0 the Gaussian `exp(-d^2 / 2 sigma^2)` divides by zero or degenerates to winner-take-all (k-means, no topology). (measured) QE keeps decreasing from 100 steps (3.70) to 50,000 steps (2.58) on a 5x5 map, so "converged" depends entirely on the step count. Comparing runs with different "iterations" (online steps) vs "epochs" (passes of 50 samples) is a classic mix-up. Sample-based vs uniform-random initialization made little difference on this data (QE 2.86 vs 2.85, measured), so do not spend a phase on it.

**Why it happens:** Schedules copied from big-data examples; no ordering/convergence two-phase thinking; hyperparameters not scaled to a 50-sample, 5x5-ish setting.

**How to avoid:** Start sigma at about half the grid side, decay to a floor of about 0.5 to 1 grid unit (never 0), decay learning rate from about 0.5 to about 0.01, and use an ordering phase then a fine-tuning phase (or one smooth exponential schedule). Count training in epochs with random shuffling per epoch, and use at least a few hundred to a few thousand epochs (hundreds of steps per neuron is Kohonen's usual guideline, cheap here). Sweep (lr0, sigma0, decay type, epochs, grid) with several seeds in `sweep.py` and report mean plus standard deviation, not the best seed. Log QE and TE against epoch to show the curve has flattened. Use the final-radius floor consistently between the C core and the Python plots.

**Warning signs:** TE rises as training goes on; neighbours in the grid with huge codebook distance everywhere in the U-matrix; NaN in weights; QE still dropping at the last epoch.

**Phase to address:** P2.

---

### Pitfall 8: Oja's rule run on uncentered data, with an unstable learning rate, and without normalization of the final weights

**What goes wrong:** Three separate failures, all measured:
1. **Not centered**: on min-max scaled (positive, uncentered) data, Oja converges to the direction of the mean (cos with mean direction about 1.0), not to PC1 of the centered data (cos about 0.28). Oja's fixed point is the top eigenvector of the second-moment matrix E[x x^T], not the covariance. "Oja != PCA" reports come from this.
2. **Learning rate**: on z-scored 31-dim data lr = 0.001 and 0.01 converge (cos with PC1 about 1), lr = 0.05 diverges to NaN. Stability needs eta times |x|^2 (about 31 for z-scored 31-dim inputs) to stay well below 1, so a safe eta is small. Dropping variables changes the safe range.
3. **Norm and sign**: |w| ends up about 1.00 to 1.04, not exactly 1 (so a computed "cosine" can come out above 1, e.g. 1.0085). The sign of w is arbitrary: w and -w are both stable fixed points, so the random init decides. With one sign the top-3 index creators are `@galeriacotidiana`, `@futbolsinvueltas`, `@crearenreels`; with the other they are `@mundoanimal.ar`, `@consejoscaninos`, `@huellasyconsejos` (dog-shelter-type creators). "Highest index" is therefore not a meaningful statement without a stated orientation.

**Why it happens:** Oja is presented as "a neuron learns PC1", which hides the centering assumption; sign symmetry is invisible when only the magnitude of a cosine is printed.

**How to avoid:** Use the same centered and standardized matrix as PCA. Shuffle samples each epoch, decay eta (for example 0.01 down to 0.0005), run until |w| ~ 1 and the change in w per epoch is below tolerance, then renormalize w to unit length before computing the index. Validate against `eigh` of the correlation matrix: report |cos(w, v1)|, then fix the orientation by a convention written down in advance (for example make the `followers` or `average_reach` loading positive) and report the PCA score under the same convention. Report Spearman rank correlation (measured: 0.92 between PC1 score and followers rank) and top-k overlap between the Oja index and PC1, which should be about identical when converged; any gap is convergence error or a centering bug, not a "finding".

**Warning signs:** cos(w, PC1) below 0.99; |w| drifting from 1; NaN; sign flipping between seeds; ranking reversed vs PCA.

**Phase to address:** P3.

---

### Pitfall 9: Treating the Oja/PC1 index as a universal quality score ("pick the max for any campaign")

**What goes wrong:** The statement asks "seria correcto elegir automaticamente al creador con el valor mas alto para cualquier campana?" The answer is no, but it needs evidence, not just a sentence. The index is a variance-maximizing direction: here (measured) PC1 explains only 48% of variance, loads on reach / impressions / views / price / trend / short-form posts and negatively on `average_caption_words`; it is a scale / "professionalization" factor, not "quality" or "fit". It correlates 0.88 with followers. (measured) Index correlation with topic shares: football +0.22, makeup +0.21, art +0.02, dogs -0.44. The top 10 by index contains only 1 of the top 10 dog creators and 1 of the top 10 art creators (football 4, makeup 3). A shelter campaign following the max-index rule picks the wrong creators; with the opposite sign it picks the right ones.

**Why it happens:** One scalar feels like a ranking; sign and meaning of the axis are never examined; campaign requirements (topic, local audience, content type, budget) are orthogonal to scale.

**How to avoid:** Interpret the index by its loadings (print them). State that the other 52% of variance is thrown away. For each campaign, filter or weight by the campaign-specific variables first (topic share, `argentina_audience_pct`, content type, price) and use the index (or SOM region) only to rank or diversify inside the shortlist. Show the evidence table (index vs topic shares, top-10 overlap) in the report.

**Warning signs:** One global ranking reused for all four campaigns; no mention of sign; the word "best" attached to the index.

**Phase to address:** P3 (interpretation), P4 (campaign use).

---

### Pitfall 10: Strawman or unmeasurable comparison against the followers-only baseline

**What goes wrong:** The comparison with `followers`-only selection is either rhetorical ("followers is bad") or claims ROI superiority the data cannot support (no conversion or revenue column; unsupervised; no ground truth). (measured) Followers correlate 0.14 with total engagement, 0.50 with non-follower reach, and -0.00 with Argentine audience share; the top 10 by followers include 0 of the top 10 art creators, 1 of the top 10 dog creators, 3 football, 5 makeup. Those are the facts the report should use. Also unfair: comparing a campaign-aware method against followers without letting followers also benefit from a topic filter.

**Why it happens:** The statement leaves the evaluation criterion open, and "alcance masivo vs descubrimiento vs profundidad" tempts a narrative answer.

**How to avoid:** Define per-campaign selection criteria up front as decision-layer metrics, and evaluate both strategies on them using the same budget or k: on-topic share, Argentine reach (`estimated_argentina_reach`), cost per thousand Argentine reached (`price_usd / estimated_argentina_reach * 1000`), engagement per 1000, non-follower reach (discovery), saves/shares/tutorial share (depth). Football: map "reach" to follower/reach columns, "discovery" to `non_follower_reach_pct` (and `trend_posts_pct`), "depth" to tutorial share, saves, caption words and watch time; state the assumption since the statement allows assumptions. List advantages of followers too (simple, stable, no model to maintain, correlates with reach). Say clearly that no claim about revenue is possible without outcome data.

**Warning signs:** Words like "better ROI" or "more sales"; no table with numbers; the same k not used on both sides.

**Phase to address:** P4.

---

### Pitfall 11: Hopfield energy and update-order bugs (async vs sync, ties, diagonal)

**What goes wrong:** (a) Energy that is not monotone non-increasing because W has a nonzero diagonal, is not symmetric, or uses synchronous updates. In synchronous mode the network can end in a 2-cycle (alternating states) and energy need not fall at every step. (measured) 0 of 200 random starts cycled with this particular W, so the bug would only show up on other data, but the theory allows it. Async energy was monotone here (measured, per sweep -185 to -2173 to -2173). (b) Ties: `sign(0)` leaves the state ambiguous, and inconsistent tie handling (always +1 vs keep current) changes results. (c) "Iterations" defined inconsistently: one neuron update vs one sweep. (measured) typical runs finish in 2 sweeps (one that changes, one that confirms nothing changes), so "converged in 2 iterations" is a property of the stop test, not of quality. (d) Fixed update order biases which fixed point is reached.

**Why it happens:** Copying the synchronous matrix form `s = sign(W s)` into code and then plotting energy.

**How to avoid:** Implement asynchronous updates with a fresh random permutation per sweep as the reference, keep a synchronous mode only as a labelled comparison with cycle detection (compare with state at t-2). Force `W_ii = 0` and check symmetry after training. On ties keep the current state. Define `E = -1/2 s^T W s` once, recompute it from scratch in tests, and record it per neuron update (or per sweep) as the statement asks. Add a test: async energy is non-increasing within a tolerance of 1e-9, otherwise fail. Stop when a full sweep produces no change. Record both counts, updates and sweeps.

**Warning signs:** Energy goes up even once; same query gives different outputs for the same seed; endless loop in sync mode.

**Phase to address:** P5 first (cheap to debug on 25 neurons), reused in P6.

---

### Pitfall 12: Misreading spurious states, inverse states and "recovery"

**What goes wrong:** (a) Every stored pattern's negative (-xi) is also a stable state (W is invariant to xi to -xi) and is a legitimate attractor, not a bug. A query with more than 50% flipped pixels converges to the inverse; flipping at exactly 50% gives something unrelated. (b) Any state that is neither a stored pattern nor its inverse is labelled "spurious" without checking whether it is a mixture state (typically the sign of an odd combination, e.g. sign(xi_a + xi_b + xi_c)) or just the majority state. (measured) For the QR set with Hebb the common attractor is the pixel-wise majority of the five QRs, 71 / 91 / 225 / 225 / 103 pixels away from the five targets. (c) Declaring success by lower energy or by "converged": energy at the majority or spurious state can be lower than at a stored pattern. (measured: majority state energy -2173; the stored patterns were not fixed points so had no stable energy). (d) With pinv, a random start lands on stored / inverse / other with 30 / 30 / 40 out of 100 (measured), so spurious states still exist even when the rule works.

**Why it happens:** "Spurious state" is used as a catch-all; success is judged visually.

**How to avoid:** Classify the final state in code: for each query compute the overlaps m_mu = xi^mu . s / N; call it stored if |m| = 1 for one pattern with m = +1, inverse if m = -1, mixture if it equals sign of a combination of 3 patterns (test explicitly), otherwise "other spurious", and report overlaps. Define success before running (exact match; or overlap at least 0.95; or "QR decodes"). For the statement's "identify a spurious state" (letters), save the seed and the very noisy input that produces it, show its overlaps and its identification (inverse? mixture?), and show energy at stored vs spurious state.

**Warning signs:** The word "spurious" without an overlap vector next to it; success defined after looking at the plot.

**Phase to address:** P5 (letters), P6 (QR).

---

### Pitfall 13: Noise-level evaluation done on a handful of single runs, or with the wrong noise model

**What goes wrong:** One run per noise level; success judged visually; i.i.d. pixel flips only, although the story in the statement is physical damage (a missing corner, stains, tears). (measured) With Hebb, a whitened 18x18 corner or a random 12x12 corner was not recovered either (the pinv behaviour on occlusion was not measured, so test it). Noise parameter definition is ambiguous (flip probability p vs exactly k pixels; flip vs set-to-random where only half the pixels actually change). p = 0.5 is a random pattern and p above 0.5 converges to the inverse, so any plot to 100% "noise" is mostly meaningless above 0.5.

**Why it happens:** Time pressure; noise is easiest to add i.i.d.

**How to avoid:** Define the noise operator in the config (type, level, seed). Use at least 30 trials per (pattern, level), report the success rate with the criterion from Pitfall 12, the mean number of sweeps and the final Hamming distance, and plot levels 0 to 0.5 only. Add structured damage (block occlusion, line scratch, random patches) because it matches the use case. Keep seeds in the output so any plotted example can be regenerated.

**Warning signs:** Plot with a single point per level; no variance bars; levels beyond 0.5; no occlusion experiment.

**Phase to address:** P6.

---

### Pitfall 14: Letters 5x5: wrong conclusions about capacity and orthogonality

**What goes wrong:** (a) Using 0.138N = 3.45 for N = 25 as a hard threshold. The asymptotic value assumes large N and random patterns; at N = 25 behaviour is dominated by which letters are chosen. (measured with my own 5x5 bitmaps, so indicative only) {A,B,C,D} (max |overlap| 0.68) had 3 of 4 patterns unstable; {C,D,E,F} 3 of 4 unstable; {E,F,P,B} (0.84) 2 of 4 unstable; while {X,H,L,T} (0.28) and {A,E,I,O} (0.44) were all stable. The most orthogonal 4-subset found among 19 letters was {F,M,O,Z} at 0.12. (b) Looking for exact orthogonality: for ±1 vectors of odd length N (25 here, and 1369 for the QRs) the dot product is always odd, so exact orthogonality is impossible. Use "small |overlap|". (c) Picking the letters that make the demo look good without saying so, or picking letters that all fail and not saying why.

**Why it happens:** The statement asks for "ortogonalidad y capacidad" together; letter bitmaps are hand-drawn so correlation is accidental.

**How to avoid:** Print the 4x4 overlap matrix and the cross-talk of each pattern. Run a capacity experiment: add letters one at a time, record the fraction that are stable fixed points and the recall rate under a fixed noise level, repeat over several random letter subsets, and compare against 0.138N. Show one well-separated and one highly correlated set side by side, and explain the difference through the cross-talk term. Use the statement's J bitmap as one pattern to check your encoding (row-major, 1 = `*`).

**Warning signs:** The 4 chosen letters never fail at any noise level; "capacity = 3.45 so 4 letters should fail" written as the conclusion without experiment.

**Phase to address:** P5.

---

### Pitfall 15: The "limitations of the use case" answer misses the real ones

**What goes wrong:** The limitation section says "capacity is limited" or "it is slow", and stops. The real, defensible limitations are: (1) correlated patterns (Pitfall 1); (2) the network only works on aligned, same-size, binarized images, so a photo of a torn QR with shift, rotation, perspective or scale breaks pixel-wise recall without separate preprocessing (and at 37x37 modules are about one pixel, so any resampling blurs them); (3) the memory is a closed list of 5 known QRs, and a trivial Hamming nearest-pattern lookup solves the same problem (the minimum distance between the QRs is 96 of 1369 pixels, so nearest-pattern should succeed well beyond the noise where Hopfield does; verify, do not assume) so the added value of Hopfield must be argued honestly; (4) QR codes have their own Reed-Solomon error correction (levels L / M / Q / H recover roughly 7 / 15 / 25 / 30% of codewords) so moderate damage may already scan without any network, and a recovered image still has to decode, which needs to be checked with a decoder rather than assumed; (5) spurious and inverse attractors; (6) quadratic storage N^2 (1369^2 doubles is about 15 MB, fine here) and full re-learning when a pattern is added for pinv.

**Why it happens:** The prompt is worded as a story and the "limitations" sentence is written last, at the end.

**How to avoid:** Add a nearest-pattern (Hamming) baseline curve to the noise experiment, and if a QR decoder is available in the analysis environment (OpenCV or pyzbar; analysis-only, outside the "no ML libraries" constraint since it is not Hopfield) run a decode test on recovered images. If not available, say the decodability of the output was not tested.

**Warning signs:** No baseline comparison; "works well" for noise levels where a lookup also works.

**Phase to address:** P6, with the interpretation in P7.

---

## Moderate Pitfalls

### Pitfall 16: Reading PCA components and the biplot wrong
**What goes wrong:** (measured, z-scored) PC1 48%, PC2 9.8%, PC3 8.6%, so 2D shows only 58%; 6 components give 80%, 10 give 90%, and 7 eigenvalues exceed 1 (Kaiser). "Reduce to 2D" is justified for visualization, not for lossless reduction. Component signs are arbitrary (eigh / SVD can return either sign, and across runs or libraries they flip). Biplot arrows are scaled for readability, so arrow length is not directly the loading. 31 arrows are unreadable.
**Prevention:** Report cumulative variance and say what is kept for which purpose (viewing: 2 PCs; clustering: the selected features, not the PCs). Fix a sign convention (largest-|loading| positive, or followers positive). Label only the top-loading arrows, show the loadings table, name the components by loadings, not by guesses. Do not read distance in biplot as distance in data (it is a 58% projection).
**Phase:** P1.

### Pitfall 17: Outliers and heavy tails with n = 50
**What goes wrong:** A few macro-creators (775k followers vs median 198k, `estimated_argentina_reach` skew 2.03, `price_usd` from 75 to 6335) dominate z-scored axes and can sit alone in a neuron.
**Prevention:** Inspect distributions first (box/hist), decide log or not once, and report singleton neurons as outlier groups rather than "segments". Do not delete creators without saying so.
**Phase:** P1.

### Pitfall 18: Compositional variables (percentages that sum to 100) treated as independent
**What goes wrong:** Topic and content shares are closed compositions: raising one lowers the others, which creates artificial negative correlation (measured: tutorial vs entertainment -0.84) and the rank-deficiency in Pitfall 3.
**Prevention:** Drop one component per composition, or apply a centered log-ratio transform (watch zeros; minimum value here is 0.38%, so it is feasible). Interpret negative correlations inside a composition as an arithmetic effect.
**Phase:** P1.

### Pitfall 19: Selecting hyperparameters by looking at the interpretation you like
**What goes wrong:** Picking the grid or schedule whose map "looks like" the four campaign topics. Circular and not reproducible.
**Prevention:** Fix the selection rule (Pitfall 5) before looking at topic overlays, then overlay topics afterwards.
**Phase:** P2.

### Pitfall 20: Maintenance question answered with generalities
**What goes wrong:** "Retrain periodically" is the entire answer.
**Prevention:** Give concrete answers. New campaign: no retraining, only a new selection rule or a new weighting on top of the same SOM / index. New creators: standardize with the stored mean/std and assign a BMU, retrain only when the distance to the BMU (QE of newcomers) rises above the training distribution. New variables: re-run the audit (Pitfall 3), re-standardize, retrain from scratch, since the codebook dimension changes. Monthly update: the SOM orientation and cluster labels can change at each retraining, so fix the seed, store a versioned scaler plus codebook, relabel regions by profile not by position, and keep Oja `w` sign convention (Pitfall 8). A month-to-month drift check (QE of the new month on the old map) tells whether retraining is needed.
**Phase:** P4.

### Pitfall 21: C / Python mismatch (numerics, seeds, formats)
**What goes wrong:** The C core uses a different standardization (ddof, float vs double), RNG or output layout from the Python plots; two seeds that "should be the same" differ; Oja in C is validated against nothing.
**Prevention:** Reuse the TP3 RNG and JSON config; keep the scaler in a single place (Python writes the standardized CSV, or C does it and both read the same file); use `double`; emit weights, BMUs, per-epoch QE/TE, energy traces as CSV; cross-check C-PCA/Oja against numpy `eigh` in a test. Remember the parsing pitfall (Pitfall 4).
**Phase:** P1 / P2.

### Pitfall 22: Binarization and encoding of the QR PNGs
**What goes wrong:** Wrong threshold, wrong polarity in display, or resampling. (measured) The five PNGs are already 37x37 grayscale with only values 0 and 255, so no resampling is needed (and none should be done); dark fraction is 0.51 to 0.53. Polarity (dark = +1 or -1) does not change Hebb dynamics (W is invariant to a global flip of a pattern), but it matters for showing images and for passing the output to a QR decoder.
**Prevention:** Threshold at 128, assert the shape and the value set, render recovered images with the same polarity as the input, keep a pixel-by-pixel round-trip test (encode then decode equals the original).
**Phase:** P6.

---

## Minor Pitfalls

### Pitfall 23: Overclaiming from a 50-point dataset
**What goes wrong:** "The method finds the optimal creators." There is no ground truth and no test set.
**Prevention:** Use hedged but concrete language, always attach a number, and restate the statement's own clarification (focus is the method and its interpretation, assumptions allowed). Keep marketing out of scope (see PROJECT.md).

### Pitfall 24: Plot and report hygiene
**What goes wrong:** Biplot with 31 labelled arrows, U-matrix with a truncated colour scale, Hopfield images with different polarity before/after, energy curves without x-axis meaning, no seed in captions.
**Prevention:** Seed and config in every caption; same colour scale for compared panels; before / noisy / recovered triptychs with Hamming distance annotated; log energy per update.

### Pitfall 25: Reporting silently different datasets or seeds between runs
**What goes wrong:** Results in slides, report and code come from different series or seeds (the user's TP3 notes already ask for versioned series and for stating which dataset each run used).
**Prevention:** Each figure carries its series id and seed; generated results are not versioned (project constraint) but the sweep config is.

### Pitfall 26: Concluding from `0.138N` as if it were exact
**What goes wrong:** 0.138N is the replica-theory critical load for random, uncorrelated patterns with Hebbian learning (a later refinement gives about 0.144N); the practical limit for perfect recall is smaller (about N / (2 ln N)); the pseudo-inverse rule raises the theoretical ceiling to N for linearly independent patterns. All are asymptotic statements.
**Prevention:** Quote 0.138N as an order of magnitude and always pair it with the empirical experiment.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Dropping derived columns without a written audit | Saves an hour | Cannot defend "all variables" vs Kohonen bullet; reviewer questions | Never; the audit table is the justification |
| Selecting the SOM by lowest QE | One number to report | Picks the largest grid, empty neurons, no generalization claim | Never as the only criterion |
| Hard-coded seed in the final figures with no sweep | Pretty reproducible map | Hides seed sensitivity | Acceptable for the displayed figure only if the sweep result is also reported |
| Printing `abs(cos)` only for Oja vs PC1 | Looks like a match | Hides sign convention and norm drift | Never; also report signed cos and rank corr |
| Running only the Hebb rule on QR and calling it done | Matches the statement literally | Result is 0% recovery; reader sees a bug | Acceptable only as the first experiment plus the pinv follow-up and an honest limitation write-up |
| Tuning noise levels to where recall works | Nice curve | Dishonest, not reproducible | Never |
| Using sklearn / scipy PCA for the Oja comparison | Fast | Allowed (PCA is not Kohonen/Oja/Hopfield), but hides convention differences | Fine for validation in Python; the C-side check should still use an independent eigen-solver |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| C core to Python analysis | Different standardization, ddof or float width | One source of the scaler (stored mean/std), `double`, CSV exports of weights, BMUs, energy traces |
| JSON config to C | Silent default when a key is missing | Fail on unknown or missing keys; echo the resolved config into the output folder |
| CSV parse in C | Count rows by newlines, last line has no `\n` | Parse then assert `n == 50`, `cols == 33` |
| PNG to pattern | Re-scaling a 37x37 image | Use as-is, assert values in {0, 255}, threshold 128 |
| Recovered image to QR decoder | Assuming pixel-exact output decodes | Test with a decoder in analysis code, mention if not tested |
| `sweep.py` and seeds | Averaging across runs that differ in init order but not seed | One seed per run, store it, mean plus std over at least 5 seeds |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Hopfield W recomputed per query / dense N^2 loops without reuse | Slow noise sweeps (levels x trials x patterns) | Build W once, vectorize field `W s`, update asynchronously with incremental field `h` | About 1369^2 = 1.9M weights: trivial per sweep, but 5 patterns x 10 levels x 30 trials x several rules x sweeps adds up; still seconds in C |
| Energy recomputed from scratch at every neuron update | O(N^2) per update, O(N^3) per sweep | Update E incrementally: delta E = -(s_new - s_old) * h_i, with a periodic full recompute to check drift | Visible at N = 1369 |
| SOM sweeps over large grids with many seeds | Long runs for no benefit | Cap grids at about 6x6 (more neurons than creators is a non-goal) | Irrelevant at n = 50 |
| Float32 for Oja/SOM | Drift in |w| | `double` | Long Oja runs |

## Security Mistakes

Not applicable for this offline academic assignment. The only domain-specific note: QR codes encode URLs (the statement shows GitHub links), so an automatically "recovered" QR that decodes to a different URL is a real-world integrity risk. A wrong spurious recovery (for example returning the "food" QR for a "beverages" query, measured with Hebb) sends the customer to the wrong menu, which is worth one sentence in the limitations section. Severity: LOW for the assignment.

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Slides with every metric and 31-arrow biplots | Audience cannot follow | One message per slide; biplot with top loadings only |
| Report that starts with method details | Reader cannot find the decisions | Start each section with the answer to the statement's question (hyperparameters chosen; is picking the max correct; followers vs ours; limitations), then evidence |
| Hopfield demo only showing success | Misleading | Show a failure and a spurious state with overlaps |
| Region names invented from two creators | Over-reading | Name regions by averaged raw variables and member count |

## "Looks Done But Isn't" Checklist

- [ ] **Data load:** n_rows = 50 and n_cols = 33 asserted; PROJECT.md "49" corrected.
- [ ] **Feature audit:** table listing each of the 31 variables as keep/drop with reason; retained matrix is full rank; smallest eigenvalue printed.
- [ ] **PCA:** standardized; sign convention stated; cumulative variance reported (2 PCs = 58%); loadings table next to the biplot.
- [ ] **Kohonen hyperparameters:** sweep over grid, lr0, sigma0, decay, epochs with at least 5 seeds; mean and std reported; QE, TE, occupancy, creators per neuron; leave-one-out QE; the choice is not "lowest QE".
- [ ] **Kohonen analysis:** hit map, U-matrix, component planes, de-standardized region profiles, signed PC1/PC2 comparison with numbers, empty neurons flagged.
- [ ] **Oja:** data centered; lr stable; w renormalized; signed cos and rank correlation vs PC1; orientation convention documented; NaN check.
- [ ] **Index interpretation:** loadings shown; correlation with each topic share; explicit "no" to the max-for-all-campaigns question with the evidence table.
- [ ] **Campaign decisions:** each campaign has a stated criterion and a table comparing against followers-only at equal k; no ROI claims.
- [ ] **Maintenance:** new campaign / creator / variable / monthly update each answered concretely (scaler and codebook stored, drift check).
- [ ] **Hopfield letters:** zero-noise stability checked; overlap matrix; capacity experiment (add letters until failure); a spurious state shown with overlaps and its type.
- [ ] **Hopfield QR:** zero-noise stability checked; Hebb result reported even if 0%; pinv or another fix with clear labelling; at least 30 trials per level; structured damage tested; nearest-pattern baseline; energy per step plotted; decoder test or explicit statement that it was not done.
- [ ] **Async energy:** non-increasing assertion in tests; sync mode (if present) has cycle detection.
- [ ] **Reproducibility:** each figure caption carries series id and seed; config is in the output folder.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Last row dropped / wrong n | LOW | Fix the parser, add the assert, rerun everything (cheap, results are generated) |
| PCA/SOM on raw or collinear data | MEDIUM | Redo standardization and audit, rerun P1 to P3; re-draw all figures |
| SOM grid picked by QE | LOW | Rerun the sweep with the multi-criterion rule and leave-one-out; rewrite one report paragraph |
| Oja not centered or diverging | LOW | Center, lower eta, renormalize, validate against `eigh` |
| Hebb on QR "fails" late in the project | MEDIUM | Reframe as finding; add pinv rule (about 20 lines in C: needs a small matrix inverse of the 5x5 Gram matrix); rerun noise sweeps |
| Energy not monotone | LOW | Check diagonal, symmetry, update order, ties; add the assertion |
| Conclusions with no numbers | LOW | Add the evidence table from the existing outputs |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 4 Row count / parser | P1 | Assertion on n=50, n_cols=33; pandas cross-check |
| 2 Unstandardized inputs | P1 | PC1 loadings not dominated by one variable; scaler persisted |
| 3 Collinearity and dependent columns | P1 | Audit table; matrix_rank equals number of retained columns; no eigenvalue below 1e-8 |
| 16 / 17 / 18 PCA reading, outliers, compositions | P1 | Cumulative variance reported; sign convention; composition handling stated |
| 21 C/Python mismatch | P1, P2 | C eigen / Oja output equals numpy `eigh` within tolerance |
| 5 Grid by QE | P2 | Sweep table with occupancy and leave-one-out QE; rule fixed before overlays |
| 7 Schedules | P2 | QE and TE vs epoch flat at the end; sigma floor above 0; mean and std across seeds |
| 6 U-matrix / region reading | P2, P7 | Hit map + U-matrix + component planes; signed PC1/PC2 correlations |
| 19 Selecting by interpretation | P2 | Selection rule written before topic overlay |
| 8 Oja centering / lr / sign | P3 | |cos(w, PC1)| above 0.99, |w| = 1 after normalize, orientation convention documented |
| 9 Index as universal score | P3, P4 | Evidence table with index vs topic share and top-10 overlap |
| 10 Followers baseline | P4 | Per-campaign table at equal k, no ROI claim |
| 20 Maintenance | P4 | Four concrete answers; scaler and codebook versioning described |
| 11 Energy / update order | P5 | Test asserts non-increasing async energy; ties and diagonal handled |
| 14 Letters capacity / orthogonality | P5 | Overlap matrix; capacity sweep over several letter subsets |
| 12 Spurious / inverse states | P5, P6 | Final-state classifier with overlap vector |
| 1 Hebb on correlated QRs | P6 | Zero-noise stability result; pinv follow-up; honest limitation text |
| 13 Noise evaluation | P6 | At least 30 trials, rates not single runs, occlusion included, levels at most 0.5 |
| 15 Limitations | P6, P7 | Nearest-pattern baseline; decoder test or explicit not-tested note |
| 22 PNG encoding | P6 | Shape and value-set assertions; round-trip test |
| 23 / 24 / 25 / 26 Reporting hygiene | P7 | Seeds and series ids in captions; hedged language with numbers |

## Sources

- Dataset and image facts: measured directly on `datos/creadores.csv` (50 rows, 33 columns, rank 26 over the 31 numeric columns) and `datos/hopfield/*.png` (five 37x37 grayscale images, values {0, 255}) with throwaway numpy prototypes (HIGH confidence; to be re-verified by the real implementation).
- Assignment text: `docs/Archivo SIATP 42026.pdf` pages 1 to 6 (statement of variables, the Oja "cualquier campana" and followers-baseline questions, Hopfield QR and letters tasks).
- Project context: `.planning/PROJECT.md`.
- Hopfield capacity, correlated patterns, projection rule (MEDIUM; secondary summaries, no primary-source derivation read): [Dynamic Capacity Estimation in Hopfield Networks (arXiv 1709.05340)](https://arxiv.org/pdf/1709.05340), [Hopfield Networks as Models of Emergent Function in Biology (arXiv 2506.13076)](https://arxiv.org/pdf/2506.13076), [Computational models of learning and synaptic plasticity (arXiv 2412.05501)](https://arxiv.org/pdf/2412.05501).
- Training knowledge (MEDIUM): Amit-Gutfreund-Sompolinsky (0.138N), McEliece et al. (N / (2 ln N)), Personnaz and Kanter-Sompolinsky (pseudo-inverse / projection rule), Oja (1982) fixed point as the top eigenvector of E[x x^T], Kohonen guidelines for ordering and convergence phases, QR Reed-Solomon levels L/M/Q/H.
- Not verified this session: QR decodability of recovered images, pinv behaviour under block occlusion, the 4-letter experiments used my own 5x5 bitmaps (indicative only).

---
*Pitfalls research for: unsupervised learning (PCA / Kohonen / Oja) and Hopfield associative memory academic assignment*
*Researched: 2026-10-20*
