import os, sys, re, time, shutil, subprocess, tempfile
import numpy as np, cv2
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

W, H = 2560, 1440
# Шаблон KLA4_tver: где лежат надписи и в каких кадрах они видны
SPECS = {
    'brand': dict(ref=120, band=(540, 700), xr=(900, 1700), first=1, last=157, kind='white', minpx=150),
    'server': dict(ref=80, band=(672, 810), xr=(900, 1700), first=10, last=157, margin=(40, 12, 40, 40), tall=0.80, wide=1.0),
    'promo': dict(ref=300, band=(660, 930), xr=(0, W), first=158, last=515, margin=(70, 55, 70, 70), tall=0.92, wide=1.0),
}
INTRO_END = 157


def res(p):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    # by lozanovvv_
    return os.path.join(base, p)


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which('ffmpeg') or 'ffmpeg'


def run(cmd):
    kw = {'creationflags': 0x08000000} if os.name == 'nt' else {}
    # by lozanovvv_
    return subprocess.run(cmd, capture_output=True, text=True, errors='replace', **kw)


def core_mask(a, sp):
    R, G, B, A = [a[..., k].astype(int) for k in range(4)]
    if sp.get('kind') == 'white':
        m = ((R > 238) & (G > 238) & (B > 238) & (A > 235)).astype(np.uint8)
    else:
        m = ((R > 235) & (R - B > 60) & (A > 200)).astype(np.uint8)
    out = np.zeros_like(m)
    # by lozanovvv_
    y0, y1 = sp['band']
    x0, x1 = sp['xr']
    out[y0:y1, x0:x1] = m[y0:y1, x0:x1]
    return out


def bbox(m, minpx=40):
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = [k for k in range(1, n) if st[k, 4] >= minpx]
    if not keep:
        return None
    # by lozanovvv_
    big = max(st[k, 4] for k in keep)
    keep = [k for k in keep if st[k, 4] >= big * 0.05]
    x0 = min(st[k, 0] for k in keep); y0 = min(st[k, 1] for k in keep)
    x1 = max(st[k, 0] + st[k, 2] for k in keep); y1 = max(st[k, 1] + st[k, 3] for k in keep)
    return np.array([x0, y0, x1, y1], float)


def hue_shift(rgb, weight, hue, sat=1.0):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
    h = hsv[..., 0] * 360 / 256
    # by lozanovvv_
    hs = np.where(h > 180, h - 360, h)
    nh = np.mod(hue + 0.35 * (hs - 12), 360) * 256 / 360
    out = hsv.copy()
    out[..., 0] = nh
    out[..., 1] = np.clip(hsv[..., 1] * sat, 0, 255)
    new = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB_FULL)
    w = weight[..., None]
    return (rgb * (1 - w) + new * w).astype(np.uint8)


def warm_weight(rgb, hmin=-60, hfull=34, hzero=42, smin=0.12):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
    # by lozanovvv_
    h = hsv[..., 0] * 360 / 256
    s = hsv[..., 1] / 255
    hs = np.where(h > 180, h - 360, h)
    w = np.clip((hzero - hs) / (hzero - hfull), 0, 1) * (hs > hmin)
    return (w * np.clip((s - smin) / 0.1, 0, 1)).astype(np.float32)


@lru_cache(maxsize=4)
def ref_info(src_dir, key):
    sp = SPECS[key]
    # by lozanovvv_
    a = np.array(Image.open(os.path.join(src_dir, '%04d.png' % sp['ref'])))
    box = bbox(core_mask(a, sp), sp.get('minpx', 40))
    return box, core_mask(a, sp)


