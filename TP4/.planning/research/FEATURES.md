# Feature Research

**Domain:** Academic unsupervised-learning + associative-memory assignment (SIA TP4, ITBA): Kohonen SOM / PCA / Oja on a ~50-creator marketing dataset; Hopfield on 5 QR (37x37) and 4 letters (5x5)
**Researched:** 2026-10-20
**Confidence:** MEDIUM-HIGH. Table stakes are taken directly from the assignment PDF (HIGH). Differentiators come from standard SOM/PCA/Hopfield practice in the course theory and the literature (MEDIUM, written from domain knowledge, no web sources consulted). Dataset facts were checked against `datos/creadores.csv`.

"Feature" here means an analysis, output or deliverable. "Users" means the grader/professor and the audience of the slides. The assignment says the focus is the methods and their interpretation, not exhaustive marketing analysis. So rigor on method and interpretation is what differentiates, not breadth of marketing content.

Dataset facts that shape the features (verified): 50 data rows, 31 columns (the brief says 49; reconcile this in the EDA). `followers` ranges 9.6k to 776k (median 198k), `price_usd` 75 to 6,335, so features are heavily skewed and on wildly different scales. Topic percentages have medians around 12 to 15 with maxima around 70 to 82, which is the signature of creators specialized in one topic. Derived and duplicate columns are present (`price_ars` = 1500 x `price_usd`, `organic_posts_pct` = 100 - `sponsored_posts_pct`, `estimated_argentina_reach`, `total_engagement_per_1000`). Topic and content-type percentages are probably compositional (sum to about 100). Verify this in the EDA.

## Feature Landscape

### Table Stakes (Required by the Assignment or Obviously Expected)

Missing any of these = the submission fails the stated rubric.

#### Exercise 1 - Exploration and PCA

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| EDA: summary stats, distributions, correlation matrix, outliers | Assignment 1: "realizar un EDA" | LOW | Histograms/boxplots of skewed columns (followers, reach, price). Heatmap of correlations. Show the redundant pairs explicitly. |
| Variable-selection decision, written and justified | Assignment 1: "seleccionar qué variables serán utilizadas" | LOW-MED | Drop exact duplicates (`price_ars`, `organic_posts_pct`). Decide on `estimated_argentina_reach` and `total_engagement_per_1000` (derived). Decide on `creator_id`/`name` (identifiers, excluded). State the rule applied. |
| Preprocessing: standardization (z-score) before PCA/SOM/Oja, and a decision on log-transform for skewed counts | PCA/SOM/Oja are scale-sensitive; without it followers/price dominate everything | LOW | Document which variables were log-transformed and why. Keep the mean/std so new creators can be projected (needed for the maintenance question). |
| PCA from scratch: covariance/correlation matrix, eigendecomposition, scree plot, explained-variance and cumulative-variance table | Assignment 1; "sin librerías que lo resuelvan" is a stated constraint | MED | Python/numpy eigendecomposition is acceptable for PCA (course provides the Autovalores doc). Verify against a reference only as a test, not as the deliverable. |
| Explicit dimensionality-reduction decision with a criterion (Kaiser, cumulative variance threshold, scree elbow) | Assignment: "Justificar si se realiza una reducción de dimensionalidad" | LOW | The answer may be "no, keep all variables for Kohonen, use PCs for interpretation". Either is fine if justified. |
| Loadings table and component interpretation (what PC1, PC2 mean in business terms) | Assignment: "cómo se interpretan las componentes" | MED | Name each PC (e.g. "scale/reach" vs "topic/engagement"). Sort loadings by magnitude. |
| Biplot PC1/PC2 (creators as points, variables as arrows) | Assignment 2 explicitly references the "biplot" | MED | Color points by dominant topic. Label extreme creators. Scale arrows legibly. |

