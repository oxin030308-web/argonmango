"""Procedurally generated neon SVG art and synthesized WAV audio for POLAR SHIFT."""
import io
import math
import random
import wave

import numpy as np

CY = "#00f0ff"
MG = "#ff2bd6"
WH = "#ffffff"
YL = "#ffe14d"
GR = "#5dff9b"
INK = "#0b0f1e"


def svg(w, h, body, defs=""):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<defs>%s</defs>%s</svg>' % (w, h, w, h, defs, body))


def glow_grad(gid, color, inner="#ffffff", a0=1.0, mid=0.35):
    return ('<radialGradient id="%s" cx="50%%" cy="50%%" r="50%%">'
            '<stop offset="0" stop-color="%s" stop-opacity="%s"/>'
            '<stop offset="%s" stop-color="%s" stop-opacity="0.85"/>'
            '<stop offset="0.62" stop-color="%s" stop-opacity="0.22"/>'
            '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
            % (gid, inner, a0, mid, color, color, color))


# ------------------------------------------------------------------ player core
def core(color, glyph):
    defs = glow_grad("g", color, a0=0.9, mid=0.3)
    g = ('<path d="M27 32h10M32 27v10" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % color
         if glyph == "+" else
         '<path d="M27 32h10" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % color)
    body = ('<circle cx="32" cy="32" r="31" fill="url(#g)"/>'
            '<circle cx="32" cy="32" r="15" fill="none" stroke="%s" stroke-width="2.5" stroke-dasharray="5 3.5"/>'
            '<circle cx="32" cy="32" r="10" fill="%s" stroke="#ffffff" stroke-width="2.5"/>%s' % (color, INK, g))
    return svg(64, 64, body, defs), 32, 32


# ------------------------------------------------------------------ enemies
def _poly(cx, cy, r, n, rot=0.0):
    pts = []
    for i in range(n):
        a = rot + 2 * math.pi * i / n
        pts.append("%.2f,%.2f" % (cx + r * math.cos(a), cy + r * math.sin(a)))
    return " ".join(pts)


def _star(cx, cy, r1, r2, n, rot=0.0):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = rot + math.pi * i / n
        pts.append("%.2f,%.2f" % (cx + r * math.cos(a), cy + r * math.sin(a)))
    return " ".join(pts)


def _glyph(cx, cy, color, plus, s=4):
    if plus:
        return ('<path d="M%g %gh%gM%g %gv%g" stroke="%s" stroke-width="2.4" stroke-linecap="round"/>'
                % (cx - s, cy, 2 * s, cx, cy - s, 2 * s, color))
    return '<path d="M%g %gh%g" stroke="%s" stroke-width="2.4" stroke-linecap="round"/>' % (cx - s, cy, 2 * s, color)


def drone(kind, color, plus, white=False):
    stroke = WH if white else color
    defs = glow_grad("g", color, inner=color, a0=0.55, mid=0.2)
    halo = '<circle cx="28" cy="28" r="27" fill="url(#g)"/>'
    if kind == 1:  # spinning star shard
        body = (halo + '<polygon points="%s" fill="%s" stroke="%s" stroke-width="2.6" stroke-linejoin="round"/>'
                % (_star(28, 28, 18, 8, 4, -math.pi / 2), INK, stroke)
                + '<polygon points="%s" fill="%s"/>' % (_star(28, 28, 7, 3, 4, -math.pi / 2), stroke))
    elif kind == 2:  # prism hexagon
        body = (halo + '<polygon points="%s" fill="%s" stroke="#ffffff" stroke-width="2.4"/>'
                % (_poly(28, 28, 17, 6, math.pi / 6), INK)
                + '<polygon points="%s" fill="none" stroke="%s" stroke-width="3"/>' % (_poly(28, 28, 11, 6, math.pi / 6), stroke)
                + _glyph(28, 28, WH, plus, 3.5))
    else:  # hunter dart (points right = direction 90)
        body = (halo + '<polygon points="46,28 14,14 21,28 14,42" fill="%s" stroke="%s" stroke-width="2.6" stroke-linejoin="round"/>'
                % (INK, stroke)
                + '<polygon points="38,28 24,22 27,28 24,34" fill="%s"/>' % stroke)
    return svg(56, 56, body, defs), 28, 28


def spark(color):
    defs = glow_grad("g", color, a0=1, mid=0.3)
    return svg(16, 16, '<circle cx="8" cy="8" r="8" fill="url(#g)"/>', defs), 8, 8


def ring(color):
    body = ('<circle cx="50" cy="50" r="45" fill="none" stroke="%s" stroke-opacity="0.25" stroke-width="9"/>'
            '<circle cx="50" cy="50" r="45" fill="none" stroke="%s" stroke-width="2.5"/>' % (color, color))
    return svg(100, 100, body), 50, 50


def blank():
    return svg(2, 2, ""), 1, 1


def flash():
    return svg(480, 360, '<rect width="480" height="360" fill="#ffffff"/>'), 240, 180


# ------------------------------------------------------------------ seven-seg digits
SEG = {"a": (0, 0, 12, 0), "b": (12, 0, 12, 11), "c": (12, 11, 12, 22), "d": (0, 22, 12, 22),
       "e": (0, 11, 0, 22), "f": (0, 0, 0, 11), "g": (0, 11, 12, 11)}
DIG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
       "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abfgcd"}