@lru_cache(maxsize=16)
def render_text(text, key, hue, src_dir):
    box, _ = ref_info(src_dir, key)
    sp = SPECS[key]
    bw, bh = box[2] - box[0], box[3] - box[1]
    # by lozanovvv_
    c = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
    SS = 3
    f = ImageFont.truetype(res('assets/Unbounded.ttf'), 200 * SS)
    f.set_variation_by_name('Black')
    tmp = Image.new('L', ((260 * len(text) + 200) * SS, 400 * SS), 0)
    d = ImageDraw.Draw(tmp)
    x = 40 * SS
    for ch in text:   # буквы по одной, с зазором между ними
        d.text((x, 40 * SS), ch, font=f, fill=255)
        x += f.getlength(ch) + 14 * SS
    # by lozanovvv_
    tmp = tmp.crop(tmp.getbbox())
    g = np.array(tmp).astype(np.float32) / 255
    gh = bh * sp['tall']
    gw = tmp.width / tmp.height * gh * 0.88
    if gw > bw * 1.25:
        sc = bw * 1.25 / gw
        gw, gh = gw * sc, gh * sc
    g = cv2.resize(g, (max(int(round(gw)), 4), max(int(round(gh)), 4)), interpolation=cv2.INTER_AREA)
    k = bh / 142.0
    PAD = int(90 * max(k, 0.6))
    # by lozanovvv_
    h2, w2 = g.shape[0] + 2 * PAD, g.shape[1] + 2 * PAD
    G = np.zeros((h2, w2), np.float32)
    G[PAD:PAD + g.shape[0], PAD:PAD + g.shape[1]] = g
    ys = np.arange(h2)[:, None].astype(np.float32) - PAD
    t = np.clip(0.5 + 0.5 * np.cos(2 * np.pi * (ys - 12 * k) / (19.7 * k)), 0, 1) ** 0.8
    dark = np.array([246, 106, 77], np.float32)
    light = np.array([255, 197, 155], np.float32)
    fill = np.broadcast_to(dark * (1 - t[..., None]) + light * t[..., None], (h2, w2, 3))
    d = cv2.distanceTransform(1 - (G > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    RIM = max(14.0 * k, 5.0)
    # by lozanovvv_
    rt = np.clip(d / RIM, 0, 1)[..., None]
    rim_col = np.array([160, 76, 58], np.float32) * (1 - rt) + np.array([88, 32, 24], np.float32) * rt
    rim_a = np.clip(RIM + 1.0 - d, 0, 1)
    gd = np.clip(d - RIM, 0, None)
    glow_a = np.where(d > RIM, 0.48 * np.exp(-gd / (6.0 * k)) + 0.40 * np.exp(-gd / (22.0 * k)), 0)
    gt = np.clip(gd / (30 * k), 0, 1)[..., None]
    glow_col = np.array([85, 30, 22], np.float32) * (1 - gt) + np.array([43, 14, 13], np.float32) * gt
    col = np.where(rim_a[..., None] > 0, rim_col * rim_a[..., None] + glow_col * (1 - rim_a[..., None]), glow_col)
    a = rim_a + glow_a * (1 - rim_a)
    ga = G[..., None]
    # by lozanovvv_
    col = fill * ga + col * (1 - ga)
    a = G + a * (1 - G)
    rgb = hue_shift(np.clip(col, 0, 255).astype(np.uint8), np.ones((h2, w2), np.float32), hue, sat=1.3)
    rgba = np.dstack([rgb, np.clip(a * 255, 0, 255).astype(np.uint8)])
    cx, cy = PAD + g.shape[1] / 2, PAD + g.shape[0] / 2
    L = np.array([[1, 0, c[0] - cx], [0, 1, c[1] - cy], [0, 0, 1]], np.float64)
    return rgba, L


def estimate(a, key, src_dir):
    sp = SPECS[key]
    # by lozanovvv_
    box, ref_m = ref_info(src_dir, key)
    m = core_mask(a, sp)
    bb = bbox(m, sp.get('minpx', 40))
    if bb is None:
        return None
    if sp.get('kind') == 'white':
        clip = bb[0] if bb[0] > box[0] + 60 else None
        return np.array([[1, 0, bb[2] - box[2]], [0, 1, bb[3] - box[3]]], np.float32), clip
    rc = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
    s = ((bb[2] - bb[0]) / (box[2] - box[0]) + (bb[3] - bb[1]) / (box[3] - box[1])) / 2
    # by lozanovvv_
    c = np.array([(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2])
    T = np.array([[s, 0, c[0] - s * rc[0]], [0, s, c[1] - s * rc[1]]], np.float32)
    if m.sum() < 0.15 * ref_m.sum():
        return T
    k = 0.5
    S = np.diag([k, k, 1.0])
    Tm = S @ np.vstack([T, [0, 0, 1]]) @ np.linalg.inv(S)
    tpl = cv2.GaussianBlur(cv2.resize(ref_m.astype(np.float32), None, fx=k, fy=k), (0, 0), 2)
    img = cv2.GaussianBlur(cv2.resize(m.astype(np.float32), None, fx=k, fy=k), (0, 0), 2)
    Wm = Tm[:2].astype(np.float32)
    # by lozanovvv_
    try:
        _, Wm = cv2.findTransformECC(tpl, img, Wm, cv2.MOTION_AFFINE,
                                     (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5), None, 5)
    except cv2.error:
        return T
    return (np.linalg.inv(S) @ np.vstack([Wm, [0, 0, 1]]) @ S)[:2].astype(np.float32)


def inpaint_mask(a, mask):
    ys, xs = np.nonzero(mask)
    # by lozanovvv_
    x0, x1 = max(xs.min() - 70, 0), min(xs.max() + 70, a.shape[1])
    y0, y1 = max(ys.min() - 70, 0), min(ys.max() + 70, a.shape[0])
    sub = a[y0:y1, x0:x1].astype(np.float32)
    mk = mask[y0:y1, x0:x1] > 0
    al = sub[..., 3:4] / 255
    pm = np.dstack([sub[..., :3] * al, sub[..., 3:4]])
    hv = cv2.cvtColor(sub[..., :3].astype(np.uint8), cv2.COLOR_RGB2HSV_FULL)
    white = ((hv[..., 1] < 80) & (hv[..., 2] > 170) & (sub[..., 3] > 60)).astype(np.uint8)
    white = cv2.dilate(white, np.ones((13, 13), np.uint8)) > 0
    known = (~mk & ~white).astype(np.float32)
    # by lozanovvv_
    res = np.zeros_like(pm)
    done = np.zeros(mk.shape, bool)
    for sg in (2, 5, 11, 22, 45, 90, 180, 360):
        den = cv2.GaussianBlur(known, (0, 0), sg)
        num = cv2.GaussianBlur(pm * known[..., None], (0, 0), sg)
        ok = (den > (0.12 if sg < 360 else 0.0005)) & ~done & mk
        res[ok] = num[ok] / den[ok][:, None]
        done |= ok
    out = a.copy()
    r = res[..., 3:4]
    # by lozanovvv_
    rgb = np.where(r > 1, res[..., :3] / np.maximum(r / 255, 1e-3), 0)
    fill = np.dstack([np.clip(rgb, 0, 255), np.clip(r, 0, 255)]).astype(np.uint8)
    sel = done
    out[y0:y1, x0:x1][sel] = fill[sel]
    return out


def remove_brand(a, key):
    sp = SPECS[key]
    core = core_mask(a, sp)
    # by lozanovvv_
    hsv = cv2.cvtColor(a[..., :3], cv2.COLOR_RGB2HSV_FULL)
    # старая надпись заменяется целиком: зона надписи очищается, низ звезды мягко затухает
    a = a.copy()
    a[566:698, 900:1700] = 0
    ramp = np.linspace(1, 0, 18)[None, :, None]
    a[548:566, 900:1700, 3] = (a[548:566, 900:1700, 3] * ramp[0]).astype(np.uint8)
    return a


def remove_old(a, T, key, src_dir):
    sp = SPECS[key]
    # by lozanovvv_
    box, _ = ref_info(src_dir, key)
    ml, mt, mr, mb = sp['margin']
    rect = np.array([[box[0] - ml, box[1] - mt], [box[2] + mr, box[1] - mt],
                     [box[2] + mr, box[3] + mb], [box[0] - ml, box[3] + mb]], np.float32)
    reg = np.zeros(a.shape[:2], np.uint8)
    cv2.fillPoly(reg, [cv2.transform(rect[None], T)[0].astype(np.int32)], 1)
    w = warm_weight(a[..., :3], -50, 28, 33, 0.18)
    mask = ((w > 0.3) & (a[..., 3] > 3) & (reg > 0)).astype(np.uint8)
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8)) & reg
    if mask.sum() == 0:
        return a
    # by lozanovvv_
    return inpaint_mask(a, mask)


def over(a, layer, T, L, clip=None):
    M = (np.vstack([T, [0, 0, 1]]) @ L)[:2].astype(np.float32)
    h, w = a.shape[:2]
    lay = layer.astype(np.float32)
    pm = np.dstack([lay[..., :3] * lay[..., 3:4] / 255, lay[..., 3]])
    wp = cv2.warpAffine(pm, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
    if clip is not None:
        wp[:, :max(int(clip), 0)] = 0
    # by lozanovvv_
    sa = wp[..., 3:4] / 255
    dst = a.astype(np.float32)
    da = dst[..., 3:4] / 255
    oa = sa + da * (1 - sa)
    orgb = np.where(oa > 0, (wp[..., :3] + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-4), 0)
    return np.dstack([np.clip(orgb, 0, 255), np.clip(oa * 255, 0, 255)]).astype(np.uint8)


def sh(g, dx, dy):
    return cv2.warpAffine(g, np.float32([[1, 0, dx], [0, 1, dy]]), (g.shape[1], g.shape[0]))


@lru_cache(maxsize=8)
def render_brand(text, src_dir):
    box, _ = ref_info(src_dir, 'brand')
    # by lozanovvv_
    bw, bh = box[2] - box[0], box[3] - box[1]
    c = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
    k = bh / 110.0
    SS = 3
    f = ImageFont.truetype(res('assets/MontserratItalic.ttf'), 200 * SS)
    f.set_variation_by_name('Black Italic')
    tmp = Image.new('L', ((260 * len(text) + 200) * SS, 400 * SS), 0)
    ImageDraw.Draw(tmp).text((40 * SS, 40 * SS), text, font=f, fill=255)
    tmp = tmp.crop(tmp.getbbox())
    gh = bh * 0.92
    # by lozanovvv_
    gw = tmp.width / tmp.height * gh * 1.1
    if gw > bw * 1.3:
        sc = bw * 1.3 / gw
        gw, gh = gw * sc, gh * sc
    c[1] = box[3] - gh / 2 - 2
    g = cv2.resize(np.array(tmp).astype(np.float32) / 255, (max(int(gw), 4), max(int(gh), 4)), interpolation=cv2.INTER_AREA)
    PAD = int(70 * max(k, 0.6))
    h2, w2 = g.shape[0] + 2 * PAD, g.shape[1] + 2 * PAD
    G = np.zeros((h2, w2), np.float32)
    G[PAD:PAD + g.shape[0], PAD:PAD + g.shape[1]] = g
    # by lozanovvv_
    G = cv2.warpAffine(G, np.float32([[1, 0, 0], [0, 1, 0]]), (w2, h2), flags=cv2.INTER_LINEAR)
    G = cv2.dilate(G, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * max(int(2 * k), 1) + 1,) * 2))
    E = max(int(6 * k), 2)
    U = G.copy()
    for o in range(1, E + 1):
        U = np.maximum(U, sh(G, o * 0.6, o))
    ring = np.clip(cv2.dilate(U, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(3 * k) + 1,) * 2)) - U, 0, 1)
    d = cv2.distanceTransform((U < 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    glow = np.where(U < 0.5, 0.38 * np.exp(-d / (14 * k)), 0).astype(np.float32)
    ys = np.arange(h2, dtype=np.float32)[:, None] - PAD
    # by lozanovvv_
    t = np.clip(ys / max(gh, 1), 0, 1)
    fill = (255 - 28 * t)[..., None] * np.ones((1, w2, 3), np.float32)
    rgb = np.zeros((h2, w2, 3), np.float32)
    a = np.zeros((h2, w2), np.float32)
    for col, al in ((np.array([255, 255, 255], np.float32), glow),
                    (np.array([40, 40, 48], np.float32), ring),
                    (np.array([128, 130, 142], np.float32), np.clip(U - G, 0, 1)),
                    (fill, G)):
        al3 = al[..., None]
        rgb = col * al3 + rgb * (1 - al3)
        # by lozanovvv_
        a = al + a * (1 - al)
    rgba = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), np.clip(a * 255, 0, 255).astype(np.uint8)])
    cx, cy = PAD + g.shape[1] / 2, PAD + g.shape[0] / 2
    return rgba, np.array([[1, 0, c[0] - cx], [0, 1, c[1] - cy], [0, 0, 1]], np.float64)


