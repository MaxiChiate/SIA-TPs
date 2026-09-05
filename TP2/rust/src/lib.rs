//! Native rasterize-and-score kernel for the TP2 triangles problem.
//!
//! This crate owns pixels and nothing else. There is no genetic algorithm in
//! here: no RNG, no selection, no crossover, no mutation. The only entry point
//! is [`Scorer`], a pure function of an allele vector, which is what keeps the
//! assignment's rule intact — external code may handle images, but the GA
//! itself is the group's own work, and it stays in Python.
//!
//! The Python side owns the search; this side answers one question, fast:
//! "how far is the picture these alleles describe from the target?"

mod color;
mod raster;
mod score;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use rayon::prelude::*;

use color::ColorSpace;
use score::{ScorerInner, GENES_PER_TRIANGLE};

/// Bumped whenever the scoring kernel's numerics change.
///
/// `RustRenderer` asserts this against a constant on the Python side, so a
/// stale `.so` left over from an earlier build fails loudly instead of quietly
/// producing fitness values that no longer match the source tree.
const SCHEMA_VERSION: u32 = 1;

#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pyfunction]
fn schema_version() -> u32 {
    SCHEMA_VERSION
}

/// Which SIMD baselines this binary was actually compiled for.
///
/// Worth surfacing: the difference between a `--release` build with
/// `target-cpu=x86-64-v3` and a default one is large enough to look like a bug
/// if you cannot tell which you are running.
#[pyfunction]
fn build_info() -> String {
    let mut features: Vec<&str> = Vec::new();
    if cfg!(target_feature = "sse4.2") {
        features.push("sse4.2");
    }
    if cfg!(target_feature = "avx") {
        features.push("avx");
    }
    if cfg!(target_feature = "avx2") {
        features.push("avx2");
    }
    if cfg!(target_feature = "fma") {
        features.push("fma");
    }
    let profile = if cfg!(debug_assertions) { "debug" } else { "release" };
    format!("{} [{}]", profile, features.join(","))
}

/// Decode three alleles as an sRGB triple, the same way the scoring kernel does.
///
/// Exposed purely so the parity tests can compare colour decoding against the
/// Python implementation directly, with no rasterizer in between.
#[pyfunction]
fn to_rgb(space: &str, a: f64, b: f64, c: f64) -> PyResult<(u8, u8, u8)> {
    let space = ColorSpace::from_name(space)
        .ok_or_else(|| PyValueError::new_err(format!("unknown color space {space:?}")))?;
    let [red, green, blue] = space.to_rgb(a, b, c);
    Ok((red, green, blue))
}

/// Scores allele vectors for one run's target image.
///
/// Constructed once per run: the target pixels and every decode rule are
/// uploaded here, not on every call, which is the whole reason this is an object
/// rather than a free function.
#[pyclass(module = "triangles_native", frozen)]
struct Scorer {
    inner: ScorerInner,
    /// A pool of this scorer's own, not rayon's global one: the thread count
    /// then comes from the config rather than from `RAYON_NUM_THREADS`, and two
    /// scorers in one process (the parity tests build several) cannot disturb
    /// each other.
    pool: rayon::ThreadPool,
}