def digit(ch):
    if ch == "x":
        lines = [(1, 8, 11, 22), (11, 8, 1, 22)]
    elif ch == "1":
        lines = [(7, 0, 7, 22), (3, 3, 7, 0)]
    else:
        lines = [SEG[s] for s in DIG[ch]]
    path = "".join("M%g %gL%g %g" % l for l in lines)
    body = ('<g transform="translate(5 4) skewX(-8)">'
            '<path d="%s" stroke="%s" stroke-opacity="0.35" stroke-width="6" stroke-linecap="round" fill="none"/>'
            '<path d="%s" stroke="#eafcff" stroke-width="2.6" stroke-linecap="round" fill="none"/></g>'
            % (path, CY, path))
    return svg(22, 30, body), 11, 15


# ------------------------------------------------------------------ text cards
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size, fill=WH, weight="normal", anchor="middle", family="Sans Serif", spacing=0, op=1):
    return ('<text x="%g" y="%g" font-family="%s" font-size="%g" font-weight="%s" fill="%s" '
            'text-anchor="%s" letter-spacing="%g" fill-opacity="%g">%s</text>'
            % (x, y, family, size, weight, fill, anchor, spacing, op, esc(s)))


def ctext(x, y, s, size, spacing=2, off=2.5):
    """Chromatic-aberration neon headline."""
    return (text(x - off, y, s, size, MG, "bold", spacing=spacing, op=0.9)
            + text(x + off, y, s, size, CY, "bold", spacing=spacing, op=0.9)
            + text(x, y, s, size, WH, "bold", spacing=spacing))


def mini(cx, cy, color, plus=True):
    return ('<polygon points="%s" fill="%s" stroke="%s" stroke-width="2"/>'
            % (_star(cx, cy, 9, 4, 4, -math.pi / 2), INK, color))


def mini_core(cx, cy, color):
    return ('<circle cx="%g" cy="%g" r="7" fill="%s" stroke="%s" stroke-width="2.5"/>' % (cx, cy, INK, color))


def title_card():
    b = ""
    b += ctext(240, 82, "POLAR SHIFT", 56, spacing=3, off=3)
    b += text(240, 108, "OPPOSITES ATTRACT  //  OPPOSITES KILL", 12, "#9fb0d8", spacing=3)
    b += '<rect x="34" y="124" width="412" height="178" rx="12" fill="#0a0f22" fill-opacity="0.82" stroke="#28335a" stroke-width="1.5"/>'
    # rule rows
    b += mini_core(62, 150, CY) + mini(84, 150, CY)
    b += text(104, 155, "SAME COLOR", 13, WH, "bold", "start")
    b += text(250, 155, "\u2192  you ABSORB it", 13, CY, "bold", "start")
    b += mini_core(62, 178, CY) + mini(84, 178, MG)
    b += text(104, 183, "OPPOSITE COLOR", 13, WH, "bold", "start")
    b += text(250, 183, "\u2192  it KILLS you", 13, MG, "bold", "start")
    b += text(240, 210, "Opposites get PULLED toward you. Same colors get PUSHED away.", 11.5, "#c8d3f0")
    b += text(240, 232, "So let the killers charge in... and FLIP your color at the last second.", 11.5, "#c8d3f0")
    b += text(240, 252, "Their own momentum crashes them into you = CLUTCH! (double points)", 11.5, YL, "bold")
    b += '<line x1="60" y1="266" x2="420" y2="266" stroke="#28335a"/>'
    b += text(150, 286, "ARROWS / WASD : drift", 11, "#9fb0d8")
    b += text(330, 286, "SPACE / CLICK : flip polarity", 11, "#9fb0d8")
    b += text(240, 334, "PRESS SPACE TO START", 18, YL, "bold", spacing=3)
    b += text(16, 25, "BEST", 12, "#9fb0d8", "bold", "start", spacing=2)
    return svg(480, 360, b), 240, 180


