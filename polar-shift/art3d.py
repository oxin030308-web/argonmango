"""3D art for POLAR SHIFT: camera projection, flat-shaded mesh renderer -> SVG, 3D arena backdrop,
and touch controls.  The same projection constants are used by the Scratch scripts in build.py."""
import math
import random

from assets import CY, MG, WH, YL, INK, svg, text, ctext, mini, mini_core, glow_grad

# ------------------------------------------------------------------ camera
# World: X right, Y up, Z away from camera.  Arena floor X in [-XW, XW], Z in [-ZW, ZW].
XW, ZW = 220, 240
C = 952.0                      # camera distance offset (depth = Z + C)
F = 1.073 * (C - ZW)           # focal length -> near edge spans the full stage width
CAMH = 0.7 * C                 # camera height -> ~35 deg viewing pitch
H0 = -170 + CAMH * F / (C - ZW)  # screen y of the horizon
PITCH = math.degrees(math.atan(CAMH / C))


def project(x, y, z):
    k = F / (z + C)
    return x * k, H0 + (y - CAMH) * k, k


def to_svg(x, y, z):
    sx, sy, _ = project(x, y, z)
    return 240 + sx, 180 - sy


# ------------------------------------------------------------------ color helpers
def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def mix(a, b, t):
    a, b = _rgb(a), _rgb(b)
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ------------------------------------------------------------------ mesh renderer
def _sub(a, b): return [a[i] - b[i] for i in range(3)]
def _dot(a, b): return sum(a[i] * b[i] for i in range(3))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _norm(a):
    l = math.sqrt(_dot(a, a)) or 1
    return [v / l for v in a]


LIGHT = _norm([-0.5, 0.85, -0.4])


def render_mesh(verts, faces, yaw, color, edge, scale, size=64, halo=True, pitch=PITCH):
    cy_, sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    vw = [[x * cy_ + z * sy_, y, -x * sy_ + z * cy_] for x, y, z in verts]
    center = [sum(v[i] for v in vw) / len(vw) for i in range(3)]
    p = math.radians(pitch)
    cam = [0, math.sin(p), -math.cos(p)]
    polys = []
    for f in faces:
        a, b, c = vw[f[0]], vw[f[1]], vw[f[2]]
        n = _norm(_cross(_sub(b, a), _sub(c, a)))
        fc = [sum(vw[i][j] for i in f) / len(f) for j in range(3)]
        if _dot(n, _sub(fc, center)) < 0:
            n = [-v for v in n]
        if _dot(n, cam) <= 0.02:
            continue
        depth = sum(vw[i][2] * math.cos(p) - vw[i][1] * math.sin(p) for i in f) / len(f)
        bright = 0.22 + 0.78 * max(0.0, _dot(n, LIGHT))
        fill = mix(INK, color, bright)
        if bright > 0.82:
            fill = mix(fill, "#ffffff", (bright - 0.82) * 2.2)
        pts = []
        for i in f:
            x, y, z = vw[i]
            up = y * math.cos(p) + z * math.sin(p)
            pts.append("%.2f,%.2f" % (size / 2 + x * scale, size / 2 - up * scale))
        polys.append((depth, '<polygon points="%s" fill="%s" stroke="%s" stroke-width="1.3" '
                             'stroke-linejoin="round" stroke-opacity="0.95"/>' % (" ".join(pts), fill, edge)))
    polys.sort(key=lambda t: -t[0])
    body = ""
    defs = ""
    if halo:
        defs = glow_grad("g", color, inner=color, a0=0.5, mid=0.15)
        body = '<circle cx="%g" cy="%g" r="%g" fill="url(#g)"/>' % (size / 2, size / 2, size / 2 - 1)
    body += "".join(s for _, s in polys)
    return svg(size, size, body, defs), size / 2, size / 2


def octahedron():
    v = [[1, 0, 0], [-1, 0, 0], [0, 1.35, 0], [0, -1.35, 0], [0, 0, 1], [0, 0, -1]]
    f = [[a, b, c] for a in (0, 1) for b in (2, 3) for c in (4, 5)]
    return v, f


def hexprism():
    v = []
    for y in (0.7, -0.7):
        for i in range(6):
            a = math.pi / 3 * i
            v.append([math.cos(a), y, math.sin(a)])
    f = [[i, (i + 1) % 6, 6 + (i + 1) % 6, 6 + i] for i in range(6)]
    f += [list(range(6)), list(range(6, 12))]
    return v, f


def dart():
    v = [[0, 0, 1.5], [-1, 0, -0.9], [1, 0, -0.9], [0, 0.55, -0.6], [0, -0.3, -0.7]]
    f = [[0, 1, 3], [0, 3, 2], [0, 2, 4], [0, 4, 1], [1, 3, 2], [1, 2, 4]]
    return v, f


