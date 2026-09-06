//! Scanline rasterization of translucent triangles onto an opaque RGB canvas.
//!
//! Three decisions carry most of the speedup over the Pillow implementation
//! this replaces:
//!
//! * **The canvas is RGB, not RGBA.** The background is opaque, so the
//!   destination alpha is 255 before the first triangle and stays 255 after
//!   every source-over composite. An always-255 channel is representable by
//!   nothing at all - 25% less memory traffic in the hot loop, for free.
//! * **Only the triangle's bounding box is touched.** The Pillow path allocated
//!   a full-canvas RGBA layer per triangle and alpha-composited the entire
//!   canvas, i.e. O(T * W * H) regardless of how small the triangles were.
//!   Here a triangle costs its own area.
//! * **Coverage is decided in fixed point.** Sub-pixel positions come from
//!   `i64` edge functions on 28.4 coordinates rather than floats, so which
//!   pixels a triangle covers cannot drift with the optimisation level, the
//!   compiler, or FMA contraction. Two machines running the same genome get the
//!   same pixels.
//!
//! Coverage uses the standard top-left fill rule, which does *not* reproduce
//! Pillow's polygon fill: `ImageDraw.polygon` paints its outline as well as its
//! interior, so it covers measurably more area. The two are different objective
//! functions, close but not equal; `tests/test_native_parity.py` quantifies the
//! gap rather than pretending it away.

/// Sub-pixel bits for the fixed-point coordinates (28.4 format).
const SUBPIXEL_BITS: i64 = 4;
const SUBPIXEL_ONE: i64 = 1 << SUBPIXEL_BITS;

#[derive(Clone, Copy)]
pub struct Triangle {
    /// Pixel-space vertices, already scaled to the canvas.
    pub vertices: [(f64, f64); 3],
    pub color: [u8; 3],
    pub alpha: u8,
}

/// `(value * 255 + 128) / 255`, exactly, without a division.
///
/// The same integer rounding Pillow uses internally, so the blend arithmetic is
/// not an extra source of divergence on top of the fill rule.
#[inline]
fn div255(value: u32) -> u32 {
    let t = value + 128;
    (t + (t >> 8)) >> 8
}

#[inline]
fn to_fixed(value: f64) -> i64 {
    (value * SUBPIXEL_ONE as f64).round_ties_even() as i64
}

/// Twice the signed area of the triangle, in fixed point.
#[inline]
fn edge(a: (i64, i64), b: (i64, i64), c: (i64, i64)) -> i64 {
    (b.0 - a.0) * (c.1 - a.1) - (b.1 - a.1) * (c.0 - a.0)
}

/// True for a top or left edge, which the fill rule includes rather than
/// excludes. Without it, adjacent triangles would either double-blend or leave
/// seams along their shared edge.
#[inline]
fn is_top_left(a: (i64, i64), b: (i64, i64)) -> bool {
    let (dx, dy) = (b.0 - a.0, b.1 - a.1);
    dy > 0 || (dy == 0 && dx < 0)
}

