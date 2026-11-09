"""Gera os arquivos oficiais de marca da Brasa Studios em brand/.

    uv run --with fonttools python tools/build_brand.py

A geometria do logo vem de build_assets.logo_mark (fonte unica, a mesma do banner).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from build_assets import (
    BLACK, BORDER, GREY, LOGO_CENTROID_Y, ORANGE, WHITE, logo_mark, n, svg_doc,
)
from text_to_path import font, svg_text

BRAND = Path(__file__).resolve().parent.parent / "brand"
RENDERS = BRAND / "_explore" / "renders"
# centro optico: entre o centro da caixa e o centroide (o triangulo "pesa" embaixo)
BOX_CENTER_Y = (92 + 356) / 2
OPTICAL_Y = BOX_CENTER_Y + (LOGO_CENTROID_Y - BOX_CENTER_Y) / 3
INK_LIGHT, GREY_LIGHT = "#0E0E0E", "#6B6B6B"
NAME = "Brasa Studios"


def write(name: str, content: str) -> Path:
    BRAND.mkdir(parents=True, exist_ok=True)
    path = BRAND / name
    path.write_text(content, encoding="utf-8")
    print(f"{name}: {path.stat().st_size / 1024:.1f} KB")
    return path


def static_doc(w: int, h: int, title: str, desc: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-labelledby="t d"><title id="t">{title}</title><desc id="d">{desc}</desc>'
        f"{body}</svg>\n"
    )


def lockup(ink: str, grey: str, dark: bool) -> str:
    """Triangulo em cima, BRASA em Inter 300 e STUDIOS pequeno; mesmas proporcoes do banner."""
    w, h = 640, 400
    mark, _ = logo_mark(ink=ink)
    title, _ = svg_text("BRASA", font("inter-300"), 76, 76 * 0.4, w / 2, 276, fill=ink, anchor="middle")
    sub, _ = svg_text("STUDIOS", font("inter-400"), 14, 14 * 0.4, w / 2, 328, fill=grey, anchor="middle")
    bg = (
        f'<rect width="{w}" height="{h}" rx="24" fill="{BLACK}"/>'
        f'<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="23" fill="none" stroke="{BORDER}" stroke-width="1.5"/>'
        if dark else ""
    )
    body = f'{bg}<g transform="translate({n(w / 2 - 75)} 40) scale(.293)">{mark}</g>{title}{sub}'
    return static_doc(w, h, f"{NAME}, lockup", "Triângulo de três vértices com o de cima laranja, BRASA e STUDIOS.", body)


def build() -> None:
    mark_white, _ = logo_mark()
    write("logo-mark.svg", static_doc(512, 512, NAME, "Logo da Brasa Studios: triângulo de três vértices, o de cima laranja.", mark_white))
    mark_dark, _ = logo_mark(ink=INK_LIGHT)
    write("logo-mark-light.svg", static_doc(512, 512, NAME, "Logo da Brasa Studios para fundo claro.", mark_dark))

    animated, css = logo_mark(animated=True)
    write("logo-animated.svg", svg_doc(512, 512, NAME, "Logo animado: arestas se desenham, vértices acendem e o anel laranja pulsa.", css, "", animated))

    scale = 0.88  # margem ~17% por lado; arestas e vertices grossos para ler a 40 px
    thick, _ = logo_mark(edge_w=34, r=42, r_top=46)
    avatar_body = (
        f'<rect width="512" height="512" fill="{BLACK}"/>'
        f'<g transform="translate(256 256) scale({scale}) translate(-256 -{n(OPTICAL_Y)})">{thick}</g>'
    )
    avatar = write("avatar.svg", static_doc(512, 512, f"{NAME}, avatar", "Triângulo de três vértices com o de cima laranja sobre fundo preto.", avatar_body))
    subprocess.run(["rsvg-convert", "-w", "1024", "-h", "1024", str(avatar), "-o", str(BRAND / "avatar.png")], check=True)

    write("lockup-dark.svg", lockup(WHITE, GREY, dark=True))
    write("lockup-light.svg", lockup(INK_LIGHT, GREY_LIGHT, dark=False))

    RENDERS.mkdir(parents=True, exist_ok=True)
    for size in (1024, 96, 40):
        subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), "-b", "#0D1117", str(avatar),
                        "-o", str(RENDERS / f"official-avatar-{size}.png")], check=True)
    for name, bgc in (("lockup-dark", "#0D1117"), ("lockup-light", "#FFFFFF")):
        subprocess.run(["rsvg-convert", "-b", bgc, str(BRAND / f"{name}.svg"), "-o", str(RENDERS / f"official-{name}.png")], check=True)
    for name in ("logo-mark-light",):
        subprocess.run(["rsvg-convert", "-w", "256", "-b", "#FFFFFF", str(BRAND / f"{name}.svg"), "-o", str(RENDERS / f"official-{name}.png")], check=True)


if __name__ == "__main__":
    build()
