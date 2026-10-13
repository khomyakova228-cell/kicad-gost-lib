#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор библиотеки УГО по ЕСКД для KiCad 10 (формат читается KiCad 7–10).

ГОСТ 2.743-91  — УГО элементов цифровой техники / ИМС (основное и доп. поля,
                 группы выводов, инверсия выводов кружком, шаг выводов);
ГОСТ 2.759-82  — ОУ: квалифицирующий символ «▷∞» в основном поле;
ГОСТ 2.755-87  — соединители в табличной форме;
ГОСТ 2.721-74  — «Заземление, общее обозначение» (табл. 6б, п. 1),
                 толщина линий УГО = толщине линий связи (табл. 7, прим.).

Запуск:  python3 gen_gost_lib.py [--pitch 5.08|2.54] [--legacy] [-o GOST_UGO.kicad_sym]
  --pitch   шаг выводов, мм. По ГОСТ 2.743 — не менее 5 мм, поэтому 5.08 (2 клетки сетки KiCad).
            2.54 — «компактный» вариант, если на листе не хватает места.
  --legacy  формат KiCad 7 (version 20220914); по умолчанию — KiCad 9/10 (20241209).
"""
import argparse
import math

# ---------------------------------------------------------------- параметры
G = 2.54            # сетка KiCad
LINE_W = 0.254      # толщина линий УГО (= линии связи)
TXT_NAME = 2.5      # высота шрифта меток выводов (ГОСТ 2.304: 2,5 мм)
TXT_NUM = 1.8       # номера выводов
TXT_FUNC = 3.5      # функциональное обозначение в основном поле
TXT_REF = 2.5       # позиционное обозначение / наименование
PIN_LEN = 5.08      # длина линии вывода

ARGS = None


def snap(v, step=G):
    return round(v / step) * step


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def hide_tok():
    return "hide" if ARGS.legacy else "(hide yes)"


def font(h, extra=""):
    return f'(effects (font (size {fmt(h)} {fmt(h)})){extra})'


def text_width(s, h=TXT_NAME):
    """Грубая оценка ширины строки шрифтом KiCad (newstroke)."""
    return len(s) * 0.92 * h


# ---------------------------------------------------------------- примитивы
def rect(x1, y1, x2, y2):
    return (f"(rectangle (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) "
            f"(stroke (width {LINE_W}) (type default)) (fill (type none)))")


def line(*pts):
    p = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in pts)
    return f"(polyline (pts {p}) (stroke (width {LINE_W}) (type default)) (fill (type none)))"


def circle(x, y, r):
    return (f"(circle (center {fmt(x)} {fmt(y)}) (radius {fmt(r)}) "
            f"(stroke (width {LINE_W}) (type default)) (fill (type none)))")


def text(s, x, y, h, justify=""):
    j = f" (justify {justify})" if justify else ""
    return f'(text "{esc(s)}" (at {fmt(x)} {fmt(y)} 0) (effects (font (size {fmt(h)} {fmt(h)})){j}))'


def pin(num, name, etype, x, y, ang, shape="line", hidden=False, length=PIN_LEN, empty="~"):
    h = f" {hide_tok()}" if hidden else ""
    nm = name if name else empty
    return (f'(pin {etype} {shape} (at {fmt(x)} {fmt(y)} {ang}) (length {fmt(length)}){h} '
            f'(name "{esc(nm)}" {font(TXT_NAME)}) (number "{esc(num)}" {font(TXT_NUM)}))')


def prop(key, val, x=0, y=0, hidden=True, h=TXT_REF, justify=""):
    j = f" (justify {justify})" if justify else ""
    hd = f" {hide_tok()}" if hidden else ""
    return (f'(property "{esc(key)}" "{esc(val)}" (at {fmt(x)} {fmt(y)} 0) '
            f'(effects (font (size {fmt(h)} {fmt(h)})){j}{hd}))')


# ---------------------------------------------------------------- символ
class Symbol:
    def __init__(self, name, ref, value, footprint="", datasheet="", descr="",
                 keywords="", mfr="", mpn="", power=False):
        self.name, self.ref, self.value = name, ref, value
        self.footprint, self.datasheet, self.descr = footprint, datasheet, descr
        self.keywords, self.mfr, self.mpn, self.power = keywords, mfr, mpn, power
        self.graphics, self.pins = [], []
        self.ref_at = (0, 0, "")
        self.val_at = (0, 0, "")
        self.hide_pin_numbers = False
        self.hide_pin_names = False
        self.name_offset = 0.762
        self.value_hidden = False
        self.extra_props = []
        self.ref_hidden = False

    def render(self):
        o = [f'  (symbol "{esc(self.name)}"']
        if self.power:
            o.append("    (power)")
        if self.hide_pin_numbers:
            o.append(f"    (pin_numbers {hide_tok()})")
        if self.hide_pin_names:
            o.append(f"    (pin_names (offset {fmt(self.name_offset)}) {hide_tok()})")
        else:
            o.append(f"    (pin_names (offset {fmt(self.name_offset)}))")
        if not ARGS.legacy:
            o.append("    (exclude_from_sim no)")
        o.append(f"    (in_bom {'no' if self.power else 'yes'}) (on_board {'no' if self.power else 'yes'})")
        rx, ry, rj = self.ref_at
        vx, vy, vj = self.val_at
        o.append("    " + prop("Reference", self.ref, rx, ry, self.ref_hidden, justify=rj))
        o.append("    " + prop("Value", self.value, vx, vy, self.value_hidden, justify=vj))
        o.append("    " + prop("Footprint", self.footprint, 0, vy - 2.54, h=1.27))
        o.append("    " + prop("Datasheet", self.datasheet, 0, vy - 5.08, h=1.27))
        o.append("    " + prop("Description", self.descr, 0, vy - 7.62, h=1.27))
        if self.mfr:
            o.append("    " + prop("Manufacturer", self.mfr, 0, vy - 10.16, h=1.27))
        if self.mpn:
            o.append("    " + prop("Manufacturer_Part_Number", self.mpn, 0, vy - 12.7, h=1.27))
        for ep in self.extra_props:
            o.append("    " + ep)
        if self.keywords:
            o.append("    " + prop("ki_keywords", self.keywords, h=1.27))
        if ARGS.legacy:
            o.append("    " + prop("ki_description", self.descr, h=1.27))
        o.append(f'    (symbol "{esc(self.name)}_0_1"')
        for g in self.graphics:
            o.append("      " + g)
        o.append("    )")
        o.append(f'    (symbol "{esc(self.name)}_1_1"')
        for p in self.pins:
            o.append("      " + p)
        o.append("    )")
        if not ARGS.legacy:
            o.append("    (embedded_fonts no)")
        o.append("  )")
        return "\n".join(o)


# ------------------------------------------------- ИМС по ГОСТ 2.743 (поля + группы)
# Вывод: (номер, метка, тип, форма) ; форма "inverted" — указатель инверсии (кружок).
def P(num, name, etype="bidirectional", shape="line"):
    return (num, name, etype, shape)


def field_width(groups, minimum=2 * G):
    w = minimum
    for g in groups:
        for _, nm, _, _ in g:
            w = max(w, text_width(nm) + 1.6)
    return math.ceil(w / G) * G


def build_ic(sym, left, right, func="", main_w=None, pitch=None, hidden_pins=(),
             right_field=True, left_field=True, top_rows=1, func_draw=None):
    """
    left/right — списки групп выводов. Между группами — пустой шаг и разделительная
    линия в дополнительном поле (ГОСТ 2.743, п. 2.3 — разделение групп).
    """
    p = pitch or ARGS.pitch
    wl = field_width(left) if left_field else 0
    wr = field_width(right) if right_field else 0
    wm = main_w if main_w else max(4 * G, math.ceil((text_width(func, TXT_FUNC) + 2.54) / G) * G)

    def rows(groups):
        n = sum(len(g) for g in groups) + max(0, len(groups) - 1)
        return n

    n = max(rows(left), rows(right))
    top = 0.0
    first = -top_rows * p                      # первая строка выводов
    bottom = snap(first - (n - 1) * p - p)     # нижний край: шаг под последней
    total = wl + wm + wr
    x0 = snap(-total / 2)
    xl, xm1, xm2, xr = x0, x0 + wl, x0 + wl + wm, x0 + total

    g = sym.graphics
    g.append(rect(xl, top, xr, bottom))
    if left_field:
        g.append(line((xm1, top), (xm1, bottom)))
    if right_field:
        g.append(line((xm2, top), (xm2, bottom)))

    # смещаем так, чтобы разделитель групп был ровно посередине пустого шага
    place_groups(sym, left, "L", xl, xm1, first, p, left_field)
    place_groups(sym, right, "R", xr, xm2, first, p, right_field)

    if func:
        g.append(text(func, (xm1 + xm2) / 2, top - p / 2 - 1.0, TXT_FUNC))
    if func_draw:
        func_draw(sym, xm1, xm2, top, p)

    for hp in hidden_pins:
        num, nm, et = hp
        # неподключаемые выводы — скрыты ВНУТРИ основного поля (длина 0), чтобы
        # не совпадать с точкой подключения других выводов
        sym.pins.append(pin(num, nm, et, snap((xm1 + xm2) / 2), snap((top + bottom) / 2),
                            0, hidden=True, length=0))

    sym.ref_at = (snap((xm1 + xm2) / 2), top + 2.54, "")
    sym.val_at = (snap((xm1 + xm2) / 2), bottom - 2.54, "")
    return (xl, xm1, xm2, xr, top, bottom)


def place_groups(sym, groups, side, xedge, xinner, first, p, has_field):
    y = first
    for gi, grp in enumerate(groups):
        if gi > 0:
            # пустой шаг между группами; разделительная линия — посередине между
            # последним выводом предыдущей группы и первым выводом следующей
            ysep = y + p / 2 - p / 2  # = y (центр пустой строки)
            if has_field:
                sym.graphics.append(line((xedge, ysep), (xinner, ysep)))
            y -= p
        for num, nm, et, sh in grp:
            if side == "L":
                sym.pins.append(pin(num, nm, et, xedge - PIN_LEN, y, 0, sh))
            else:
                sym.pins.append(pin(num, nm, et, xedge + PIN_LEN, y, 180, sh))
            y -= p


# ---------------------------------------------------------------- компоненты
def sym_opa340():
    """ОУ OPA340P (DIP-8): ГОСТ 2.759 — основное поле с «▷∞», доп. поле входов слева,
    инверсный вход — кружком; выводы питания отдельной группой (ГОСТ 2.743)."""
    s = Symbol("OPA340P", "DA", "OPA340P",
               footprint="GOST_FP:DIP-8_W7.62mm",
               datasheet="https://www.ti.com/lit/ds/symlink/opa340.pdf",
               descr="ОУ rail-to-rail, однополярное питание 2,7…5,5 В, DIP-8",
               keywords="ОУ opamp rail-to-rail CMOS", mfr="Texas Instruments", mpn="OPA340PA")
    p = ARGS.pitch
    wl = 3 * G                     # доп. поле: метки «+U», «−U»
    wm = 4 * G if p > 3 else 4 * G
    x0 = -snap((wl + wm) / 2)
    xl, xm, xr = x0, x0 + wl, x0 + wl + wm
    top = 0
    y_in_p, y_in_n = -p, -2 * p
    y_sep = -3 * p
    y_vp, y_vn = -4 * p, -5 * p
    bottom = -6 * p
    g = s.graphics
    g.append(rect(xl, top, xr, bottom))
    g.append(line((xm, top), (xm, bottom)))
    g.append(line((xl, y_sep), (xm, y_sep)))
    # «▷∞» — треугольник и знак бесконечности (две окружности), чтобы не зависеть от шрифта
    tx, ty = xm + 1.6, top - 1.0
    th = 3.0
    g.append(line((tx, ty), (tx + th * 0.866, ty - th / 2), (tx, ty - th), (tx, ty)))
    r = 0.65
    cx = tx + th * 0.866 + 1.0 + r
    cy = ty - th / 2
    g.append(circle(cx, cy, r))
    g.append(circle(cx + 2 * r, cy, r))
    s.pins += [
        pin("3", "", "input", xl - PIN_LEN, y_in_p, 0),
        pin("2", "", "input", xl - PIN_LEN, y_in_n, 0, "inverted"),
        pin("7", "+U", "power_in", xl - PIN_LEN, y_vp, 0),
        pin("4", "-U", "power_in", xl - PIN_LEN, y_vn, 0),
        pin("6", "", "output", xr + PIN_LEN, snap((y_in_p + y_in_n) / 2), 180),
        pin("1", "NC", "no_connect", snap((xm + xr) / 2), -5 * p, 0, hidden=True, length=0),
        pin("5", "NC", "no_connect", snap((xm + xr) / 2), -5 * p, 0, hidden=True, length=0),
        pin("8", "NC", "no_connect", snap((xm + xr) / 2), -5 * p, 0, hidden=True, length=0),
    ]
    s.ref_at = (snap((xm + xr) / 2), top + 2.54, "")
    s.val_at = (snap((xm + xr) / 2), bottom - 2.54, "")
    return s


def sym_kr590kn2():
    s = Symbol("KR590KN2", "DA", "КР590КН2",
               footprint="GOST_FP:DIP-16_W7.62mm",
               datasheet="",
               descr="Четырёхканальный аналоговый ключ КР590КН2, DIP-16",
               keywords="ключ коммутатор switch КН2", mfr="", mpn="КР590КН2")
    left = [
        [P("3", "D1", "input"), P("4", "D2", "input"), P("12", "D3", "input"), P("13", "D4", "input")],
        [P("2", "IN1", "passive"), P("5", "IN2", "passive"), P("11", "IN3", "passive"), P("14", "IN4", "passive")],
    ]
    right = [
        [P("1", "OUT1", "passive"), P("6", "OUT2", "passive"), P("10", "OUT3", "passive"), P("15", "OUT4", "passive")],
        [P("8", "+U", "power_in"), P("16", "-U", "power_in"), P("7", "0V", "power_in")],
    ]
    build_ic(s, left, right, func="SW", hidden_pins=[("9", "NC", "no_connect")])
    return s


def sym_lm1117():
    s = Symbol("LM1117MP-ADJ", "DA", "LM1117MP-ADJ",
               footprint="GOST_FP:SOT-223-3_TabPin2",
               datasheet="https://www.ti.com/lit/ds/symlink/lm1117.pdf",
               descr="Линейный стабилизатор LDO 800 мА, регулируемый 1,25…13,8 В, SOT-223",
               keywords="стабилизатор LDO regulator adjustable", mfr="Texas Instruments",
               mpn="LM1117MPX-ADJ/NOPB")
    left = [[P("3", "IN", "power_in")], [P("1", "ADJ", "input")]]
    right = [[P("2", "OUT", "power_out")]]
    build_ic(s, left, right, func="", main_w=4 * G)
    return s


def sym_stm32():
    s = Symbol("STM32F030C8Tx", "DD", "STM32F030C8T6",
               footprint="GOST_FP:LQFP-48_7x7mm_P0.5mm",
               datasheet="https://www.st.com/resource/en/datasheet/stm32f030c8.pdf",
               descr="МК ARM Cortex-M0, 64 КБ Flash, 8 КБ RAM, 48 МГц, LQFP-48",
               keywords="МК MCU STM32 Cortex-M0", mfr="STMicroelectronics", mpn="STM32F030C8T6")
    bi = "bidirectional"
    left = [
        [P("7", "RST", "input", "inverted"), P("44", "BOOT0", "input")],
        [P("5", "PF0", bi), P("6", "PF1", bi), P("35", "PF6", bi), P("36", "PF7", bi)],
        [P("2", "PC13", bi), P("3", "PC14", bi), P("4", "PC15", bi)],
        [P(str(n), f"PB{i}", bi) for i, n in zip(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            [18, 19, 20, 39, 40, 41, 42, 43, 45, 46, 21, 22, 25, 26, 27, 28])],
    ]
    right = [
        [P(str(n), f"PA{i}", bi) for i, n in zip(
            range(16), [10, 11, 12, 13, 14, 15, 16, 17, 29, 30, 31, 32, 33, 34, 37, 38])],
        [P("1", "VDD", "power_in"), P("24", "VDD", "power_in"), P("48", "VDD", "power_in"),
         P("9", "VDDA", "power_in"), P("23", "VSS", "power_in"), P("47", "VSS", "power_in"),
         P("8", "VSSA", "power_in")],
    ]
    build_ic(s, left, right, func="MCU")
    return s


def sym_ft232rl():
    s = Symbol("FT232RL", "DD", "FT232RL",
               footprint="GOST_FP:SSOP-28_5.3x10.2mm_P0.65mm",
               datasheet="https://ftdichip.com/wp-content/uploads/2020/08/DS_FT232R.pdf",
               descr="Преобразователь интерфейса USB–UART, SSOP-28",
               keywords="USB UART FTDI преобразователь", mfr="FTDI", mpn="FT232RL-REEL")
    left = [
        [P("15", "USBDP", "bidirectional"), P("16", "USBDM", "bidirectional")],
        [P("5", "RXD", "input"), P("11", "CTS", "input", "inverted"), P("9", "DSR", "input", "inverted"),
         P("10", "DCD", "input", "inverted"), P("6", "RI", "input", "inverted")],
        [P("19", "RST", "input", "inverted"), P("27", "OSCI", "input"), P("26", "TEST", "input")],
    ]
    right = [
        [P("1", "TXD", "output"), P("3", "RTS", "output", "inverted"), P("2", "DTR", "output", "inverted")],
        [P("23", "CBUS0", "bidirectional"), P("22", "CBUS1", "bidirectional"),
         P("13", "CBUS2", "bidirectional"), P("14", "CBUS3", "bidirectional"),
         P("12", "CBUS4", "bidirectional")],
        [P("28", "OSCO", "output")],
        [P("20", "VCC", "power_in"), P("4", "VCCIO", "power_in"), P("17", "3V3OUT", "power_out"),
         P("7", "GND", "power_in"), P("18", "GND", "power_in"), P("21", "GND", "power_in"),
         P("25", "AGND", "power_in")],
    ]
    build_ic(s, left, right, func="USB/UART",
             hidden_pins=[("8", "NC", "no_connect"), ("24", "NC", "no_connect")])
    return s


def sym_conn(n, nets=None):
    """Соединитель в табличной форме по ГОСТ 2.755 / ГОСТ 2.702:
    таблица «Конт. | Цепь», выводы справа против строк.
    Наименование цепи — поле экземпляра «Цепь<N>», редактируется в свойствах символа."""
    nets = nets or [""] * n
    s = Symbol(f"Conn_1x{n:02d}", "X", f"Conn_1x{n:02d}",
               footprint=f"GOST_FP:PinHeader_1x{n:02d}_P2.54mm_Vertical",
               descr=f"Соединитель {n}-конт., табличная форма по ГОСТ 2.755 "
                     f"(поз. обозначение: XP — вилка, XS — розетка). "
                     f"Цепи задаются в полях Цепь1…Цепь{n}",
               keywords="разъём соединитель вилка розетка connector")
    RH = 5.08                       # высота строки таблицы
    w1, w2 = 12.7, 20.32            # столбцы «Конт.» и «Цепь»
    xr = 0.0
    xm = xr - w2
    xl = xm - w1
    top = RH / 2                    # шапка: от +2,54 до −2,54; строки — центры на −5,08·i
    bottom = top - (n + 1) * RH
    g = s.graphics
    g.append(rect(xl, top, xr, bottom))
    g.append(line((xm, top), (xm, bottom)))
    for i in range(1, n + 1):
        g.append(line((xl, top - i * RH), (xr, top - i * RH)))
    g.append(text("Конт.", (xl + xm) / 2, 0, TXT_NAME))
    g.append(text("Цепь", (xm + xr) / 2, 0, TXT_NAME))
    for i in range(n):
        y = -(i + 1) * RH
        g.append(text(str(i + 1), (xl + xm) / 2, y, TXT_NAME))
        s.pins.append(pin(str(i + 1), "", "passive", xr + PIN_LEN, y, 180, empty=""))
        s.extra_props.append(prop(f"Цепь{i + 1}", nets[i], (xm + xr) / 2, y,
                                  hidden=False, h=TXT_NAME))
    s.hide_pin_numbers = True
    s.hide_pin_names = True
    s.ref_at = (xl, top + 2.54, "left")
    s.val_at = ((xl + xr) / 2, bottom - 2.54, "")
    s.value_hidden = True
    return s


def dline(*pts):
    """Штриховая линия — линия механической связи (ГОСТ 2.721)."""
    p = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in pts)
    return f"(polyline (pts {p}) (stroke (width {LINE_W}) (type dash)) (fill (type none)))"


def sym_button():
    """Выключатель кнопочный нажимной с замыкающим контактом (ГОСТ 2.755-87,
    привод — ГОСТ 2.721-74). Выводы в тех же точках, что у штатного Switch:SW_Push
    (±5,08 мм), — замена не рвёт провода. Поз. обозначение по ГОСТ 2.710 — SB."""
    s = Symbol("SW_Push_NO", "SB", "SW_Push_NO", footprint="GOST_FP:SW_PUSH_6mm",
               descr="Выключатель кнопочный нажимной, замыкающий контакт, самовозврат (ГОСТ 2.755)",
               keywords="кнопка выключатель кнопочный SB push button switch")
    g = s.graphics
    ang = math.radians(30)
    L = 9.3
    x0, y0 = -3.81, 0.0                       # шарнир подвижного контакта
    x1, y1 = x0 + L * math.cos(ang), y0 + L * math.sin(ang)
    g.append(line((x0, y0), (x1, y1)))        # подвижный контакт под 30°
    # механическая связь от середины контакта к приводу
    ys = (0 - x0) / (x1 - x0) * (y1 - y0)
    g.append(dline((0, ys), (0, 6.35)))
    # нажимной привод
    g.append(line((-1.905, 5.588), (-1.905, 6.35), (1.905, 6.35), (1.905, 5.588)))
    s.pins += [
        pin("1", "", "passive", -5.08, 0, 0, length=1.27, empty=""),
        pin("2", "", "passive", 5.08, 0, 180, length=1.27, empty=""),
    ]
    s.hide_pin_numbers = True
    s.hide_pin_names = True
    s.ref_at = (0, 8.89, "")
    s.val_at = (0, -2.54, "")
    s.value_hidden = True
    return s


# ------------------------------------------------- дискретные элементы (масштаб 1:2 к размерам ГОСТ)
# Выводы стоят в тех же точках и с теми же номерами, что у штатных символов KiCad
# (Device:R, Device:C, Device:R_Potentiometer, Device:LED, Diode:ZYxxx, Sensor_Optical:BPW34,
# Transistor_BJT:BD235, power:GND) — замена символа на схеме не рвёт провода.
THICK = 0.508


def wline(w, *pts):
    p = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in pts)
    return f"(polyline (pts {p}) (stroke (width {fmt(w)}) (type default)) (fill (type none)))"


def fpoly(*pts):
    p = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in pts + (pts[0],))
    return f"(polyline (pts {p}) (stroke (width 0.1) (type default)) (fill (type outline)))"


def arrow(sx, sy, ex, ey, head=0.75, half=0.3):
    """линия со сплошной стрелкой на конце (ex, ey)"""
    L = math.hypot(ex - sx, ey - sy)
    ux, uy = (ex - sx) / L, (ey - sy) / L
    nx, ny = -uy, ux
    bx, by = ex - head * ux, ey - head * uy
    return [line((sx, sy), (bx, by)),
            fpoly((ex, ey), (bx + half * nx, by + half * ny), (bx - half * nx, by - half * ny))]


def two_pin(s, x1, y1, a1, x2, y2, a2, length, n1="", n2=""):
    s.pins.append(pin("1", n1, "passive", x1, y1, a1, length=length, empty=""))
    s.pins.append(pin("2", n2, "passive", x2, y2, a2, length=length, empty=""))
    s.hide_pin_numbers = True
    s.hide_pin_names = True


def diode_body(g, x_apex, x_base, half=1.27, k_end=None, a_end=None):
    """треугольник 60° (вершина — катод) и черта катода"""
    g.append(line((x_base, half), (x_base, -half), (x_apex, 0), (x_base, half)))
    g.append(line((x_apex, half), (x_apex, -half)))
    if k_end is not None:
        g.append(line((k_end, 0), (x_apex, 0)))
    if a_end is not None:
        g.append(line((x_base, 0), (a_end, 0)))


def sym_r():
    """Резистор постоянный, ГОСТ 2.728 (10 × 4 мм -> 5,08 × 2,03)."""
    s = Symbol("R", "R", "R", footprint="GOST_FP:R_Axial_DIN0309_L9.0mm_D3.2mm_P2.54mm_Vertical",
               descr="Резистор постоянный (ГОСТ 2.728)", keywords="резистор resistor")
    s.graphics.append(rect(-1.016, 2.54, 1.016, -2.54))
    two_pin(s, 0, 3.81, 270, 0, -3.81, 90, 1.27)
    s.ref_at, s.val_at = (2.54, 1.27, "left"), (2.54, -1.27, "left")
    return s


def sym_r_trim():
    """Резистор подстроечный, ГОСТ 2.728: регулирующий элемент — отрезок с «Т» на конце."""
    s = Symbol("R_Trim", "R", "R_Trim", footprint="GOST_FP:Potentiometer_Bourns_3296W_Vertical",
               descr="Резистор подстроечный (ГОСТ 2.728)", keywords="резистор подстроечный trimmer")
    g = s.graphics
    g.append(rect(-1.016, 2.54, 1.016, -2.54))
    g.append(line((2.54, 0), (1.27, 0)))
    g.append(wline(LINE_W, (1.27, 0.762), (1.27, -0.762)))
    s.pins += [pin("1", "1", "passive", 0, 3.81, 270, length=1.27),
               pin("2", "2", "passive", 3.81, 0, 180, length=1.27),
               pin("3", "3", "passive", 0, -3.81, 90, length=1.27)]
    s.hide_pin_numbers = True
    s.hide_pin_names = True
    s.ref_at, s.val_at = (-2.54, 1.27, "right"), (-2.54, -1.27, "right")
    return s


def sym_c():
    """Конденсатор постоянной ёмкости, ГОСТ 2.728 (пластины 8 мм, зазор 1,5 мм -> 4,06 / 0,76)."""
    s = Symbol("C", "C", "C", footprint="GOST_FP:C_Disc_D5.1mm_W3.2mm_P5.00mm",
               descr="Конденсатор постоянной ёмкости (ГОСТ 2.728)", keywords="конденсатор capacitor")
    s.graphics += [wline(THICK, (-2.032, 0.381), (2.032, 0.381)),
                   wline(THICK, (-2.032, -0.381), (2.032, -0.381))]
    two_pin(s, 0, 3.81, 270, 0, -3.81, 90, 3.429)
    s.ref_at, s.val_at = (2.54, 1.27, "left"), (2.54, -1.27, "left")
    return s


def sym_led():
    """Светодиод, ГОСТ 2.730: диод в корпусе Ø10 (-> Ø5,08), две стрелки наружу под 45°."""
    s = Symbol("LED", "HL", "LED", descr="Светодиод (ГОСТ 2.730)", keywords="светодиод LED",
               footprint="GOST_FP:LaserDiode_TO18-D5.6-3")
    g = s.graphics
    g.append(circle(0, 0, 2.54))
    diode_body(g, -1.1, 1.1, k_end=-1.27, a_end=1.27)
    d = (0.7071, 0.7071)
    for sx, sy in ((-0.508, 1.778), (0.889, 1.397)):
        g += arrow(sx, sy, sx + 2.8 * d[0], sy + 2.8 * d[1])
    two_pin(s, -3.81, 0, 0, 3.81, 0, 180, 2.54, "K", "A")
    s.ref_at, s.val_at = (0, -3.81, ""), (0, -5.588, "")
    return s


def sym_photodiode():
    """Фотодиод, ГОСТ 2.730: диод в корпусе Ø10 (-> Ø5,08), две стрелки внутрь под 45°."""
    s = Symbol("Photodiode", "VD", "Photodiode", descr="Фотодиод (ГОСТ 2.730)",
               keywords="фотодиод photodiode PIN", footprint="GOST_FP:Osram_DIL2_4.3x4.65mm_P5.08mm")
    g = s.graphics
    g.append(circle(-1.27, 0, 2.54))
    diode_body(g, -2.2, 0, k_end=-2.54)
    for ex, ey in ((-1.651, 1.905), (-0.254, 1.651)):
        g += arrow(ex + 2.0, ey + 2.0, ex, ey)
    two_pin(s, -5.08, 0, 0, 2.54, 0, 180, 2.54, "K", "A")
    s.ref_at, s.val_at = (-1.27, -3.81, ""), (-1.27, -5.588, "")
    return s


def sym_zener():
    """Стабилитрон, ГОСТ 2.730: диод, черта катода с одним отгибом."""
    s = Symbol("D_Zener", "VD", "D_Zener", descr="Стабилитрон (ГОСТ 2.730)",
               keywords="стабилитрон zener", footprint="GOST_FP:D_DO-41_SOD81_P10.16mm_Horizontal")
    g = s.graphics
    diode_body(g, -1.1, 1.1, k_end=-1.27, a_end=1.27)
    g.append(line((-1.1, 1.27), (-0.35, 1.27)))
    two_pin(s, -3.81, 0, 0, 3.81, 0, 180, 2.54, "K", "A")
    s.ref_at, s.val_at = (0, 2.54, ""), (0, -2.54, "")
    return s


def sym_npn():
    """Транзистор биполярный n-p-n, ГОСТ 2.730: корпус Ø12 (-> Ø6), угол между К и Э 60°."""
    s = Symbol("Q_NPN", "VT", "Q_NPN", descr="Транзистор n-p-n (ГОСТ 2.730); выводы 1-Э, 2-К, 3-Б",
               keywords="транзистор npn BJT", footprint="GOST_FP:TO-126-3_Vertical")
    g = s.graphics
    g.append(circle(1.27, 0, 3.0))
    g.append(wline(THICK, (0, 2.25), (0, -2.25)))       # база
    g.append(line((-2.54, 0), (0, 0)))
    g.append(line((0, 1.074), (2.54, 2.54)))            # коллектор
    ux, uy = 0.866, -0.5                                 # эмиттер, 30° к оси
    tip = (0 + 2.2 * ux, -1.074 + 2.2 * uy)
    g.append(line((0, -1.074), (2.54, -2.54)))
    g.append(fpoly(tip, (tip[0] - 0.8 * ux + 0.3 * 0.5, tip[1] - 0.8 * uy + 0.3 * 0.866),
                   (tip[0] - 0.8 * ux - 0.3 * 0.5, tip[1] - 0.8 * uy - 0.3 * 0.866)))
    s.pins += [pin("1", "E", "passive", 2.54, -5.08, 90, length=2.54),
               pin("2", "C", "passive", 2.54, 5.08, 270, length=2.54),
               pin("3", "B", "input", -5.08, 0, 0, length=2.54)]
    s.hide_pin_numbers = True
    s.hide_pin_names = True
    s.ref_at, s.val_at = (5.08, 1.27, "left"), (5.08, -1.27, "left")
    return s


def sym_gnd():
    """Электрическое соединение с корпусом (общий провод) — ГОСТ 2.721-74, табл. 6б, п. 4:
    «⊥», горизонтальная линия толстая (6 мм -> 3,05 мм)."""
    s = Symbol("GND", "#PWR", "GND", descr="Общий провод (соединение с корпусом), ГОСТ 2.721",
               keywords="общий провод корпус GND ground", power=True)
    s.graphics += [line((0, 0), (0, -1.27)), wline(THICK, (-1.524, -1.27), (1.524, -1.27))]
    s.pins.append(pin("1", "GND", "power_in", 0, 0, 270, hidden=True, length=0))
    s.ref_at = (0, -3.81, "")
    s.ref_hidden = True
    s.val_at = (0, -2.54, "")
    s.value_hidden = True
    s.name_offset = 0
    return s


def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--pitch", type=float, default=2.54)
    ap.add_argument("--legacy", action="store_true")
    ap.add_argument("-o", "--out", default="symbols/GOST_UGO.kicad_sym")
    ARGS = ap.parse_args()
    if ARGS.pitch < 3:          # компактный шаг 2,54 — уменьшаем шрифт, чтобы метки не слипались
        global TXT_NAME, TXT_NUM, TXT_FUNC
        TXT_NAME, TXT_NUM, TXT_FUNC = 1.8, 1.27, 2.5

    syms = [sym_opa340(), sym_kr590kn2(), sym_lm1117(), sym_stm32(), sym_ft232rl()]
    syms += [sym_conn(n, ["+12 В", "-12 В", "Общий"] if n == 3 else None) for n in range(2, 7)]
    syms.append(sym_gnd())
    syms.append(sym_button())
    syms += [sym_r(), sym_r_trim(), sym_c(), sym_led(), sym_photodiode(), sym_zener(), sym_npn()]

    hdr = ["(kicad_symbol_lib"]
    if ARGS.legacy:
        hdr += ["  (version 20220914)", '  (generator "gost_ugo_gen")']
    else:
        hdr += ["  (version 20241209)", '  (generator "gost_ugo_gen")', '  (generator_version "10.0")']
    body = "\n".join(s.render() for s in syms)
    with open(ARGS.out, "w", encoding="utf-8") as f:
        f.write("\n".join(hdr) + "\n" + body + "\n)\n")
    print(f"{ARGS.out}: {len(syms)} УГО, шаг выводов {ARGS.pitch} мм")


if __name__ == "__main__":
    main()