/// Composite one triangle onto `canvas` (`width * height * 3` RGB bytes).
pub fn draw(canvas: &mut [u8], width: usize, height: usize, triangle: &Triangle) {
    if triangle.alpha == 0 {
        return;
    }

    let mut v: [(i64, i64); 3] = [(0, 0); 3];
    for (slot, (x, y)) in v.iter_mut().zip(triangle.vertices.iter()) {
        *slot = (to_fixed(*x), to_fixed(*y));
    }

    // Orient counter-clockwise so a single sign convention covers both windings.
    let area = edge(v[0], v[1], v[2]);
    if area == 0 {
        return; // degenerate: collinear vertices cover nothing
    }
    if area < 0 {
        v.swap(1, 2);
    }

    let min_x = (v.iter().map(|p| p.0).min().unwrap() >> SUBPIXEL_BITS).max(0) as usize;
    let min_y = (v.iter().map(|p| p.1).min().unwrap() >> SUBPIXEL_BITS).max(0) as usize;
    let max_x = ((v.iter().map(|p| p.0).max().unwrap() >> SUBPIXEL_BITS) + 1)
        .min(width as i64) as usize;
    let max_y = ((v.iter().map(|p| p.1).max().unwrap() >> SUBPIXEL_BITS) + 1)
        .min(height as i64) as usize;
    if min_x >= max_x || min_y >= max_y {
        return; // entirely off-canvas
    }

    // A top-left edge includes points exactly on it, a right/bottom edge does
    // not. Folding that into a per-edge bias keeps the inner loop a plain
    // "all three >= 0" test.
    let bias = [
        if is_top_left(v[0], v[1]) { 0 } else { -1 },
        if is_top_left(v[1], v[2]) { 0 } else { -1 },
        if is_top_left(v[2], v[0]) { 0 } else { -1 },
    ];

    let alpha = triangle.alpha as u32;
    let inverse = 255 - alpha;
    let source = [
        triangle.color[0] as u32 * alpha,
        triangle.color[1] as u32 * alpha,
        triangle.color[2] as u32 * alpha,
    ];

    // Each edge function is affine in x, so stepping one pixel to the right
    // adds a constant. Rather than evaluating three edges per pixel, solve each
    // inequality for x once per row and blend the resulting span with no test
    // inside the loop at all - the triangle is convex, so the covered pixels of
    // a row are exactly one contiguous span.
    let steps = [
        -(v[1].1 - v[0].1) * SUBPIXEL_ONE,
        -(v[2].1 - v[1].1) * SUBPIXEL_ONE,
        -(v[0].1 - v[2].1) * SUBPIXEL_ONE,
    ];

    for y in min_y..max_y {
        // Pixel centres, hence the half-subpixel offset.
        let py = (y as i64) * SUBPIXEL_ONE + SUBPIXEL_ONE / 2;
        let left = ((min_x as i64) * SUBPIXEL_ONE + SUBPIXEL_ONE / 2, py);
        let values = [
            edge(v[0], v[1], left) + bias[0],
            edge(v[1], v[2], left) + bias[1],
            edge(v[2], v[0], left) + bias[2],
        ];

        let mut first = 0i64;
        let mut last = (max_x - min_x) as i64 - 1;
        let mut empty = false;
        for (value, step) in values.iter().zip(steps.iter()) {
            match (*step).cmp(&0) {
                // value + k*step >= 0, k the pixel offset within the row.
                std::cmp::Ordering::Greater => first = first.max(ceil_div(-*value, *step)),
                std::cmp::Ordering::Less => last = last.min((*value).div_euclid(-*step)),
                std::cmp::Ordering::Equal => empty |= *value < 0,
            }
        }
        if empty || first > last {
            continue;
        }

        let start = min_x + first as usize;
        let end = min_x + last as usize + 1;
        let row = y * width * 3;
        for pixel in canvas[row + start * 3..row + end * 3].chunks_exact_mut(3) {
            for channel in 0..3 {
                pixel[channel] =
                    div255(source[channel] + pixel[channel] as u32 * inverse) as u8;
            }
        }
    }
}

/// `ceil(numerator / denominator)` for a strictly positive denominator.
#[inline]
fn ceil_div(numerator: i64, denominator: i64) -> i64 {
    -((-numerator).div_euclid(denominator))
}

/// Sum of squared per-channel differences between two RGB buffers.
///
/// Accumulated in `u64` as exact integers rather than in floating point: the
/// total is then the same number `numpy` computes, because every partial sum on
/// both sides is an integer well inside the range `f64` represents exactly.
#[inline]
pub fn squared_error(rendered: &[u8], target: &[u8]) -> u64 {
    debug_assert_eq!(rendered.len(), target.len());
    let mut total: u64 = 0;
    for (a, b) in rendered.iter().zip(target.iter()) {
        let difference = *a as i32 - *b as i32;
        total += (difference * difference) as u64;
    }
    total
}

#[cfg(test)]
mod tests {
    use super::*;

    fn canvas(width: usize, height: usize) -> Vec<u8> {
        vec![255u8; width * height * 3]
    }

    #[test]
    fn an_opaque_triangle_replaces_the_pixels_it_covers() {
        let (w, h) = (8, 8);
        let mut buffer = canvas(w, h);
        draw(
            &mut buffer,
            w,
            h,
            &Triangle {
                vertices: [(0.0, 0.0), (8.0, 0.0), (0.0, 8.0)],
                color: [10, 20, 30],
                alpha: 255,
            },
        );
        assert_eq!(&buffer[0..3], &[10, 20, 30]); // inside
        assert_eq!(&buffer[(7 * w + 7) * 3..(7 * w + 7) * 3 + 3], &[255, 255, 255]);
    }