#### Exercise 1 - Kohonen

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Kohonen SOM in C, configurable (grid size, radius schedule, learning-rate schedule, epochs, init, distance, seed) | Assignment 2; PROJECT.md constraint | MED-HIGH | Hex or rectangular grid; decide and state topology (square vs toroidal). Neighborhood function (gaussian or step) with decaying radius. |
| Hyperparameter sweep (grid size, initial radius, learning rate, epochs, init) with multiple seeds | Assignment 2: "variar los hiperparámetros" | MED | Reuse TP3 `sweep.py` pattern. Report mean +/- std over seeds, not a single run. |
| Performance metrics to justify the final choice: quantization error (QE) and topographic error (TE) | Assignment 2: "justificar la elección final evaluando la performance" | LOW-MED | QE = mean distance of each creator to its BMU. TE = fraction of samples whose first and second BMU are not adjacent. Plot QE/TE vs each hyperparameter. These two are the standard answer; without them "performance" has no definition. |
| Final-choice justification table (config, QE, TE, why) | Same | LOW | Include the trade-off: bigger grid lowers QE but with 50 samples gives many empty neurons. |
| Grid analysis: hit map / counts per neuron and creator names or labels per neuron | Assignment 2: "analizar la grilla ... y la distribución de los creadores" | LOW-MED | Hit map plus a grid annotated with creator names or dominant topic. |
| U-matrix (unified distance matrix) | Assignment 2: explicit | MED | Average distance of each neuron to its grid neighbors. Needs a correct hex/square neighbor definition. |
| Interpretation of U-matrix: what a high distance between neighboring neurons means (cluster boundary) | Assignment 2 asks this question verbatim | LOW | Short written answer tied to a figure showing a boundary separating real groups. |
| Region profiles: which creator profiles each grid region gathers | Assignment 2 | MED | Component planes or per-region mean tables. |
| Contrast SOM regions with PC1/PC2 biplot | Assignment 2: "¿Coinciden con los perfiles observados en la PC1 y PC2?" | MED | Overlay: plot the biplot colored by SOM region/BMU, or color the SOM by mean PC1/PC2. Say where they agree and where they do not. |

#### Exercise 1 - Oja and campaign decisions

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Oja's rule implementation in C (single neuron), config: learning rate (constant or decaying), epochs, init, seed | Assignment 3 | MED | Needs centered/standardized input. Without centering Oja converges to the uncentered principal direction, not PC1. |
| Convergence evidence: weight-vector norm -> 1, angle/cosine to PC1 vs epoch | Without it "Oja converged" is unsupported | LOW-MED | Cheap to log inside the C core. Plot over several seeds. |
| Creator index = projection onto the Oja weight vector, ranked | Assignment 3: "generar un índice de creadores" | LOW | Ranked table, top and bottom creators. |
| Index interpretation: what it represents (loading signs/weights) | Assignment 3 | LOW-MED | Likely a "size/scale" factor if the data is not log-transformed. Tie to loadings. |
| Answer: is it correct to pick the max creator for any campaign? | Assignment 3 asks this verbatim | LOW | No. PC1 captures overall variance (probably size/reach), not topic fit. A football campaign needs football affinity. Show a counterexample (top-index creator with ~5% football). |
| Oja vs PC1 comparison (cosine/angle between vectors, correlation of projections, sign ambiguity handled, rank agreement) | Assignment 3: "Comparar el resultado con la proyección sobre PC1" | LOW-MED | Remember that eigenvectors are sign-ambiguous: compare |cos|, or align sign before correlating. |
| Campaign decisions for the 4 clients (football, dogs, makeup, art) with a shortlist per campaign | Assignment 4 | MED | Use topic share, audience (`argentina_audience_pct`), engagement, price and SOM region. Short, evidence-linked. Not an exhaustive marketing study. |
| Football campaign: reach vs discovery vs educational depth, argued from results | Assignment 4 bullet 1 | MED | Map "reach" to reach/followers, "discovery" to `non_follower_reach_pct`, "depth" to tutorial/saves/watch time. Say which cluster/PC aligns with each. |
| Comparison against a followers-only strategy (advantages and disadvantages) | Assignment 4 bullet 2 | LOW-MED | Show overlap of top-k lists, and what the followers ranking misses (e.g. cheap, high-affinity, high-Argentina-audience creators) and what it does well (simple, cheap, brand-safe). Honest about both sides. |
| System maintenance discussion: new campaign, new creators, new variables, monthly refresh | Assignment 4 bullet 3 | LOW-MED | A written section grounded in technical facts: BMU lookup without retraining for new creators, saved scaler parameters, retraining triggers, SOM re-orientation between retrainings (maps are not stable across runs), Oja/PCA sign flips, adding variables changes the input dimension so retrain. |

