"""Gera os SVG animados do perfil da Brasa Studios em profile/assets/.

    uv run --with fonttools python tools/build_assets.py

Linguagem visual minimalista (referencia: logo do Vertex): fundo preto, arestas e vertices
brancos/cinza e um unico acento laranja-brasa. Todo texto vira <path> (text_to_path.py).
Animacao so por CSS @keyframes, calma; o quadro t=0 ja esta completo (animation-delay
negativo) e prefers-reduced-motion desliga tudo.
"""

from __future__ import annotations

import random
from pathlib import Path

from text_to_path import fit_size, font, layout, measure, svg_text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "profile" / "assets"

BLACK, WHITE = "#000", "#FFFFFF"
GREY, DIM, MESH = "#8B8B8B", "#3A3A3A", "#1A1A1A"
ORANGE = "#FF5A1F"
BORDER = "#222222"

REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def n(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def svg_doc(w: int, h: int, title: str, desc: str, css: str, defs: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
        f'height="{h}" role="img" aria-labelledby="t d">'
        f'<title id="t">{title}</title><desc id="d">{desc}</desc>'
        f"<style>{css}{REDUCED}</style><defs>{defs}</defs>{body}</svg>\n"
    )


def write(name: str, content: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(content, encoding="utf-8")
    print(f"{name}: {len(content.encode()) / 1024:.1f} KB")


def card(w: int, h: int, radius: int) -> tuple[str, str]:
    """(defs, markup) do fundo preto arredondado + borda fina; o conteudo usa clip #card."""
    defs = f'<clipPath id="card"><rect width="{w}" height="{h}" rx="{radius}"/></clipPath>'
    border = (
        f'<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="{radius - 1}" '
        f'fill="none" stroke="{BORDER}" stroke-width="1.5"/>'
    )
    return defs, border


# ------------------------------------------------- arestas que se desenham / vertices
CYCLE = 14.0  # ciclo calmo: desenha, segura, some e recomeca


class Reveal:
    """Gera keyframes de 'linha se desenha' e 'vertice acende' num ciclo comum."""

    def __init__(self, cycle: float, now: float) -> None:
        self.cycle, self.now, self.css, self._count = cycle, now, [], 0

    def _pct(self, t: float) -> str:
        return f"{t / self.cycle * 100:.2f}"

    def _name(self) -> str:
        self._count += 1
        return f"r{self._count}"

    def _style(self, name: str) -> str:
        return f"animation:{name} {n(self.cycle)}s linear {n(-self.now)}s infinite"

    def edge(self, start: float, dur: float = 1.3) -> str:
        """Devolve o atributo style (usar com pathLength="1")."""
        name = self._name()
        a, b = self._pct(start), self._pct(start + dur)
        self.css.append(
            f"@keyframes {name}{{0%,{a}%{{stroke-dasharray:1 2;stroke-dashoffset:1;opacity:1}}"
            f"{b}%,88%{{stroke-dasharray:1 2;stroke-dashoffset:0;opacity:1}}"
            f"96%,100%{{stroke-dasharray:1 2;stroke-dashoffset:0;opacity:0}}}}"
        )
        return self._style(name)

    def vertex(self, start: float) -> str:
        name = self._name()
        a, a2 = self._pct(start), self._pct(start + 0.5)
        self.css.append(
            f"@keyframes {name}{{0%,{a}%{{opacity:0}}{a2}%,88%{{opacity:1}}96%,100%{{opacity:0}}}}"
        )
        return self._style(name)


PULSE_CSS = (
    "@keyframes ring{0%{transform:scale(1);opacity:.7}100%{transform:scale(2.6);opacity:0}}"
    ".ring{animation:ring 3.6s ease-out infinite;transform-box:fill-box;transform-origin:center}"
)


def edge_line(
    x1: float, y1: float, x2: float, y2: float, width: float, style: str,
    opacity: float = 1, ink: str = WHITE,
) -> str:
    anim = f' pathLength="1" style="{style}"' if style else ""
    return (
        f'<line x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}" stroke="{ink}" '
        f'stroke-width="{n(width)}" stroke-linecap="round" stroke-opacity="{n(opacity)}"{anim}/>'
    )


def vertex_dot(x: float, y: float, r: float, style: str, fill: str = WHITE) -> str:
    anim = f' style="{style}"' if style else ""
    return f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="{fill}"{anim}/>'


# ------------------------------------------------------------ logo oficial (fonte unica)
# Triangulo de 3 vertices em viewBox 512; o de cima e a brasa laranja. Banner, marcas,
# avatar e lockups saem desta funcao.
LOGO_TOP, LOGO_LEFT, LOGO_RIGHT = (256, 92), (108, 356), (404, 356)
LOGO_EDGES = [(LOGO_LEFT, LOGO_TOP, 1.0), (LOGO_TOP, LOGO_RIGHT, 1.9), (LOGO_RIGHT, LOGO_LEFT, 2.8)]
LOGO_CENTROID_Y = (LOGO_TOP[1] + LOGO_LEFT[1] + LOGO_RIGHT[1]) / 3


def logo_mark(
    ink: str = WHITE, accent: str = ORANGE, edge_w: float = 12, r: float = 20, r_top: float = 22,
    animated: bool = False,
) -> tuple[str, str]:
    """Devolve (markup, css) do simbolo em coordenadas 512x512.

    animated=True: arestas se desenham, vertices acendem em sequencia e o anel laranja
    pulsa (ciclo de 14 s, quadro t=0 completo). Falso: simbolo estatico, sem anel."""
    rev = Reveal(CYCLE, 6.0) if animated else None
    edges = "".join(
        edge_line(a[0], a[1], b[0], b[1], edge_w, rev.edge(t) if rev else "", 1, ink)
        for a, b, t in LOGO_EDGES
    )
    verts = (
        vertex_dot(*LOGO_LEFT, r, rev.vertex(1.0) if rev else "", ink)
        + vertex_dot(*LOGO_RIGHT, r, rev.vertex(2.8) if rev else "", ink)
        + vertex_dot(*LOGO_TOP, r_top, rev.vertex(1.9) if rev else "", accent)
    )
    ring = (
        f'<circle class="ring" cx="{LOGO_TOP[0]}" cy="{LOGO_TOP[1]}" r="{n(r_top)}" fill="none" '
        f'stroke="{accent}" stroke-width="5" opacity="0"/>'
        if rev else ""
    )
    css = PULSE_CSS + "".join(rev.css) if rev else ""
    return edges + verts + ring, css


# ------------------------------------------------------------------------- malha de fundo
def mesh(x0: float, x1: float, y0: float, y1: float, step: float, seed: int) -> str:
    """Malha sutil de arestas/vertices (#1A1A1A) numa grade irregular."""
    rng = random.Random(seed)
    cols, rows = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    pts = {
        (c, r): (x0 + c * step + rng.uniform(-14, 14), y0 + r * step + rng.uniform(-14, 14))
        for c in range(cols)
        for r in range(rows)
    }
    lines: list[str] = []
    for (c, r), (px, py) in pts.items():
        for nb in ((c + 1, r), (c, r + 1)):
            if nb in pts and rng.random() < 0.6:
                qx, qy = pts[nb]
                lines.append(f"M{n(px)} {n(py)}L{n(qx)} {n(qy)}")
    dots = "".join(f'<circle cx="{n(px)}" cy="{n(py)}" r="2.4"/>' for px, py in pts.values())
    return (
        f'<path d="{"".join(lines)}" fill="none" stroke="{MESH}" stroke-width="1.2" stroke-linecap="round"/>'
        f'<g fill="{MESH}">{dots}</g>'
    )


def sparks(count: int, seed: int, x0: float, x1: float, top: float, ground: float) -> str:
    """Poucas brasas minusculas laranja subindo devagar, com opacidade baixa."""
    rng = random.Random(seed)
    parts = []
    for _ in range(count):
        cx, cy = rng.uniform(x0, x1), ground - (ground - top) * rng.random()
        dur = (ground - top + 30) / rng.uniform(12, 24)
        parts.append(
            f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(rng.uniform(1.3, 2.2))}" fill="{ORANGE}" opacity=".35" '
            f'style="--f:{n(ground - cy)}px;--dx:{n(rng.uniform(-30, 30))}px;--t:{n(top - 30 - cy)}px;'
            f'animation:rise {n(dur)}s linear {n(-rng.uniform(0, dur))}s infinite"/>'
        )
    return "".join(parts)


RISE_CSS = (
    "@keyframes rise{0%{transform:translate(0,var(--f));opacity:0}15%{opacity:.5}"
    "80%{opacity:.35}100%{transform:translate(var(--dx),var(--t));opacity:0}}"
)


# ------------------------------------------------------------------------------- banner
def build_banner() -> None:
    w, h = 1280, 400
    light, text = font("inter-300"), font("inter-400")
    title_size = 76
    title, _ = svg_text("BRASA", light, title_size, title_size * 0.4, w / 2, 276, fill=WHITE, anchor="middle")
    sub, _ = svg_text("STUDIOS  ·  JOGOS NO ROBLOX", text, 14, 14 * 0.4, w / 2, 328, fill=GREY, anchor="middle")

    mark, mark_css = logo_mark(animated=True)
    css = RISE_CSS + mark_css
    card_defs, border = card(w, h, 24)
    body = f"""
<g clip-path="url(#card)">
<rect width="{w}" height="{h}" fill="{BLACK}"/>
{mesh(40, 340, 40, 360, 75, 4)}
{mesh(940, 1240, 40, 360, 75, 9)}
{sparks(8, 3, 330, 950, 40, 380)}
<g id="logo-slot" transform="translate(565 40) scale(.293)">
<!-- logo oficial: logo_mark() em build_assets.py (viewBox 512, escala .293 = 150 px, centrado em x=640) -->
{mark}
</g>
{title}
{sub}
</g>
{border}
"""
    write(
        "banner.svg",
        svg_doc(
            w, h, "Brasa Studios",
            "Banner minimalista da Brasa Studios, estúdio indie de jogos no Roblox: um triângulo de vértices com o de cima laranja e o nome BRASA.",
            css, card_defs, body,
        ),
    )


# ------------------------------------------------------------------------------- typing
PHRASES = [
    "Jogos no Roblox feitos com fogo",
    "Terror, mistério e aventura",
    "Estúdio indie brasileiro",
    "Nosso primeiro jogo está chegando...",
]


def pct(t: float, total: float) -> str:
    return f"{t / total * 100:.3f}"


def build_typing() -> None:
    w, h = 900, 60
    f = font("inter-400")
    size, base_y = 30.0, 40.0
    type_step, hold, erase_step, gap = 0.07, 1.9, 0.03, 0.4
    cursor_pad = 3.0

    glyph_css: list[str] = []
    glyph_markup: list[str] = []
    cursor_stops: list[tuple[float, float]] = []
    t0, index = 0.0, 0
    first_done_at, first_cursor = 0.0, 0.0
    total = sum((len(p) + 1) * type_step + hold + len(p) * erase_step + gap for p in PHRASES)
    for p_idx, phrase in enumerate(PHRASES):
        width = measure(phrase, f, size)
        lay = layout(phrase, f, size, 0, (w - width) / 2, base_y)
        count = len(lay.glyphs)
        start_x = lay.glyphs[0].x - cursor_pad
        edge = [g.x + g.advance + cursor_pad for g in lay.glyphs]
        left = [g.x - cursor_pad for g in lay.glyphs]
        erase_start = t0 + (count + 1) * type_step + hold
        cursor_stops.append((t0, start_x))
        for i, g in enumerate(lay.glyphs):
            shown = t0 + (i + 1) * type_step
            gone = erase_start + (count - 1 - i) * erase_step
            cursor_stops.append((shown, edge[i]))
            cursor_stops.append((gone, left[i]))
            if not g.d:
                continue
            name = f"g{index}"
            index += 1
            glyph_css.append(
                f"@keyframes {name}{{0%,{pct(shown, total)}%{{opacity:0}}"
                f"{float(pct(shown, total)) + .003:.3f}%,{pct(gone, total)}%{{opacity:1}}"
                f"{float(pct(gone, total)) + .003:.3f}%,100%{{opacity:0}}}}"
                f".{name}{{animation-name:{name}}}"
            )
            glyph_markup.append(f'<path class="a {name}" opacity="{1 if p_idx == 0 else 0}" d="{g.d}"/>')
        if p_idx == 0:
            first_done_at = t0 + (count + 1) * type_step + 0.6
            first_cursor = edge[-1]
        t0 = erase_start + count * erase_step + gap

    cursor_kf = "".join(
        f"{pct(t, total)}%{{transform:translateX({n(x)}px)}}" for t, x in sorted(cursor_stops)
    )
    css = (
        f".a{{animation-duration:{n(total)}s;animation-iteration-count:infinite;"
        f"animation-timing-function:linear;animation-delay:{n(-first_done_at)}s}}"
        + "".join(glyph_css)
        + f"@keyframes move{{{cursor_kf}}}"
        + f".cur{{animation:move {n(total)}s step-end {n(-first_done_at)}s infinite}}"
        + "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        + ".blink{animation:blink 1.1s step-end infinite}"
    )
    body = (
        f'<g fill="{ORANGE}">{"".join(glyph_markup)}</g>'
        f'<g class="cur" transform="translate({n(first_cursor)} 0)">'
        f'<rect class="blink" x="0" y="14" width="1.8" height="30" rx=".9" fill="{ORANGE}"/></g>'
    )
    write(
        "typing.svg",
        svg_doc(
            w, h, "Brasa Studios, frases digitadas",
            "Texto que se digita sozinho alternando: " + "; ".join(PHRASES) + ".",
            css, "", body,
        ),
    )


# ------------------------------------------------------------------------------ divider
def build_divider() -> None:
    w, h = 1280, 20
    css = (
        "@keyframes walk{from{transform:translateX(-560px)}to{transform:translateX(560px)}}"
        ".walk{animation:walk 9s ease-in-out -4.5s infinite alternate}"
        + PULSE_CSS
    )
    body = f"""
<line x1="80" y1="10" x2="1200" y2="10" stroke="{GREY}" stroke-opacity=".5" stroke-width="1.5" stroke-linecap="round"/>
<circle cx="80" cy="10" r="2.6" fill="{GREY}" fill-opacity=".7"/>
<circle cx="1200" cy="10" r="2.6" fill="{GREY}" fill-opacity=".7"/>
<g class="walk"><circle class="ring" cx="640" cy="10" r="3.6" fill="none" stroke="{ORANGE}" stroke-width="1.2" opacity="0"/><circle cx="640" cy="10" r="3.6" fill="{ORANGE}"/></g>
"""
    write(
        "divider.svg",
        svg_doc(w, h, "Divisória", "Linha fina cinza com um vértice laranja andando por ela.", css, "", body),
    )


# -------------------------------------------------------------------------------- footer
def build_footer() -> None:
    w, h = 1280, 120
    text = font("inter-400")
    label, _ = svg_text("FEITO NO BRASIL", text, 12, 12 * 0.5, w / 2, 92, fill=GREY, anchor="middle")
    rev = Reveal(CYCLE, 7.0)
    count, x0, x1 = 9, 200, 1080
    pts = [
        (x0 + i * (x1 - x0) / (count - 1), 40 + (12 if i % 2 else -12) + (4 if i % 3 == 0 else 0))
        for i in range(count)
    ]
    hot = 4
    edges = "".join(
        edge_line(*pts[i], *pts[i + 1], 1.4, rev.edge(0.8 + i * 0.7, 0.9), 0.55) for i in range(count - 1)
    )
    dots = "".join(
        vertex_dot(x, y, 5 if i == hot else 3.6, rev.vertex(0.8 + i * 0.7), ORANGE if i == hot else WHITE)
        for i, (x, y) in enumerate(pts)
    )
    hx, hy = pts[hot]
    ring = f'<circle class="ring" cx="{n(hx)}" cy="{n(hy)}" r="5" fill="none" stroke="{ORANGE}" stroke-width="1.5" opacity="0"/>'
    css = PULSE_CSS + "".join(rev.css)
    card_defs, border = card(w, h, 20)
    body = f"""
<g clip-path="url(#card)">
<rect width="{w}" height="{h}" fill="{BLACK}"/>
{edges}
{dots}
{ring}
{label}
</g>
{border}
"""
    write(
        "footer.svg",
        svg_doc(
            w, h, "Rodapé",
            "Uma fileira de vértices ligados por arestas finas, um deles laranja pulsando, e o texto Feito no Brasil.",
            css, card_defs, body,
        ),
    )


# ---------------------------------------------------------------------------------- jogo
COLS, ROWS, CELL = 15, 10, 42
MX, MY = 44, 30
PLAYER = (1, 5)
MONSTER = (9, 4)
KEY_CELLS = [(3, 1), (6, 8), (8, 2), (11, 7), (13, 1)]
Point = tuple[int, int]


def cell_center(c: int, r: int) -> tuple[float, float]:
    return MX + c * CELL + CELL / 2, MY + r * CELL + CELL / 2


def maze_segments(seed: int) -> list[tuple[Point, Point]]:
    """DFS recursivo + alguns lacos; devolve segmentos de parede de 1 celula."""
    rng = random.Random(seed)
    open_edges: set[tuple[Point, Point]] = set()
    seen, stack = {(0, 0)}, [(0, 0)]
    while stack:
        c, r = stack[-1]
        options = [
            (c + dc, r + dr)
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= c + dc < COLS and 0 <= r + dr < ROWS and (c + dc, r + dr) not in seen
        ]
        if not options:
            stack.pop()
            continue
        nxt = rng.choice(options)
        open_edges |= {((c, r), nxt), (nxt, (c, r))}
        seen.add(nxt)
        stack.append(nxt)
    for _ in range(14):
        c, r = rng.randrange(COLS - 1), rng.randrange(ROWS - 1)
        other = (c + 1, r) if rng.random() < 0.5 else (c, r + 1)
        open_edges |= {((c, r), other), (other, (c, r))}
    segs: list[tuple[Point, Point]] = []
    for r in range(ROWS):
        for c in range(COLS):
            x, y = MX + c * CELL, MY + r * CELL
            if c + 1 < COLS and ((c, r), (c + 1, r)) not in open_edges:
                segs.append(((x + CELL, y), (x + CELL, y + CELL)))
            if r + 1 < ROWS and ((c, r), (c, r + 1)) not in open_edges:
                segs.append(((x, y + CELL), (x + CELL, y + CELL)))
            if r == 0:
                segs.append(((x, y), (x + CELL, y)))
            if c == 0:
                segs.append(((x, y), (x, y + CELL)))
            if r == ROWS - 1 and c < COLS - 1:  # vao da saida no canto inferior direito
                segs.append(((x, y + CELL), (x + CELL, y + CELL)))
            if c == COLS - 1 and r < ROWS - 1:
                segs.append(((x + CELL, y), (x + CELL, y + CELL)))
    return segs


def junctions(segs: list[tuple[Point, Point]]) -> list[Point]:
    """Pontas, T, cruzes e cantos (nao as passagens retas)."""
    around: dict[Point, set[tuple[int, int]]] = {}
    for a, b in segs:
        dx, dy = (b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1])
        around.setdefault(a, set()).add((dx, dy))
        around.setdefault(b, set()).add((-dx, -dy))
    out = []
    for p, dirs in around.items():
        straight = len(dirs) == 2 and all((-dx, -dy) in dirs for dx, dy in dirs)
        if not straight:
            out.append(p)
    return out