    #[test]
    fn a_fully_transparent_triangle_changes_nothing() {
        let (w, h) = (4, 4);
        let mut buffer = canvas(w, h);
        let untouched = buffer.clone();
        draw(
            &mut buffer,
            w,
            h,
            &Triangle {
                vertices: [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)],
                color: [0, 0, 0],
                alpha: 0,
            },
        );
        assert_eq!(buffer, untouched);
    }

    #[test]
    fn a_degenerate_triangle_covers_nothing() {
        let (w, h) = (4, 4);
        let mut buffer = canvas(w, h);
        let untouched = buffer.clone();
        draw(
            &mut buffer,
            w,
            h,
            &Triangle {
                vertices: [(0.0, 0.0), (2.0, 2.0), (4.0, 4.0)],
                color: [0, 0, 0],
                alpha: 255,
            },
        );
        assert_eq!(buffer, untouched);
    }

    #[test]
    fn a_triangle_outside_the_canvas_is_skipped() {
        let (w, h) = (4, 4);
        let mut buffer = canvas(w, h);
        let untouched = buffer.clone();
        draw(
            &mut buffer,
            w,
            h,
            &Triangle {
                vertices: [(20.0, 20.0), (30.0, 20.0), (20.0, 30.0)],
                color: [0, 0, 0],
                alpha: 255,
            },
        );
        assert_eq!(buffer, untouched);
    }

    #[test]
    fn winding_does_not_change_coverage() {
        let (w, h) = (8, 8);
        let mut clockwise = canvas(w, h);
        let mut counter = canvas(w, h);
        let vertices = [(1.0, 1.0), (7.0, 2.0), (3.0, 6.0)];
        draw(&mut clockwise, w, h, &Triangle { vertices, color: [0, 0, 0], alpha: 200 });
        let mut reversed = vertices;
        reversed.swap(1, 2);
        draw(
            &mut counter,
            w,
            h,
            &Triangle { vertices: reversed, color: [0, 0, 0], alpha: 200 },
        );
        assert_eq!(clockwise, counter);
    }

    #[test]
    fn half_alpha_blends_towards_the_source() {
        let (w, h) = (4, 4);
        let mut buffer = canvas(w, h);
        draw(
            &mut buffer,
            w,
            h,
            &Triangle {
                vertices: [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)],
                color: [0, 0, 0],
                alpha: 128,
            },
        );
        // 255 * 127 / 255 rounded = 127
        assert_eq!(buffer[0], 127);
    }

    /// The per-pixel form the span solver replaced: three edge tests per pixel.
    fn draw_brute_force(canvas: &mut [u8], width: usize, height: usize, triangle: &Triangle) {
        if triangle.alpha == 0 {
            return;
        }
        let mut v: [(i64, i64); 3] = [(0, 0); 3];
        for (slot, (x, y)) in v.iter_mut().zip(triangle.vertices.iter()) {
            *slot = (to_fixed(*x), to_fixed(*y));
        }
        let area = edge(v[0], v[1], v[2]);
        if area == 0 {
            return;
        }
        if area < 0 {
            v.swap(1, 2);
        }
        let bias = [
            if is_top_left(v[0], v[1]) { 0 } else { -1 },
            if is_top_left(v[1], v[2]) { 0 } else { -1 },
            if is_top_left(v[2], v[0]) { 0 } else { -1 },
        ];
        let alpha = triangle.alpha as u32;
        let inverse = 255 - alpha;
        for y in 0..height {
            let py = (y as i64) * SUBPIXEL_ONE + SUBPIXEL_ONE / 2;
            for x in 0..width {
                let point = ((x as i64) * SUBPIXEL_ONE + SUBPIXEL_ONE / 2, py);
                let inside = edge(v[0], v[1], point) + bias[0] >= 0
                    && edge(v[1], v[2], point) + bias[1] >= 0
                    && edge(v[2], v[0], point) + bias[2] >= 0;
                if !inside {
                    continue;
                }
                let base = (y * width + x) * 3;
                for channel in 0..3 {
                    canvas[base + channel] = div255(
                        triangle.color[channel] as u32 * alpha
                            + canvas[base + channel] as u32 * inverse,
                    ) as u8;
                }
            }
        }
    }

    #[test]
    fn span_solving_covers_exactly_the_same_pixels_as_per_pixel_testing() {
        // A cheap deterministic LCG: no dev-dependency, and a failure is
        // reproducible from the seed alone.
        let mut state: u64 = 0x2026_0905;
        let mut next = || {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            ((state >> 33) as f64) / (u32::MAX as f64 / 2.0)
        };
        let (w, h) = (37, 23);
        for _ in 0..400 {
            // Deliberately overshoot the canvas so clipping is exercised too.
            let vertices = [
                (next() * 1.4 * w as f64 - 0.2 * w as f64, next() * 1.4 * h as f64 - 0.2 * h as f64),
                (next() * 1.4 * w as f64 - 0.2 * w as f64, next() * 1.4 * h as f64 - 0.2 * h as f64),
                (next() * 1.4 * w as f64 - 0.2 * w as f64, next() * 1.4 * h as f64 - 0.2 * h as f64),
            ];
            let triangle = Triangle {
                vertices,
                color: [17, 200, 90],
                alpha: 137,
            };
            let mut spans = vec![255u8; w * h * 3];
            let mut brute = vec![255u8; w * h * 3];
            draw(&mut spans, w, h, &triangle);
            draw_brute_force(&mut brute, w, h, &triangle);
            assert_eq!(spans, brute, "diverged on vertices {vertices:?}");
        }
    }

    #[test]
    fn squared_error_is_zero_for_identical_buffers() {
        assert_eq!(squared_error(&[1, 2, 3], &[1, 2, 3]), 0);
        assert_eq!(squared_error(&[0, 0], &[3, 4]), 9 + 16);
    }
}