#### Exercise 2 - Hopfield

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Letters first (4 patterns 5x5, +/-1), Hebbian weights W = (1/N) sum xi xi^T with zero diagonal | Assignment 2.2: "primero probar con un caso sencillo" and 2.2.1 | LOW-MED | Asynchronous and synchronous update modes, selectable. Pick letters deliberately (see ortho. analysis). |
| Recovery of each letter from a noisy query, with iterations to convergence | Assignment 2.2 | LOW | Visualize query -> steps -> final as small image grids. |
| Orthogonality analysis: pairwise overlaps/dot products (Gram or correlation matrix) of stored patterns | Assignment 2.2.2 | LOW | Show the matrix as a heatmap. Relate overlap to crosstalk. Show a letter set with low overlap vs a high-overlap set. |
| Capacity analysis (theory p/N ~ 0.138 for random patterns, ~N/(2 ln N) rigorous bound, and the empirical check) | Assignment 2.2.2 | MED | N=25: theoretical limit about 3 random patterns; 4 letters are at or above it, so interesting. Empirically: store k=1..K patterns, measure the fraction of stored patterns that remain stable fixed points. |
| Very-noisy query that lands on a spurious state, identified and shown | Assignment 2.2.3 | LOW-MED | Must demonstrate it is spurious: not equal to any stored pattern or its negation, and it is a stable fixed point (check sign(Wx)=x). Typical types: mixture/combination states, and the negated pattern (-xi is always a fixed point, which is a spurious-ish state worth explaining). |
| QR: convert the 5 PNGs to 37x37 +/-1 vectors (N = 1369) and verify the conversion | Assignment 2.1 | LOW-MED | Threshold, resize/nearest-neighbor, show the binarized images side by side. Check the original is a clean 37x37 module grid. |
| Store 5 QR in the net and verify each is a fixed point | Assignment 2.1 | LOW | Prerequisite for all noise experiments. |
| Query construction with random noise at multiple levels (e.g. flip p = 0.05 .. 0.5), several trials | Assignment 2.1: "distintos niveles de ruido" | MED | Multiple trials/seeds per level. Say how noise is applied (flip fraction exactly p vs Bernoulli p). |
| Iterations to convergence and energy at every step, shown per noise level | Assignment 2.1: "cantidad de iteraciones y la energía en cada paso" | MED | Energy E = -1/2 x^T W x logged by the C core each step (or each full sweep in async mode). Plot E vs step with one curve per noise level. Energy must be monotonically non-increasing (async), which is itself a correctness test. |
| Limitations of the use case explained | Assignment 2.1: "Explicar las limitaciones" | LOW-MED | Distinct points: small capacity relative to N, correlated patterns (QR share finder patterns, so overlaps are high), spurious attractors, +/- inverse patterns, random noise is not realistic damage (real damage is a missing corner/blocks/scratches), 37x37 downscale loses real scanability, O(N^2) memory, the recovered image must still decode to be useful. |

#### Cross-cutting deliverables

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| C core (Kohonen, Oja, Hopfield) + JSON config + Makefile, Python for analysis/plots | PROJECT.md constraint | MED-HIGH | Mirrors TP3 structure (`neuron/`, `analysis/`, `scripts/`). |
| Fixed seeds, reproducible runs, multi-seed series | PROJECT.md and TP3 convention | LOW-MED | Reuse TP3 rng/sweep infrastructure. Generated results not versioned. |
| Slides (one section per exercise) | User requirement | MED | Figure-led. One conclusion per slide. |
| Written report (Artifact) | User requirement | MED | Method, results and interpretation. Every figure answers an assignment question. |
| Explicit mapping "assignment question -> where answered" | Graders scan for the verbatim questions | LOW | A checklist table in the report. Cheap insurance. |

