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

use pyo3::prelude::*;

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

#[pymodule]
fn triangles_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(version, module)?)?;
    module.add_function(wrap_pyfunction!(schema_version, module)?)?;
    module.add_function(wrap_pyfunction!(build_info, module)?)?;
    Ok(())
}