WAVE_TIPS = {
    1: "let the opposite color come to you...",
    2: "flip at the very last second = CLUTCH",
    3: "NEW: PRISMS swap color when they flicker",
    4: "NEW: HUNTERS. fast. hungry. no mercy",
    5: "chain absorbs to pump your multiplier",
    6: "absorbing refills your flip energy",
    7: "the walls will not save you",
    8: "you are the magnet now",
}
FLAVOR = ["keep the chain alive", "hear the pitch climb?", "flip. absorb. repeat.",
          "they can smell your polarity", "stay calm. stay charged.", "nothing is safe for long",
          "the field is collapsing", "legend status incoming"]


def wave_card(n):
    tip = WAVE_TIPS.get(n, FLAVOR[n % len(FLAVOR)])
    b = ctext(240, 192, "WAVE %d" % n, 54, spacing=4, off=3)
    b += '<line x1="150" y1="210" x2="330" y2="210" stroke="%s" stroke-width="2"/>' % YL
    b += text(240, 232, tip.upper(), 12, YL, "bold", spacing=2)
    return svg(480, 360, b), 240, 180


def over_card():
    b = '<rect x="90" y="52" width="300" height="270" rx="14" fill="#0a0f22" fill-opacity="0.85" stroke="#28335a" stroke-width="1.5"/>'
    b += ctext(240, 106, "SIGNAL LOST", 44, spacing=3, off=3)
    b += text(240, 146, "FINAL SCORE", 12, "#9fb0d8", "bold", spacing=3)
    b += text(240, 224, "BEST", 12, "#9fb0d8", "bold", spacing=3)
    b += text(240, 300, "SPACE / CLICK TO RETRY", 15, YL, "bold", spacing=2)
    return svg(480, 360, b), 240, 180


def popup(label, color, w=220):
    b = (text(w / 2, 30, label, 22, "#000000", "bold", spacing=2, op=0.6).replace('y="30"', 'y="32"')
         + text(w / 2, 30, label, 22, color, "bold", spacing=2))
    return svg(w, 40, b), w / 2, 20


def backdrop():
    rnd = random.Random(7)
    b = ('<rect width="480" height="360" fill="url(#bg)"/>')
    for x in range(0, 481, 30):
        b += '<line x1="%d" y1="0" x2="%d" y2="360" stroke="#1a2348" stroke-width="1"/>' % (x, x)
    for y in range(0, 361, 30):
        b += '<line x1="0" y1="%d" x2="480" y2="%d" stroke="#1a2348" stroke-width="1"/>' % (y, y)
    for _ in range(70):
        b += '<circle cx="%.1f" cy="%.1f" r="%.2f" fill="#ffffff" fill-opacity="%.2f"/>' % (
            rnd.uniform(0, 480), rnd.uniform(0, 360), rnd.uniform(0.4, 1.3), rnd.uniform(0.15, 0.7))
    b += '<rect width="480" height="360" fill="url(#vig)"/>'
    b += '<rect x="3" y="3" width="474" height="354" rx="6" fill="none" stroke="#2b3a78" stroke-width="2"/>'
    defs = ('<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d1030"/>'
            '<stop offset="1" stop-color="#05060f"/></linearGradient>'
            '<radialGradient id="vig" cx="50%" cy="50%" r="70%"><stop offset="0.55" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#000" stop-opacity="0.7"/></radialGradient>')
    return svg(480, 360, b, defs), 240, 180


# ------------------------------------------------------------------ audio
SR = 22050