STAR_BOX = (850, 300, 1750, 566)   # область звезды над надписью (x0, y0, x1, y1)
STAR_REF = 43700.0                 # площадь звезды в статичном состоянии
STAR_CX, STAR_BOTTOM, STAR_W, STAR_H = 1260, 566, 460, 250


def cut_background(im):
    # нет настоящей прозрачности (нарисована «шашечка» или белый фон) — вырезаем фон от краёв
    # by lozanovvv_
    a = np.array(im)
    if a[..., 3].min() < 250:
        return im
    rgb = a[..., :3].astype(np.int16)
    bgm = ((rgb.max(2) - rgb.min(2) < 22) & (rgb.min(2) > 170)).astype(np.uint8)
    # шашечка: клетки не связаны между собой, поэтому закрываем щели и берём крупные области, в т.ч. внутри картинки
    closed = cv2.morphologyEx(bgm, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(closed, connectivity=4)
    keep = [k for k in range(1, n) if st[k, 4] > 120]
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    # by lozanovvv_
    cut = np.isin(lab, list(set(keep) | edge)) & (bgm > 0)
    cut = cv2.dilate(cut.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    alpha = np.where(cut, 0, 255).astype(np.uint8)
    a[..., 3] = cv2.GaussianBlur(alpha, (3, 3), 0)
    return Image.fromarray(a)


@lru_cache(maxsize=4)
def load_star(path):
    im = cut_background(Image.open(path).convert('RGBA'))
    # by lozanovvv_
    bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
    if bb:
        im = im.crop(bb)
    k = min(STAR_W / im.width, STAR_H / im.height)
    return np.array(im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS))


def star_state(a):
    x0, y0, x1, y1 = STAR_BOX
    return float((a[y0:y1, x0:x1, 3] > 200).sum())


def remove_star(a):
    x0, y0, x1, y1 = STAR_BOX
    # by lozanovvv_
    a[y0:y1, x0:x1] = 0
    # хвост звезды на верху букв: цветные (не белые) пиксели
    t = a[y1:y1 + 40, 1000:1560]
    c = t.astype(np.int16)
    sat = (c[..., :3].max(2) - c[..., :3].min(2)) / np.maximum(c[..., :3].max(2), 1)
    t[(sat > 0.25) & (c[..., 3] > 0)] = 0
    return a


def put_star(a, path, area):
    r = area / STAR_REF
    # by lozanovvv_
    if r < 0.02:
        return a
    s = min(1.0, r ** 0.5)
    im = load_star(path).astype(np.float32)
    h, w = im.shape[:2]
    nw, nh = max(2, int(w * s)), max(2, int(h * s))
    im = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_AREA)
    im[..., 3] *= min(1.0, r * 2)
    layer = np.zeros(a.shape, np.uint8)
    ox, oy = STAR_CX - nw // 2, STAR_BOTTOM - nh
    # by lozanovvv_
    layer[oy:oy + nh, ox:ox + nw] = im.astype(np.uint8)
    return over(a, layer, np.float32([[1, 0, 0], [0, 1, 0]]), np.eye(3))