### Differentiators (Add Rigor, Not Required)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Component planes for every (or key) variable on the SOM grid | Explains why regions differ, and links SOM to variable semantics. Often expected in a strong SOM analysis even though the assignment does not name it | LOW-MED | Small multiples. Group variables (topics, content, scale, audience). Probably table-stakes-adjacent: needed for "region profiles". |
| Cluster extraction from the SOM (e.g. hierarchical/k-means on the codebook vectors, or U-matrix boundaries) with a silhouette check | Turns the map into named creator segments usable for campaign shortlists | MED | Using k-means/hierarchical from a library for post-processing is fine (the "no ML libs" constraint targets Kohonen/Oja/Hopfield). Keep it small. |
| SOM stability across seeds (BMU/cluster agreement, adjusted Rand index between runs) | 50 samples on a map is fragile. Shows the result is not a seed artifact | MED | Directly supports "the final choice is justified". |
| Hyperparameter sensitivity heatmaps (QE and TE over 2 hyperparameters) plus a QE-TE Pareto view | Better than one-at-a-time plots. Makes the trade-off visible | MED | Also shows convergence of QE vs epoch. |
| Empty-neuron count / map-utilization as a third criterion | Prevents over-large grids that "win" on QE | LOW | Reported in the choice table. |
| Preprocessing ablation: raw vs z-score vs log+z-score on PCA/SOM (QE/TE, variance explained) | Justifies preprocessing with evidence, not assertion | MED | One figure. Strong answer to "why these variables". |
| Handling collinearity with evidence: variance-inflation or correlation clusters, PCA with and without derived columns | The brief explicitly flags the derived variables. Shows the effect (e.g. duplicate columns double-weighting a direction) | MED | Tie to the variable-selection decision. |
| Correlation circle and per-creator contribution/cos2 on the biplot | Reads the biplot correctly (arrow length only means something if the variable is well represented in PC1-2) | LOW-MED | Cheap once loadings exist. |
| Parallel analysis or broken-stick for the number of components | A more defensible rule than Kaiser, especially at n=50 | MED | Permutation-based, a few lines. |
| Oja variants: Sanger/generalized Hebbian for PC2 (and beyond), learning-rate sensitivity, convergence speed | Course docs include "Oja y Sanger". Gives a second PC from the net and a full-biplot comparison | MED | Optional. Only if time remains. A 2-component Sanger comparison is neat but not required. |
| Oja index sensitivity: with/without centering, with/without log, rank correlation (Spearman/Kendall) with PC1 and with followers | Shows exactly when the "index" is just size | LOW-MED | Feeds directly into the "is max always right?" answer. |
| Topic-conditioned index / campaign-specific scoring (e.g. Oja or PC applied to the subset of relevant variables, or weighted by topic) | A defensible alternative to "just take the max index" | MED | A short, honest contrast: the global index does not know the campaign. Keep it small, do not build a recommender. |
| Quantitative followers-only comparison: overlap@k, mean topic share / engagement / Argentina-audience / cost-per-reach for the top-k under each strategy | Makes the comparison concrete and checkable | LOW-MED | A single table. Cost efficiency uses `price_usd` / `estimated_argentina_reach`. State assumptions (the brief allows it). |
| Projecting a new creator onto the trained SOM/PCA (BMU lookup, nearest neighbors) as a demo for the maintenance question | Demonstrates the claim rather than only asserting it | LOW-MED | Needs saved scaler and weights. Simple script. |
| Hopfield: noise-robustness curves (probability of exact recovery and mean final overlap/Hamming error vs noise level, per pattern, with error bars over trials) | The standard "analysis of noise levels". The central quantitative output | MED | Mark the critical noise level where recovery collapses. Include 50 percent noise as chance. |
| Hopfield: energy-landscape evidence (stored patterns as minima, energy of noisy start vs final, energy of spurious states being higher than that of stored patterns) | Connects the dynamics to the theory | LOW-MED | One table or plot, derived from the same logs. |
| Hopfield: overlap (Mattis) order parameter m_mu(t) vs time for each stored pattern | Shows which memory the state is attracted to, and diagnoses mixtures | LOW-MED | Cheap from the logs. Great for the spurious-state explanation. |
| Hopfield: stored-QR cross-correlation matrix (5x5 overlaps) and its relation to failures | Quantifies why QR is a hard case (shared finder patterns and timing patterns) | LOW | Same code as letters. Predicts which pair confuses first. |
| Hopfield: structured damage (missing corner, block erasure, scratch lines, stains) instead of only random flips | The story in the assignment is a torn corner and stains. Tests the use case honestly | MED | Same recovery pipeline with different corruption masks. Contrast with random flips. |
| Hopfield: decoding check, i.e. run the recovered QR through a QR decoder (e.g. an image/QR library) to confirm it is scannable | Ties the metric to the use case ("send it to a QR reader") | LOW-MED | The decoder is only a verification tool, not the object of study. Likely fails at 37x37 downscale. Check the original binarization decodes first, and report that honestly. |
| Hopfield: capacity experiment on random patterns (N = 25 and N = 1369) comparing empirical alpha_c with 0.138 | Verifies the capacity theory on the very networks used | MED | Sweep P, many random sets. A fast C implementation makes this cheap. |
| Hopfield: stored-pattern stability check (fraction of stored patterns that are fixed points vs P) and the inverse-pattern / mixture spurious catalogue | Systematic spurious-state evidence, not a single example | MED | Enumerate fixed points reached from many random starts in the 25-neuron case (2^25 is enumerable but not needed, sampling is enough). Classify: stored, negated, 3-mixture, other. |
| Hopfield: synchronous vs asynchronous update comparison (convergence, 2-cycles) | Synchronous updates can oscillate in 2-cycles. A known pitfall worth showing | LOW-MED | Only if energy curves are already there. |
| Hopfield: pseudo-inverse / Storkey learning as a short comparison | Demonstrates how correlated QR patterns could be made storable | MED-HIGH | Optional extension. Only after the core is complete. Not required. |
| Reproducible figures from one command (Makefile target) and archived configs per figure | Graders can re-run. Pairs with the TP3 style | LOW | Cheap given existing TP3 scaffolding. |
| One-page "decision summary" per campaign (client, shortlist, rationale, risks) | Makes the campaign decisions skimmable | LOW | Appendix style. |

