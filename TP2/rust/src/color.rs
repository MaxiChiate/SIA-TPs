//! Colour spaces: three `[0,1]` alleles -> an sRGB triple.
//!
//! A line-for-line port of `problems/triangles/colorspace.py`, which was
//! deliberately written as allocation-free scalar `f64` maths for exactly this.
//! Because none of it involves rasterization, the port is **bit-exact** with the
//! Python original — `tests/test_native_parity.py` asserts equality with `==`
//! over the whole allele cube, with no tolerance. That matters: it retires the
//! riskiest third of the port before any rasterizer exists to confound it.
//!
//! Two traps that silently break exactness and are guarded against here:
//!
//! 1. Python's `round()` is banker's rounding (half to even); Rust's
//!    `f64::round` is half away from zero. `round(0.5) == 0` in Python but
//!    `1` in Rust. Every conversion to a byte therefore uses
//!    `round_ties_even()`.
//! 2. `colorsys.hsv_to_rgb` has to be ported branch for branch, including the
//!    `s == 0` early return and the `i = int(h * 6.0); i %= 6` wraparound.

/// Allele scaling for hcl. L is CIELAB lightness in [0,100]; C is capped at the
/// most colourful sRGB colour in Lab (blue, C ~ 133.8), so the whole gamut stays
/// reachable and the inverse never has to clamp a real colour's chroma.
const MAX_CHROMA: f64 = 140.0;
/// Bisection depth: 140/2^12 is far below one 8-bit step.
const GAMUT_STEPS: u32 = 12;
/// Slack on the gamut test, in linear light. Sized so a colour sitting exactly
/// on the gamut surface survives float noise without being pushed inward, while
/// staying orders of magnitude below one 8-bit step.
const GAMUT_TOLERANCE: f64 = 1e-6;

// CIELAB, D65 white point (the sRGB reference white).
const WHITE_X: f64 = 0.95047;
const WHITE_Y: f64 = 1.0;
const WHITE_Z: f64 = 1.08883;
const LAB_EPSILON: f64 = 216.0 / 24389.0;
const LAB_KAPPA: f64 = 24389.0 / 27.0;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ColorSpace {
    Rgb,
    Hsv,
    Hcl,
}

impl ColorSpace {
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "rgb" => Some(Self::Rgb),
            "hsv" => Some(Self::Hsv),
            "hcl" => Some(Self::Hcl),
            _ => None,
        }
    }

    #[inline]
    pub fn to_rgb(self, a: f64, b: f64, c: f64) -> [u8; 3] {
        match self {
            Self::Rgb => [to_byte(a), to_byte(b), to_byte(c)],
            Self::Hsv => hsv_to_rgb(a, b, c),
            Self::Hcl => hcl_to_rgb(a, b, c),
        }
    }
}

#[inline]
fn clamp01(value: f64) -> f64 {
    value.clamp(0.0, 1.0)
}

/// `round(v * 255)` with Python's rounding rule.
#[inline]
pub fn to_byte(value: f64) -> u8 {
    (clamp01(value) * 255.0).round_ties_even() as u8
}

// -- hsv ---------------------------------------------------------------------

/// Every point of the HSV cube is a valid sRGB colour, so there is no gamut
/// step here - only a change of coordinates. Ported from `colorsys.hsv_to_rgb`.
fn hsv_to_rgb(h: f64, s: f64, v: f64) -> [u8; 3] {
    let (h, s, v) = (clamp01(h), clamp01(s), clamp01(v));
    if s == 0.0 {
        let grey = to_byte(v);
        return [grey, grey, grey];
    }
    let sector = (h * 6.0) as i64;
    let fraction = h * 6.0 - sector as f64;
    let p = v * (1.0 - s);
    let q = v * (1.0 - s * fraction);
    let t = v * (1.0 - s * (1.0 - fraction));
    let (r, g, b) = match sector.rem_euclid(6) {
        0 => (v, t, p),
        1 => (q, v, p),
        2 => (p, v, t),
        3 => (p, q, v),
        4 => (t, p, v),
        _ => (v, p, q),
    };
    [to_byte(r), to_byte(g), to_byte(b)]
}

// -- hcl (CIE LCh(ab), D65) --------------------------------------------------

#[inline]
fn srgb_companding(linear: f64) -> f64 {
    if linear <= 0.0031308 {
        12.92 * linear
    } else {
        1.055 * linear.powf(1.0 / 2.4) - 0.055
    }
}

