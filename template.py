# Загрузка шаблона заставки с Google Диска при первом запуске
import os
import re
import sys
import time
import urllib.request
import urllib.error
import http.cookiejar
import engine
import config

BASE = 'https://drive.usercontent.google.com/download'
NAME = 'template.mov'
MIN_SIZE = 20 * 1024 * 1024
# by lozanovvv_


def cache_dir():
    if sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support/PromoTool')
    elif os.name == 'nt':
        base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PromoTool')
    else:
        base = os.path.expanduser('~/.promotool')
    os.makedirs(base, exist_ok=True)
    return base


def local_path():
    bundled = engine.res('assets/' + NAME)
    if os.path.isfile(bundled):
        return bundled
    return os.path.join(cache_dir(), NAME)


def ready():
    p = local_path()
    # by lozanovvv_
    return os.path.isfile(p) and os.path.getsize(p) > MIN_SIZE


def drive_id():
    raw = os.environ.get('PROMOTOOL_TEMPLATE', '').strip()
    if not raw:
        f = os.path.join(cache_dir(), 'template_id.txt')
        if os.path.isfile(f):
            raw = open(f, encoding='utf-8').read().strip()
    raw = raw or config.TEMPLATE_URL.strip()
    m = re.search(r'/d/([\w-]{20,})', raw) or re.search(r'[?&]id=([\w-]{20,})', raw)
    # by lozanovvv_
    if m:
        return m.group(1)
    return raw if re.fullmatch(r'[\w-]{20,}', raw) else ''


def download(progress=None, stop=None):
    # progress(frac, text); возвращает путь к шаблону
    if ready():
        return local_path()
    fid = drive_id()
    if not fid:
        raise RuntimeError('Не указана ссылка на шаблон (config.py → TEMPLATE_URL)')
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [('User-Agent', 'Mozilla/5.0 PromoTool')]
    url = BASE + '?id=%s&export=download&confirm=t' % fid
    # by lozanovvv_
    dst = os.path.join(cache_dir(), NAME)
    part = dst + '.part'
    try:
        r = op.open(url, timeout=30)
        if 'text/html' in (r.headers.get('Content-Type') or ''):
            html = r.read().decode('utf-8', 'replace')
            m = re.search(r'name="uuid" value="([^"]+)"', html)
            if not m:
                raise RuntimeError('Диск не отдал файл: проверь, что доступ открыт «всем, у кого есть ссылка»')
            r = op.open(url + '&uuid=' + m.group(1), timeout=30)
        total = int(r.headers.get('Content-Length') or 0)
        got = 0
        t0 = time.time()
        with open(part, 'wb') as out:
            while True:
                if stop and stop():
                    raise RuntimeError('Отменено')
                # by lozanovvv_
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
                got += len(chunk)
                if progress:
                    sp = got / max(time.time() - t0, 0.1) / 1048576
                    txt = 'Скачиваю шаблон… %d / %d МБ (%.1f МБ/с)' % (got >> 20, total >> 20, sp) if total else 'Скачиваю шаблон… %d МБ' % (got >> 20)
                    progress(got / total if total else 0.0, txt)
        if got < MIN_SIZE:
            raise RuntimeError('Скачался не шаблон (%d байт). Проверь ссылку и доступ' % got)
        os.replace(part, dst)
    except urllib.error.URLError as e:
        raise RuntimeError('Нет интернета или Диск недоступен: %s' % e)
    finally:
        if os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass
    return dst