### Anti-Features (Do Not Build)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Exhaustive marketing analysis (ROI models, audience segmentation studies, budget optimizers) | Looks thorough and "business-valuable" | The assignment says it is not expected and the focus is methods and interpretation. Burns time and dilutes the narrative | Short evidence-based shortlist per campaign and clear stated assumptions |
| Calling sklearn/minisom/numpy-free libraries for Kohonen, Oja or Hopfield | Faster and "more correct" | Violates the pedagogical constraint (the methods are the object of study) | Implement in C. Use libraries only to cross-check in tests and for plotting/eigendecomposition reference |
| Using a library PCA as the only PCA | Less code | The assignment is about interpreting components. Hand-computing is cheap and avoids black-box sign/scale confusion | Eigendecomposition of the covariance/correlation matrix, then optional cross-check |
| Choosing hyperparameters from a single seed or by eye on one map | Fast | 50 samples make SOM layouts seed-dependent. The "justify with performance" requirement fails | Multi-seed QE/TE with variability, plus a stability metric |
| Keeping all 31 columns unfiltered, including exact duplicates | "All variables" in the brief | Duplicate and derived columns double-count the same information and distort distances/PCA | Documented selection rule. Keep a with/without ablation if worried about the instruction "todas sus variables" |
| Picking the highest Oja/PC1 score as "the best creator" for every campaign | The index looks like a quality score | Directly the trap in the assignment question. PC1 is a size/variance direction with no campaign semantics | Use it as a descriptive index, then filter by campaign-relevant variables and SOM region |
| Interpreting a single SOM picture as ground truth (naming clusters without U-matrix and hit counts) | SOM maps look convincing | Map orientation is arbitrary. Empty neurons and folds mislead. Edges distort | Report U-matrix, hit map, TE and cross-seed stability together |
| Large SOM grids (e.g. 20x20) for 50 samples | Lowers QE | Mostly empty map, overfit, uninterpretable | Choose a grid around the sqrt(5 sqrt(n)) heuristic (about 6x6) as the starting point, then sweep |
| Interpreting the Hopfield result by a single noisy example | Easy to make a pretty figure | Not evidence. Random noise outcomes vary run to run | Many trials per noise level with error bars |
| Higher-resolution QR images / full-size QR | More realistic | The brief fixes 37x37. N=1369 means a 1.9M-weight matrix (fine) but patterns are highly correlated and capacity is the point | Stay at 37x37. Mention scaling in the limitations |
| Storing many more QR or "trying to make Hopfield production-grade" | Practical appeal | Capacity limit is the lesson. Real QR codes already have Reed-Solomon error correction, so Hopfield is an interesting but unnecessary solution | State this clearly in the limitations. Do not engineer around it |
| Web app / dashboard / interactive UI for the campaigns | Looks polished | Not a deliverable. Adds maintenance for no grading value | Static figures, one report (Artifact) and slides |
| A generic ML pipeline framework or config-schema system | Elegance | Over-engineering for three small algorithms | Plain JSON config per executable, as in TP3 |
| Reporting results from many unrelated metrics without interpretation | Looks rigorous | Graders ask "what does it mean?" every time | Each metric appears only next to the decision it supports |
| Emojis, decorative graphics, 3D charts | Presentation polish | Reduces clarity | Plain, labeled, color-blind-safe plots |

