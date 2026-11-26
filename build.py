#!/usr/bin/env python3
"""Build index.html from site.gmi.

Usage:  python3 build.py            (reads site.gmi, writes index.html)

Standard library only. The first "# heading" in site.gmi becomes the ASCII
mosaic that fills the screen. Links, paragraphs, headings and bullets are woven
into the same grid of characters below the name, as real text and real links.
Mosaic characters are set in a ```mosaic block (fill, shadow, texture).
"""
import html
import math
import pathlib
import re

HERE = pathlib.Path(__file__).parent

# --- 5x7 pixel font (fallback for digits and punctuation) ---------------------------------------------------------
FONT_SRC = """
A .###. #...# #...# ##### #...# #...# #...#
B ####. #...# #...# ####. #...# #...# ####.
C .###. #...# #.... #.... #.... #...# .###.
D ####. #...# #...# #...# #...# #...# ####.
E ##### #.... #.... ####. #.... #.... #####
F ##### #.... #.... ####. #.... #.... #....
G .###. #...# #.... #.### #...# #...# .####
H #...# #...# #...# ##### #...# #...# #...#
I .###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.
J ..### ...#. ...#. ...#. ...#. #..#. .##..
K #...# #..#. #.#.. ##... #.#.. #..#. #...#
L #.... #.... #.... #.... #.... #.... #####
M #...# ##.## #.#.# #.#.# #...# #...# #...#
N #...# #...# ##..# #.#.# #..## #...# #...#
O .###. #...# #...# #...# #...# #...# .###.
P ####. #...# #...# ####. #.... #.... #....
Q .###. #...# #...# #...# #.#.# #..#. .##.#
R ####. #...# #...# ####. #.#.. #..#. #...#
S .#### #.... #.... .###. ....# ....# ####.
T ##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..
U #...# #...# #...# #...# #...# #...# .###.
V #...# #...# #...# #...# #...# .#.#. ..#..
W #...# #...# #...# #.#.# #.#.# #.#.# .#.#.
X #...# #...# .#.#. ..#.. .#.#. #...# #...#
Y #...# #...# .#.#. ..#.. ..#.. ..#.. ..#..
Z ##### ....# ...#. ..#.. .#... #.... #####
0 .###. #...# #..## #.#.# ##..# #...# .###.
1 ..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.
2 .###. #...# ....# ...#. ..#.. .#... #####
3 ##### ...#. ..#.. ...#. ....# #...# .###.
4 ...#. ..##. .#.#. #..#. ##### ...#. ...#.
5 ##### #.... ####. ....# ....# #...# .###.
6 ..##. .#... #.... ####. #...# #...# .###.
7 ##### ....# ...#. ..#.. .#... .#... .#...
8 .###. #...# #...# .###. #...# #...# .###.
9 .###. #...# #...# .#### ....# ...#. .##..
. ..... ..... ..... ..... ..... .##.. .##..
, ..... ..... ..... ..... .##.. ..#.. .#...
! ..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#..
? .###. #...# ....# ...#. ..#.. ..... ..#..
- ..... ..... ..... ##### ..... ..... .....
' ..#.. ..#.. .#... ..... ..... ..... .....
& .##.. #..#. #.#.. .#... #.#.# #..#. .##.#
@ .###. #...# #.### #.#.# #.### #.... .###.
/ ....# ....# ...#. ..#.. .#... #.... #....
: ..... .##.. .##.. ..... .##.. .##.. .....
"""
FONT = {}
for line in FONT_SRC.strip().splitlines():
    ch, *rows = line.split()
    FONT[ch] = [[c == "#" for c in r] for r in rows]
FONT[" "] = [[False] * 5 for _ in range(7)]

# Drop shadow: a cell is shadow if a letter cell sits this far up/left of it
SHADOW_OFFSETS = [(1, 1), (1, 2), (0, 1), (0, 2)]  # (rows, cols)

CHAR_W = 0.6  # monospace character width relative to its height (line-height 1)