def key_icon(cx: float, cy: float, scale: float, delay: float, rot: float, lit: bool) -> str:
    stroke = ORANGE if lit else GREY
    return (
        f'<g transform="translate({n(cx)} {n(cy)}) rotate({n(rot)}) scale({n(scale)}) translate(-15 -6)">'
        f'<g class="key" fill="none" stroke="{stroke}" stroke-width="1.9" stroke-linecap="round" '
        f'stroke-linejoin="round" style="animation-delay:{n(delay)}s">'
        '<circle cx="6" cy="6" r="5"/><path d="M11 6H29M23 6V11M28 6V10.5"/></g></g>'
    )


def build_game() -> None:
    w, h = 1280, 480
    light, text = font("inter-300"), font("inter-400")
    px, py = cell_center(*PLAYER)
    mx, my = cell_center(*MONSTER)
    segs = maze_segments(21)
    walls = "".join(f"M{a[0]} {a[1]}L{b[0]} {b[1]}" for a, b in segs)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="2.3"/>' for x, y in junctions(segs))

    cycle, window = 6.0, 1.2
    delays = [-((0.6 - window * i) % cycle) for i in range(5)]
    maze_keys = "".join(
        key_icon(*cell_center(*cell), 0.95, delays[i], -30 + 25 * i, i == 0)
        for i, cell in enumerate(KEY_CELLS)
    )
    hud_keys = "".join(key_icon(1068 + i * 38, 396, 0.85, delays[i], 0, i == 0) for i in range(5))

    tx = 740
    chip, _ = svg_text("TERROR COOPERATIVO", text, 12, 12 * 0.4, tx, 88, fill=GREY)
    t_size = fit_size("LABIRINTO", light, 470, 0.4)
    t1, _ = svg_text("LABIRINTO", light, t_size, t_size * 0.4, tx, 160, fill=WHITE)
    t2, _ = svg_text("DO MEDO", light, t_size, t_size * 0.4, tx, 160 + t_size * 1.45, fill=WHITE)
    base = 160 + t_size * 1.45 + 56
    tag1, _ = svg_text("Ache as 5 chaves. Não faça barulho.", text, 20, 0.2, tx, base, fill=GREY)
    tag2, _ = svg_text("O Medo está ouvindo.", text, 20, 0.2, tx, base + 30, fill=WHITE)
    pill_y = 362
    seal, seal_w = svg_text("EM DESENVOLVIMENTO", text, 12, 12 * 0.34, tx + 40, pill_y + 26, fill=WHITE)
    pill_w = seal_w + 40 + 26

    css = (
        "@keyframes sweep{0%,100%{transform:rotate(-26deg)}50%{transform:rotate(24deg)}}"
        "@keyframes blink{0%,90%,100%{transform:scaleY(1)}94%{transform:scaleY(.1)}}"
        f"@keyframes lit{{0%{{stroke:{GREY}}}8%,20%{{stroke:{ORANGE}}}34%,100%{{stroke:{GREY}}}}}"
        "@keyframes seal{0%,100%{stroke-opacity:.3}50%{stroke-opacity:1}}"
        "@keyframes beat{0%,100%{opacity:1}50%{opacity:.3}}"
        ".cone{animation:sweep 11s ease-in-out -3s infinite;transform-box:fill-box;transform-origin:0% 50%}"
        ".eyes{animation:blink 4.6s ease-in-out -1s infinite;transform-box:fill-box;transform-origin:center}"
        f".key{{animation:lit {n(cycle)}s ease-in-out infinite}}"
        ".seal{animation:seal 2.8s ease-in-out infinite}"
        ".beat{animation:beat 2.8s ease-in-out infinite}"
        + PULSE_CSS
    )
    defs = f"""
<clipPath id="card"><rect width="{w}" height="{h}" rx="26"/></clipPath>
<radialGradient id="cone" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="300"><stop offset="0" stop-color="{WHITE}" stop-opacity=".26"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></radialGradient>
<radialGradient id="dark" gradientUnits="userSpaceOnUse" cx="{n(px)}" cy="{n(py)}" r="430"><stop offset=".15" stop-color="{BLACK}" stop-opacity="0"/><stop offset="1" stop-color="{BLACK}" stop-opacity=".82"/></radialGradient>
"""
    eye = lambda dx, rot: (  # noqa: E731
        f'<ellipse cx="{n(mx + dx)}" cy="{n(my)}" rx="6" ry="3.6" fill="{ORANGE}" '
        f'transform="rotate({rot} {n(mx + dx)} {n(my)})"/>'
    )
    body = f"""
<g clip-path="url(#card)">
<rect width="{w}" height="{h}" fill="{BLACK}"/>
<path d="{walls}" fill="none" stroke="{WHITE}" stroke-opacity=".35" stroke-width="2" stroke-linecap="round"/>
<g fill="{WHITE}" fill-opacity=".55">{dots}</g>
<rect x="{MX}" y="{MY}" width="{COLS * CELL}" height="{ROWS * CELL}" fill="url(#dark)"/>
<g transform="translate({n(px)} {n(py)})"><g class="cone" transform="rotate(-3)">
<path d="M0 0L300 -130A327 327 0 0 1 300 130Z" fill="url(#cone)"/>
<path d="M0 0L300 -130M0 0L300 130" stroke="{WHITE}" stroke-opacity=".16" stroke-width="1" fill="none"/>
</g></g>
<circle cx="{n(px)}" cy="{n(py)}" r="4.5" fill="{WHITE}"/>
<circle cx="{n(px)}" cy="{n(py)}" r="9" fill="none" stroke="{WHITE}" stroke-opacity=".4" stroke-width="1"/>
{maze_keys}
<g class="eyes">{eye(-10, 12)}{eye(10, -12)}</g>

{chip}
{t1}
{t2}
{tag1}
{tag2}
<rect class="seal" x="{tx}" y="{pill_y}" width="{n(pill_w)}" height="40" rx="20" fill="none" stroke="{ORANGE}" stroke-width="1.2"/>
<circle class="beat" cx="{tx + 22}" cy="{pill_y + 20}" r="3.4" fill="{ORANGE}"/>
{seal}
{hud_keys}
</g>
<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="25" fill="none" stroke="{BORDER}" stroke-width="1.5"/>
"""
    write(
        "game-labirinto.svg",
        svg_doc(
            w, h, "Labirinto do Medo",
            "Card do jogo Labirinto do Medo, terror cooperativo em desenvolvimento: labirinto de arame, lanterna, cinco chaves e dois olhos laranja no escuro.",
            css, defs, body,
        ),
    )


if __name__ == "__main__":
    build_banner()
    build_typing()
    build_divider()
    build_footer()
    build_game()
