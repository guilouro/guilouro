#!/usr/bin/env python3
"""Build the SVG assets used by the profile README.

Text is converted to outlines, so the images look the same on every machine,
and every icon is self-hosted, so the README never depends on a third-party
image service being up.

    python3 -m venv .venv
    .venv/bin/pip install -r scripts/requirements.txt
    .venv/bin/python scripts/build_assets.py

Edit BANNER, STATS or STACK below and run it again to refresh the assets.
"""

import math
import pathlib
import re
import urllib.request

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CACHE = ROOT / ".cache"

FONTS = {
    "sans": "https://github.com/google/fonts/raw/main/ofl/geist/Geist%5Bwght%5D.ttf",
    "mono": "https://github.com/google/fonts/raw/main/ofl/geistmono/GeistMono%5Bwght%5D.ttf",
}

BANNER = {
    "name": "Guilherme Louro",
    "title": "Staff Software Engineer",
    "tagline": "Frontend architecture  ·  Platform engineering  ·  Applied AI",
    "code": '{ since: 2007, based: "Petrópolis, BR" }',
}

# "★" is not in Geist, so it is drawn as a shape.
STATS = [
    ("~20 yrs", "building for the web"),
    ("12.9K", "students, 4.9★ course"),
    ("1M", "monthly views (peak)"),
    ("10+ yrs", "running my own product"),
]

THEMES = {
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "dots": "#30363d",
        "glow1": ("#2f81f7", 0.35), "glow2": ("#3fb950", 0.18),
        "text": "#e6edf3", "muted": "#9198a1", "subtle": "#6e7681",
        "accent": ("#4493f8", "#3fb950"),
    },
    "light": {
        "bg": "#ffffff", "border": "#d1d9e0", "dots": "#d1d9e0",
        "glow1": ("#0969da", 0.14), "glow2": ("#1a7f37", 0.10),
        "text": "#1f2328", "muted": "#59636e", "subtle": "#818b98",
        "accent": ("#0969da", "#1a7f37"),
    },
}

SKILLICONS = "https://skillicons.dev/icons?i={}"
LOBE = "https://unpkg.com/@lobehub/icons-static-svg@1.68.0/icons/{}.svg"
DEVICON = "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/{0}/{0}-original.svg"

# Stack icons, by id. ("skill", id) comes ready from skillicons.dev; the others
# are drawn on a tile in the same style. Mono icons are painted white, and an
# optional last value sets the icon size inside the 256px tile (default 150).
STACK = {
    "typescript": ("skill", "ts"), "javascript": ("skill", "js"),
    "react": ("skill", "react"), "nextjs": ("skill", "nextjs"),
    "redux": ("skill", "redux"), "tailwind": ("skill", "tailwind"),
    "styled-components": ("skill", "styledcomponents"),
    "nodejs": ("skill", "nodejs"), "python": ("skill", "python"),
    "django": ("skill", "django"), "fastapi": ("skill", "fastapi"),
    "graphql": ("skill", "graphql"), "postgres": ("skill", "postgres"),
    "mysql": ("skill", "mysql"), "redis": ("skill", "redis"),
    "rabbitmq": ("skill", "rabbitmq"), "docker": ("skill", "docker"),
    "aws": ("skill", "aws"), "cloudflare": ("skill", "cloudflare"),
    "github-actions": ("skill", "githubactions"), "jest": ("skill", "jest"),
    "vitest": ("skill", "vitest"), "cypress": ("skill", "cypress"),
    "playwright": ("tile", DEVICON.format("playwright"), None, 210),
    "openai": ("tile", LOBE.format("openai"), "#ffffff"),
    "claude": ("tile", LOBE.format("claude-color"), None),
    "crewai": ("tile", LOBE.format("crewai-color"), None),
    "langchain": ("tile", LOBE.format("langchain"), "#ffffff"),
    "mcp": ("tile", LOBE.format("mcp"), "#ffffff"),
}


def fetch(url, dest):
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "profile-assets"})
        with urllib.request.urlopen(req, timeout=30) as res:
            dest.write_bytes(res.read())
    return dest


def num(v):
    s = f"{v:.1f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


class Text:
    """Shapes text with HarfBuzz and returns it as a single SVG path."""

    def __init__(self, path):
        self.face = hb.Face(hb.Blob.from_file_path(str(path)))
        self.font = hb.Font(self.face)

    def path(self, text, size, x, y, weight=400, tracking=0.0, anchor="start", fill="#000"):
        self.font.set_variations({"wght": weight})
        scale = size / self.face.upem
        runs = text.split("★")
        glyphs, stars, pen_x = [], [], 0.0
        for i, run in enumerate(runs):
            if run:
                buf = hb.Buffer()
                buf.add_str(run)
                buf.guess_segment_properties()
                hb.shape(self.font, buf, {"kern": True, "liga": True})
                for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
                    if info.codepoint == 0:
                        raise ValueError(f"missing glyph in {text!r}")
                    glyphs.append((info.codepoint, pen_x + pos.x_offset * scale, pos.y_offset * scale))
                    pen_x += pos.x_advance * scale + tracking * size
            if i < len(runs) - 1:
                stars.append(pen_x + size * 0.42)
                pen_x += size * 0.86
        width = pen_x - tracking * size
        x0 = x - {"start": 0, "middle": width / 2, "end": width}[anchor]
        pen = SVGPathPen(None, ntos=num)
        for gid, gx, gy in glyphs:
            self.font.draw_glyph_with_pen(gid, TransformPen(pen, (scale, 0, 0, -scale, x0 + gx, y - gy)))
        d = pen.getCommands()
        for cx in stars:
            d += star(x0 + cx, y - size * 0.35, size * 0.42)
        return f'<path fill="{fill}" d="{d}"/>'