# Screen-shape variants:
# (css class, columns, min aspect, max aspect, stack words?, vertical stretch)
VARIANTS = [
    ("v-tall", 56, 0.4, 0.7, True, 1.9),
    ("v-portrait", 90, 0.7, 1.0, True, 1.0),
    ("v-landscape", 140, 1.0, 2.1, True, 1.0),
    ("v-wide", 180, 2.1, 4.0, False, 1.0),
]


# --- Geometric, Futura-style capitals ------------------------------------------
# Each glyph is drawn in a box 1 unit tall (cap height) from filled shapes, then
# clipped. Coordinates: x to the right, y downwards. Diagonals are exactly as
# wide as the stems on every row; pointed apexes come from clipping to the outline.
S_W = 0.155        # stroke weight
LETTER_GAP = 0.2   # space between letters
WORD_GAP = 0.5     # extra space for a word space
LINE_GAP = 0.38    # space between stacked lines


def _inside(pts, x, y):
    hit = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]; xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def poly(*pts):
    return lambda x, y: _inside(pts, x, y)


def rect(x, y, w, h):
    return poly((x, y), (x + w, y), (x + w, y + h), (x, y + h))


def ring(cx, cy, r, arcs=None, wv=S_W, wh=S_W):
    """Circular stroke, wv thick at the sides and wh thick at top and bottom.
    arcs = allowed (from, to) angles in degrees, 0 = right, 90 = down."""
    def f(x, y):
        dx, dy = x - cx, y - cy
        if dx * dx + dy * dy >= r * r:
            return False
        if (dx / (r - wv)) ** 2 + (dy / (r - wh)) ** 2 < 1:
            return False
        if arcs is None:
            return True
        a = math.degrees(math.atan2(dy, dx)) % 360
        return any((a0 <= a <= a1) if a0 <= a1 else (a >= a0 or a <= a1) for a0, a1 in arcs)
    return f


def G(width, shapes, clip=None):
    return (width, shapes, clip)


