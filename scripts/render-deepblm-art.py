#!/usr/bin/env python3
"""Generate the five DeepBLM Studio art plates (assets/deepblm-art/*.webp).

Deterministic, offline, no external assets. The script writes hand-authored SVG
sources to assets/deepblm-art/svg/, renders them with headless Chromium at 2x
(3200x2000), then downsamples to 1600x1000 and encodes lossy WebP.

Usage:
  .venv/bin/python scripts/render-deepblm-art.py [--svg-only]

Chromium render needs Playwright. The WebP encoder uses a Python interpreter
with Pillow; set DEEPBLM_PIL_PYTHON to its path (WSL default: /usr/bin/python3).
Temporary renders use TMPDIR when set; no network, paid model or source photos.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "deepblm-art")
SVG_DIR = os.path.join(OUT, "svg")
PIL_PY = os.environ.get("DEEPBLM_PIL_PYTHON", "/usr/bin/python3")

W, H = 1600, 1000
SCALE = 2

# restrained palette shared by all five plates
INK = "#101b35"
BLUE = "#1677ff"
DEEP = "#0057c2"
VIOLET = "#8f7bf0"
CYAN = "#6fd6e8"
SILVER = "#c9d3e0"


class S:
    def __init__(self):
        self.defs = []
        self.body = []
        self.n = 0

    def uid(self, p="g"):
        self.n += 1
        return "%s%d" % (p, self.n)

    def lg(self, x1, y1, x2, y2, stops, units=True):
        i = self.uid("l")
        u = ' gradientUnits="userSpaceOnUse"' if units else ""
        self.defs.append(
            '<linearGradient id="%s"%s x1="%s" y1="%s" x2="%s" y2="%s">%s</linearGradient>'
            % (i, u, x1, y1, x2, y2, "".join(
                '<stop offset="%s" stop-color="%s" stop-opacity="%s"/>' % st for st in stops))
        )
        return i

    def rg(self, cx, cy, r, stops, units=True):
        i = self.uid("r")
        u = ' gradientUnits="userSpaceOnUse"' if units else ""
        self.defs.append(
            '<radialGradient id="%s"%s cx="%s" cy="%s" r="%s">%s</radialGradient>'
            % (i, u, cx, cy, r, "".join(
                '<stop offset="%s" stop-color="%s" stop-opacity="%s"/>' % st for st in stops))
        )
        return i

    def add(self, *items):
        self.body.extend(items)

    def svg(self):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d">\n<defs>\n%s\n%s\n</defs>\n%s\n</svg>\n'
            % (W, H, W, H, base_defs(), "\n".join(self.defs),
               "\n".join(self.body))
        )


def base_defs():
    return """
<linearGradient id="bg" x1="0" y1="0" x2="0.35" y2="1">
  <stop offset="0" stop-color="#f6f9fc"/>
  <stop offset="0.35" stop-color="#e8eef6"/>
  <stop offset="0.7" stop-color="#cddaea"/>
  <stop offset="1" stop-color="#b3c5da"/>
</linearGradient>
<radialGradient id="halo" cx="1110" cy="440" r="620" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/>
  <stop offset="0.5" stop-color="#f2f7fd" stop-opacity="0.28"/>
  <stop offset="1" stop-color="#e6edf6" stop-opacity="0"/>
</radialGradient>
<radialGradient id="vig" cx="800" cy="500" r="980" gradientUnits="userSpaceOnUse">
  <stop offset="0.5" stop-color="#0b1727" stop-opacity="0"/>
  <stop offset="0.8" stop-color="#0b1727" stop-opacity="0.07"/>
  <stop offset="1" stop-color="#0b1727" stop-opacity="0.2"/>
</radialGradient>
<linearGradient id="floor" x1="0" y1="700" x2="0" y2="1000" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#dae3ee" stop-opacity="0"/>
  <stop offset="1" stop-color="#a9bacf" stop-opacity="0.7"/>
