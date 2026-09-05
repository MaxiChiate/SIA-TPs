//! The per-individual kernel: allele vector -> rendered canvas -> fitness.
//!
//! Everything a run needs and never changes lives in [`ScorerInner`], built
//! once: the target pixels, the canvas dimensions, the decode rules, and a
//! prebuilt background canvas that each evaluation starts from with a single
//! `memcpy` rather than a fill loop.

use crate::color::{to_byte, ColorSpace};
use crate::raster::{draw, squared_error, Triangle};

/// Six vertex coordinates + three colour channels + alpha.
pub const GENES_PER_TRIANGLE: usize = 10;

pub struct ScorerInner {
    pub width: usize,
    pub height: usize,
    pub triangle_count: usize,
    pub color_space: ColorSpace,
    pub baseline_mse: f64,
    target: Vec<u8>,
    background_rgb: [u8; 3],
    background_canvas: Vec<u8>,
}

impl ScorerInner {
    pub fn new(
        target: Vec<u8>,
        width: usize,
        height: usize,
        background_rgb: [u8; 3],
        triangle_count: usize,
        color_space: ColorSpace,
        baseline_mse: f64,
    ) -> Self {
        let background_canvas = background_rgb
            .iter()
            .copied()
            .cycle()
            .take(width * height * 3)
            .collect();
        Self {
            width,
            height,
            triangle_count,
            color_space,
            baseline_mse,
            target,
            background_rgb,
            background_canvas,
        }
    }

    pub fn genome_len(&self) -> usize {
        self.triangle_count * GENES_PER_TRIANGLE
    }

    /// Decode the `index`-th triangle of a genome at the given canvas size.
    ///
    /// Mirrors `genotype.triangles_from_alleles`: coordinates scale by the
    /// canvas dimensions, colour goes through the run's colour space, and alpha
    /// is always the linear tenth gene.
    fn triangle(&self, alleles: &[f64], index: usize, width: f64, height: f64) -> Triangle {
        let base = index * GENES_PER_TRIANGLE;
        let g = &alleles[base..base + GENES_PER_TRIANGLE];
        Triangle {
            vertices: [
                (g[0] * width, g[1] * height),
                (g[2] * width, g[3] * height),
                (g[4] * width, g[5] * height),
            ],
            color: self.color_space.to_rgb(g[6], g[7], g[8]),
            alpha: to_byte(g[9]),
        }
    }

    /// Render a genome into `canvas`, which must already be the right length.
    pub fn render_into(&self, alleles: &[f64], canvas: &mut [u8], width: usize, height: usize) {
        if width == self.width && height == self.height {
            // The scoring resolution: one memcpy from the canvas built at
            // construction, which beats any fill loop.
            canvas.copy_from_slice(&self.background_canvas);
        } else {
            // An export at some other resolution; not a hot path.
            for pixel in canvas.chunks_exact_mut(3) {
                pixel.copy_from_slice(&self.background_rgb);
            }
        }
        let (fw, fh) = (width as f64, height as f64);
        for index in 0..self.triangle_count {
            draw(canvas, width, height, &self.triangle(alleles, index, fw, fh));
        }
    }

    /// Mean squared error of a genome against the target, before normalisation.
    pub fn mse(&self, alleles: &[f64], canvas: &mut Vec<u8>) -> f64 {
        let pixels = self.width * self.height * 3;
        canvas.resize(pixels, 0);
        self.render_into(alleles, canvas, self.width, self.height);
        squared_error(canvas, &self.target) as f64 / pixels as f64
    }

    /// Fitness: 1 - mse/baseline, floored at 0.
    ///
    /// Identical to `fitness.pixel_similarity`, floor included - the backend's
    /// job is to be fast, not to change the objective function.
    pub fn score(&self, alleles: &[f64], canvas: &mut Vec<u8>) -> f64 {
        let mse = self.mse(alleles, canvas);
        (1.0 - mse / self.baseline_mse).max(0.0)
    }
}