fn lab_to_linear_rgb(lightness: f64, a: f64, b: f64) -> [f64; 3] {
    let fy = (lightness + 16.0) / 116.0;
    let fx = fy + a / 500.0;
    let fz = fy - b / 200.0;

    let fx3 = fx * fx * fx;
    let fz3 = fz * fz * fz;
    let x = if fx3 > LAB_EPSILON { fx3 } else { (116.0 * fx - 16.0) / LAB_KAPPA };
    let y = if lightness > LAB_KAPPA * LAB_EPSILON { fy * fy * fy } else { lightness / LAB_KAPPA };
    let z = if fz3 > LAB_EPSILON { fz3 } else { (116.0 * fz - 16.0) / LAB_KAPPA };
    let (x, y, z) = (x * WHITE_X, y * WHITE_Y, z * WHITE_Z);

    [
        3.2404542 * x - 1.5371385 * y - 0.4985314 * z,
        -0.9692660 * x + 1.8760108 * y + 0.0415560 * z,
        0.0556434 * x - 0.2040259 * y + 1.0572252 * z,
    ]
}

#[inline]
fn in_gamut(linear: &[f64; 3]) -> bool {
    linear
        .iter()
        .all(|c| *c >= -GAMUT_TOLERANCE && *c <= 1.0 + GAMUT_TOLERANCE)
}

#[inline]
fn lch_to_linear_rgb(lightness: f64, chroma: f64, hue_radians: f64) -> [f64; 3] {
    lab_to_linear_rgb(
        lightness,
        chroma * hue_radians.cos(),
        chroma * hue_radians.sin(),
    )
}

/// Read `(h, c, l)` alleles as an sRGB colour, reducing chroma if needed.
///
/// Roughly 40% of the H x C x L box falls outside the sRGB gamut. Those colours
/// are brought back by lowering chroma at constant hue and lightness rather than
/// by clamping the RGB channels: clamping distorts all three axes at once and
/// collapses large regions of the box onto the same colour, which would flatten
/// the fitness landscape in H, C and L alike.
fn hcl_to_rgb(h: f64, c: f64, lightness: f64) -> [u8; 3] {
    let hue = clamp01(h) * 2.0 * std::f64::consts::PI;
    let chroma = clamp01(c) * MAX_CHROMA;
    let light = clamp01(lightness) * 100.0;

    let mut linear = lch_to_linear_rgb(light, chroma, hue);
    if !in_gamut(&linear) {
        // Start from the achromatic colour of this lightness rather than from
        // the out-of-gamut one: when the in-gamut chroma range is narrower than
        // the bisection's first step (e.g. at L = 100, where only pure white
        // fits), no midpoint is ever accepted, and `linear` must still hold a
        // real colour instead of falling back to clamping the raw channels.
        let (mut low, mut high) = (0.0_f64, chroma);
        linear = lch_to_linear_rgb(light, 0.0, hue);
        for _ in 0..GAMUT_STEPS {
            let middle = (low + high) / 2.0;
            let candidate = lch_to_linear_rgb(light, middle, hue);
            if in_gamut(&candidate) {
                low = middle;
                linear = candidate;
            } else {
                high = middle;
            }
        }
    }

    [
        to_byte(srgb_companding(clamp01(linear[0]))),
        to_byte(srgb_companding(clamp01(linear[1]))),
        to_byte(srgb_companding(clamp01(linear[2]))),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn python_rounding_is_half_to_even() {
        // f64::round would give 1 here, and every byte on a .5 boundary would
        // drift from the Python implementation.
        assert_eq!(to_byte(0.5 / 255.0), 0);
        assert_eq!(to_byte(1.5 / 255.0), 2);
    }

    #[test]
    fn hcl_extremes_are_achromatic() {
        assert_eq!(ColorSpace::Hcl.to_rgb(0.1, 0.9, 1.0), [255, 255, 255]);
        assert_eq!(ColorSpace::Hcl.to_rgb(0.1, 0.9, 0.0), [0, 0, 0]);
    }

    #[test]
    fn hsv_hue_sweeps_the_primaries() {
        assert_eq!(ColorSpace::Hsv.to_rgb(0.0, 1.0, 1.0), [255, 0, 0]);
        assert_eq!(ColorSpace::Hsv.to_rgb(1.0 / 3.0, 1.0, 1.0), [0, 255, 0]);
        assert_eq!(ColorSpace::Hsv.to_rgb(2.0 / 3.0, 1.0, 1.0), [0, 0, 255]);
    }
}