def make_glyphs(wv=S_W, wh=S_W):
    """Capitals A-Z. wv = width of vertical stems, wh = height of horizontal bars.
    Both are snapped to whole characters per screen size, so every stem and bar
    is equally thick and every corner is square."""
    def hband(p, q, side, t=None, ext=0.4, centred=False):
        """Diagonal stroke along p->q that is exactly t wide on every row
        (default: the stem width). side=1 puts it to the right of the line, -1 to the left."""
        t = wv if t is None else t
        dx, dy = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(dx, dy); ux, uy = dx / ln, dy / ln
        a = (p[0] - ux * ext, p[1] - uy * ext); b = (q[0] + ux * ext, q[1] + uy * ext)
        o = -t / 2 if centred else (0 if side > 0 else -t)
        return poly((a[0] + o, a[1]), (b[0] + o, b[1]), (b[0] + o + t, b[1]), (a[0] + o + t, a[1]))

    def hseg(p, q):
        return hband(p, q, 1, centred=True)

    def bowl(top, bottom, xc):          # bars from the stem to xc, closed by a half circle
        r = (bottom - top) / 2
        return [rect(0, top, xc, wh), rect(0, bottom - wh, xc, wh),
                ring(xc, top + r, r, [(270, 90)], wv, wh)]

    def diag(x_top, x_bot, top, bot, thick):
        """Parallelogram from (x_top, top) to (x_bot, bot), thick wide horizontally."""
        return poly((x_top, top), (x_top + thick, top), (x_bot + thick, bot), (x_bot, bot))

    return {
        "A": G(0.9, [hband((0, 1), (0.45, 0), 1), hband((0.45, 0), (0.9, 1), -1), rect(0, 0.64, 0.9, wh)],
               poly((0, 1), (0.45, 0), (0.9, 1))),
        "B": G(0.6, [rect(0, 0, wv, 1)] + bowl(0, 0.47 + wh / 2, 0.33) + bowl(0.47 - wh / 2, 1, 0.3)),
        "C": G(0.95, [ring(0.5, 0.5, 0.5, [(42, 318)], wv, wh)]),
        "D": G(0.8, [rect(0, 0, wv, 1)] + bowl(0, 1, 0.3)),
        "E": G(0.5, [rect(0, 0, wv, 1), rect(0, 0, 0.5, wh), rect(0, 0.5 - wh / 2, 0.45, wh), rect(0, 1 - wh, 0.5, wh)]),
        "F": G(0.5, [rect(0, 0, wv, 1), rect(0, 0, 0.5, wh), rect(0, 0.5 - wh / 2, 0.45, wh)]),
        "G": G(1.0, [ring(0.5, 0.5, 0.5, [(0, 300)], wv, wh), rect(0.55, 0.5, 0.45, wh), rect(1 - wv, 0.5, wv, 0.12)]),
        "H": G(0.72, [rect(0, 0, wv, 1), rect(0.72 - wv, 0, wv, 1), rect(0, 0.5 - wh / 2, 0.72, wh)]),
        "I": G(S_W, [rect(0, 0, wv, 1)]),
        "J": G(0.48, [rect(0.48 - wv, 0, wv, 0.76), ring(0.24, 0.76, 0.24, [(0, 180)], wv, wh)]),
        "K": G(0.68, [rect(0, 0, wv, 1), hseg((wv, 0.62), (0.7, -0.02)), hseg((0.3, 0.45), (0.72, 1.02))]),
        "L": G(0.45, [rect(0, 0, wv, 1), rect(0, 1 - wh, 0.45, wh)]),
        "M": G(1.05, [hband((0, 1), (0.2, 0), 1), hband((0.2, 0), (0.525, 1), -1),
                      hband((0.525, 1), (0.85, 0), 1), hband((0.85, 0), (1.05, 1), -1)],
               poly((0, 1), (0.2, 0), (0.525, 1), (0.85, 0), (1.05, 1))),
        "N": G(0.75, [rect(0, 0, wv, 1), rect(0.75 - wv, 0, wv, 1), diag(0, 0.75 - wv, 0, 1, wv)]),
        "O": G(1.0, [ring(0.5, 0.5, 0.5, None, wv, wh)]),
        "P": G(0.58, [rect(0, 0, wv, 1)] + bowl(0, 0.58, 0.29)),
        "Q": G(1.0, [ring(0.5, 0.5, 0.5, None, wv, wh), hseg((0.6, 0.62), (1.0, 1.0))]),
        "R": G(0.62, [rect(0, 0, wv, 1), hseg((0.28, 0.52), (0.66, 1.02))] + bowl(0, 0.58, 0.29)),
        "S": G(0.56, [ring(0.27, 0.255, 0.255, [(95, 340)], wv, wh), ring(0.29, 0.735, 0.265, [(265, 155)], wv, wh)]),
        "T": G(0.64, [rect(0, 0, 0.64, wh), rect(0.32 - wv / 2, 0, wv, 1)]),
        "U": G(0.72, [rect(0, 0, wv, 0.64), rect(0.72 - wv, 0, wv, 0.64), ring(0.36, 0.64, 0.36, [(0, 180)], wv, wh)]),
        "V": G(0.85, [hband((0, 0), (0.425, 1), 1), hband((0.425, 1), (0.85, 0), -1)],
               poly((0, 0), (0.85, 0), (0.425, 1))),
        "W": G(1.25, [hband((0, 0), (0.3, 1), 1), hband((0.3, 1), (0.625, 0), -1),
                      hband((0.625, 0), (0.95, 1), 1), hband((0.95, 1), (1.25, 0), -1)],
               poly((0, 0), (1.25, 0), (0.95, 1), (0.625, 0), (0.3, 1))),
        "X": G(0.8, [hseg((0, 0), (0.8, 1)), hseg((0.8, 0), (0, 1))]),
        "Y": G(0.8, [hseg((0, 0), (0.4, 0.55)), hseg((0.8, 0), (0.4, 0.55)), rect(0.4 - wv / 2, 0.5, wv, 0.5)]),
        "Z": G(0.62, [rect(0, 0, 0.62, wh), rect(0, 1 - wh, 0.62, wh), diag(0.62 - wv, 0, wh, 1 - wh, wv)]),
    }


