#!/usr/bin/env python3
"""Fixtures for bench/h264/disp_reader_tb.sv: random 4:2:0 pictures as DPB store words
(docs/h264_recon.md S2.2: luma rows of 2W words, then Cb, Cr rows of W) and the expected
720x480 raster of every variant the reader shows, one line per active dot, {de, R, G, B}
as 7 hex digits (de 0 and black beyond the picture). The RGB is the BT.601 limited-range
integer conversion h264/disp_reader.sv states, of each dot's Y / Cb / Cr:

  frame   the store as a FRAME at the identity fit (progressive, 1:1): chroma INTERPOLATED at
          H.264's default siting (chroma_sample_loc_type 0; docs/display.md "Chroma at the
          identity"): horizontally co-sited with even luma columns -- odd column x = (c[x >> 1] +
          c[(x + 1) >> 1] + 1) >> 1, the right edge replicated -- then vertically between luma
          rows 2m and 2m + 1 -- row 2m = (3 h[m] + h[m - 1] + 2) >> 2, 2m + 1 = (3 h[m] + h[m + 1]
          + 2) >> 2, the edges replicated; checked here against ffmpeg's own upsampling
          (scale=in_chroma_loc=left, bilinear, full_chroma_int) within one code
  frame_il  the same store at 480i (not the identity): chroma NEAREST, luma line y takes chroma row y >> 1
  field   the store as a FIELD PAIR (line-interleaved), woven: luma line y takes its own
          field's chroma. That siting is NOT computed here from the RTL's formula
          (2 (y >> 2) + (y & 1)): ffmpeg's `separatefields` splits the woven picture into
          its two fields (every plane, chroma included, line-interleaved -- the layout the
          reconstruction writes and ffmpeg decodes to), each field's chroma is expanded with
          its own planes -- horizontally interpolated as the frame's, vertically nearest (the
          rows above and below are the other field's) -- and the two are woven back; field_il
          is the same with chroma nearest (480i).
  blend   the field pair's 4:4:4 lines through ffmpeg's `interlace` lowpass (vf_tinterlace:
          (1 + a + 2b + d) >> 2 on every line, per plane), the Blend kernel's definition. The
          filter clamps each FIELD's first and last lines to themselves; the reader mirrors
          the PICTURE's edges (line -1 := line 1, line H := line H - 2), so the planes go in
          padded by two mirrored lines each side and come out cropped: ffmpeg's edge rule never
          touches a scored line, and the golden checks the reader's edge rule too.
  bob0/1  the Bob kernel, keeping the top (0) / bottom (1) field: its lines as woven, the
          other field's (a + d + 1) >> 1, edges mirrored. No ffmpeg filter computes this (its
          bobs are temporal or edge-directed): the formula is the definition, and the kept
          lines are the ffmpeg-split weave's.

Three pictures: L, 720x480 (the raster's size); S, 480x272 (the PSP's own; its last line
is inside the raster, so the bottom mirror is seen, and the dots beyond it are black); T,
720x576 (the Level 3.0 maximum, 1,620 macroblocks, clipped to the raster's 480 lines: the
last shown line's d is the picture's real line 480, not a mirror).
Without ffmpeg the field split falls back to numpy and blend to the formula (no oracle) and
the script says so.

    disp_golden.py   -> bench/h264/fixtures/gen/disp_store{,_s,_t}.hex, disp_want_*.hex
"""
import os
import shutil
import subprocess
import tempfile
import sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colour_ref                                 # noqa: E402  (0.16: the colour codes' integers)

RW, RH = 720, 480                                 # the raster
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bench", "h264", "fixtures", "gen")
os.makedirs(out, exist_ok=True)
HAVE_FFMPEG = shutil.which("ffmpeg") is not None


