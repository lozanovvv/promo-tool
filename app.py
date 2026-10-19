import os, sys, subprocess, tempfile, threading, argparse, colorsys
import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
from multiprocessing import freeze_support
import customtkinter as ctk
from PIL import ImageTk
import engine
import template
import mock

BG, PANEL, LINE, TXT, MUTED, ACC = '#0a0c14', '#11141f', '#262c4a', '#e9ecf7', '#8b93b0', '#4d8dff'
# by lozanovvv_
PRESETS = [('Синий', 222), ('Голубой', 195), ('Фиолетовый', 275), ('Розовый', 320),
           ('Красный', 355), ('Оригинал', 12), ('Жёлтый', 48), ('Зелёный', 140)]


def circle(hue, size=18):
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (size * 4, size * 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([8, 8, size * 4 - 8, size * 4 - 8], fill=mock.hue_rgb(hue) + (255,))
    return ctk.CTkImage(im, im, size=(size, size))


def label(master, text, **kw):
    return ctk.CTkLabel(master, text=text, anchor='w', **kw)


def section(master, text):
    return label(master, text, font=ctk.CTkFont(size=11, weight='bold'), text_color=MUTED)


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        # by lozanovvv_
        ctk.set_appearance_mode('dark')
        self.title('PromoTool')
        try:
            if os.name == 'nt':
                self.iconbitmap(engine.res('assets/icon.ico'))
        except Exception:
            pass
        self.geometry('1000x700')
        self.minsize(980, 680)
        self.hue = 222
        # by lozanovvv_
        self.src = template.local_path()
        self.loading = not template.ready()
        self.busy = False
        self.stop_flag = False
        self.star_path = None
        self.brand = tk.StringVar(value='RMRP')
        self.server = tk.StringVar(value='')
        self.promo = tk.StringVar(value='')
        self.mp4 = tk.BooleanVar(value=True)
        self._job = None
        # by lozanovvv_
        self.main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.rend = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.done = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        for f in (self.main, self.rend, self.done):
            f.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.build_main()
        self.build_render()
        self.build_done()
        self.main.tkraise()
        for v in (self.brand, self.server, self.promo):
            v.trace_add('write', lambda *a: self.schedule())
        # by lozanovvv_
        self.refresh()
        if self.loading:
            self.fetch_template()

    def bar(self, parent):
        b = ctk.CTkFrame(parent, fg_color='#0e111b', height=40, corner_radius=0)
        b.pack(side='bottom', fill='x')
        st = label(b, 'Готов к работе', text_color=MUTED, font=ctk.CTkFont(size=12))
        st.pack(side='left', padx=(20, 14))
        pb = ctk.CTkProgressBar(b, height=4, progress_color=ACC, fg_color='#1a1f35')
        # by lozanovvv_
        pb.set(0)
        pb.pack(side='left', fill='x', expand=True, pady=18)
        label(b, 'by lozanovvv_', text_color='#4a5272', font=ctk.CTkFont(size=10)).pack(side='left', padx=(14, 20))
        return st, pb

    def build_main(self):
        self.st_main, self.pb_main = self.bar(self.main)
        body = ctk.CTkFrame(self.main, fg_color=BG)
        body.pack(fill='both', expand=True, padx=20, pady=20)
        left = ctk.CTkFrame(body, fg_color=BG, width=408)
        # by lozanovvv_
        left.pack(side='left', fill='y')
        left.pack_propagate(False)
        section(left, '01 · ВИДЕО').pack(fill='x')
        card = ctk.CTkFrame(left, fg_color='#0f1424', border_color='#34407a', border_width=1, corner_radius=12)
        card.pack(fill='x', pady=(8, 18))
        info = ctk.CTkFrame(card, fg_color='transparent')
        info.pack(side='left', fill='x', expand=True, padx=14, pady=12)
        self.vname = label(info, 'Шаблон встроен ✓', font=ctk.CTkFont(size=14, weight='bold'), text_color=TXT)
        self.vname.pack(fill='x')
        self.vinfo = label(info, 'Ничего вставлять не нужно · можно выбрать своё', font=ctk.CTkFont(size=12), text_color=MUTED)
        # by lozanovvv_
        self.vinfo.pack(fill='x')
        ctk.CTkButton(card, text='Другое…', width=96, height=44, corner_radius=10, fg_color='#151b33',
                      hover_color='#1d2544', border_width=1, border_color='#2a3260', command=self.pick).pack(side='right', padx=12)
        section(left, '02 · ТЕКСТЫ').pack(fill='x')
        for cap, var, ph in (('Надпись сверху', self.brand, ''), ('Название сервера', self.server, 'Введи название'),
                             ('Промокод', self.promo, 'Введи промокод')):
            label(left, cap, font=ctk.CTkFont(size=12), text_color='#9aa2c0').pack(fill='x', pady=(8, 2))
            ctk.CTkEntry(left, textvariable=var, placeholder_text=ph, height=44, corner_radius=10, fg_color=PANEL, border_color=LINE,
                         text_color=TXT, font=ctk.CTkFont(size=15, weight='bold')).pack(fill='x')
        section(left, '03 · ЦВЕТ').pack(fill='x', pady=(18, 8))
        # by lozanovvv_
        grid = ctk.CTkFrame(left, fg_color=BG)
        grid.pack(fill='x')
        self.sw = []
        for i, (name, hue) in enumerate(PRESETS):
            b = ctk.CTkButton(grid, text=name, image=circle(hue), compound='left', width=94, height=44, corner_radius=10,
                              fg_color=PANEL, hover_color='#1a2038', border_width=2, border_color=LINE, text_color='#cfd6f3',
                              font=ctk.CTkFont(size=12), command=lambda h=hue: self.set_hue(h))
            b.grid(row=i // 4, column=i % 4, padx=3, pady=3, sticky='ew')
            self.sw.append((b, hue))
        for c in range(4):
            grid.grid_columnconfigure(c, weight=1)
        # by lozanovvv_
        ctk.CTkButton(grid, text='Свой цвет…', height=36, corner_radius=10, fg_color='transparent', border_width=1,
                      border_color=LINE, text_color=MUTED, hover_color='#1a2038', command=self.custom).grid(
            row=2, column=0, columnspan=4, padx=3, pady=(6, 0), sticky='ew')
        right = ctk.CTkFrame(body, fg_color=BG)
        right.pack(side='left', fill='both', expand=True, padx=(20, 0))
        section(right, 'ПРЕДПРОСМОТР').pack(fill='x')
        stage = ctk.CTkFrame(right, fg_color='#0d101a', border_color='#232842', border_width=1, corner_radius=14)
        stage.pack(fill='both', expand=True, pady=(8, 14))
        self.pv = ctk.CTkLabel(stage, text='')
        self.pv.pack(expand=True)
        # by lozanovvv_
        srow = ctk.CTkFrame(right, fg_color=BG)
        srow.pack(fill='x', pady=(0, 12))
        label(srow, 'ЗВЕЗДА', font=ctk.CTkFont(size=11, weight='bold'), text_color=MUTED).pack(side='left', padx=(0, 10))
        self.star_mode = ctk.CTkSegmentedButton(srow, values=['Оригинал', 'Убрать', 'Своя картинка'], command=self.star_pick,
                                                fg_color=PANEL, selected_color=ACC, unselected_color=PANEL)
        self.star_mode.set('Оригинал')
        self.star_mode.pack(side='left', fill='x', expand=True)
        row = ctk.CTkFrame(right, fg_color=BG)
        row.pack(fill='x')
        ctk.CTkCheckBox(row, text='Лёгкое превью .mp4', variable=self.mp4, text_color=MUTED, fg_color=ACC,
                        font=ctk.CTkFont(size=13)).pack(side='left')
        ctk.CTkButton(row, text='Сделать видео', height=44, width=150, corner_radius=10, fg_color=ACC, hover_color='#6a5cff',
                      font=ctk.CTkFont(size=14, weight='bold'), command=self.do_run).pack(side='right')
        ctk.CTkButton(row, text='Предпросмотр', height=44, width=130, corner_radius=10, fg_color='#151b33',
                      hover_color='#1d2544', border_width=1, border_color='#2a3260', font=ctk.CTkFont(size=14),
                      command=self.do_preview).pack(side='right', padx=10)
        self.set_hue(222)

    def build_render(self):
        self.st_rend, self.pb_rend = self.bar(self.rend)
        # by lozanovvv_
        mid = ctk.CTkFrame(self.rend, fg_color=BG)
        mid.pack(expand=True)
        self.ring = tk.Canvas(mid, width=200, height=200, bg=BG, highlightthickness=0)
        self.ring.pack(pady=(0, 24))
        self.ring.create_oval(14, 14, 186, 186, outline='#1a1f35', width=12)
        self.arc = self.ring.create_arc(14, 14, 186, 186, start=90, extent=0, style='arc', outline=ACC, width=12)
        self.pct = self.ring.create_text(100, 92, text='0%', fill=TXT, font=('Helvetica', 40, 'bold'))
        self.sub = self.ring.create_text(100, 130, text='', fill=MUTED, font=('Helvetica', 11))
        self.stages = []
        for t in ('Распаковка кадров', 'Замена текстов и цвета', 'Сборка .mov и превью .mp4'):
            f = ctk.CTkFrame(mid, fg_color='#0d101a', border_color='#1a1f35', border_width=1, corner_radius=12, width=520, height=46)
            # by lozanovvv_
            f.pack(pady=4)
            f.pack_propagate(False)
            lb = label(f, '○   ' + t, font=ctk.CTkFont(size=14), text_color=MUTED)
            lb.place(x=16, rely=0.5, anchor='w')
            self.stages.append((f, lb, t))
        ctk.CTkButton(mid, text='Отменить', height=44, width=140, corner_radius=10, fg_color='#1a1322', hover_color='#2a1a30',
                      border_width=1, border_color='#3a2a4a', text_color='#ff9aa8', command=self.cancel).pack(pady=(20, 0))

    def build_done(self):
        self.bar(self.done)
        # by lozanovvv_
        mid = ctk.CTkFrame(self.done, fg_color=BG)
        mid.pack(expand=True)
        ctk.CTkLabel(mid, text='✓', width=96, height=96, corner_radius=48, fg_color='#0d1f1a', text_color='#3ddc97',
                     font=ctk.CTkFont(size=44, weight='bold')).pack()
        ctk.CTkLabel(mid, text='Готово', font=ctk.CTkFont(size=30, weight='bold'), text_color=TXT).pack(pady=(18, 4))
        self.done_info = ctk.CTkLabel(mid, text='', text_color=MUTED, justify='center', font=ctk.CTkFont(size=13))
        self.done_info.pack(pady=(0, 20))
        row = ctk.CTkFrame(mid, fg_color=BG)
        row.pack()
        ctk.CTkButton(row, text='Показать в папке', height=44, width=170, corner_radius=10, fg_color=ACC,
                      font=ctk.CTkFont(size=14, weight='bold'), command=self.reveal).pack(side='left', padx=6)
        ctk.CTkButton(row, text='Сделать ещё', height=44, width=140, corner_radius=10, fg_color='#151b33', border_width=1,
                      border_color='#2a3260', command=lambda: self.main.tkraise()).pack(side='left', padx=6)

    def schedule(self):
        if self._job:
            self.after_cancel(self._job)
        # by lozanovvv_
        self._job = self.after(120, self.refresh)

    def refresh(self):
        img = mock.make_preview(self.brand.get().upper(), self.server.get().upper(), self.promo.get().upper(), self.hue)
        self._pv = ctk.CTkImage(img, img, size=img.size)
        self.pv.configure(image=self._pv)

    def set_hue(self, h):
        self.hue = h
        for b, hue in self.sw:
            b.configure(border_color=('#7aa7ff' if hue == h else LINE))
        # by lozanovvv_
        self.schedule()

    def star_pick(self, v):
        self.star_path = None
        if v == 'Своя картинка':
            p = filedialog.askopenfilename(title='PNG со звездой/эмблемой', filetypes=[('Картинки', '*.png *.webp *.jpg'), ('Все', '*.*')])
            if p:
                self.star_path = p
                self.star_mode.configure(values=['Оригинал', 'Убрать', os.path.basename(p)[:18]])
                self.star_mode.set(os.path.basename(p)[:18])
            else:
                self.star_mode.set('Оригинал')

    def custom(self):
        c = colorchooser.askcolor(title='Выбери цвет')
        # by lozanovvv_
        if c and c[0]:
            r, g, b = [v / 255 for v in c[0]]
            self.set_hue(colorsys.rgb_to_hsv(r, g, b)[0] * 360)

    def fetch_template(self):
        self.vname.configure(text='Загрузка шаблона…')
        self.vinfo.configure(text='Нужен интернет, это один раз')

        def prog(frac, text):
            self.after(0, lambda: (self.st_main.configure(text=text), self.pb_main.set(frac)))

        def job():
            try:
                p = template.download(prog)
                # by lozanovvv_
                self.src = p
                self.loading = False
                self.after(0, lambda: (self.vname.configure(text='Шаблон готов ✓'), self.vinfo.configure(text='Ничего вставлять не нужно · можно выбрать своё'),
                                       self.st_main.configure(text='Готов к работе'), self.pb_main.set(0)))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: (self.vname.configure(text='Шаблон не загружен'), self.vinfo.configure(text=msg[:70]),
                                       self.st_main.configure(text='Выбери видео вручную или перезапусти')))
        threading.Thread(target=job, daemon=True).start()

    def pick(self):
        p = filedialog.askopenfilename(filetypes=[('Видео', '*.mov *.mp4'), ('Все файлы', '*.*')])
        # by lozanovvv_
        if p:
            self.src = p
            self.loading = False
            self.vname.configure(text=os.path.basename(p))
            try:
                fps, size = engine.probe(p)
                self.vinfo.configure(text='%dx%d · %g fps' % (size[0], size[1], fps))
            except Exception:
                self.vinfo.configure(text=p)

    def opts(self):
        b, sv = self.brand.get().strip().upper(), self.server.get().strip().upper()
        # by lozanovvv_
        m = self.star_mode.get()
        star = 'none' if m == 'Убрать' else (self.star_path if m not in ('Оригинал', 'Своя картинка') else None)
        return dict(hue=self.hue, star=star, promo=self.promo.get().strip().upper(),
                    brand=b if b and b != 'RMRP' else None, server=sv if sv and sv != 'ТВЕРСКОЙ' else None)

    def check(self):
        if self.loading:
            messagebox.showinfo('Подожди', 'Шаблон ещё скачивается')
            return False
        if not os.path.isfile(self.src):
            messagebox.showwarning('Нет файла', 'Шаблон не найден, выбери видео вручную')
            # by lozanovvv_
            return False
        return not self.busy

    def do_preview(self):
        if not self.check():
            return
        self.busy = True
        self.st_main.configure(text='Делаю предпросмотр…')

        def job():
            try:
                with tempfile.TemporaryDirectory() as w:
                    img = engine.preview(self.src, self.opts(), w)
                # by lozanovvv_
                self.after(0, lambda: self.show(img))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror('Ошибка', str(e)))
            self.busy = False
            self.after(0, lambda: self.st_main.configure(text='Готов к работе'))
        threading.Thread(target=job, daemon=True).start()

    def show(self, img):
        t = tk.Toplevel(self)
        t.title('Предпросмотр кадров')
        # by lozanovvv_
        im = img.copy()
        im.thumbnail((900, 700))
        ph = ImageTk.PhotoImage(im)
        lb = tk.Label(t, image=ph)
        lb.image = ph
        lb.pack()

    def progress(self, v):
        self.after(0, lambda: self.apply_progress(*v))

    def apply_progress(self, text, frac):
        self.ring.itemconfigure(self.arc, extent=-360 * min(frac, 0.9999))
        # by lozanovvv_
        self.ring.itemconfigure(self.pct, text='%d%%' % int(frac * 100))
        self.ring.itemconfigure(self.sub, text=text if text.startswith('Обработка') else '')
        self.pb_rend.set(frac)
        self.st_rend.configure(text=text)
        act = 0 if text.startswith('Распаковка') else (1 if text.startswith('Обработка') else 2)
        for i, (f, lb, t) in enumerate(self.stages):
            if i < act or text == 'Готово':
                lb.configure(text='✓   ' + t, text_color='#3ddc97')
                f.configure(fg_color='#0d101a', border_color='#1a1f35')
            elif i == act:
                lb.configure(text='◐   ' + t, text_color=TXT)
                # by lozanovvv_
                f.configure(fg_color='#121a33', border_color='#34407a')
            else:
                lb.configure(text='○   ' + t, text_color=MUTED)
                f.configure(fg_color='#0d101a', border_color='#1a1f35')

    def cancel(self):
        self.stop_flag = True

    def do_run(self):
        if not self.check():
            return
        # by lozanovvv_
        miss = [n for n, v in (('название сервера', self.server), ('промокод', self.promo)) if not v.get().strip()]
        if miss and not messagebox.askyesno('Не всё заполнено', 'Не заполнено: ' + ', '.join(miss) + '.\nВ видео останется оригинальный текст. Продолжить?'):
            return
        out = filedialog.asksaveasfilename(defaultextension='.mov', initialfile=(self.promo.get() or 'promo') + '.mov',
                                           filetypes=[('QuickTime MOV', '*.mov')])
        if not out:
            return
        self.busy, self.stop_flag, self.out = True, False, out
        self.apply_progress('Распаковка кадров…', 0.0)
        self.rend.tkraise()

        def job():
            try:
                engine.convert(self.src, out, self.opts(), self.progress, self.mp4.get(), stop=lambda: self.stop_flag)
                # by lozanovvv_
                self.after(0, self.finish)
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: (self.main.tkraise(), messagebox.showinfo('Остановлено', msg) if msg == 'Отменено' else messagebox.showerror('Ошибка', msg)))
            self.busy = False
        threading.Thread(target=job, daemon=True).start()

    def finish(self):
        mb = os.path.getsize(self.out) / 1048576
        self.done_info.configure(text='%s\n%.0f МБ · ProRes 4444 + альфа' % (self.out, mb))
        # by lozanovvv_
        self.done.tkraise()

    def reveal(self):
        d = os.path.dirname(self.out)
        if sys.platform == 'darwin':
            subprocess.run(['open', '-R', self.out])
        elif os.name == 'nt':
            subprocess.run(['explorer', '/select,', os.path.normpath(self.out)])
        else:
            subprocess.run(['xdg-open', d])


def cli():
    ap = argparse.ArgumentParser()
    # by lozanovvv_
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--promo', default='')
    ap.add_argument('--server', default='ТВЕРСКОЙ')
    ap.add_argument('--brand', default='RMRP')
    ap.add_argument('--hue', type=float, default=222)
    ap.add_argument('--star', default=None, help='none или путь к PNG')
    a = ap.parse_args()
    engine.convert(a.src, a.out, dict(hue=a.hue, star=a.star, promo=a.promo.upper(), server=a.server.upper() if a.server != 'ТВЕРСКОЙ' else None,
                                      brand=a.brand.upper() if a.brand != 'RMRP' else None), print, False)


if __name__ == '__main__':
    freeze_support()
    # by lozanovvv_
    if len(sys.argv) > 1:
        cli()
    else:
        App().mainloop()