## Feature Dependencies

```
Variable selection + preprocessing (z-score, log decision, saved scaler)
    ├──requires──> EDA (distributions, correlations, duplicates)
    ├──enables──> PCA (eigendecomposition, scree, loadings)
    │                 ├──enables──> Biplot ──enables──> SOM-vs-PC1/PC2 contrast
    │                 └──enables──> Oja-vs-PC1 comparison (the reference direction)
    ├──enables──> Kohonen C core
    │                 ├──requires──> QE and TE computation
    │                 │                  └──enables──> Hyperparameter sweep ──> final-choice justification
    │                 ├──enables──> Hit map, U-matrix, component planes
    │                 │                  └──enables──> Region profiles ──> SOM-vs-PC contrast
    │                 └──enables──> New-creator BMU demo (maintenance answer)
    └──enables──> Oja C core ──> Convergence log ──> Index ──> "max is not always right" answer

Region profiles + Oja index + PC analysis ──feed──> Campaign decisions ──> followers-only comparison
Campaign decisions ──informs──> Maintenance discussion

Hopfield C core (Hebb, zero diagonal, async/sync, energy log, overlap log)
    ├──enables──> Letters (4 patterns) ──> Orthogonality + capacity ──> Spurious state identification
    └──enables──> QR (binarization first) ──> Noise sweep ──> Energy/iterations plots ──> Limitations
                                              └──enhanced-by──> QR cross-correlation, structured damage, decoder check

Letters analysis ──informs──> QR analysis (same tooling, simple case first, as the assignment recommends)
Sweep infrastructure (multi-seed, from TP3) ──supports──> Kohonen sweep, Oja convergence, Hopfield noise curves
All figures ──feed──> Slides + Artifact report
```

### Dependency Notes

- **Preprocessing requires EDA, and everything else requires preprocessing:** an un-standardized or un-logged `followers`/`price` column makes PCA PC1 a size axis, makes the SOM map follow size, and makes Oja converge to the same size axis. The Oja-vs-PC1 agreement is only meaningful if both use the same preprocessed data and Oja's inputs are centered.
- **Hyperparameter sweep requires QE/TE:** "justify with performance" has no content until the metrics exist. Build the metrics before the sweep, and the sweep before any interpretation figure, so interpretation is done on the final map only.
- **Region profiles require hit map + U-matrix + component planes:** each answers a different part ("who is there", "where are the boundaries", "why").
- **SOM-vs-PC contrast requires the biplot and the final SOM:** do it last in Exercise 1 analysis.
- **Oja convergence log requires Oja C core to emit weights per epoch:** cheap to add up front, hard to add later across seeds.
- **Hopfield energy curve requires per-step logging in C:** decide the logging granularity (per neuron update vs per sweep) up front. Async per-update energy is monotone. Sweep-level is smoother to plot.
- **QR analysis requires binarization and a stable preprocessing check:** a wrong threshold silently changes the stored patterns.
- **Letters' spurious-state identification requires the capacity discussion:** 4 letters on 25 neurons is at or above the Hebbian capacity (about 0.138 N = 3.5), so spurious states are expected. Choosing the letters (overlap) controls how visible this is.
- **Decoder check conflicts with downscaled resolution:** a 37x37 binarization may decode, since 37x37 is a QR version 5 (37 modules) grid, but verify. If the 5 PNGs are not exactly module-aligned, the stored patterns are not valid QRs at all. Check this before promising a decoder check.
- **Pseudo-inverse/Storkey conflicts with "implement Hopfield as in the course":** keep it as a clearly labeled extension, not a replacement of the Hebbian baseline.
- **Followers-only comparison requires the campaign shortlists:** compare the same k and the same metrics.
- **Maintenance discussion enhances from the BMU/projection demo but does not require it:** the written answer is table stakes, the demo is a differentiator.