#[pymethods]
impl Scorer {
    #[new]
    #[pyo3(signature = (
        target_rgb, width, height, background_rgb, triangle_count, color_space,
        baseline_mse, threads = 0
    ))]
    fn new(
        target_rgb: &[u8],
        width: usize,
        height: usize,
        background_rgb: (u8, u8, u8),
        triangle_count: usize,
        color_space: &str,
        baseline_mse: f64,
        threads: usize,
    ) -> PyResult<Self> {
        // Every argument is validated here, before any kernel code runs. The
        // release profile aborts on panic, so a bad length must come back as a
        // Python exception rather than take the interpreter down with it.
        if width == 0 || height == 0 {
            return Err(PyValueError::new_err("canvas must have a positive size"));
        }
        if target_rgb.len() != width * height * 3 {
            return Err(PyValueError::new_err(format!(
                "target_rgb has {} bytes, expected {} for {}x{} RGB",
                target_rgb.len(),
                width * height * 3,
                width,
                height
            )));
        }
        if triangle_count == 0 {
            return Err(PyValueError::new_err("triangle_count must be > 0"));
        }
        if !(baseline_mse > 0.0) {
            return Err(PyValueError::new_err("baseline_mse must be > 0"));
        }
        let space = ColorSpace::from_name(color_space).ok_or_else(|| {
            PyValueError::new_err(format!("unknown color space {color_space:?}"))
        })?;
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(threads) // 0 means one per available core
            .build()
            .map_err(|err| PyValueError::new_err(format!("cannot build thread pool: {err}")))?;
        Ok(Self {
            inner: ScorerInner::new(
                target_rgb.to_vec(),
                width,
                height,
                [background_rgb.0, background_rgb.1, background_rgb.2],
                triangle_count,
                space,
                baseline_mse,
            ),
            pool,
        })
    }

    /// How many threads `score_batch` will actually use.
    #[getter]
    fn threads(&self) -> usize {
        self.pool.current_num_threads()
    }

    fn score(&self, alleles: Vec<f64>) -> PyResult<f64> {
        self.check_len(alleles.len())?;
        let mut canvas = Vec::new();
        Ok(self.inner.score(&alleles, &mut canvas))
    }

    /// Raw mean squared error, before the fitness normalisation.
    ///
    /// Exposed for the parity tests: fitness floors at 0 for anything worse
    /// than a blank canvas, and that floor hides the difference being measured.
    fn mse(&self, alleles: Vec<f64>) -> PyResult<f64> {
        self.check_len(alleles.len())?;
        let mut canvas = Vec::new();
        Ok(self.inner.mse(&alleles, &mut canvas))
    }

    /// Score a whole generation, spreading it across this scorer's threads.
    ///
    /// The GIL is held only long enough to marshal the genomes in and the
    /// results out; the rendering itself runs outside it, which is what makes
    /// the threads real. Parallelism is strictly *across* individuals - the
    /// per-individual kernel is sequential and there is no accumulation shared
    /// between them - so a genome's score does not depend on the thread count,
    /// and `collect` restores input order regardless of completion order.
    fn score_batch(&self, py: Python<'_>, genomes: Vec<Vec<f64>>) -> PyResult<Vec<f64>> {
        for genome in &genomes {
            self.check_len(genome.len())?;
        }
        Ok(py.allow_threads(|| {
            self.pool.install(|| {
                genomes
                    .par_iter()
                    // One scratch canvas per worker thread, reused across every
                    // individual it handles: no allocation in the hot loop.
                    .map_init(Vec::new, |canvas, genome| self.inner.score(genome, canvas))
                    .collect()
            })
        }))
    }

    /// Render a genome at an arbitrary resolution, as raw RGB bytes.
    ///
    /// The genotype is resolution-independent, so this can draw the same
    /// individual at export size.
    fn render_rgb<'py>(
        &self,
        py: Python<'py>,
        alleles: Vec<f64>,
        width: usize,
        height: usize,
    ) -> PyResult<Bound<'py, PyBytes>> {
        self.check_len(alleles.len())?;
        if width == 0 || height == 0 {
            return Err(PyValueError::new_err("canvas must have a positive size"));
        }
        let mut canvas = vec![0u8; width * height * 3];
        self.inner.render_into(&alleles, &mut canvas, width, height);
        Ok(PyBytes::new(py, &canvas))
    }
}

impl Scorer {
    fn check_len(&self, given: usize) -> PyResult<()> {
        let expected = self.inner.genome_len();
        if given != expected {
            return Err(PyValueError::new_err(format!(
                "genome has {given} alleles, expected {expected} \
                 ({} triangles x {GENES_PER_TRIANGLE})",
                self.inner.triangle_count
            )));
        }
        Ok(())
    }
}

#[pymodule]
fn triangles_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(version, module)?)?;
    module.add_function(wrap_pyfunction!(schema_version, module)?)?;
    module.add_function(wrap_pyfunction!(build_info, module)?)?;
    module.add_function(wrap_pyfunction!(to_rgb, module)?)?;
    module.add_class::<Scorer>()?;
    Ok(())
}