</linearGradient>
<filter id="b6" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="b14" x="-70%" y="-70%" width="240%" height="240%"><feGaussianBlur stdDeviation="14"/></filter>
<filter id="b28" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="28"/></filter>
<filter id="b60" x="-90%" y="-90%" width="280%" height="280%"><feGaussianBlur stdDeviation="60"/></filter>
<linearGradient id="densV" x1="0" y1="0" x2="0.12" y2="1" gradientUnits="objectBoundingBox">
  <stop offset="0" stop-color="#ffffff"/><stop offset="0.22" stop-color="#c3d6ea"/>
  <stop offset="0.6" stop-color="#8ea8c6"/><stop offset="0.86" stop-color="#5b769b"/>
  <stop offset="1" stop-color="#96aecb"/>
</linearGradient>
<linearGradient id="densRing" x1="0" y1="0" x2="0.3" y2="1" gradientUnits="objectBoundingBox">
  <stop offset="0" stop-color="#ffffff"/><stop offset="0.45" stop-color="#a8c2dd"/>
  <stop offset="0.8" stop-color="#6d88aa"/><stop offset="1" stop-color="#b8cde3"/>
</linearGradient>
<filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="7"/>
  <feColorMatrix type="saturate" values="0"/>
</filter>
"""


def frame(s, img_filter=None):
    """Background, floor, halo, vignette and grain shared by every plate."""
    s.add('<rect width="1600" height="1000" fill="url(#bg)"/>')
    s.add('<rect width="1600" height="1000" fill="url(#halo)"/>')
    s.add('<rect y="640" width="1600" height="360" fill="url(#floor)"/>')


def finish(s):
    s.add('<rect width="1600" height="1000" fill="url(#vig)"/>')
    s.add('<rect width="1600" height="1000" filter="url(#grain)" opacity="0.045" '
          'style="mix-blend-mode:overlay"/>')


def glass(s, x1, y1, x2, y2, a=0.9, tint=CYAN, tint_a=0.20, tint2=VIOLET, tint2_a=0.16):
    """Layered glass gradient: white rim, cool body, tint and second tint."""
    return s.lg(x1, y1, x2, y2, [
        ("0", "#ffffff", a),
        ("0.1", "#dce8f6", 0.97),
        ("0.3", tint, 0.72),
        ("0.44", "#93aecb", 1.0),
        ("0.62", "#718aab", 1.0),
        ("0.8", "#4f6b8d", 1.0),
        ("0.93", tint2, 0.55),
        ("1", "#c9dcef", 0.95),
    ])


def metal(s, x1, y1, x2, y2):
    return s.lg(x1, y1, x2, y2, [
        ("0", "#ffffff", 0.95),
        ("0.28", "#dfe6ef", 0.95),
        ("0.52", "#a9b8cc", 0.95),
        ("0.72", "#e8eef6", 0.95),
        ("1", "#b6c3d4", 0.95),
    ])


def shadow(s, cx, cy, rx, ry, op=0.30, blur="b28"):
    s.add('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#1d2c46" opacity="%s" '
          'filter="url(#%s)"/>' % (cx, cy, rx, ry, op, blur))


def sphere(s, cx, cy, r):
    """Frosted metal-glass sphere with rim light and specular."""
    body = s.rg(cx - r * 0.35, cy - r * 0.45, r * 1.85, [
        ("0", "#ffffff", 0.98),
        ("0.14", "#f4f8fd", 0.95),
        ("0.36", "#c2d4e9", 0.96),
        ("0.62", "#7e97b6", 0.95),
        ("0.84", "#5c7595", 0.95),
        ("0.95", "#9fb5cc", 0.95),
        ("1", "#e6eef8", 0.95),
    ])
    rim = s.lg(cx - r, cy - r, cx + r, cy + r, [
        ("0", "#ffffff", 0.9), ("0.5", "#ffffff", 0.1), ("1", "#ffffff", 0.55)])
    s.add('<circle cx="%s" cy="%s" r="%s" fill="url(#%s)"/>' % (cx, cy, r, body))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="url(#%s)" stroke-width="2"/>'
          % (cx, cy, r * 0.995, rim))
    s.add('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#ffffff" opacity="0.85" '
          'filter="url(#b6)"/>' % (cx - r * 0.36, cy - r * 0.44, r * 0.3, r * 0.22))
    s.add('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#ffffff" opacity="0.35" '
          'filter="url(#b14)"/>' % (cx + r * 0.1, cy + r * 0.62, r * 0.5, r * 0.16))


# ---------------------------------------------------------------- plate 1
def plate_insight():
    s = S()
    frame(s)
    # ambient pool of light behind the subject
    s.add('<ellipse cx="1110" cy="470" rx="330" ry="270" fill="#ffffff" opacity="0.16" '
          'filter="url(#b60)"/>')
    shadow(s, 1120, 790, 250, 34, 0.22, "b28")

    # incoming light wedge from the left
    s.add('<path d="M600 470 L1010 424 L1010 512 Z" fill="#ffffff" opacity="0.55" '
          'filter="url(#b14)"/>')
    s.add('<path d="M600 470 L1010 424 L1010 512 Z" fill="#dff1ff" opacity="0.30" '
          'filter="url(#b6)"/>')

    # dispersing strands leaving the prism (very restrained)
    for col, dy, op, wd in ((CYAN, -34, 0.85, 9), (BLUE, 6, 0.75, 11), (VIOLET, 44, 0.7, 8)):
        s.add('<path d="M1230 470 Q1330 %s 1450 %s" fill="none" stroke="%s" '
              'stroke-width="%d" opacity="%s" filter="url(#b6)"/>'
              % (470 + dy * 0.9, 470 + dy, col, wd, op))
        s.add('<path d="M1230 470 Q1330 %s 1450 %s" fill="none" stroke="%s" '
              'stroke-width="2" opacity="%s" stroke-linecap="round"/>'
              % (470 + dy * 0.9, 470 + dy, col, op * 0.8))

    # prism body (apex up, tilted)
    s.add('<g transform="rotate(-6 1120 520)">')
    tri = "M1120 236 L1310 742 L930 742 Z"
    s.add('<path d="%s" fill="#ffffff" opacity="0.30" filter="url(#b14)" '
          'transform="translate(6 10)"/>' % tri)
    prism = s.lg(930, 236, 1310, 742, [
        ("0", "#ffffff", 0.99), ("0.18", "#e9f2fc", 0.96), ("0.4", "#bcd2ea", 0.94),
        ("0.58", CYAN, 0.55), ("0.72", "#7d97b7", 0.9), ("0.86", VIOLET, 0.45),
        ("1", "#ffffff", 0.95)])
    s.add('<path d="%s" fill="url(%s)"/>' % (tri, prism))
    # inner facets: refraction bands
    s.add('<path d="M1120 262 L1150 736 L1078 736 Z" fill="#ffffff" opacity="0.30" '
          'filter="url(#b6)"/>')
    s.add('<path d="M1120 300 L1292 726 L1190 726 Z" fill="%s" opacity="0.16" '
          'filter="url(#b6)"/>' % VIOLET)
    s.add('<path d="M968 700 L1010 700 L1240 700 L1252 742 L946 742 Z" fill="#ffffff" '
          'opacity="0.22"/>')
    # body density so the glass reads against a light ground
    s.add('<path d="%s" fill="url(#densV)" style="mix-blend-mode:multiply" opacity="0.62"/>' % tri)
    # edges: dark contact line under the white highlight reads as real glass
    s.add('<path d="%s" fill="none" stroke="#4b6484" stroke-width="2.4" opacity="0.42" '
          'stroke-linejoin="round"/>' % tri)
    s.add('<path d="%s" fill="none" stroke="#ffffff" stroke-width="2.2" opacity="0.95" '
          'stroke-linejoin="round"/>' % tri)
    s.add('<path d="M1120 236 L1310 742" fill="none" stroke="%s" stroke-width="1.6" '
          'opacity="0.4"/>' % CYAN)
    # specular streak
    s.add('<path d="M1098 300 L1120 300 L1052 640 L1030 640 Z" fill="#ffffff" '
          'opacity="0.42" filter="url(#b6)"/>')
    s.add('</g>')

    # floating lens disc
    lx, ly, lr = 1290, 330, 118
    shadow(s, lx + 12, ly + lr + 34, lr * 0.8, 16, 0.13, "b14")
    rim = s.rg(lx - 30, ly - 40, lr * 1.2, [("0", "#ffffff", 0.95), ("0.6", "#cfdbea", 0.95),
                                            ("1", "#9fb2ca", 0.95)])
    s.add('<circle cx="%s" cy="%s" r="%s" fill="url(%s)"/>' % (lx, ly, lr, rim))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="url(%s)"/>'
          % (lx, ly, lr - 14, glass(s, lx - lr, ly - lr, lx + lr, ly + lr, 0.75)))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#ffffff" stroke-width="1.4" '
          'opacity="0.9"/>' % (lx, ly, lr - 14))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="url(#densV)" style="mix-blend-mode:multiply" '
          'opacity="0.45"/>' % (lx, ly, lr - 14))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#60789a" stroke-width="1.8" '
          'opacity="0.45"/>' % (lx, ly, lr + 1))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#ffffff" stroke-width="1.6" '
          'opacity="0.9"/>' % (lx, ly, lr - 1))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#7e94ae" stroke-width="1.4" '
          'opacity="0.35"/>' % (lx, ly, lr - 14))
    s.add('<path d="M%s %s a115 115 0 0 1 96 -66" fill="none" stroke="#ffffff" '
          'stroke-width="7" opacity="0.55" filter="url(#b6)"/>'
          % (lx - 82, ly - 78))
    finish(s)
    return s


# ---------------------------------------------------------------- plate 2
def plate_strategy():
    s = S()
    frame(s)
    s.add('<ellipse cx="1090" cy="490" rx="340" ry="260" fill="#ffffff" opacity="0.16" '
          'filter="url(#b60)"/>')
    shadow(s, 1090, 800, 260, 32, 0.2, "b28")

    cx, cy = 1090, 492
    rings = (
        (300, 108, -18, CYAN, 0.55),
        (352, 128, 12, BLUE, 0.5),
        (250, 92, -46, VIOLET, 0.45),
    )
    for rx, ry, rot, col, op in rings:
        s.add('<g transform="rotate(%s %s %s)">' % (rot, cx, cy))
        s.add('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="none" stroke="%s" '
              'stroke-width="7" opacity="%s" filter="url(#b6)"/>'
              % (cx, cy, rx, ry, col, op * 0.55))
        s.add('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="none" stroke="url(%s)" '
              'stroke-width="2.4" opacity="0.85"/>'
              % (cx, cy, rx, ry, s.lg(cx - rx, cy - ry, cx + rx, cy + ry, [
                  ("0", "#ffffff", 0.95), ("0.45", col, 0.85), ("1", "#ffffff", 0.7)])))
        s.add('</g>')

    # nodes riding the orbits
    import math
    nodes = ((300, 108, -18, 40), (300, 108, -18, 200), (352, 128, 12, 145),
             (352, 128, 12, 300), (250, 92, -46, 70))
    for rx, ry, rot, deg in nodes:
        a = math.radians(deg)
        px = cx + rx * math.cos(a)
        py = cy + ry * math.sin(a)
        rr = math.radians(rot)
        dx, dy = px - cx, py - cy
        px = cx + dx * math.cos(rr) - dy * math.sin(rr)
        py = cy + dx * math.sin(rr) + dy * math.cos(rr)
        shadow(s, px + 6, py + 16, 20, 7, 0.16, "b14")
        sphere(s, px, py, 15)

    # core
    shadow(s, cx + 18, cy + 128, 120, 20, 0.18, "b14")
    s.add('<circle cx="%s" cy="%s" r="%s" fill="#ffffff" opacity="0.45" '
          'filter="url(#b14)"/>' % (cx, cy, 132))
    sphere(s, cx, cy, 108)
    s.add('<circle cx="%s" cy="%s" r="112" fill="none" stroke="#ffffff" stroke-width="1.2" '
          'opacity="0.55"/>' % (cx, cy))
    finish(s)
    return s


# ---------------------------------------------------------------- plate 3
def plate_execution():
    s = S()
    frame(s)
    s.add('<ellipse cx="1120" cy="480" rx="360" ry="270" fill="#ffffff" opacity="0.16" '
          'filter="url(#b60)"/>')
    shadow(s, 1150, 812, 280, 30, 0.2, "b28")

    plates = (
        (900, 620, 250, 92),   # front-left, low
        (1010, 520, 250, 92),
        (1120, 420, 250, 92),
        (1230, 320, 250, 92),  # back-right, high
    )
    for i, (x, y, w, h) in enumerate(plates):
        # drop shadow for this plate
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="#1d2c46" '
              'opacity="0.13" filter="url(#b14)"/>' % (x + 10, y + 16, w, h))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="url(%s)"/>'
              % (x, y, w, h, glass(s, x, y, x + w, y + h, 0.95, CYAN, 0.18, BLUE, 0.12)))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="url(#densV)" '
              'style="mix-blend-mode:multiply" opacity="0.62"/>' % (x, y, w, h))
        # machined metal edge along the bottom of each plate
        edge = s.lg(x, y + h - 16, x, y + h, [("0", "#ffffff", 0.7), ("0.5", SILVER, 0.95),
                                              ("1", "#8e9fb6", 0.8)])
        s.add('<path d="M%s %s h%s a18 18 0 0 1 -18 18 h-%s a18 18 0 0 1 -18 -18 z" '
              'fill="url(%s)" opacity="0.9"/>'
              % (x + 18, y + h - 18, w - 36, w - 36, edge))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="none" '
              'stroke="#ffffff" stroke-width="1.7" opacity="0.85"/>' % (x, y, w, h))
        # top light streak
        s.add('<rect x="%s" y="%s" width="%s" height="26" rx="13" fill="#ffffff" '
              'opacity="0.36" filter="url(#b6)"/>' % (x + 16, y + 8, w - 32))
        # etched step index (no glyphs): thin tick marks
        for k in range(3):
            s.add('<rect x="%s" y="%s" width="26" height="3" rx="1.5" fill="#ffffff" '
                  'opacity="0.55"/>' % (x + 42 + k * 34, y + h - 44))

    # ascent path
    s.add('<path d="M960 660 L960 596 L1070 496 L1070 440 L1180 340 L1180 300 L1290 240" '
          'fill="none" stroke="%s" stroke-width="12" opacity="0.35" filter="url(#b14)"/>' % BLUE)
    s.add('<path d="M960 660 L960 596 L1070 496 L1070 440 L1180 340 L1180 300 L1290 240" '
          'fill="none" stroke="#ffffff" stroke-width="2" opacity="0.85"/>')
    sphere(s, 1290, 240, 17)
    finish(s)
    return s


# ---------------------------------------------------------------- plate 4
def plate_foundation():
    s = S()
    frame(s)
    s.add('<ellipse cx="1110" cy="470" rx="340" ry="280" fill="#ffffff" opacity="0.16" '
          'filter="url(#b60)"/>')
    shadow(s, 1110, 800, 250, 32, 0.2, "b28")

    # base plate
    bx, by, bw, bh = 900, 706, 420, 54
    s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="16" fill="url(%s)"/>'
          % (bx, by, bw, bh, glass(s, bx, by, bx + bw, by + bh, 0.9)))
    s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="16" fill="url(#densV)" '
          'style="mix-blend-mode:multiply" opacity="0.6"/>' % (bx, by, bw, bh))
    s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="16" fill="none" stroke="#ffffff" '
          'stroke-width="1.6" opacity="0.85"/>' % (bx, by, bw, bh))
    s.add('<rect x="%s" y="%s" width="%s" height="14" rx="7" fill="#ffffff" opacity="0.4"/>'
          % (bx + 18, by + 6, bw - 36))

    # two frosted columns
    for x in (960, 1196):
        cw = 64
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="12" fill="url(%s)"/>'
              % (x, 400, cw, 306, s.lg(x, 356, x + cw, 706, [
                  ("0", "#ffffff", 0.95), ("0.24", "#e6eef8", 0.85),
                  ("0.55", "#b9cde4", 0.55), ("0.8", "#d9e6f4", 0.6),
                  ("1", "#ffffff", 0.85)])))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="12" fill="url(#densV)" '
              'style="mix-blend-mode:multiply" opacity="0.7"/>' % (x, 356, cw, 350))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="12" fill="none" '
              'stroke="#41597a" stroke-width="2" opacity="0.45"/>' % (x, 356, cw, 350))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="12" fill="none" '
              'stroke="#ffffff" stroke-width="1.6" opacity="0.95"/>' % (x, 356, cw, 350))
        s.add('<rect x="%s" y="%s" width="7" height="%s" rx="3.5" fill="#ffffff" '
              'opacity="0.6" filter="url(#b6)"/>' % (x + 12, 380, 300))
        s.add('<rect x="%s" y="%s" width="%s" height="16" rx="8" fill="url(%s)" '
              'opacity="0.95"/>' % (x - 6, 392, cw + 12, metal(s, x, 392, x + cw, 408)))

    # support ring (torus) balanced on the columns
    s.add('<ellipse cx="1110" cy="342" rx="212" ry="66" fill="none" stroke="#1d2c46" '
          'opacity="0.12" stroke-width="26" filter="url(#b14)"/>')
    ring = s.lg(898, 276, 1322, 408, [("0", "#ffffff", 0.95), ("0.3", "#cfe0f2", 0.9),
                                      ("0.55", CYAN, 0.55), ("0.8", "#9db4d0", 0.9),
                                      ("1", "#ffffff", 0.9)])
    s.add('<ellipse cx="1110" cy="342" rx="212" ry="66" fill="none" stroke="url(%s)" '
          'stroke-width="26"/>' % ring)
    s.add('<ellipse cx="1110" cy="342" rx="212" ry="66" fill="none" stroke="url(#densRing)" '
          'stroke-width="26" style="mix-blend-mode:multiply" opacity="0.62"/>')
    s.add('<ellipse cx="1110" cy="342" rx="212" ry="66" fill="none" stroke="#3f5878" '
          'stroke-width="1.6" opacity="0.45"/>')
    s.add('<ellipse cx="1110" cy="342" rx="212" ry="66" fill="none" stroke="#ffffff" '
          'stroke-width="1.5" opacity="0.9"/>')
    s.add('<ellipse cx="1110" cy="342" rx="199" ry="59" fill="none" stroke="#ffffff" '
          'stroke-width="1.2" opacity="0.6"/>')
    s.add('<ellipse cx="1110" cy="342" rx="225" ry="73" fill="none" stroke="%s" '
          'stroke-width="1" opacity="0.35"/>' % CYAN)

    s.add('<ellipse cx="992" cy="386" rx="44" ry="12" fill="#2b3f5e" opacity="0.35" filter="url(#b6)"/>')
    s.add('<ellipse cx="1228" cy="386" rx="44" ry="12" fill="#2b3f5e" opacity="0.35" filter="url(#b6)"/>')
    # balanced disc floating inside the ring
    shadow(s, 1110, 372, 96, 10, 0.14, "b14")
    s.add('<ellipse cx="1110" cy="330" rx="96" ry="30" fill="url(%s)"/>'
          % glass(s, 1014, 300, 1206, 360, 0.9, VIOLET, 0.14))
    s.add('<ellipse cx="1110" cy="330" rx="96" ry="30" fill="none" stroke="#ffffff" '
          'stroke-width="1.6" opacity="0.9"/>')
    s.add('<ellipse cx="1088" cy="322" rx="46" ry="12" fill="#ffffff" opacity="0.4" '
          'filter="url(#b6)"/>')
    finish(s)
    return s


# ---------------------------------------------------------------- plate 5
def plate_review():
    s = S()
    frame(s)
    s.add('<ellipse cx="1110" cy="480" rx="350" ry="280" fill="#ffffff" opacity="0.16" '
          'filter="url(#b60)"/>')
    shadow(s, 1120, 806, 250, 30, 0.2, "b28")

    # three offset glass sheets, fanned
    sheets = ((-11, 1012, 292, 300, 400), (-4, 1046, 292, 300, 400), (4, 1080, 300, 300, 400))
    for i, (rot, x, y, w, h) in enumerate(sheets):
        s.add('<g transform="rotate(%s %s %s)">' % (rot, x + w / 2, y + h / 2))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="#1d2c46" '
              'opacity="0.10" filter="url(#b14)" transform="translate(8 14)"/>'
              % (x, y, w, h))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="url(%s)" '
              'opacity="%s"/>' % (x, y, w, h, glass(s, x, y, x + w, y + h, 0.99), 0.98))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="url(#densV)" '
              'style="mix-blend-mode:multiply" opacity="0.34"/>' % (x, y, w, h))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="none" '
              'stroke="#405a7b" stroke-width="1.8" opacity="0.4"/>' % (x, y, w, h))
        s.add('<rect x="%s" y="%s" width="%s" height="%s" rx="18" fill="none" '
              'stroke="#ffffff" stroke-width="1.5" opacity="0.95"/>' % (x, y, w, h))
        # etched block rhythm (abstract, no text)
        if i == 2:
            for k in range(4):
                s.add('<rect x="%s" y="%s" width="%s" height="7" rx="3.5" fill="#ffffff" '
                      'opacity="0.42"/>' % (x + 34, y + 44 + k * 30,
                                            w - 68 - (0 if k == 3 else 70)))
        s.add('</g>')

    # lens hovering over the top sheet
    lx, ly, lr = 1218, 392, 96
    s.add('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#1d2c46" opacity="0.12" '
          'filter="url(#b14)"/>' % (lx + 10, ly + lr + 30, lr * 0.8, 14))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="url(%s)"/>'
          % (lx, ly, lr + 12, s.rg(lx - 26, ly - 34, (lr + 12) * 1.2,
                                   [("0", "#ffffff", 0.95), ("0.55", "#cfdbea", 0.95),
                                    ("1", "#94a8c1", 0.95)])))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="url(%s)"/>'
          % (lx, ly, lr, glass(s, lx - lr, ly - lr, lx + lr, ly + lr, 0.7)))
    s.add('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#ffffff" stroke-width="1.3" '
          'opacity="0.9"/>' % (lx, ly, lr))
    s.add('<path d="M%s %s a96 96 0 0 1 76 -50" fill="none" stroke="#ffffff" '
          'stroke-width="6" opacity="0.6" filter="url(#b6)"/>' % (lx - 68, ly - 64))
    # focused light pool under the lens
    s.add('<ellipse cx="%s" cy="%s" rx="90" ry="26" fill="#ffffff" opacity="0.55" '
          'filter="url(#b14)"/>' % (lx - 20, 610))
    finish(s)
    return s


PLATES = (
    ("insight", plate_insight),
    ("strategy", plate_strategy),
    ("execution", plate_execution),
    ("foundation", plate_foundation),
    ("review", plate_review),
)

PIL_STEP = r"""
import sys
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
im = im.resize((1600, 1000), Image.LANCZOS)
from PIL import ImageEnhance, ImageFilter
im = ImageEnhance.Contrast(im).enhance(1.10)
im = ImageEnhance.Color(im).enhance(1.06)
im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=45, threshold=2))
im.save(dst, "WEBP", quality=int(sys.argv[3]), method=6)
print("wrote", dst, im.size)
"""


def main():
    svg_only = "--svg-only" in sys.argv
    os.makedirs(SVG_DIR, exist_ok=True)
    built = []
    for name, fn in PLATES:
        path = os.path.join(SVG_DIR, name + ".svg")
        with open(path, "w") as fh:
            fh.write(fn().svg())
        built.append((name, path))
        print("svg", path, os.path.getsize(path), "bytes")
    if svg_only:
        return

    from playwright.sync_api import sync_playwright

    scratch = tempfile.TemporaryDirectory(prefix="deepblm-art-", dir=os.environ.get("TMPDIR") or OUT)
    tmp_png = os.path.join(scratch.name, "%s.png")
    # Chromium wraps a bare .svg in an HTML doc with an 8px body margin, which
    # shifts the plate. Render through a margin-free HTML wrapper that inlines
    # the exact same SVG source; device_scale_factor=2 provides the supersample.
    def html_for(svg_text):
        return (
            "<!doctype html><meta charset=utf-8>"
            "<style>html,body{margin:0;padding:0;background:#fff;overflow:hidden}"
            "svg{display:block}</style>" + svg_text
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb",
                                          "--disable-lcd-text",
                                          "--hide-scrollbars"])
        for name, path in built:
            with open(path) as fh:
                svg_text = fh.read()
            page = browser.new_page(viewport={"width": W, "height": H},
                                    device_scale_factor=SCALE)
            page.set_content(html_for(svg_text))
            page.wait_for_timeout(150)
            png = tmp_png % name
            page.screenshot(path=png, type="png", omit_background=False,
                            clip={"x": 0, "y": 0, "width": W, "height": H})
            page.close()
            out = os.path.join(OUT, name + ".webp")
            q = {"insight": 88, "strategy": 88, "execution": 88,
                 "foundation": 88, "review": 88}[name]
            subprocess.run([PIL_PY, "-c", PIL_STEP, png, out, str(q)], check=True)
            os.unlink(png)
        browser.close()
    scratch.cleanup()
    for name, _ in built:
        out = os.path.join(OUT, name + ".webp")
        print("webp", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()