## MVP Definition

### Launch With (v1: covers every assignment bullet)

- [ ] EDA, variable-selection rule, preprocessing (z-score, log decision) with saved scaler
- [ ] PCA with scree, cumulative variance, loadings, interpreted components, biplot
- [ ] Kohonen C core, multi-seed hyperparameter sweep with QE and TE, final-choice table
- [ ] Hit map, U-matrix, component planes (needed to give region profiles), region profiles, SOM-vs-PC1/PC2 contrast
- [ ] Oja C core with convergence log, index and ranking, interpretation, answer to "is the max always right?", Oja-vs-PC1 comparison (cosine and rank correlation)
- [ ] Campaign decisions for the four clients, football reach/discovery/depth argument, followers-only comparison, maintenance discussion
- [ ] Hopfield C core with energy and iteration logging; letters (4 patterns), orthogonality heatmap, capacity discussion with a small empirical check, very-noisy query landing on an identified spurious state
- [ ] QR binarization, storage, multi-level multi-trial noise experiment, energy-per-step and iterations plots, limitations
- [ ] Slides (three sections) and written report (Artifact), with a question-to-answer checklist

### Add After Core Works (v1.x: highest rigor per hour)

- [ ] Hopfield noise-robustness curves with error bars and the critical-noise estimate (trigger: Hopfield core runs)
- [ ] Overlap (Mattis) trajectories and the QR cross-correlation matrix (trigger: energy logging exists)
- [ ] Structured damage (missing corner, blocks) matching the assignment story (trigger: noise pipeline works)
- [ ] SOM stability across seeds, hyperparameter sensitivity heatmaps, empty-neuron count (trigger: sweep works)
- [ ] Preprocessing ablation and collinearity evidence (trigger: PCA and SOM run)
- [ ] Quantitative followers-only table (overlap@k, topic share, cost per Argentine reach) (trigger: shortlists exist)
- [ ] Spurious-state catalogue by sampling random starts on the 25-neuron net (trigger: letters work)
- [ ] Parallel analysis for the number of components

### Future Consideration (only if time remains)

- [ ] Sanger/generalized Hebbian (second component) and the full biplot comparison
- [ ] QR decoder verification of recovered images
- [ ] Capacity experiment on random patterns at N=1369
- [ ] Synchronous vs asynchronous comparison with 2-cycle demonstration
- [ ] Pseudo-inverse or Storkey rule comparison
- [ ] New-creator projection demo script
- [ ] Topic-conditioned campaign scoring

## Feature Prioritization Matrix

