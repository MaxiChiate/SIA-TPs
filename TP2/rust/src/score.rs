//! The per-individual kernel: allele vector -> rendered canvas -> fitness.
//!
//! Everything a run needs and never changes lives in [`ScorerInner`], built
//! once: the target pixels, the canvas dimensions, the decode rules, and a
//! prebuilt background canvas that each evaluation starts from with a single
//! `memcpy` rather than a fill loop.
//!
//! A genome is a flat list of shape blocks. [`ShapeMode`] decides what is in
//! each block:
//!
//! - `Triangle`: `x1,y1,x2,y2,x3,y3, r,g,b, a` (10 genes) - unchanged from the
//!   original triangles-only layout.
//! - `Oval`: `cx,cy,rx,ry,theta, r,g,b, a` (9 genes).
//! - `Both`: `kind, p0..p5, r,g,b, a` (11 genes). `kind` is a discrete 0/1
//!   gene mutation is free to flip like any other locus; `p0..p5` are six
//!   generic slots read as the triangle's six coordinates when `kind` rounds
//!   to 0, or as the oval's `cx,cy,rx,ry,theta` (with the sixth slot unused
//!   but still mutating) when it rounds to 1. Colour and alpha always sit in
//!   the same trailing slots regardless of `kind`, which is what lets
//!   `render_into` decode a whole genome without ever branching on shape type
//!   itself - only [`ScorerInner::shape`] and `raster::draw` know two kinds
//!   exist.
//!
//! Alpha is always the last gene of a block in every mode, which is what lets
//! the Python side seed generation 0 with `initial_alpha` by locus offset
//! alone, with no per-mode special case.

use crate::color::{to_byte, ColorSpace};
use crate::raster::{draw, squared_error, Oval, Shape, Triangle};

/// Genes per shape block, one constant per [`ShapeMode`].
const TRIANGLE_GENES: usize = 10;
const OVAL_GENES: usize = 9;
const BOTH_GENES: usize = 11;

/// Which shape (or mix of shapes) a genome's blocks decode to.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ShapeMode {
    Triangle,
    Oval,
    Both,
}

impl ShapeMode {
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "triangle" => Some(Self::Triangle),
            "oval" => Some(Self::Oval),
            "both" => Some(Self::Both),
            _ => None,
        }
    }

    pub fn genes_per_shape(self) -> usize {
        match self {
            Self::Triangle => TRIANGLE_GENES,
            Self::Oval => OVAL_GENES,
            Self::Both => BOTH_GENES,
        }
    }
}

pub struct ScorerInner {
    pub width: usize,
    pub height: usize,
    pub shape_count: usize,
    pub shape_mode: ShapeMode,
    pub color_space: ColorSpace,
    pub baseline_mse: f64,
    target: Vec<u8>,
    background_rgb: [u8; 3],
    background_canvas: Vec<u8>,
}

impl ScorerInner {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        target: Vec<u8>,
        width: usize,
        height: usize,
        background_rgb: [u8; 3],
        shape_count: usize,
        shape_mode: ShapeMode,
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
            shape_count,
            shape_mode,
            color_space,
            baseline_mse,
            target,
            background_rgb,
            background_canvas,
        }
    }

    pub fn genes_per_shape(&self) -> usize {
        self.shape_mode.genes_per_shape()
    }

    pub fn genome_len(&self) -> usize {
        self.shape_count * self.genes_per_shape()
    }

    /// Decode the `index`-th shape block of a genome at the given canvas size.
    ///
    /// Mirrors `genotype.figures_from_alleles`: coordinates scale by the
    /// canvas dimensions, colour goes through the run's colour space, and
    /// alpha is always the block's last gene.
    fn shape(&self, alleles: &[f64], index: usize, width: f64, height: f64) -> Shape {
        let genes = self.genes_per_shape();
        let base = index * genes;
        let g = &alleles[base..base + genes];
        match self.shape_mode {
            // g: x1,y1,x2,y2,x3,y3, c1,c2,c3, a
            ShapeMode::Triangle => Shape::Triangle(decode_triangle(
                &g[0..6],
                &g[6..9],
                g[9],
                width,
                height,
                self.color_space,
            )),
            // g: cx,cy,rx,ry,theta, c1,c2,c3, a
            ShapeMode::Oval => Shape::Oval(decode_oval(
                &g[0..5],
                &g[5..8],
                g[8],
                width,
                height,
                self.color_space,
            )),
            // g: kind, p0..p5, c1,c2,c3, a
            ShapeMode::Both => {
                let kind = g[0].round() as u8;
                let params = &g[1..7];
                let color = &g[7..10];
                let alpha_allele = g[10];
                if kind == 0 {
                    Shape::Triangle(decode_triangle(
                        params,
                        color,
                        alpha_allele,
                        width,
                        height,
                        self.color_space,
                    ))
                } else {
                    Shape::Oval(decode_oval(
                        params,
                        color,
                        alpha_allele,
                        width,
                        height,
                        self.color_space,
                    ))
                }
            }
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
        for index in 0..self.shape_count {
            draw(canvas, width, height, &self.shape(alleles, index, fw, fh));
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

/// `params`: 6 coordinate alleles (x1,y1,x2,y2,x3,y3). `color`: 3 colour
/// alleles. `alpha_allele`: the block's linear alpha gene.
fn decode_triangle(
    params: &[f64],
    color: &[f64],
    alpha_allele: f64,
    width: f64,
    height: f64,
    space: ColorSpace,
) -> Triangle {
    Triangle {
        vertices: [
            (params[0] * width, params[1] * height),
            (params[2] * width, params[3] * height),
            (params[4] * width, params[5] * height),
        ],
        color: space.to_rgb(color[0], color[1], color[2]),
        alpha: to_byte(alpha_allele),
    }
}

/// `params`: at least 5 alleles (cx,cy,rx,ry,theta); a sixth, if present (the
/// `Both`-mode padding slot), is ignored. `theta` is normalised to `[0, pi)`
/// rather than `[0, 2*pi)`: an ellipse looks identical rotated by pi, so the
/// full turn would waste half the mutation range on visual duplicates.
fn decode_oval(
    params: &[f64],
    color: &[f64],
    alpha_allele: f64,
    width: f64,
    height: f64,
    space: ColorSpace,
) -> Oval {
    Oval {
        center: (params[0] * width, params[1] * height),
        radii: (params[2] * width, params[3] * height),
        angle: params[4] * std::f64::consts::PI,
        color: space.to_rgb(color[0], color[1], color[2]),
        alpha: to_byte(alpha_allele),
    }
}