GLYPHS = make_glyphs()   # default weights; used for widths and layout


def _pixel_glyph(ch):
    """Fallback for digits and punctuation: the 5x7 pixel font, scaled to cap height."""
    bmp = FONT[ch]
    return G(5 / 7, [lambda x, y: 0 <= x < 5 / 7 and 0 <= y < 1 and bmp[int(y * 7)][int(x * 7)]])


def glyph(ch, table=None):
    table = table or GLYPHS
    if ch in table:
        return table[ch]
    if ch in FONT and ch != " ":
        return _pixel_glyph(ch)
    return None


def glyph_lines(text, stacked):
    text = "".join(c if (c in GLYPHS or c in FONT) else " " for c in text.upper())
    return text.split() if stacked else [" ".join(text.split())]


def layout_line(line, table=None):
    """[(x offset, glyph)] and total width for one line of text."""
    items, x = [], 0.0
    for ch in line:
        if ch == " ":
            x += WORD_GAP
            continue
        g = glyph(ch, table)
        items.append((x, g))
        x += g[0] + LETTER_GAP
    return items, max(x - LETTER_GAP, 0)


def fit_word(lines, cols, avail_rows, stretch):
    """Scale so the word fits 86% of the width and avail_rows of the height."""
    laid = [layout_line(l) for l in lines]
    W = max(wd for _, wd in laid)
    H = len(lines) + (len(lines) - 1) * LINE_GAP
    sx = min(0.86 * cols / W, avail_rows / (H * CHAR_W * stretch))  # columns per unit
    sy = sx * CHAR_W * stretch                                      # rows per unit
    return laid, W, H, sx, sy


def coverage_grid(lines, cols, rows, pad, vis_rows, stretch, avail_rows=None, top=None):
    """1.0 where a cell's centre falls inside a letter, else 0.0.

    Cap height is snapped to whole rows and stroke weights to whole characters,
    so stems and bars are equally thick everywhere and corners stay square."""
    _, W, H, sx, sy = fit_word(lines, cols, avail_rows or 0.72 * vis_rows, stretch)
    sy = max(round(sy), 2)                                   # rows per cap height
    wv = max(1, round(S_W * sx)) / sx
    wh = max(1, round(S_W * sy)) / sy
    table = make_glyphs(wv, wh)
    laid = [layout_line(l, table) for l in lines]
    pitch = round((1 + LINE_GAP) * sy)                       # rows from line to line
    x0 = pad + (cols - W * sx) / 2
    y0 = round((rows - (len(lines) - 1) * pitch - sy) / 2 if top is None else top)

    # Each letter starts on a whole column, so repeated letters are identical.
    starts = [[(round(x0 + ((W - wd) / 2 + gx0) * sx), g) for gx0, g in items] for items, wd in laid]

    def lit(cx, cy):                                         # cell centre, in cells
        li, ry = divmod(cy - y0, pitch)
        li = int(li)
        if cy < y0 or li >= len(laid) or ry >= sy:
            return False
        gy = ry / sy
        for col, (gw, shapes, clip) in starts[li]:
            gx = (cx - col) / sx
            if 0 <= gx < gw:
                if clip is not None and not clip(gx, gy):
                    return False
                return any(f(gx, gy) for f in shapes)
        return False

    total = cols + 2 * pad
    grid = [[0.0] * total for _ in range(rows)]
    for r in range(max(y0, 0), min(y0 + len(lines) * pitch + 1, rows)):
        for c in range(max(int(x0) - 1, 0), min(int(x0 + W * sx) + 2, total)):
            grid[r][c] = 1.0 if lit(c + 0.5, r + 0.5) else 0.0
    return grid


CONTENT_GAP = 3   # rows between the word and the content below it
ITEM_GAP = 3      # texture characters between links on a row


def wrap_words(text, width):
    rows, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            rows.append(cur); cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    return rows + ([cur] if cur else [])