def to_wav(x):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype("<i2")
    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return bio.getvalue(), len(pcm)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def sweep(f0, f1, dur, shape="sine"):
    t = tt(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    if shape == "sine":
        return np.sin(ph)
    if shape == "square":
        return np.tanh(4 * np.sin(ph))
    if shape == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    return np.sin(ph)


def lowpass(x, a):
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def snd_pop():
    t = tt(0.16)
    x = sweep(620, 1500, 0.16) * np.exp(-t * 22) * 0.7
    x += sweep(1240, 3000, 0.16) * np.exp(-t * 40) * 0.2
    return x


def snd_flip(up):
    t = tt(0.17)
    x = sweep(240, 1150, 0.17, "square") if up else sweep(1150, 240, 0.17, "square")
    return x * np.minimum(1, t * 200) * np.exp(-t * 9) * 0.35


def snd_denied():
    t = tt(0.18)
    x = np.tanh(5 * np.sin(2 * np.pi * 95 * t)) * 0.3
    x *= (np.sin(2 * np.pi * 22 * t) > -0.2)
    return x * np.exp(-t * 6)


def snd_boom():
    rng = np.random.default_rng(3)
    t = tt(1.1)
    n = lowpass(rng.uniform(-1, 1, len(t)), 0.08) * 3
    x = n * np.exp(-t * 4) * 0.7 + sweep(110, 28, 1.1) * np.exp(-t * 3) * 0.7
    return x


def pluck(f, dur, decay=9, shape="square"):
    t = tt(dur)
    ph = 2 * np.pi * f * t
    w = np.tanh(3 * np.sin(ph)) if shape == "square" else np.sin(ph)
    return w * np.exp(-t * decay)


def seq(notes, step, dur, decay=9, amp=0.4):
    total = tt(step * len(notes) + dur)
    out = np.zeros(len(total))
    for i, f in enumerate(notes):
        s = int(i * step * SR)
        p = pluck(f, dur, decay) * amp
        out[s:s + len(p)] += p
    return out


def snd_wave():
    return seq([440, 523.25, 659.25, 880], 0.07, 0.35, 8, 0.32)


def snd_clear():
    return seq([523.25, 659.25, 783.99, 1046.5, 1318.5], 0.06, 0.4, 7, 0.28)


def snd_clutch():
    t = tt(0.45)
    x = (np.sin(2 * np.pi * 1318.5 * t) + 0.5 * np.sin(2 * np.pi * 1975.5 * t)) * np.exp(-t * 7)
    t2 = tt(0.35)
    y = (np.sin(2 * np.pi * 1760 * t2) + 0.5 * np.sin(2 * np.pi * 2637 * t2)) * np.exp(-t2 * 8)
    out = np.zeros(len(t) + int(0.08 * SR))
    out[:len(x)] += x * 0.3
    out[int(0.08 * SR):int(0.08 * SR) + len(y)] += y * 0.3
    return out


def snd_music():
    bpm = 124
    beat = 60 / bpm
    bars = 4
    total = int(bars * 4 * beat * SR)
    out = np.zeros(total)
    rng = np.random.default_rng(11)
    chords = [(110.0, [440, 523.25, 659.25]),        # Am
              (87.31, [349.23, 440, 523.25]),        # F
              (130.81, [523.25, 659.25, 783.99]),    # C
              (98.0, [392, 493.88, 587.33])]         # G

    def put(sig, start):
        s = int(start * SR)
        e = min(total, s + len(sig))
        out[s:e] += sig[:e - s]

    sixteenth = beat / 4
    for bar, (root, arp) in enumerate(chords):
        b0 = bar * 4 * beat
        for k in range(4):  # kick + snare
            t = tt(0.32)
            kick = np.sin(2 * np.pi * np.cumsum(45 + 130 * np.exp(-t * 28)) / SR) * np.exp(-t * 9) * 0.75
            put(kick, b0 + k * beat)
            if k in (1, 3):
                tn = tt(0.2)
                nz = np.diff(rng.uniform(-1, 1, len(tn) + 1)) * np.exp(-tn * 20) * 0.22
                put(nz + np.sin(2 * np.pi * 190 * tn) * np.exp(-tn * 25) * 0.15, b0 + k * beat)
        for s16 in range(16):
            st = b0 + s16 * sixteenth
            if s16 % 2 == 1:  # hats
                th = tt(0.05)
                put(np.diff(rng.uniform(-1, 1, len(th) + 1)) * np.exp(-th * 70) * 0.09, st)
            # bass: driving 8ths with octave pops
            if s16 % 2 == 0:
                f = root * (2 if s16 in (6, 14) else 1)
                tb = tt(sixteenth * 1.8)
                bass = sweep(f, f, sixteenth * 1.8, "saw") * np.exp(-tb * 5) * 0.32
                put(lowpass(bass, 0.18), st)
            # arp
            f = arp[[0, 1, 2, 1][s16 % 4]] * (2 if s16 >= 8 else 1)
            put(pluck(f, sixteenth * 1.6, 14) * 0.07, st)
    # soft pad
    for bar, (root, arp) in enumerate(chords):
        t = tt(4 * beat)
        env = np.minimum(1, t * 3) * np.minimum(1, (4 * beat - t) * 3)
        pad = sum(np.sin(2 * np.pi * f / 2 * t + i) for i, f in enumerate(arp)) * env * 0.035
        put(pad, bar * 4 * beat)
    return out / max(1e-6, np.max(np.abs(out))) * 0.8
