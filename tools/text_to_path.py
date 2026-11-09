"""Converte texto em <path> SVG (fontTools), sem depender de fonte no cliente.

Uso como biblioteca:
    from text_to_path import font, layout, svg_text
    f = font("inter-300")
    g, width = svg_text("BRASA", f, size=96, tracking=2, x=0, y=96, fill="#FFF3E6")

Uso na linha de comando:
    uv run --with fonttools python tools/text_to_path.py "Olá" --font inter-400 \
        --size 40 --tracking 1 --anchor middle --x 450 --y 40 --fill "#FF5A1F"
    (imprime o <path> no stdout e a largura em stderr; --glyphs devolve um <g> com um
    <path> por glifo, util para animar letra a letra)

Limitacoes assumidas: sem kerning (GPOS) e sem ligaduras; avanco horizontal vem da hmtx
mais o tracking em px. Suficiente para titulos e frases curtas de banner.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
INTER_URL = "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf"
# nome -> eixos fixados na instancia (opsz 32 = desenho para titulos grandes)
INTER_INSTANCES = {
    "inter-300": {"wght": 300, "opsz": 32},
    "inter-400": {"wght": 400, "opsz": 14},
}


@dataclass(frozen=True)
class Glyph:
    char: str
    x: float  # posicao do glifo (px, origem do texto)
    advance: float  # avanco do glifo sem tracking (px)
    d: str  # path 'd' ja posicionado em x/y absolutos


@dataclass(frozen=True)
class Layout:
    glyphs: list[Glyph]
    width: float  # largura total (ultimo glifo sem tracking final)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (https fixo)
        dest.write_bytes(resp.read())


def ensure_fonts() -> None:
    """Baixa Inter do google/fonts (OFL) e instancia 300 e 400."""
    variable = FONTS_DIR / "Inter-VF.ttf"
    if not variable.exists():
        _download(INTER_URL, variable)
    for name, axes in INTER_INSTANCES.items():
        out = FONTS_DIR / f"{name}.ttf"
        if not out.exists():
            instancer.instantiateVariableFont(TTFont(variable), axes).save(out)


_CACHE: dict[str, TTFont] = {}


def font(name: str) -> TTFont:
    """name: 'inter-300' (titulos) ou 'inter-400' (texto)."""
    if name in _CACHE:
        return _CACHE[name]
    if name not in INTER_INSTANCES:
        raise ValueError(f"fonte desconhecida: {name} (use {', '.join(INTER_INSTANCES)})")
    ensure_fonts()
    _CACHE[name] = TTFont(FONTS_DIR / f"{name}.ttf")
    return _CACHE[name]


def _fmt(value: float) -> str:
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def layout(
    text: str, ttfont: TTFont, size: float, tracking: float = 0.0, x: float = 0.0, y: float = 0.0
) -> Layout:
    """Posiciona cada glifo. `y` e a linha de base; `x` o inicio (anchor start)."""
    cmap = ttfont.getBestCmap()
    glyph_set = ttfont.getGlyphSet()
    scale = size / ttfont["head"].unitsPerEm
    cursor = 0.0
    glyphs: list[Glyph] = []
    for char in text:
        name = cmap.get(ord(char)) or ".notdef"
        advance = ttfont["hmtx"][name][0] * scale
        pen = SVGPathPen(glyph_set, ntos=_fmt)
        glyph_set[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x + cursor, y)))
        glyphs.append(Glyph(char, x + cursor, advance, pen.getCommands()))
        cursor += advance + tracking
    return Layout(glyphs, max(cursor - tracking, 0.0))


def measure(text: str, ttfont: TTFont, size: float, tracking: float = 0.0) -> float:
    return layout(text, ttfont, size, tracking).width


def fit_size(text: str, ttfont: TTFont, max_width: float, tracking_em: float = 0.0) -> float:
    """Maior tamanho (px) em que o texto cabe em max_width; tracking como fracao do corpo."""
    unit = measure(text, ttfont, 100.0, 100.0 * tracking_em)
    return max_width / unit * 100.0


def svg_text(
    text: str,
    ttfont: TTFont,
    size: float,
    tracking: float = 0.0,
    x: float = 0.0,
    y: float = 0.0,
    fill: str | None = None,
    anchor: str = "start",
    attrs: str = "",
    per_glyph: bool = False,
) -> tuple[str, float]:
    """Devolve (markup, largura). anchor: start | middle | end."""
    width = measure(text, ttfont, size, tracking)
    offset = {"start": 0.0, "middle": -width / 2, "end": -width}[anchor]
    lay = layout(text, ttfont, size, tracking, x + offset, y)
    fill_attr = f' fill="{fill}"' if fill else ""
    extra = f" {attrs}" if attrs else ""
    if per_glyph:
        parts = [
            f'<path d="{g.d}"/>' for g in lay.glyphs if g.d  # espacos nao geram path
        ]
        return f'<g{fill_attr}{extra}>{"".join(parts)}</g>', width
    d = "".join(g.d for g in lay.glyphs)
    return f'<path{fill_attr}{extra} d="{d}"/>', width


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("text")
    parser.add_argument("--font", default="inter-400")
    parser.add_argument("--size", type=float, default=32)
    parser.add_argument("--tracking", type=float, default=0.0, help="px entre glifos")
    parser.add_argument("--x", type=float, default=0.0)
    parser.add_argument("--y", type=float, default=0.0)
    parser.add_argument("--fill", default=None)
    parser.add_argument("--anchor", choices=["start", "middle", "end"], default="start")
    parser.add_argument("--glyphs", action="store_true", help="um <path> por glifo dentro de <g>")
    args = parser.parse_args()
    markup, width = svg_text(
        args.text, font(args.font), args.size, args.tracking, args.x, args.y,
        args.fill, args.anchor, per_glyph=args.glyphs,
    )
    print(markup)
    print(f"largura={width:.2f}", file=sys.stderr)


if __name__ == "__main__":
    main()