def content_rows(blocks, width):
    """Lay the page content out as rows of segments: (kind, text, href).

    Links and bullets flow side by side and wrap; paragraphs word-wrap;
    headings get a row of their own. A texture row separates every content row.
    """
    out, i = [], 0
    while i < len(blocks):
        kind = blocks[i][0]
        if kind in ("link", "li"):
            items = []
            while i < len(blocks) and blocks[i][0] == kind:
                b = blocks[i]
                items.append(("a", b[2], b[1]) if kind == "link" else ("t", b[1], None))
                i += 1
            row, used = [], 0
            for it in items:
                need = len(it[1]) + 2 + (ITEM_GAP if row else 0)
                if row and used + need > width:
                    out.append(row); row, used = [], 0
                    need = len(it[1]) + 2
                row.append(it); used += need
            if row:
                out.append(row)
            continue
        b = blocks[i]
        if kind == "h":
            out.append([("h", b[2], None)])
        elif kind in ("p", "quote"):
            out.extend([("t", line, None)] for line in wrap_words(b[1], width - 2))
        i += 1
    return out


def mosaic(text, blocks, cfg, cls, cols, amin, amax, stacked, stretch):
    pad = round(cols * 0.08)               # spare columns for narrower fonts
    rows = math.ceil(CHAR_W * cols / amin) + 4
    vis_rows = CHAR_W * cols / amax
    crow = content_rows(blocks, int(cols * (0.9 if cols < 110 else 0.6)))
    n_content = max(len(crow) * 2 - 1, 0)
    lines = glyph_lines(text, stacked)
    avail = max(0.72 * vis_rows - (n_content + CONTENT_GAP if crow else 0), 6)
    _, _, H, _, sy = fit_word(lines, cols, avail, stretch)
    word_h = H * sy
    total = word_h + (CONTENT_GAP + n_content if crow else 0)
    top = (rows - total) / 2
    grid = coverage_grid(lines, cols, rows, pad, vis_rows, stretch, avail, top)
    lit = [[cov >= 0.5 for cov in row] for row in grid]

    # Content overlay: cell -> (group key, character)
    overlay = {}
    r0 = math.ceil(top + word_h + CONTENT_GAP)
    for n, segs in enumerate(crow):
        r = r0 + n * 2
        width = sum(len(t) + 2 for _, t, _ in segs) + ITEM_GAP * (len(segs) - 1)
        c = pad + (cols - width) // 2
        for j, (kind, label, href) in enumerate(segs):
            if j:
                c += ITEM_GAP
            overlay[(r, c)] = (("d", "f"), " ")
            key = ("a", n, j, href) if kind == "a" else ("t", "h" if kind == "h" else "t")
            for k_, ch in enumerate(label):
                overlay[(r, c + 1 + k_)] = (key, ch)
            overlay[(r, c + 1 + len(label))] = (("d", "f"), " ")
            c += len(label) + 2

    fill = [c for c in cfg["fill"] if not c.isspace()] or ["#"]
    shadow, texture = cfg["shadow"] or "/", cfg["texture"] or "."
    shadow_offsets = SHADOW_OFFSETS
    e = html.escape
    k = 0
    out = []
    for r, row in enumerate(lit):
        runs, cur, buf = [], None, []
        for c, on in enumerate(row):
            if (r, c) in overlay:
                key, ch = overlay[(r, c)]
            elif on:
                key, ch = ("d", "i"), fill[k % len(fill)]; k += 1
            elif any(r - dr >= 0 and c - dc >= 0 and lit[r - dr][c - dc]
                     for dr, dc in shadow_offsets):
                key, ch = ("d", "m"), shadow[(r + c) % len(shadow)]
            else:
                key, ch = ("d", "f"), texture[(r + c) % len(texture)]
            if ch == " " and key[0] == "d" and cur and cur[0] == "d":
                key = cur                  # decorative spaces never start a new span
            if key != cur and buf:
                runs.append((cur, "".join(buf))); buf = []
            cur = key
            buf.append(ch)
        runs.append((cur, "".join(buf)))
        html_row = []
        for key, txt in runs:
            if key[0] == "d":
                html_row.append(f'<span class="{key[1]}" aria-hidden="true">{e(txt)}</span>')
            elif key[0] == "a":
                html_row.append(f'<a href="{e(key[3], quote=True)}">{e(txt)}</a>')
            else:
                html_row.append(f'<span class="{key[1]}">{e(txt)}</span>')
        out.append("".join(html_row))
    return (f'<pre class="mosaic {cls}" style="--cols:{cols};--rows:{rows}">'
            + "\n".join(out) + "</pre>")