def picture(seed, W, H):
    rng = np.random.default_rng(seed)
    Y = rng.integers(0, 256, (H, W))
    Y[:40] = np.arange(W) % 256                   # a ramp band: every level of the clip
    Cb = rng.integers(0, 256, (H // 2, W // 2))
    Cr = rng.integers(0, 256, (H // 2, W // 2))
    return Y, Cb, Cr


def words(p):
    h, w = p.shape
    b = p.astype(np.uint64).reshape(h, w // 8, 8)
    return (sum(b[:, :, i] << np.uint64(8 * i) for i in range(8))).reshape(-1)


def up(c):
    """4:2:0 chroma -> one sample per luma dot, NEAREST (rows sited on luma row pairs): every
    output that is not the identity fit (480i, a scaled picture)."""
    return np.repeat(np.repeat(c, 2, 0), 2, 1)


def hup(c, cols=None, last=None):
    """(docs/display.md "Chroma at the identity") horizontal interpolation at H.264's default siting:
    luma column x takes c[x >> 1] (x even) or (c[x >> 1] + c[min((x + 1) >> 1, last)] + 1) >> 1 (x odd);
    `last` the crop's last chroma sample (kmax_x >> 1), `cols` the luma columns wanted (all by default)."""
    c = np.asarray(c, np.int64)
    if cols is None:
        cols = np.arange(2 * c.shape[1])
    if last is None:
        last = c.shape[1] - 1
    n, nx = cols >> 1, np.minimum((cols + 1) >> 1, last)
    return np.where(cols & 1, (c[:, n] + c[:, nx] + 1) >> 1, c[:, n])


def vrow(h, k, kmin, kmax):
    """the vertical interpolation of luma row k of a FRAME (h: the horizontally interpolated chroma
    rows), with the reader's rows a / d at the identity: a = k - 1 (k + 1 at the first row), d = k + 1
    (k - 1 at the last) -- their chroma rows >> 1; row 2m weighs a's, 2m + 1 d's"""
    ra = (k if k == kmax else k + 1) if k == kmin else k - 1
    rd = (k if k == kmin else k - 1) if k == kmax else k + 1
    o = ra if (k & 1) == 0 else rd
    return (3 * h[k >> 1] + h[o >> 1] + 2) >> 2


def up_ident(c):
    """a whole frame's chroma at the identity (no crop): horizontal, then vertical"""
    h = hup(c)
    H = 2 * c.shape[0]
    return np.stack([vrow(h, k, 0, H - 1) for k in range(H)])


def up_field(c):
    """one field's chroma at the identity: horizontal only (vertically nearest within the field)"""
    return np.repeat(hup(c), 2, 0)


def rgb(Y, U, V, code=1):
    """The display's conversion under a colour code (0.16; default 1, BT.601 limited: the 0.15
    integers). The integers are tools/colour_ref.py's, derived from Kr / Kb -- not the RTL's table."""
    return colour_ref.rgb(Y, U, V, code)


def ffmpeg(args, planes, W, H, fmt):
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.yuv"), os.path.join(d, "out.yuv")
        with open(src, "wb") as f:
            f.write(b"".join(p.astype(np.uint8).tobytes() for p in planes))
        subprocess.run(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", fmt, "-s", "%dx%d" % (W, H),
                        "-i", src] + args + ["-f", "rawvideo", "-pix_fmt", fmt, dst], check=True)
        return np.frombuffer(open(dst, "rb").read(), np.uint8).astype(np.int64)


def fields(Y, Cb, Cr):
    """The two fields' 4:2:0 planes, split by ffmpeg `separatefields` (numpy without it)."""
    H, W = Y.shape
    if not HAVE_FFMPEG:
        return [(Y[p::2], Cb[p::2], Cr[p::2]) for p in (0, 1)]
    raw = ffmpeg(["-vf", "setfield=tff,separatefields"], (Y, Cb, Cr), W, H, "yuv420p")
    fh = H // 2
    fsz = W * fh + 2 * (W // 2) * (fh // 2)
    assert raw.size == 2 * fsz, "separatefields: %d bytes" % raw.size
    res = []
    for k in range(2):                            # output order = top field, then bottom (tff)
        a = raw[k * fsz:(k + 1) * fsz]
        yp = a[:W * fh].reshape(fh, W)
        cb = a[W * fh:W * fh + (W // 2) * (fh // 2)].reshape(fh // 2, W // 2)
        cr = a[W * fh + (W // 2) * (fh // 2):].reshape(fh // 2, W // 2)
        res.append((yp, cb, cr))
    # the split must be the luma lines as stored (a sanity check on the oracle's field order)
    assert all((res[p][0] == Y[p::2]).all() for p in (0, 1)), "field order"
    return res


def woven444(Y, Cb, Cr, cup=None):
    """Every luma line with its own field's chroma, woven (H x W, three planes); `cup` the chroma
    expansion of each field (up_field at the identity, up -- nearest -- at 480i)."""
    cup = up_field if cup is None else cup
    H, W = Y.shape
    planes = [np.zeros((H, W), np.int64) for _ in range(3)]
    for p, (yp, cb, cr) in enumerate(fields(Y, Cb, Cr)):
        planes[0][p::2], planes[1][p::2], planes[2][p::2] = yp, cup(cb), cup(cr)
    return planes


def mirror_pad(p, n=2):
    """Rows -n..-1 and H..H+n-1 mirrored about the picture's first / last line."""
    top = p[1:n + 1][::-1]
    bot = p[-n - 1:-1][::-1]
    return np.concatenate([top, p, bot])


def blend(planes):
    H, W = planes[0].shape
    padded = [mirror_pad(p) for p in planes]
    if HAVE_FFMPEG:
        # two identical frames in, one out: each output line is the lowpass of its own frame
        raw = ffmpeg(["-vf", "interlace=scan=tff:lowpass=linear"], padded * 2, W, H + 4, "yuv444p")
        n = W * (H + 4)
        assert raw.size == 3 * n, "interlace: %d bytes" % raw.size
        return [raw[k * n:(k + 1) * n].reshape(H + 4, W)[2:-2] for k in range(3)]
    return [(pp[1:-3] + 2 * pp[2:-2] + pp[3:-1] + 1) >> 2 for pp in padded]


def bob(planes, keep):
    res = []
    for p in planes:
        pp = mirror_pad(p, 1)                     # pp[y + 1] = line y
        o = p.copy()
        for y in range(p.shape[0]):
            if (y & 1) != keep:
                o[y] = (pp[y] + pp[y + 2] + 1) >> 1
        res.append(o)
    return res


def write_want(name, img):
    """img: the picture's RGB (h x w x 3), placed at the raster's top left."""
    h, w, _ = img.shape
    with open(os.path.join(out, name), "w") as f:
        for y in range(RH):
            for x in range(RW):
                if y < h and x < w:
                    f.write("1%02x%02x%02x\n" % tuple(img[y, x]))
                else:
                    f.write("0000000\n")


def write_store(name, Y, Cb, Cr):
    with open(os.path.join(out, name), "w") as f:
        for p in (Y, Cb, Cr):
            f.write("".join("%016x\n" % int(v) for v in words(p)))


# L: 720x480 (seed 7: the picture the frame / field fixtures have always used)
L = picture(7, 720, 480)
write_store("disp_store.hex", *L)
write_want("disp_want_frame.hex", rgb(L[0], up_ident(L[1]), up_ident(L[2])))
for _c in range(2, 7):                            # (0.16) the frame under every other colour code
    write_want("disp_want_frame_c%d.hex" % _c, rgb(L[0], up_ident(L[1]), up_ident(L[2]), _c))
write_want("disp_want_frame_il.hex", rgb(L[0], up(L[1]), up(L[2])))       # 480i: chroma nearest
write_want("disp_want_field_il.hex", rgb(*woven444(*L, cup=up)))
Lf = woven444(*L)
write_want("disp_want_field.hex", rgb(*Lf))


def check_chroma_oracle(c):
    """the independent check of the identity's chroma: ffmpeg's own 4:2:0 -> 4:4:4 upsampling at
    H.264's default siting (in_chroma_loc=left; validated on an impulse 2026-10-09: the even column
    full, odd neighbours one half; luma rows 2m / 2m + 1 three quarters, the rows beyond one quarter)
    against up_ident, within one code (ffmpeg rounds once, the reader twice)"""
    if not HAVE_FFMPEG:
        print("disp_golden: identity chroma NOT checked (no ffmpeg)")
        return
    h, w = c.shape
    Yp = np.full((2 * h, 2 * w), 128)
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.yuv"), os.path.join(d, "out.yuv")
        with open(src, "wb") as f:
            f.write(b"".join(p.astype(np.uint8).tobytes() for p in (Yp, c, c)))
        subprocess.run(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", "%dx%d" % (2 * w, 2 * h),
                        "-i", src, "-vf", "scale=in_chroma_loc=left:flags=bilinear+full_chroma_int+accurate_rnd",
                        "-f", "rawvideo", "-pix_fmt", "yuv444p", dst], check=True)
        raw = np.frombuffer(open(dst, "rb").read(), np.uint8).astype(np.int64)
    n = 4 * h * w
    assert raw.size == 3 * n, "ffmpeg's upsample: %d bytes" % raw.size
    ref = raw[n:2 * n].reshape(2 * h, 2 * w)       # the U plane
    ours = up_ident(c)
    d = np.abs(ours - ref)[1:-1, 1:-2]            # (ffmpeg's own edge rule at the borders)
    assert d.max() <= 1, "identity chroma %d codes from ffmpeg's upsampling" % d.max()
    print("disp_golden: identity chroma within %d code of ffmpeg's upsampling (in_chroma_loc=left)" % d.max())


check_chroma_oracle(L[1])
write_want("disp_want_blend.hex", rgb(*blend(Lf)))
write_want("disp_want_bob0.hex", rgb(*bob(Lf, 0)))
write_want("disp_want_bob1.hex", rgb(*bob(Lf, 1)))
# (P6: the 480x272 and 720x576 kernel fixtures retired -- the kernels apply at the identity
# fit only, where L's first and last lines are the mirrors; those pictures are FIT's s / t)


# ---- P6 step 3: the FITTED raster (docs/analog.md §5) -------------------------------------
# Written from the design's formulas (tools/disp_fit_ref.py holds the fit's integers): the
# box decimation, the 2-tap blends (horizontal on rows k and k + 1, then vertical), chroma
# NEAREST at the luma tap >> 1, black outside the rectangle. Not from the RTL.
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import disp_fit_ref as _fr


def box(p, dh, dv):
    """(sum + 2^(s-1)) >> s over each dh x dv block, s = log2(dh dv)"""
    H, W = p.shape
    s = (dh * dv).bit_length() - 1
    t = p.reshape(H // dv, dv, W // dh, dh).sum(axis=(1, 3))
    return (t + (1 << (s - 1))) >> s if s else t


def prefiltered(p, dh, dv, hpf, vpf):
    """(docs/analog.md §11b) the stored luma: over the box sums B (dh x dv, unrounded), the
    vertical pre-filter's weights (eighths) on boxes k, k + 1, k + 2 and the horizontal's on
    samples m, m + 1, m + 2, ONE rounding: (sum + 2^(s+5)) >> (s + 6), s = log2(dh dv). Anti-
    twitter's sliding rows (§9) are vpf 4: (B_k + B_k+1 + 2^s) >> (s + 1), and (8, 0, 0) both ways
    the plain box -- the old integers exactly. Samples past the picture (only a clamped tap's
    neighbours, never read) replicate the last."""
    H, W = p.shape
    s = (dh * dv).bit_length() - 1
    B = p.reshape(H // dv, dv, W // dh, dh).sum(axis=(1, 3)).astype(np.int64)
    wv, wh = _fr.pf_weights(vpf), _fr.pf_weights(hpf)
    Bp = np.pad(B, ((0, 2), (0, 2)), mode='edge')
    V = sum(wv[i] * Bp[i:i + B.shape[0], :] for i in range(3))
    T = sum(wh[j] * V[:, j:j + B.shape[1]] for j in range(3))
    return (T + (1 << (s + 5))) >> (s + 6)


def taps(f, j, axis):
    """src_pos over an array of output indices (numpy: // and >> floor like Python's); the
    pre-filtered sample k is centred at k + S / 8 (docs/analog.md §11b; anti-twitter's sliding
    rows are S = 4, §9), so the position is S / 8 of a decimated sample up, and the last sample
    whose boxes lie inside the crop is kmax - (nb - 1)"""
    step, d, org, size = (f['sx'], f['dh'], f['lx'], f['wc']) if axis == 'x' else \
                         (f['sy'], f['dv'], f['ty'], f['hc'])
    c = f['hpf'] if axis == 'x' else f['vpf']
    Q = _fr.Q
    pos = (org << Q) + j * step + (step >> 1) - (1 << (Q - 1))
    u = (pos - ((d - 1) << (Q - 1)) - ((d * _fr.pf_shift(c)) << (Q - 3))) // d
    kmin, kmax = org // d, (org + size - 1) // d - _fr.pf_extra(c)
    k = u >> Q
    w = (u >> (Q - 8)) & 0xFF
    w = np.where(k < kmin, 0, w)
    return np.clip(k, kmin, kmax), np.clip(k + 1, kmin, kmax), w


def lerp(a, b, w):
    return (a * (256 - w) + b * w + 128) >> 8


def render(Y, Cb, Cr, f, luma=None):
    """the raster (RH x RW x 3) and its de mask for a picture fitted by f (luma: a dict that
    receives each shown line's luma, for the ffmpeg check below).
    The pre-filters (§11b; anti-twitter's sliding rows among them): luma only; chroma is
    unfiltered and read at the tap NEAREST the unshifted position -- (w + 32 (S mod 8) >= 128 ?
    k1 : k0) + S // 8 -- so colour stays registered with luma"""
    Yd = prefiltered(Y, f['dh'], f['dv'], f['hpf'], f['vpf'])
    Ud, Vd = box(Cb, f['dh'], f['dv']), box(Cr, f['dh'], f['dv'])
    rh, rw = f['rh'], f['rw']                     # the raster (576 lines at 50 Hz; stage 2: a native raster)
    img = np.zeros((rh, rw, 3), np.int64)
    de = np.zeros((rh, rw), bool)
    x0, x1 = max(0, f['ox0']), min(rw, f['ox0'] + f['ow'])
    if x1 <= x0:
        return img, de
    xs = np.arange(x0, x1)
    kx0, kx1, wx = taps(f, xs - f['ox0'], 'x')
    sh, sv = _fr.pf_shift(f['hpf']), _fr.pf_shift(f['vpf'])
    cx = (np.where(wx + 32 * (sh % 8) >= 128, kx1, kx0) + sh // 8) >> 1
    # (docs/display.md "Chroma at the identity") the identity fit on a progressive raster: chroma
    # interpolated at H.264's default siting -- hup over the crop's columns, then vrow -- instead of
    # nearest; every other fit keeps chroma nearest
    ident = (not f.get('il', False)) and f['sx'] == (1 << _fr.Q) and f['sy'] == (1 << _fr.Q) and \
        f['dh'] == 1 and f['dv'] == 1
    if ident:
        lastc = (f['lx'] + f['wc'] - 1) >> 1
        kmin_y, kmax_y = f['ty'], f['ty'] + f['hc'] - 1
        hU, hV = hup(Ud, kx0, lastc), hup(Vd, kx0, lastc)
    for L in range(max(0, f['oy0']), min(rh, f['oy0'] + f['oh'])):
        ky0, ky1, wy = taps(f, np.array([L - f['oy0']]), 'y')
        ky0, ky1, wy = int(ky0[0]), int(ky1[0]), int(wy[0])
        y = lerp(lerp(Yd[ky0, kx0], Yd[ky0, kx1], wx), lerp(Yd[ky1, kx0], Yd[ky1, kx1], wx), wy)
        cy = ((ky1 if wy + 32 * (sv % 8) >= 128 else ky0) + sv // 8) >> 1
        if ident:
            img[L, x0:x1] = rgb(y, vrow(hU, ky0, kmin_y, kmax_y), vrow(hV, ky0, kmin_y, kmax_y))
        else:
            img[L, x0:x1] = rgb(y, Ud[cy, cx], Vd[cy, cx])
        if luma is not None:
            luma[L] = y
            luma.setdefault('cx', cx)                 # the chroma taps chosen (check_filter scores them)
            luma.setdefault('cy', {})[L] = cy
        de[L, x0:x1] = True
    return img, de


def check_filter(name, wm, hm, cr, sar, mode, il, at, pal, flt):
    """(docs/analog.md §11b) independent of the arithmetic above:
    - a RAMP: every filter here sums to 1 and is symmetric about the centre it claims, so on a
      linear ramp the output equals the ramp at the output pixel's own source position (within
      the quantisation): a centre offset wrong by any fraction of a sample shows
    - chroma: the tap chosen is the decimated sample NEAREST the unshifted position, computed
      in floating point from the source position (ties excepted): colour registered with luma
    - an upscale (r <= 1 both ways) renders exactly Sharp's raster"""
    f = _fr.fit(wm, hm, cr, sar[0], sar[1], mode, il, at, pal, flt=flt)
    if f['hpf'] == 0 and f['vpf'] == 0:
        g = _fr.fit(wm, hm, cr, sar[0], sar[1], mode, il, at, pal)
        P = picture(1, 16 * wm, 16 * hm)
        assert (render(*P, f)[0] == render(*P, g)[0]).all() and f['dh'] == g['dh'], name + ": not Sharp's"
        print("disp_golden: %s: no pre-filter, Sharp's raster exactly" % name)
        return
    W, H = 16 * wm, 16 * hm
    xx, yy = np.meshgrid(np.arange(W), np.arange(H))
    for axis in ('x', 'y'):
        ramp = (xx if axis == 'x' else yy) * (180.0 / (W if axis == 'x' else H)) + 30
        Y = np.round(ramp).astype(np.int64)
        lum = {}
        render(Y, np.full((H // 2, W // 2), 128), np.full((H // 2, W // 2), 128), f, lum)
        taken = (lum.pop('cx'), lum.pop('cy'))
        step, org, size, o0, n = (f['sx'], f['lx'], f['wc'], f['ox0'], f['ow']) if axis == 'x' else \
                                 (f['sy'], f['ty'], f['hc'], f['oy0'], f['oh'])
        span = W if axis == 'x' else H
        worst = 0.0
        for L, y in lum.items():
            j = np.arange(len(y)) if axis == 'x' else np.full(len(y), L - f['oy0'])
            if axis == 'x':
                j = np.arange(max(0, f['ox0']), max(0, f['ox0']) + len(y)) - f['ox0']
            src = org + (j + 0.5) * step / 65536.0 - 0.5
            inner = (src > org + 12 * (f['dh'] if axis == 'x' else f['dv'])) & \
                    (src < org + size - 1 - 12 * (f['dh'] if axis == 'x' else f['dv']))
            if inner.any():
                worst = max(worst, float(np.abs(y[inner] - (src[inner] * 180.0 / span + 30)).max()))
        assert worst <= 1.5, "%s: the %s ramp off by %.2f codes (a centre offset)" % (name, axis, worst)
        print("disp_golden: %s: the %s ramp within %.2f codes" % (name, axis, worst))
    cxs, cys = taken
    # IMPULSES: isolated one-sample lines at spread output phases; each one's centroid on the output, mapped back
    # through the fit, against where it is -- the mean signed error is the centre offset (rounding
    # noise averages out; a 3/8-sample offset at r 1.8 is 0.2 output pixels)
    for axis in ('x', 'y'):
        pos_of = np.arange(W) if axis == 'x' else np.arange(H)
        # each line placed (within 8 of every 37th) so its output phase is the next of a uniform
        # set: the sampling's own bias, odd about each phase, then averages to zero
        st_, org_ = (f['sx'], f['lx']) if axis == 'x' else (f['sy'], f['ty'])
        base = np.arange(20, (W if axis == 'x' else H) - 28, 37)
        ph = lambda x: (((x - org_ + 0.5) * 65536.0 / st_ - 0.5) % 1.0)
        lines = np.array([min(range(b - 8, b + 9), key=lambda x: abs(ph(x) - (i + 0.5) / len(base)))
                          for i, b in enumerate(base)])
        Y = np.full((H, W), 16, np.int64)
        if axis == 'x':
            Y[:, lines] = 235
        else:
            Y[lines, :] = 235
        lum = {}
        render(Y, np.full((H // 2, W // 2), 128), np.full((H // 2, W // 2), 128), f, lum)
        lum.pop('cx'); lum.pop('cy')
        step, org, size, o0 = (f['sx'], f['lx'], f['wc'], f['ox0']) if axis == 'x' else \
                              (f['sy'], f['ty'], f['hc'], f['oy0'])
        if axis == 'x':
            L0 = sorted(lum)[len(lum) // 2]
            prof = lum[L0].astype(float) - 16
            j = np.arange(max(0, o0), max(0, o0) + len(prof)) - o0
        else:
            Ls = sorted(lum)
            x0 = len(lum[Ls[0]]) // 2
            prof = np.array([lum[L][x0] for L in Ls], float) - 16
            j = np.array(Ls) - o0
        s_out = step / 65536.0
        errs = []
        for x in lines:
            if x < org + 8 * s_out or x > org + size - 1 - 8 * s_out:
                continue
            want = (x - org + 0.5) / s_out - 0.5          # the output coordinate of the source line
            m = np.abs(j - want) <= 3 + 3 / s_out
            if prof[m].sum() <= 0:
                continue
            errs.append(float((j[m] * prof[m]).sum() / prof[m].sum() - want))
        if errs:
            me = float(np.mean(errs))
            assert abs(me) <= 0.08, "%s: the %s impulses' centroids off by %.3f output pixels (a centre offset)" % (name, axis, me)
            print("disp_golden: %s: %d %s impulses centred within %.3f" % (name, len(errs), axis, me))
    for axis in ('x', 'y'):
        step, d, org, size, n = (f['sx'], f['dh'], f['lx'], f['wc'], f['ow']) if axis == 'x' else \
                                (f['sy'], f['dv'], f['ty'], f['hc'], f['oh'])
        if axis == 'x':
            j = np.arange(max(0, f['ox0']), max(0, f['ox0']) + len(cxs)) - f['ox0']
            chosen = np.asarray(cxs)              # render's chroma column (decimated chroma units)
        else:
            Ls = sorted(cys)
            j = np.array(Ls) - f['oy0']
            chosen = np.array([cys[L] for L in Ls])
        # the decimated luma sample nearest the UNSHIFTED position, then its chroma sample (>> 1);
        # positions within 0.1 of a tie between chroma samples are excepted
        u = ((org + (j + 0.5) * step / 65536.0 - 0.5) - (d - 1) / 2.0) / d
        near = np.floor(u + 0.5).astype(np.int64) >> 1
        inner = (u > org // d + 3) & (u < (org + size - 1) // d - 3) & (np.abs(u - np.round(u)) < 0.4)
        bad = int((chosen[inner] != near[inner]).sum())
        assert bad == 0, "%s: chroma's %s tap off the unshifted position on %d of %d" % (name, axis, bad, int(inner.sum()))
    print("disp_golden: %s: chroma's taps nearest the unshifted position" % name)


def write_want_de(name, img, de):
    with open(os.path.join(out, name), "w") as fh:
        for y in range(img.shape[0]):
            for x in range(img.shape[1]):
                fh.write(("1%02x%02x%02x\n" % tuple(img[y, x])) if de[y, x] else "0000000\n")


# the identity: 720x480 in Fit on the progressive raster is the frame golden, bit for bit -- render's
# crop-aware identity chroma (hup over the crop's columns, vrow) against up_ident's whole frame
_f = _fr.fit(45, 30, mode='fit')
_img, _de = render(*L, _f)
assert _de.all() and (_img == rgb(L[0], up_ident(L[1]), up_ident(L[2]))).all(), "the identity fit is not the frame golden"
# the fitted cases: (name, seed, W, H in MBs, crop (cuy4, l, r, t, b), sar, mode, il, at[, pal])
FIT = [("s",    11, 30, 17,  (0, 0, 0, 0, 0), (1, 1),   'fit',       False, False),   # 480x272 up, progressive
       ("t",    13, 45, 36,  (0, 0, 0, 0, 0), (1, 1),   'letterbox', True,  False),   # 720x576 pillarbox, 480i
       ("w",    17, 54, 30,  (0, 2, 3, 0, 0), (1, 1),   'letterbox', True,  False),   # 854x480 (cropped 4 + 6) letterbox
       ("wc",   17, 54, 30,  (0, 0, 5, 0, 0), (1, 1),   'crop',      True,  False),   # 854x480 Crop: the sides cut
       ("v",    19, 30, 54,  (0, 0, 0, 2, 3), (1, 1),   'letterbox', True,  False),   # 480x854 portrait (cropped 4 + 6)
       ("snap", 23, 44, 30,  (0, 0, 0, 0, 0), (10, 11), 'letterbox', True,  False),   # 704x480 10:11: 1:1, offset 8
       ("tall", 29, 12, 128, (0, 0, 0, 0, 0), (1, 1),   'letterbox', True,  False),   # 192x2048: dv 8, dh 2
       ("wide", 31, 128, 12, (0, 0, 0, 0, 0), (1, 1),   'fit',       False, False),   # 2048x192: dh 2 (the buffer)
       ("p640", 37, 40, 30,  (0, 0, 0, 0, 0), (1, 1),   'fit',       False, False),   # 640x480 stretched
       # anti-twitter (P6 step 4, docs/analog.md §9): 480i, sliding boxes
       ("at_id",   41, 45, 30,  (0, 0, 0, 0, 0), (1, 1), 'fit',       True, True),     # 720x480: the (1, 2, 1)
       ("at_w",    43, 54, 30,  (0, 2, 3, 0, 0), (1, 1), 'letterbox', True, True),     # 854x480 letterbox
       ("at_v",    47, 30, 54,  (0, 0, 0, 2, 3), (1, 1), 'letterbox', True, True),     # 480x854: the crop's top
       ("at_tall", 53, 12, 128, (0, 0, 0, 0, 0), (1, 1), 'letterbox', True, True),     # 192x2048: dv 4, 8-row boxes
       ("at_wide", 59, 128, 12, (0, 0, 0, 0, 0), (1, 1), 'letterbox', True, True),     # 2048x192: dv 2 (the W > 40 cap), dh 2
       ("at_up",   61, 22, 15,  (0, 0, 0, 0, 0), (1, 1), 'letterbox', True, True),     # 352x240 scaled up
       # the 576-line raster (P6 step 6, docs/analog.md §10)
       ("pal_w",   67, 54, 30,  (0, 0, 5, 0, 0), (1, 1),   'letterbox', False, False, True),  # 854x480 on 576p: 720x432
       ("pal_n",   71, 45, 36,  (0, 0, 0, 0, 0), (12, 11), 'letterbox', True,  False, True),  # 720x576 12:11: the snap, 576i
       ("pal_at",  73, 64, 23,  (0, 0, 0, 0, 8), (1, 1),   'letterbox', True,  True,  True),  # 1024x352 (cropped) 576i anti-twitter
       # (0.11) 1280x720, 3,600 macroblocks: the 2 MiB store (Cb at word 115,200, past 2^17), dh 2
       ("hd",      97, 80, 45,  (0, 0, 0, 0, 0), (1, 1),   'fit',       False, False),        # 1280x720 Fit, 480p: 640 stored
       ("hd_il",  101, 80, 45,  (0, 0, 0, 0, 0), (1, 1),   'letterbox', True,  False),        # letterboxed at 480i
       ("hd_at",  103, 80, 45,  (0, 0, 0, 0, 0), (1, 1),   'letterbox', True,  True),         # ... with anti-twitter
       ("hd_pal", 107, 80, 45,  (0, 0, 0, 0, 0), (1, 1),   'letterbox', True,  False, True),  # letterboxed at 576i
       # (docs/analog.md §11b) the Area pre-filter: (..., pal, flt) -- 'area' the core's, the cases above
       # without it the Sharp control (bit-identical to main)
       ("hd_area",    109, 80, 45,  (0, 0, 0, 0, 0), (1, 1), 'fit',       False, False, False, 'area'),    # 1,280 kept: A 3 / 2
       ("hd_il_area", 127, 80, 45,  (0, 0, 0, 0, 0), (1, 1), 'letterbox', True,  False, False, 'area'),    # 480i
       ("hd_at_area", 131, 80, 45,  (0, 0, 0, 0, 0), (1, 1), 'letterbox', True,  True,  False, 'area'),    # ... with anti-twitter
       ("w_area",     137, 54, 30,  (0, 2, 3, 0, 0), (1, 1), 'letterbox', True,  False, False, 'area'),    # 854x480 at 480i: A 1 / 1
       ("w_at_area",  139, 54, 30,  (0, 2, 3, 0, 0), (1, 1), 'letterbox', True,  True,  False, 'area'),    # ... anti-twitter the stronger
       ("p_area",     149, 54, 30,  (0, 0, 5, 0, 0), (1, 1), 'fit',       False, False, False, 'area'),    # horizontal only (rows 1:1)
       ("port_area",  151, 45, 80,  (0, 0, 0, 0, 0), (1, 1), 'letterbox', False, False, False, 'area'),    # 720x1280: dh 2 dv 2, W odd
       ("wide_area",  163, 128, 28, (0, 0, 0, 0, 0), (1, 1), 'letterbox', False, False, False, 'area'),    # 2048x448: past the budget
       ("tall_area",  167, 12, 128, (0, 0, 0, 0, 0), (1, 1), 'letterbox', True,  False, False, 'area'),    # 192x2048 dv 4
       ("pal_area",   173, 64, 36,  (0, 0, 0, 0, 0), (1, 1), 'letterbox', True,  False, True,  'area'),    # 1024x576 at 576i
       ("s_area",     11, 30, 17,   (0, 0, 0, 0, 0), (1, 1), 'fit',       False, False, False, 'area')]    # an upscale: Sharp's raster
# (hdmi_raster stage 2) the native raster: raster_geom's geometry for the picture on a 1920x1080
# display, the fit's identity on it -- (name, seed, W, H in MBs, crop, sar, std)
import raster_geom_ref as _rg
NAT = [("nat_scope", 79, 54, 23, (0, 0, 6, 0, 6), (640, 639), 0),   # 852x356 letterboxed in 852x480
       ("nat_43",    83, 40, 30, (0, 0, 0, 0, 0), (1, 1),     0),   # 640x480 pillarboxed in 853x480
       ("nat_pal",   89, 45, 36, (0, 0, 0, 0, 0), (16, 15),   2),   # 720x576 4:3 PAL: display-shaped 960x576 (hd_raster), 50 Hz
       ("nat_hd",    91, 80, 45, (0, 0, 0, 0, 0), (1, 1),     0),   # (hd_raster stage B) 1280x720 at its own pixels
       ("nat_w2k",   93, 128, 28, (0, 0, 0, 0, 0), (1, 1),    0)]   # ... the widest legal picture, 2048x448
with open(os.path.join(out, "disp_nat_cases.txt"), "w") as nf:
    for name, seed, wm, hm, cr, sar, std in NAT:
        P = picture(seed, 16 * wm, 16 * hm)
        f0 = _fr.fit(wm, hm, cr, sar[0], sar[1], 'fit')
        g = _rg.geom(f0['wc'], f0['hc'], sar[0], sar[1], wm, 1920, 1080, std, 1)
        assert g['mode'] == _rg.MODE_NATIVE, (name, g)
        f = _fr.fit(wm, hm, cr, sar[0], sar[1], 'fit', False, False, std == 2, 0, 0, True, g['rw'], g['rh'])
        img, de = render(*P, f)
        write_store("disp_store_nat_%s.hex" % name, *P)
        write_want_de("disp_want_nat_%s.hex" % name, img, de)
        nf.write("%s %d %d %d %d %d %d %d %d %d %d  %d %d %d %d %d  %dx%d at (%d, %d)\n" % (
            name, wm, hm, cr[0], cr[1], cr[2], cr[3], cr[4], sar[0], sar[1], std,
            g['rw'], g['rh'], g['l'], g['nt'], g['last'], f['ow'], f['oh'], f['ox0'], f['oy0']))
with open(os.path.join(out, "disp_fit_cases.txt"), "w") as cf:
    for name, seed, wm, hm, cr, sar, mode, il, at, *rest in FIT:
        pal = bool(rest and rest[0])
        flt = rest[1] if len(rest) > 1 else 'sharp'
        P = picture(seed, 16 * wm, 16 * hm)
        f = _fr.fit(wm, hm, cr, sar[0], sar[1], mode, il, at, pal, flt=flt)
        lum = {}
        img, de = render(*P, f, lum)
        write_store("disp_store_fit_%s.hex" % name, *P)
        write_want_de("disp_want_fit_%s.hex" % name, img, de)
        cf.write("%s %d %d %d %d %d %d %d %d %d %d %d %d %d %d  %dx%d at (%d, %d) dh %d dv %d snap %d pf %d/%d\n" % (
            name, wm, hm, cr[0], cr[1], cr[2], cr[3], cr[4], sar[0], sar[1],
            ('letterbox', 'crop', 'fit').index(mode), int(il), int(at), int(pal), _fr.FLT.index(flt),
            f['ow'], f['oh'], f['ox0'], f['oy0'], f['dh'], f['dv'], int(f['snap']), f['hpf'], f['vpf']))
        if flt != 'sharp':
            check_filter(name, wm, hm, cr, sar, mode, il, at, pal, flt)
        if name == "at_id":
            # the independent check: at the identity the sliding boxes ARE the (1, 2, 1) --
            # ffmpeg's `interlace` lowpass ((1 + a + 2b + d) >> 2) within one code (the design
            # rounds twice), on every line but the edges (the design clamps, ffmpeg mirrors)
            ref = blend([P[0]] * 3)[0]
            ours = np.array([lum[L] for L in range(1, 479)])
            dmax = int(np.abs(ours - ref[1:479]).max())
            assert dmax <= 1, "anti-twitter at the identity is %d codes from the (1, 2, 1)" % dmax
            print("disp_golden: anti-twitter at the identity within %d code of %s" % (
                dmax, "ffmpeg's interlace lowpass" if HAVE_FFMPEG else "the (1, 2, 1) formula (NO ffmpeg)"))
print("disp_golden: %d fitted rasters (the identity fit = the frame golden)" % len(FIT))

oracle = "ffmpeg separatefields + interlace lowpass" if HAVE_FFMPEG else \
    "numpy (NO ffmpeg: not an independent oracle)"
print("disp_golden: the 720x480 store; frame, field, blend, bob0/1 rasters (%s)" % oracle)