def process_frame(args):
    i, src_dir, dst_dir, opt = args
    a = np.array(Image.open(os.path.join(src_dir, '%04d.png' % i)))
    hue = opt['hue']
    texts = {'brand': opt.get('brand'), 'server': opt.get('server'), 'promo': opt.get('promo')}
    star = opt.get('star')
    # by lozanovvv_
    star_area = star_state(a) if star and i <= INTRO_END else 0
    Ts = {}
    for key, txt in texts.items():
        sp = SPECS[key]
        if txt and sp['first'] <= i <= sp['last']:
            T = estimate(a, key, src_dir)
            if T is not None:
                Ts[key] = T
    for key, T in Ts.items():
        a = remove_brand(a, key) if key == 'brand' else remove_old(a, T, key, src_dir)
    # by lozanovvv_
    if star_area > 0:
        a = remove_star(a)
    if i <= INTRO_END:
        a[..., :3] = hue_shift(a[..., :3], warm_weight(a[..., :3]), hue)
    else:
        y2 = a[560:660, :, :3]
        a[560:660, :, :3] = hue_shift(y2, warm_weight(y2, -40, 24, 30, 0.62) * (np.max(y2, axis=2) > 200), hue)
        z = a[660:, :, :3]
        a[660:, :, :3] = hue_shift(z, warm_weight(z, -40, 24, 30, 0.45), hue)
    if star_area > 0 and star != 'none':
        a = put_star(a, star, star_area)
    # by lozanovvv_
    for key, T in Ts.items():
        if key == 'brand':
            layer, L = render_brand(texts[key], src_dir)
            a = over(a, layer, T[0], L, T[1])
        else:
            layer, L = render_text(texts[key], key, hue, src_dir)
            a = over(a, layer, T, L)
    Image.fromarray(a).save(os.path.join(dst_dir, '%04d.png' % i), compress_level=1)
    return i