# --- Gemtext to HTML ----------------------------------------------------------
def parse(src):
    title, cfg, blocks = None, {"fill": "", "shadow": "", "texture": ""}, []
    lines = src.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            alt = line[3:].strip()
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i]); i += 1
            if alt == "mosaic":
                for b in body:
                    if ":" in b:
                        key, val = b.split(":", 1)
                        val = val.strip()
                        if len(val) >= 2 and val[0] == val[-1] == '"':
                            val = val[1:-1]
                        cfg[key.strip().lower()] = val
            else:
                blocks.append(("pre", alt, "\n".join(body)))
        elif line.startswith("=>"):
            parts = line[2:].strip().split(maxsplit=1)
            if parts:
                blocks.append(("link", parts[0], parts[1] if len(parts) > 1 else parts[0]))
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            if title is None and level == 1:
                title = text
            else:
                blocks.append(("h", min(level + 1, 3) if level == 1 else min(level, 3), text))
        elif line.startswith("* "):
            blocks.append(("li", line[2:].strip()))
        elif line.startswith(">"):
            blocks.append(("quote", line[1:].strip()))
        elif line.strip():
            blocks.append(("p", line.strip()))
        i += 1
    return title or "Hello", cfg, blocks


CSS = """
:root{--bg:#fff;--ink:#111;--mid:#9a9a9a;--faint:#cfcfcf}
*{box-sizing:border-box}
html{background:var(--bg);color:var(--ink)}
body{margin:0}
main{display:flex;justify-content:center;overflow:hidden;min-height:100vh;min-height:100svh}
.mosaic{display:none;flex:none;margin:0;line-height:1;font-family:ui-monospace,"SF Mono",Menlo,Consolas,"DejaVu Sans Mono",monospace;
  font-size:max(calc(100vw / (var(--cols) * 0.6)), 0.75rem);margin-top:calc((100vh - var(--rows) * 1em) / 2);margin-top:calc((100svh - var(--rows) * 1em) / 2)}
.mosaic span[aria-hidden]{user-select:none}
.v-tall{display:block}
@media (min-aspect-ratio:7/10){.v-tall{display:none}.v-portrait{display:block}}
@media (min-aspect-ratio:1/1){.v-portrait{display:none}.v-landscape{display:block}}
@media (min-aspect-ratio:21/10){.v-landscape{display:none}.v-wide{display:block}}
.i{color:var(--ink);font-weight:700}.m{color:var(--mid)}.f{color:var(--faint)}
.t{color:var(--ink)}.h{color:var(--ink);font-weight:700}
a{color:#0000ee;text-underline-offset:.15em}a:visited{color:#551a8b}a:active{color:#e00}
a:focus-visible{outline:2px solid #0000ee;outline-offset:2px}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media (forced-colors:active){.i,.m,.f,.t,.h{color:CanvasText}a{color:LinkText}}
"""


def build():
    title, cfg, blocks = parse((HERE / "site.gmi").read_text(encoding="utf-8"))
    desc = next((b[1] for b in blocks if b[0] == "p"), title)
    mosaics = "\n".join(mosaic(title, blocks, cfg, *v) for v in VARIANTS)
    e = html.escape
    page = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc, quote=True)}">
<style>{CSS}</style>
</head>
<body>
<main>
<h1 class="sr-only">{e(title)}</h1>
{mosaics}
</main>
</body>
</html>
"""
    (HERE / "index.html").write_text(page, encoding="utf-8")
    print(f"index.html written ({len(page) // 1024} KB)")


if __name__ == "__main__":
    build()