def drone_frames(kind, color, white=False):
    """8 frames: spin for kinds 1/2, heading (yaw 0,45..315 from +Z toward +X) for kind 3."""
    edge = WH if white else mix(color, "#ffffff", 0.35)
    out = []
    for i in range(8):
        if kind == 1:
            v, f = octahedron()
            out.append(render_mesh(v, f, i * 90 / 8, color, edge, 13))
        elif kind == 2:
            v, f = hexprism()
            out.append(render_mesh(v, f, i * 60 / 8, color, WH if not white else WH, 15))
        else:
            v, f = dart()
            out.append(render_mesh(v, f, i * 45, color, edge, 13))
    return out


# ------------------------------------------------------------------ player core (sphere + spinning ring)
def core_frame(color, plus, i):
    cx = cy = 32
    rx = 24
    ry = rx * math.sin(math.radians(PITCH))
    off = i * 10 / 8
    defs = (glow_grad("h", color, inner=color, a0=0.45, mid=0.2)
            + '<radialGradient id="s" cx="38%%" cy="32%%" r="70%%"><stop offset="0" stop-color="#ffffff"/>'
              '<stop offset="0.3" stop-color="%s"/><stop offset="1" stop-color="%s"/></radialGradient>'
            % (mix(color, "#ffffff", 0.25), mix(color, INK, 0.7)))
    ring = ('stroke="%s" stroke-width="3" fill="none" stroke-dasharray="6 4" stroke-dashoffset="%.2f" '
            'stroke-linecap="round"' % (color, off))
    glyph = ('<path d="M27 30h10M32 25v10" stroke="#ffffff" stroke-width="2.6" stroke-linecap="round" stroke-opacity="0.9"/>'
             if plus else
             '<path d="M27 30h10" stroke="#ffffff" stroke-width="2.6" stroke-linecap="round" stroke-opacity="0.9"/>')
    body = ('<circle cx="32" cy="32" r="31" fill="url(#h)"/>'
            '<path d="M%g %g A%g %g 0 0 1 %g %g" %s stroke-opacity="0.55"/>' % (cx - rx, cy, rx, ry, cx + rx, cy, ring)
            + '<circle cx="32" cy="32" r="12.5" fill="url(#s)" stroke="%s" stroke-width="1.2"/>' % mix(color, "#ffffff", 0.5)
            + glyph
            + '<path d="M%g %g A%g %g 0 0 1 %g %g" %s/>' % (cx + rx, cy, rx, ry, cx - rx, cy, ring))
    return svg(64, 64, body, defs), 32, 32


# ------------------------------------------------------------------ floor shockwave rings (ellipses)
RING_SQUASH = (0.9, 0.72, 0.56)   # near / mid / far bands


def ring_ellipse(color, squash):
    ry = 45 * squash
    body = ('<ellipse cx="50" cy="50" rx="45" ry="%.2f" fill="none" stroke="%s" stroke-opacity="0.25" stroke-width="9"/>'
            '<ellipse cx="50" cy="50" rx="45" ry="%.2f" fill="none" stroke="%s" stroke-width="2.5"/>'
            % (ry, color, ry, color))
    return svg(100, 100, body), 50, 50


# ------------------------------------------------------------------ touch controls
def pad_base():
    arrows = ""
    for ang in (0, 90, 180, 270):
        a = math.radians(ang)
        x, y = 60 + 44 * math.cos(a), 60 - 44 * math.sin(a)
        px, py = -math.sin(a), -math.cos(a)
        tip = (x + 7 * math.cos(a), y - 7 * math.sin(a))
        arrows += '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#ffffff" fill-opacity="0.7"/>' % (
            tip[0], tip[1], x + 6 * px, y + 6 * py, x - 6 * px, y - 6 * py)
    body = ('<circle cx="60" cy="60" r="56" fill="#0a1030" fill-opacity="0.45" stroke="#ffffff" stroke-opacity="0.55" stroke-width="3"/>'
            '<circle cx="60" cy="60" r="30" fill="none" stroke="#ffffff" stroke-opacity="0.15" stroke-width="2"/>' + arrows)
    return svg(120, 120, body), 60, 60


def pad_knob():
    defs = ('<radialGradient id="k" cx="40%" cy="35%" r="70%"><stop offset="0" stop-color="#ffffff"/>'
            '<stop offset="1" stop-color="#7d8bb8"/></radialGradient>')
    return svg(52, 52, '<circle cx="26" cy="26" r="23" fill="url(#k)" fill-opacity="0.85" stroke="#ffffff" stroke-width="2"/>', defs), 26, 26