def probe(src):
    r = run([ffmpeg_exe(), '-i', src])
    # by lozanovvv_
    txt = r.stderr
    fps = re.search(r'([\d.]+) fps', txt)
    size = re.search(r'(\d{3,5})x(\d{3,5})', txt)
    return (float(fps.group(1)) if fps else 60.0), ((int(size.group(1)), int(size.group(2))) if size else (W, H))


def extract_frame(src, n, fps, out_png):
    run([ffmpeg_exe(), '-y', '-v', 'error', '-ss', '%.4f' % (n / fps), '-i', src, '-frames:v', '1', '-pix_fmt', 'rgba', out_png])


def preview(src, opt, work):
    # быстрый предпросмотр: два ключевых кадра (сервер и промокод)
    # by lozanovvv_
    fps, _ = probe(src)
    sd = os.path.join(work, 'pv_src'); dd = os.path.join(work, 'pv_out')
    os.makedirs(sd, exist_ok=True); os.makedirs(dd, exist_ok=True)
    ref_info.cache_clear(); render_text.cache_clear(); render_brand.cache_clear()
    frames = [SPECS['brand']['ref'], SPECS['promo']['ref']]
    for n in sorted({sp['ref'] for sp in SPECS.values()}):
        extract_frame(src, n - 1, fps, os.path.join(sd, '%04d.png' % n))
    crops = []
    for n, (y0, y1) in zip(frames, [(300, 860), (560, 940)]):
        process_frame((n, sd, dd, opt))
        # by lozanovvv_
        im = Image.open(os.path.join(dd, '%04d.png' % n)).crop((760, y0, 1800, y1))
        bg = Image.new('RGBA', im.size, (40, 40, 40, 255))
        bg.alpha_composite(im)
        crops.append(bg.convert('RGB'))
    out = Image.new('RGB', (crops[0].width, sum(c.height for c in crops)))
    y = 0
    for c in crops:
        out.paste(c, (0, y)); y += c.height
    return out