def star(cx, cy, r):
    pts = []
    for k in range(10):
        rad = r if k % 2 == 0 else r * 0.45
        a = -math.pi / 2 + k * math.pi / 5
        pts.append(f"{num(cx + rad * math.cos(a))} {num(cy + rad * math.sin(a))}")
    return "M" + "L".join(pts) + "Z"


def banner(sans, mono, t):
    w, h = 1200, 300
    c1, c2 = t["accent"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f"<title>{BANNER['name']}, {BANNER['title']}</title>",
        "<defs>",
        f'<radialGradient id="g1" cx="85%" cy="10%" r="70%"><stop offset="0" stop-color="{t["glow1"][0]}" stop-opacity="{t["glow1"][1]}"/><stop offset="1" stop-color="{t["glow1"][0]}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="g2" cx="100%" cy="100%" r="60%"><stop offset="0" stop-color="{t["glow2"][0]}" stop-opacity="{t["glow2"][1]}"/><stop offset="1" stop-color="{t["glow2"][0]}" stop-opacity="0"/></radialGradient>',
        f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.4" fill="{t["dots"]}"/></pattern>',
        f'<linearGradient id="accent" x1="66" x2="470" y1="0" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>',
        '<linearGradient id="fade" x1="0" x2="1"><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>',
        f'<mask id="m"><rect width="{w}" height="{h}" fill="url(#fade)"/></mask>',
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath>',
        "</defs>",
        '<g clip-path="url(#clip)">',
        f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>',
        f'<rect width="{w}" height="{h}" fill="url(#dots)" mask="url(#m)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g1)"/>',
        f'<rect width="{w}" height="{h}" fill="url(#g2)"/>',
        "</g>",
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="{t["border"]}"/>',
        sans.path(BANNER["name"], 66, 64, 128, weight=700, tracking=-0.025, fill=t["text"]),
        sans.path(BANNER["title"], 30, 66, 182, weight=600, tracking=-0.01, fill="url(#accent)"),
        sans.path(BANNER["tagline"], 21, 66, 228, fill=t["muted"]),
        mono.path(BANNER["code"], 16, 1136, 262, anchor="end", fill=t["subtle"]),
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def stats(sans, t):
    w, h = 1200, 150
    cell = w / len(STATS)
    alt = ". ".join(f"{n} {label}" for n, label in STATS).replace("★", " star")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f"<title>{alt}</title>",
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>',
    ]
    for i, (value, label) in enumerate(STATS):
        cx = cell * i + cell / 2
        if i:
            parts.append(f'<path stroke="{t["border"]}" d="M{num(cell * i)} 1v{h - 2}"/>')
        parts.append(sans.path(value, 46, cx, 80, weight=700, tracking=-0.02, anchor="middle", fill=t["text"]))
        parts.append(sans.path(label, 20, cx, 116, anchor="middle", fill=t["muted"]))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def tile(src, color, size=150):
    raw = src.read_text()
    view_box = re.search(r'viewBox="([^"]+)"', raw).group(1)
    inner = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", raw, flags=re.S)
    inner = re.sub(r"<title>.*?</title>", "", inner, flags=re.S)
    fill = f' fill="{color}"' if color else ""
    rule = ' fill-rule="evenodd"' if 'fill-rule="evenodd"' in raw.split(">", 1)[0] else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256" fill="none">'
        '<rect width="256" height="256" fill="#242938" rx="60"/>'
        f'<svg x="{(256 - size) / 2:g}" y="{(256 - size) / 2:g}" width="{size}" height="{size}" viewBox="{view_box}"{fill}{rule}>{inner}</svg>'
        "</svg>\n"
    )


def main():
    sans = Text(fetch(FONTS["sans"], CACHE / "Geist.ttf"))
    mono = Text(fetch(FONTS["mono"], CACHE / "GeistMono.ttf"))

    for name, theme in THEMES.items():
        (ASSETS / f"banner-{name}.svg").write_text(banner(sans, mono, theme))
        (ASSETS / f"stats-{name}.svg").write_text(stats(sans, theme))

    stack_dir = ASSETS / "stack"
    stack_dir.mkdir(parents=True, exist_ok=True)
    for name, spec in STACK.items():
        if spec[0] == "skill":
            src = fetch(SKILLICONS.format(spec[1]), CACHE / "icons" / f"skill-{spec[1]}.svg")
            svg = src.read_text().strip()
            if "<rect" not in svg:
                raise ValueError(f"skillicons has no icon for {spec[1]!r}")
            (stack_dir / f"{name}.svg").write_text(svg + "\n")
        else:
            src = fetch(spec[1], CACHE / "icons" / f"tile-{name}.svg")
            (stack_dir / f"{name}.svg").write_text(tile(src, *spec[2:]))

    print(f"wrote {len(THEMES) * 2} theme assets and {len(STACK)} stack icons")


if __name__ == "__main__":
    main()