def pad_flip(color, label="FLIP"):
    body = ('<circle cx="45" cy="45" r="41" fill="%s" fill-opacity="0.22" stroke="%s" stroke-width="3.5"/>'
            '<path d="M27 38 A19 19 0 0 1 61 33" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round"/>'
            '<polygon points="64,26 66,38 55,35" fill="%s"/>'
            '<path d="M63 52 A19 19 0 0 1 29 57" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round"/>'
            '<polygon points="26,64 24,52 35,55" fill="%s"/>'
            % (color, color, color, color, color, color)
            + text(45, 51, label, 15, "#ffffff", "bold", spacing=1))
    return svg(90, 90, body), 45, 45


# ------------------------------------------------------------------ 3D arena backdrop
def _poly_svg(pts, attrs):
    return '<polygon points="%s" %s/>' % (" ".join("%.1f,%.1f" % to_svg(*p) for p in pts), attrs)


def _line(a, b, attrs):
    (x1, y1), (x2, y2) = to_svg(*a), to_svg(*b)
    return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s/>' % (x1, y1, x2, y2, attrs)


def backdrop3d():
    rnd = random.Random(5)
    defs = ('<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#120c34"/>'
            '<stop offset="1" stop-color="#03040b"/></linearGradient>'
            '<linearGradient id="fl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b0f2e"/>'
            '<stop offset="1" stop-color="#060818"/></linearGradient>'
            '<radialGradient id="neb1" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ff2bd6" stop-opacity="0.35"/>'
            '<stop offset="1" stop-color="#ff2bd6" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="neb2" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#00f0ff" stop-opacity="0.3"/>'
            '<stop offset="1" stop-color="#00f0ff" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="pool" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#3b4cff" stop-opacity="0.22"/>'
            '<stop offset="1" stop-color="#3b4cff" stop-opacity="0"/></radialGradient>')
    b = '<rect width="480" height="360" fill="url(#sky)"/>'
    b += '<ellipse cx="60" cy="40" rx="150" ry="80" fill="url(#neb1)"/>'
    b += '<ellipse cx="430" cy="30" rx="150" ry="80" fill="url(#neb2)"/>'
    for _ in range(90):
        b += '<circle cx="%.1f" cy="%.1f" r="%.2f" fill="#ffffff" fill-opacity="%.2f"/>' % (
            rnd.uniform(0, 480), rnd.uniform(0, 360), rnd.uniform(0.3, 1.3), rnd.uniform(0.2, 0.8))
    # underside / thickness of the floating platform
    th = -26
    b += _poly_svg([(-XW, 0, -ZW), (XW, 0, -ZW), (XW, th, -ZW), (-XW, th, -ZW)], 'fill="#151b44"')
    b += _poly_svg([(-XW, 0, -ZW), (-XW, 0, ZW), (-XW, th, ZW), (-XW, th, -ZW)], 'fill="#0d1236"')
    b += _poly_svg([(XW, 0, -ZW), (XW, 0, ZW), (XW, th, ZW), (XW, th, -ZW)], 'fill="#0d1236"')
    # floor
    b += _poly_svg([(-XW, 0, -ZW), (XW, 0, -ZW), (XW, 0, ZW), (-XW, 0, ZW)], 'fill="url(#fl)"')
    cx, cy = to_svg(0, 0, 0)
    b += '<ellipse cx="%.1f" cy="%.1f" rx="210" ry="130" fill="url(#pool)"/>' % (cx, cy)
    # grid
    for x in range(-XW, XW + 1, 40):
        b += _line((x, 0, -ZW), (x, 0, ZW), 'stroke="#2a3a8c" stroke-opacity="0.55" stroke-width="1"')
    for z in range(-ZW, ZW + 1, 40):
        op = 0.25 + 0.45 * (ZW - z) / (2 * ZW)
        b += _line((-XW, 0, z), (XW, 0, z), 'stroke="#2a3a8c" stroke-opacity="%.2f" stroke-width="1"' % op)
    # center landing ring
    pts = [to_svg(70 * math.cos(a / 40 * 2 * math.pi), 0, 70 * math.sin(a / 40 * 2 * math.pi)) for a in range(40)]
    b += '<polygon points="%s" fill="none" stroke="#7c8cff" stroke-opacity="0.35" stroke-width="2" stroke-dasharray="6 6"/>' % \
         " ".join("%.1f,%.1f" % p for p in pts)
    # walls: back (violet), left (cyan), right (magenta)
    wh = 24
    for (a, c_, col) in (((-XW, ZW), (XW, ZW), "#9a6bff"), ((-XW, -ZW), (-XW, ZW), CY), ((XW, -ZW), (XW, ZW), MG)):
        p0, p1 = (a[0], 0, a[1]), (c_[0], 0, c_[1])
        q0, q1 = (a[0], wh, a[1]), (c_[0], wh, c_[1])
        b += _poly_svg([p0, p1, q1, q0], 'fill="%s" fill-opacity="0.10"' % col)
        b += _line(p0, p1, 'stroke="%s" stroke-width="5" stroke-opacity="0.25"' % col)
        b += _line(p0, p1, 'stroke="%s" stroke-width="2"' % col)
        b += _line(q0, q1, 'stroke="%s" stroke-width="2" stroke-opacity="0.8"' % col)
    # near rail
    b += _line((-XW, 0, -ZW), (XW, 0, -ZW), 'stroke="#9a6bff" stroke-width="5" stroke-opacity="0.25"')
    b += _line((-XW, 0, -ZW), (XW, 0, -ZW), 'stroke="#c9b6ff" stroke-width="2"')
    # corner pylons
    for x, z in ((-XW, ZW), (XW, ZW), (-XW, -ZW), (XW, -ZW)):
        b += _line((x, 0, z), (x, 44, z), 'stroke="#ffffff" stroke-width="6" stroke-opacity="0.15" stroke-linecap="round"')
        b += _line((x, 0, z), (x, 44, z), 'stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"')
        tx, ty = to_svg(x, 44, z)
        b += '<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (tx, ty, YL)
    return svg(480, 360, b, defs), 240, 180