def convert(src, dst, opt, progress=print, make_mp4=True, stop=None):
    from multiprocessing import Pool
    # by lozanovvv_
    fps, size = probe(src)
    if size != (W, H):
        raise RuntimeError('Ожидается видео %dx%d, а у файла %dx%d' % (W, H, size[0], size[1]))
    work = tempfile.mkdtemp(prefix='lznv_')
    sd = os.path.join(work, 'src'); dd = os.path.join(work, 'out')
    os.makedirs(sd); os.makedirs(dd)
    try:
        progress(('Распаковка кадров…', 0.01))
        total = 0
        try:
            m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', run([ffmpeg_exe(), '-i', src]).stderr)
            # by lozanovvv_
            total = int(round((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * fps))
        except Exception:
            total = 0
        kw = {'creationflags': 0x08000000} if os.name == 'nt' else {}
        proc = subprocess.Popen([ffmpeg_exe(), '-y', '-v', 'error', '-i', src, '-pix_fmt', 'rgba', os.path.join(sd, '%04d.png')],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace', **kw)
        while proc.poll() is None:
            if stop and stop():
                proc.kill()
                raise RuntimeError('Отменено')
            # by lozanovvv_
            got = len(os.listdir(sd))
            txt = 'Распаковка кадров %d/%d' % (got, total) if total else 'Распаковка кадров…'
            progress((txt, 0.01 + 0.04 * min(got / total, 1.0) if total else 0.02))
            time.sleep(0.3)
        err = proc.stderr.read()
        n = len([f for f in os.listdir(sd) if f.endswith('.png')])
        if n == 0:
            raise RuntimeError('Не удалось прочитать видео:\n' + err[-400:])
        ref_info.cache_clear(); render_text.cache_clear(); render_brand.cache_clear()
        jobs = [(i, sd, dd, opt) for i in range(1, n + 1)]
        # by lozanovvv_
        done = 0
        with Pool(max(1, (os.cpu_count() or 2) - 1)) as p:
            for _ in p.imap_unordered(process_frame, jobs, chunksize=2):
                if stop and stop():
                    raise RuntimeError('Отменено')
                done += 1
                progress(('Обработка кадров %d/%d' % (done, n), 0.05 + 0.85 * done / n))
        progress(('Сборка видео…', 0.93))
        r = run([ffmpeg_exe(), '-y', '-v', 'error', '-framerate', str(fps), '-i', os.path.join(dd, '%04d.png'),
                 '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', '-alpha_bits', '8',
                 '-qscale:v', '6', '-vendor', 'apl0', '-metadata', 'comment=by lozanovvv_', dst])
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-400:])
        # by lozanovvv_
        if make_mp4:
            mp4 = os.path.splitext(dst)[0] + '_preview.mp4'
            run([ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=0x282828:s=1280x720:r=%s' % fps,
                 '-framerate', str(fps), '-i', os.path.join(dd, '%04d.png'),
                 '-filter_complex', '[1]scale=1280:720[f];[0][f]overlay=shortest=1,format=yuv420p',
                 '-c:v', 'libx264', '-crf', '20', mp4])
        progress(('Готово', 1.0))
    finally:
        shutil.rmtree(work, ignore_errors=True)