| Feature | Grading/Insight Value | Implementation Cost | Priority |
|---------|-----------------------|---------------------|----------|
| EDA + variable selection + preprocessing | HIGH | LOW | P1 |
| PCA scree/loadings/biplot | HIGH | MEDIUM | P1 |
| Kohonen core + QE/TE sweep | HIGH | HIGH | P1 |
| Hit map + U-matrix + component planes + region profiles | HIGH | MEDIUM | P1 |
| SOM-vs-PC contrast | HIGH | MEDIUM | P1 |
| Oja core + convergence + index + answer | HIGH | MEDIUM | P1 |
| Oja vs PC1 comparison | HIGH | LOW | P1 |
| Campaign decisions + followers comparison + maintenance | HIGH | MEDIUM | P1 |
| Hopfield letters: ortho, capacity, spurious | HIGH | MEDIUM | P1 |
| Hopfield QR: noise levels, energy, iterations, limitations | HIGH | MEDIUM | P1 |
| Slides + report + question checklist | HIGH | MEDIUM | P1 |
| Noise-robustness curves with error bars | HIGH | MEDIUM | P2 |
| Overlap trajectories, QR cross-correlation | MEDIUM | LOW | P2 |
| Structured QR damage | MEDIUM | MEDIUM | P2 |
| SOM seed stability, sensitivity heatmaps | MEDIUM | MEDIUM | P2 |
| Preprocessing ablation / collinearity evidence | MEDIUM | MEDIUM | P2 |
| Quantitative followers-only table | MEDIUM | LOW | P2 |
| SOM cluster extraction + silhouette | MEDIUM | MEDIUM | P2 |
| Spurious-state catalogue | MEDIUM | MEDIUM | P2 |
| Sanger / second component | LOW | MEDIUM | P3 |
| Decoder verification of recovered QR | LOW-MEDIUM | LOW-MEDIUM | P3 |
| Pseudo-inverse / Storkey | LOW | HIGH | P3 |
| Sync vs async comparison | LOW | LOW-MEDIUM | P3 |

**Priority key:** P1 = required by the assignment or needed to answer a verbatim question. P2 = rigor that strengthens a P1 claim at modest cost. P3 = nice to have.

## Reference Analysis (Comparable Strong Submissions / Standard Practice)

| Aspect | Typical submission | Strong submission | Our approach |
|--------|--------------------|-------------------|--------------|
| SOM evaluation | One map, qualitative description | QE and TE vs hyperparameters, multi-seed, hit map, U-matrix, component planes | QE/TE sweep over several seeds plus utilization and stability |
| PCA | Scree and a 2D scatter | Loadings, named components, biplot with arrows and contributions, preprocessing justified | Loadings-first interpretation and an explicit reduction decision |
| Oja | Weights printed, "it works" | Convergence vs PC1 (cosine), norm to 1, centered input, rank comparison | Convergence log and quantified Oja-vs-PC1 agreement |
| Index interpretation | "Highest is best" | Explains that PC1 is not campaign-specific and shows a counterexample | Counterexample from the data, campaign-conditioned shortlist |
| Hopfield letters | Recovers a letter | Overlap matrix, capacity theory vs empirical, identified spurious state with a fixed-point check | Same, plus a small spurious-state catalogue |
| Hopfield QR | One noisy example | Multiple noise levels, many trials, robustness curve, energy per step, honest limitations | Same, plus structured damage that matches the story |

## Sources

- Assignment text: `/Users/gonzalocuri/Documents/dev/repos/SIA/SIA-TPs/TP4/docs/Archivo SIATP 42026.pdf` (HIGH, primary source for all table stakes)
- Project context: `/Users/gonzalocuri/Documents/dev/repos/SIA/SIA-TPs/TP4/.planning/PROJECT.md` (HIGH)
- Dataset inspection: `/Users/gonzalocuri/Documents/dev/repos/SIA/SIA-TPs/TP4/datos/creadores.csv` (HIGH for the facts listed above: row count, ranges)
- Course theory docs in `/Users/gonzalocuri/Documents/dev/repos/SIA/SIA-TPs/TP4/docs/` (Kohonen Model, PCA, Regla de Oja y Sanger, Modelo de Hopfield, Autovalores y Autovectores). Not read in this pass, so definitions of QE/TE, capacity constants and neighbor conventions should be checked against them before requirements are frozen (flag for phase research)
- Standard SOM practice (QE, TE, U-matrix, component planes; Kohonen 1982/2001; Vesanto 1999 heuristics) and Hopfield theory (Hopfield 1982; Amit-Gutfreund-Sompolinsky 1985 alpha_c ~ 0.138; McEliece et al. N/(2 ln N)) from domain knowledge (MEDIUM: not re-verified online in this pass)