# ------------------------------------------------------------------ cards with touch instructions
def title_card3d():
    b = ""
    b += ctext(226, 78, "POLAR SHIFT", 52, spacing=3, off=3)
    b += ('<rect x="404" y="40" width="46" height="28" rx="6" fill="%s" transform="rotate(-8 427 54)"/>' % YL
          + text(427, 61, "3D", 20, "#120c34", "bold").replace("<text", '<text transform="rotate(-8 427 54)"'))
    b += text(240, 104, "OPPOSITES ATTRACT  //  OPPOSITES KILL", 12, "#9fb0d8", spacing=3)
    b += '<rect x="34" y="118" width="412" height="186" rx="12" fill="#0a0f22" fill-opacity="0.85" stroke="#28335a" stroke-width="1.5"/>'
    b += mini_core(62, 144, CY) + mini(84, 144, CY)
    b += text(104, 149, "SAME COLOR", 13, WH, "bold", "start")
    b += text(250, 149, "→  you ABSORB it", 13, CY, "bold", "start")
    b += mini_core(62, 172, CY) + mini(84, 172, MG)
    b += text(104, 177, "OPPOSITE COLOR", 13, WH, "bold", "start")
    b += text(250, 177, "→  it KILLS you", 13, MG, "bold", "start")
    b += text(240, 203, "Opposites get PULLED toward you. Same colors get PUSHED away.", 11.5, "#c8d3f0")
    b += text(240, 224, "So let the killers charge in... and FLIP your color at the last second.", 11.5, "#c8d3f0")
    b += text(240, 244, "Their own momentum crashes them into you = CLUTCH! (double points)", 11.5, YL, "bold")
    b += '<line x1="60" y1="257" x2="420" y2="257" stroke="#28335a"/>'
    b += text(240, 275, "MOVE:  arrows / WASD  or  drag the on-screen stick", 11, "#9fb0d8")
    b += text(240, 293, "FLIP:  space  or  tap / click anywhere else", 11, "#9fb0d8")
    b += text(240, 336, "PRESS SPACE OR TAP TO START", 17, YL, "bold", spacing=3)
    b += text(16, 25, "BEST", 12, "#9fb0d8", "bold", "start", spacing=2)
    return svg(480, 360, b), 240, 180


def over_card3d():
    b = '<rect x="90" y="52" width="300" height="270" rx="14" fill="#0a0f22" fill-opacity="0.88" stroke="#28335a" stroke-width="1.5"/>'
    b += ctext(240, 106, "SIGNAL LOST", 44, spacing=3, off=3)
    b += text(240, 146, "FINAL SCORE", 12, "#9fb0d8", "bold", spacing=3)
    b += text(240, 224, "BEST", 12, "#9fb0d8", "bold", spacing=3)
    b += text(240, 300, "SPACE / TAP TO RETRY", 15, YL, "bold", spacing=2)
    return svg(480, 360, b), 240, 180


if __name__ == "__main__":
    print("C=%.1f F=%.1f CAMH=%.1f H0=%.1f pitch=%.1f" % (C, F, CAMH, H0, PITCH))
    for p in ((-XW, 0, -ZW), (XW, 0, ZW), (0, 0, 0), (0, 44, ZW)):
        print(p, ["%.1f" % v for v in project(*p)])
