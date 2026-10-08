#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор рамки листа KiCad (.kicad_wks) по ГОСТ 2.104-2006:
  * рамка: поле слева 20 мм, остальные 5 мм;
  * основная надпись по форме 1 (185 × 55 мм) — чертежи и схемы;
  * дополнительные графы 19–26 (левое поле и графа 26 в левом верхнем углу);
  * «Копировал» и «Формат» под рамкой.

Графы заполняются из основной надписи проекта (Файл → Параметры страницы):
  ${COMMENT1}  графы 2 и 26 — обозначение документа (БИГЕ.ХХХХХХ.ХХХ Э3)
  ${TITLE}     графа 1, строка 1 — наименование изделия
  ${COMMENT2}  графа 1, строка 2 — наименование документа («Схема электрическая принципиальная»)
  ${COMMENT3}  Разраб.        ${COMMENT4}  Пров.        ${COMMENT5}  Т.контр.
  ${COMMENT6}  Н.контр.       ${COMMENT7}  Утв.
  ${COMPANY}   графа 9, строка 1 (организация)
  ${COMMENT8}  графа 9, строка 2      ${COMMENT9}  графа 9, строка 3
  ${#} / ${##} лист / листов,  ${PAPER} — формат.

Запуск:  python3 tools/gen_wks.py  [-o drawing_sheets/GOST_form1.kicad_wks]
"""
import argparse

THICK = 0.5    # основная линия (S)
THIN = 0.25    # тонкая линия (S/2 … S/3)
F_LBL = 2.5    # подписи граф
F_TXT = 3.5    # содержимое граф
F_DES = 5.0    # обозначение документа

items = []


def fmt(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


# --- примитивы в координатах «от угла листа» (поля в setup = 0) -------------
def line(x1, y1, x2, y2, corner="rbcorner", w=THIN):
    items.append(f'(line (name "") (start {fmt(x1)} {fmt(y1)} {corner}) '
                 f'(end {fmt(x2)} {fmt(y2)} {corner}) (linewidth {w}))')


def rect(x1, y1, x2, y2, c1, c2, w=THICK):
    items.append(f'(rect (name "") (start {fmt(x1)} {fmt(y1)} {c1}) '
                 f'(end {fmt(x2)} {fmt(y2)} {c2}) (linewidth {w}))')


def text(s, x, y, corner="rbcorner", size=F_TXT, hj="center", rot=0, maxlen=None, italic=True):
    opts = f'(font (size {fmt(size)} {fmt(size)}){" italic" if italic else ""})'
    j = f" (justify {hj})" if hj != "left" else ""
    r = f" (rotate {rot})" if rot else ""
    m = f" (maxlen {fmt(maxlen)})" if maxlen else ""
    items.append(f'(tbtext "{esc(s)}" (name "") (pos {fmt(x)} {fmt(y)} {corner}) {opts}{j}{r}{m})')


# --- основная надпись: локальные координаты (u вправо, v вниз от левого верхнего угла) ---
SW, SH = 185.0, 55.0
OX, OY = 5.0, 5.0              # правый нижний угол надписи совпадает с углом рамки


def P(u, v):
    """локальные (u, v) -> координаты от правого нижнего угла листа"""
    return OX + (SW - u), OY + (SH - v)


def sl(u1, v1, u2, v2, w=THIN):
    x1, y1 = P(u1, v1)
    x2, y2 = P(u2, v2)
    line(x1, y1, x2, y2, "rbcorner", w)


def st(s, u, v, size=F_TXT, hj="center", maxlen=None, rot=0):
    x, y = P(u, v)
    text(s, x, y, "rbcorner", size, hj, rot, maxlen)


def stamp():
    # контур
    sl(0, 0, SW, 0, THICK)
    sl(0, 0, 0, SH, THICK)
    # левая часть: графы 14–18 (изменения), шапка, графы 10–13
    for u in (17, 40, 55, 65):
        sl(u, 0, u, SH, THICK)
    sl(7, 0, 7, 25, THICK)
    for v in (5, 10, 15):
        sl(0, v, 65, v, THIN)
    sl(0, 20, 65, 20, THICK)
    sl(0, 25, 65, 25, THICK)
    for v in (30, 35, 40, 45, 50):
        sl(0, v, 65, v, THIN)
    for s, u, w in (("Изм.", 3.5, 7), ("Лист", 12, 10), ("N докум.", 28.5, 23), ("Подп.", 47.5, 15),
                    ("Дата", 60, 10)):
        st(s, u, 22.5, F_LBL, maxlen=w - 0.8)
    rows = (("Разраб.", "${COMMENT3}"), ("Пров.", "${COMMENT4}"), ("Т.контр.", "${COMMENT5}"),
            ("", ""), ("Н.контр.", "${COMMENT6}"), ("Утв.", "${COMMENT7}"))
    for i, (lbl, val) in enumerate(rows):
        v = 27.5 + 5 * i
        if lbl:
            st(lbl, 0.8, v, F_LBL, "left")
        if val:
            st(val, 18, v, F_LBL, "left", maxlen=21.5)
    # правая часть
    sl(65, 15, SW, 15, THICK)                   # низ графы 2
    sl(135, 15, 135, SH, THICK)                 # граница граф 1/3 и 4–9
    sl(65, 40, SW, 40, THICK)                   # верх граф 3 и 9
    sl(135, 20, SW, 20, THICK)                  # шапка Лит./Масса/Масштаб
    sl(135, 35, SW, 35, THICK)                  # строка Лист/Листов
    sl(150, 15, 150, 35, THICK)
    sl(167, 15, 167, 35, THICK)
    sl(140, 20, 140, 35, THIN)                  # три клетки графы 4
    sl(145, 20, 145, 35, THIN)
    sl(155, 35, 155, 40, THICK)
    st("Лит.", 142.5, 17.5, F_LBL)
    st("Масса", 158.5, 17.5, F_LBL)
    st("Масштаб", 176, 17.5, F_LBL, maxlen=17)
    st("Лист ${#}", 136, 37.5, F_LBL, "left")
    st("Листов ${##}", 156, 37.5, F_LBL, "left")
    # графа 2 — обозначение документа
    st("${COMMENT1}", 125, 7.5, F_DES, maxlen=114)
    # графа 1 — наименование изделия и документа
    st("${TITLE}", 100, 23.5, F_TXT, maxlen=66)
    st("${COMMENT2}", 100, 31, F_TXT, maxlen=66)
    # графа 9 — организация
    st("${COMPANY}", 160, 43.5, F_LBL, maxlen=48)
    st("${COMMENT8}", 160, 47.5, F_LBL, maxlen=48)
    st("${COMMENT9}", 160, 51.5, F_LBL, maxlen=48)


def side_columns():
    """Графы 19–23 (снизу вверх) и 24–25 (сверху вниз) в поле подшивки, графа 26."""
    x0, x1, x2 = 8.0, 13.0, 20.0               # от левого края листа
    # 19–23 — от нижней рамки вверх
    blocks = (("Инв. N подл.", 25), ("Подп. и дата", 35), ("Взам. инв. N", 25),
              ("Инв. N дубл.", 25), ("Подп. и дата", 35))
    y = 5.0
    line(x0, y, x2, y, "lbcorner", THICK)
    for lbl, h in blocks:
        line(x0, y, x0, y + h, "lbcorner", THICK)
        line(x1, y, x1, y + h, "lbcorner", THICK)
        line(x0, y + h, x2, y + h, "lbcorner", THICK)
        text(lbl, (x0 + x1) / 2, y + h / 2, "lbcorner", F_LBL, "center", rot=90, maxlen=h - 2)
        y += h
    # 24–25 — от верхней рамки вниз
    y = 5.0
    for lbl, h in (("Перв. примен.", 60), ("Справ. N", 60)):
        line(x0, y, x0, y + h, "ltcorner", THICK)
        line(x1, y, x1, y + h, "ltcorner", THICK)
        line(x0, y + h, x2, y + h, "ltcorner", THICK)
        text(lbl, (x0 + x1) / 2, y + h / 2, "ltcorner", F_LBL, "center", rot=90, maxlen=h - 2)
        y += h
    line(x0, 5, x2, 5, "ltcorner", THICK)
    # графа 26 — обозначение, повёрнутое на 180°
    line(20, 19, 90, 19, "ltcorner", THICK)
    line(90, 5, 90, 19, "ltcorner", THICK)
    text("${COMMENT1}", 55, 12, "ltcorner", F_DES, "center", rot=180, maxlen=66)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="drawing_sheets/GOST_form1.kicad_wks")
    a = ap.parse_args()

    rect(20, 5, 5, 5, "ltcorner", "rbcorner", THICK)       # рамка
    stamp()
    side_columns()
    text("Копировал", 5 + 185 - 110, 2.5, "rbcorner", F_LBL)
    text("Формат ${PAPER}", 5 + 25, 2.5, "rbcorner", F_LBL)

    out = ["(kicad_wks", "\t(version 20231118)", '\t(generator "gost_wks_gen")',
           '\t(generator_version "9.0")',
           "\t(setup (textsize 2.5 2.5) (linewidth 0.25) (textlinewidth 0.25)",
           "\t\t(left_margin 0) (right_margin 0) (top_margin 0) (bottom_margin 0))"]
    out += ["\t" + i for i in items]
    out.append(")")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"{a.out}: {len(items)} элементов")


if __name__ == "__main__":
    main()
