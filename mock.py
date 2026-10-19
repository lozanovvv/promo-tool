import colorsys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import engine

W, H = 540, 340


def hue_rgb(hue, s=0.72, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(hue / 360, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def hue_hex(hue):
    return '#%02x%02x%02x' % hue_rgb(hue, 0.7, 1.0)


def _font(px, italic=False):
    f = ImageFont.truetype(engine.res('assets/MontserratItalic.ttf' if italic else 'assets/Unbounded.ttf'), px)
    # by lozanovvv_
    f.set_variation_by_name('Black Italic' if italic else 'Black')
    return f


def _mask(text, px, pad=40, italic=False):
    f = _font(px, italic)
    l, t, r, b = f.getbbox(text)
    m = Image.new('L', (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(m).text((pad - l, pad - t), text, font=f, fill=255)
    return m


def _fit(text, px, maxw):
    while px > 12 and _font(px).getbbox(text)[2] > maxw:
        px -= 2
    # by lozanovvv_
    return px


def _put(base, img, cx, y):
    base.paste(img, (int(cx - img.width / 2), int(y)), img)
    return y + img.height - 60


def _glow(m, col, radius, k=1.2):
    a = m.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * k)))
    # by lozanovvv_
    g = Image.new('RGBA', m.size, col + (0,))
    g.putalpha(a)
    return g


def _neon(text, px, hue):
    m = _mask(text, px)
    w, h = m.size
    col = hue_rgb(hue)
    tint = tuple(int(c + (255 - c) * 0.5) for c in col)
    # by lozanovvv_
    fill = Image.new('RGBA', (w, h), col + (255,))
    d = ImageDraw.Draw(fill)
    step = max(4, px // 9)
    for yy in range(0, h, step * 2):
        d.rectangle([0, yy, w, yy + step - 1], fill=tint + (255,))
    out = _glow(m, col, 10)
    out.paste(fill, (0, 0), m)
    return out


def _white(text, px, shear=0.18, italic=True):
    m = _mask(text, px, italic=italic)
    # by lozanovvv_
    shear = 0 if italic else shear
    w, h = m.size
    m = m.transform(m.size, Image.AFFINE, (1, shear, -shear * h / 2, 0, 1, 0), Image.BICUBIC)
    out = _glow(m, (255, 255, 255), 9, 0.55)
    sh = Image.new('RGBA', m.size, (125, 129, 150, 255))
    out.paste(sh, (3, 4), m)
    out.paste(Image.new('RGBA', m.size, (255, 255, 255, 255)), (0, 0), m)
    return out


def make_preview(brand, server, promo, hue):
    img = Image.new('RGBA', (W, H), (13, 16, 26, 255))
    # by lozanovvv_
    d = ImageDraw.Draw(img)
    for yy in range(0, H, 24):
        for xx in range(0, W, 24):
            if (xx // 24 + yy // 24) % 2:
                d.rectangle([xx, yy, xx + 23, yy + 23], fill=(16, 19, 31, 255))
    glow = Image.new('RGBA', (W, H), hue_rgb(hue) + (0,))
    ga = Image.new('L', (W, H), 0)
    ImageDraw.Draw(ga).ellipse([60, 120, W - 60, H + 40], fill=46)
    glow.putalpha(ga.filter(ImageFilter.GaussianBlur(40)))
    img.paste(glow, (0, 0), glow)
    # by lozanovvv_
    brand, server, promo = (brand or 'RMRP'), (server or 'ТВЕРСКОЙ'), (promo or 'KLA4')
    maxw = W - 70
    y = 6
    y = _put(img, _white(brand, _fit(brand, 62, maxw)), W / 2, y)
    y = _put(img, _neon(server, _fit(server, 36, maxw), hue), W / 2, y + 2)
    y = _put(img, _white('ПРОМОКОД', 20, 0.18, False), W / 2, y + 12)
    _put(img, _neon(promo, _fit(promo, 70, maxw), hue), W / 2, y + 2)
    return img.convert('RGB')
