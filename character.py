"""Upgraded stick-figure character + Charakterset (pose/expression library).

Style (like the reference "Stickman Director" look):
- large round WHITE head (filled), thick black outline
- expressive face: oval eyes + mouth + eyebrows
- body/limbs = thin black stick lines (no filled body)
- white background, muted color accents for props

The character is defined ONCE; poses + expressions are a named library
(the "Charakterset") so every scene reuses the exact same hero.
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FPS = 24
BG = (255, 255, 255)
INK = (18, 18, 22)
MUTED = {
    "yellow": (240, 200, 80),
    "blue": (120, 160, 210),
    "gray": (150, 150, 155),
    "purple": (160, 130, 200),
    "red": (215, 90, 90),
}

# ---------------------------------------------------------------------------
# Charakterset: poses (limb angles) + expressions (face)
# ---------------------------------------------------------------------------
POSES = {
    "stand":     dict(arm_l=14, arm_r=14, leg_l=0,  leg_r=0,  lean=0, hand_r=None),
    "point":     dict(arm_l=12, arm_r=12, leg_l=6,  leg_r=6,  lean=0, hand_r="POINT"),
    "think":     dict(arm_l=10, arm_r=10, leg_l=4,  leg_r=4,  lean=6, hand_r="CHIN"),
    "celebrate": dict(arm_l=-150, arm_r=-150, leg_l=10, leg_r=10, lean=0, hand_r=None),
    "sad":       dict(arm_l=8,  arm_r=8,  leg_l=0,  leg_r=0,  lean=-6, hand_r=None),
    "run":       dict(arm_l=25, arm_r=-25, leg_l=-30, leg_r=30, lean=14, hand_r=None),
}

EXPRESSIONS = {
    "neutral":   dict(eyes="oval", brow=0, mouth="line"),
    "happy":     dict(eyes="oval", brow=0, mouth="smile"),
    "surprised": dict(eyes="big",  brow=2, mouth="o"),
    "worried":   dict(eyes="oval", brow=1, mouth="small"),
    "sad":       dict(eyes="oval", brow=-1, mouth="frown"),
    "confident": dict(eyes="oval", brow=0, mouth="smirk"),
}


def load_font(size, bold=False):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _limb(origin, length, angle, bend=0.0):
    a = math.radians(angle)
    b = math.radians(bend)
    mid = (origin[0] + length * 0.5 * math.sin(a + b),
           origin[1] + length * 0.5 * math.cos(a + b))
    end = (origin[0] + length * math.sin(a),
           origin[1] + length * math.cos(a))
    return mid, end


def draw_character(d, hx, hy, s=1.0, pose="stand", expr="neutral", walk_phase=0.0):
    """Draw the hero anchored at hip (hx, hy)."""
    P = dict(POSES[pose])
    E = EXPRESSIONS[expr]

    L = 46 * s      # leg
    T = 42 * s      # torso
    R = 15 * s      # head radius (a bit larger = rounder, friendlier)
    lw = max(2, int(2.6 * s))     # limb line width (thin)
    hw = max(3, int(3.6 * s))     # head outline width (thick)

    hip = (hx, hy)
    neck = (hx, hy - T)
    head_c = (hx + P["lean"], hy - T - R)
    shoulder = (hx, hy - T + 7 * s)

    # legs (with walk swing)
    leg_l = P["leg_l"] * (1 + walk_phase)
    leg_r = P["leg_r"] * (1 - walk_phase)
    for ang in (leg_l, leg_r):
        knee, foot = _limb(hip, L * 0.55, ang, bend=-(abs(ang) * 0.7 + 12))
        d.line([hip, knee, foot], fill=INK, width=lw, joint="curve")
        d.ellipse([foot[0] - 5 * s, foot[1] - 2, foot[0] + 5 * s, foot[1] + 2], fill=INK)

    # torso
    d.line([hip, neck], fill=INK, width=lw)

    # arms
    for ang, target_key in ((P["arm_l"], None), (P["arm_r"], P["hand_r"])):
        if target_key == "POINT":
            target = (shoulder[0] + 46 * s, shoulder[1] - 30 * s)
        elif target_key == "CHIN":
            target = (head_c[0] + 10 * s, head_c[1] + 6 * s)
        else:
            target = None
        if target is not None:
            elbow = ((shoulder[0] + target[0]) / 2 + 6 * s,
                     (shoulder[1] + target[1]) / 2 - 4 * s)
            d.line([shoulder, elbow, target], fill=INK, width=lw, joint="curve")
            d.ellipse([target[0] - 4.5 * s, target[1] - 4.5 * s,
                       target[0] + 4.5 * s, target[1] + 4.5 * s], fill=INK)
        else:
            _, hand = _limb(shoulder, T * 0.72, ang, bend=18)
            d.line([shoulder, hand], fill=INK, width=lw, joint="curve")

    # head: FILLED white circle + thick outline
    d.ellipse([head_c[0] - R, head_c[1] - R, head_c[0] + R, head_c[1] + R],
              fill=(255, 255, 255), outline=INK, width=hw)

    # face
    ex = 5 * s          # eye x-offset from center
    ey = -2 * s         # eye y-offset
    if E["eyes"] == "big":
        er = 3.2 * s
    else:
        er = 2.2 * s
    for dx in (-ex, ex):
        d.ellipse([head_c[0] + dx - er, head_c[1] + ey - er,
                   head_c[0] + dx + er, head_c[1] + ey + er], fill=INK)

    # eyebrows (expression)
    brow = E["brow"]
    by = head_c[1] - 7 * s
    for dx in (-ex, ex):
        if brow == 1:      # worried: inner-up
            d.line([(head_c[0] + dx - 4 * s, by + 1), (head_c[0] + dx + 4 * s, by - 2)], fill=INK, width=lw)
        elif brow == -1:   # sad: inner-down
            d.line([(head_c[0] + dx - 4 * s, by - 2), (head_c[0] + dx + 4 * s, by + 1)], fill=INK, width=lw)
        elif brow == 2:    # surprised: raised
            d.line([(head_c[0] + dx - 4 * s, by - 4), (head_c[0] + dx + 4 * s, by - 4)], fill=INK, width=lw)

    # mouth
    mx, my = head_c[0], head_c[1] + 8 * s
    m = E["mouth"]
    if m == "smile":
        d.arc([mx - 5 * s, my - 3 * s, mx + 5 * s, my + 3 * s], 20, 160, fill=INK, width=lw)
    elif m == "smirk":
        d.arc([mx - 5 * s, my - 2 * s, mx + 5 * s, my + 4 * s], 30, 150, fill=INK, width=lw)
    elif m == "o":
        d.ellipse([mx - 3.2 * s, my - 3.2 * s, mx + 3.2 * s, my + 3.2 * s], fill=INK)
    elif m == "frown":
        d.arc([mx - 5 * s, my - 6 * s, mx + 5 * s, my + 1 * s], 200, 340, fill=INK, width=lw)
    elif m == "small":
        d.line([(mx - 2.5 * s, my), (mx + 2.5 * s, my)], fill=INK, width=lw)
    else:  # line
        d.line([(mx - 4 * s, my), (mx + 4 * s, my)], fill=INK, width=lw)


def text_center(d, xy, txt, font, fill=INK):
    w = d.textlength(txt, font=font)
    d.text((xy[0] - w / 2, xy[1]), txt, font=font, fill=fill)


# ---------------------------------------------------------------------------
# Demo renderers
# ---------------------------------------------------------------------------
def render_sheet():
    """Character sheet: the hero in 6 poses/expressions (the Charakterset)."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    title = load_font(40, bold=True)
    label = load_font(24)
    text_center(d, (W / 2, 40), "Charakterset — ein Held, viele Posen & Gesichter", title)

    cells = [
        ("stand", "neutral", "stand · neutral"),
        ("point", "confident", "point · confident"),
        ("think", "worried", "think · worried"),
        ("celebrate", "happy", "celebrate · happy"),
        ("run", "surprised", "run · surprised"),
        ("sad", "sad", "sad · sad"),
    ]
    cols, rows = 3, 2
    cw, ch = W / cols, (H - 90) / rows
    for i, (pose, expr, name) in enumerate(cells):
        r, c = divmod(i, cols)
        cx = c * cw + cw / 2
        cy = 90 + r * ch + ch / 2 + 30
        draw_character(d, cx, cy, s=1.7, pose=pose, expr=expr,
                       walk_phase=0.5 if pose == "run" else 0.0)
        text_center(d, (cx, 90 + r * ch + 40), name, label, fill=(110, 110, 118))
    img.save(os.path.join(OUT, "character_sheet.png"))
    print("sheet saved")


def render_clip():
    """Short scene using the hero with expression changes."""
    scenes = [
        # (duration, draw_fn)
        (4.0, lambda t, d: scene_title(t, d)),
        (5.0, lambda t, d: scene_walk(t, d)),
        (6.0, lambda t, d: scene_question(t, d)),
    ]
    frames = []
    for dur, fn in scenes:
        for i in range(int(dur * FPS)):
            t = i / FPS
            img = Image.new("RGB", (W, H), BG)
            dd = ImageDraw.Draw(img)
            fn(t, dd)
            img.save(os.path.join(FRAMES, f"{len(frames):05d}.png"))
            frames.append(img)
    print(f"clip frames: {len(frames)} ({sum(s[0] for s in scenes):.1f}s)")


def scene_title(t, d):
    big = load_font(64, bold=True)
    small = load_font(32)
    text_center(d, (W / 2, H / 2 - 70), "Why do we procrastinate?", big)
    draw_character(d, W / 2, H - 60, s=1.7, pose="think", expr="worried")
    if t > 1.2:
        text_center(d, (W / 2, H / 2 + 10), "A story about tomorrow", small, fill=(120, 120, 128))


def scene_walk(t, d):
    phase = math.sin(t * 5.0)
    x = min(W * 0.55, W * 0.15 + t * 55)
    draw_character(d, x, H - 80, s=1.6, pose="stand", expr="happy", walk_phase=phase)


def scene_question(t, d):
    draw_character(d, W * 0.34, H - 80, s=1.6, pose="point", expr="confident")
    q = load_font(140, bold=True)
    text_center(d, (W * 0.67, H / 2), "?", q, fill=MUTED["red"])
    # thought bubble
    if t > 0.6:
        bx, by, bw, bh = W * 0.28, H - 430, 400, 96
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=18, outline=INK, width=3)
        text_center(d, (bx + bw / 2, by + 24), "Maybe I'll start", load_font(28), fill=INK)
        text_center(d, (bx + bw / 2, by + 58), "tomorrow...", load_font(28), fill=INK)


OUT = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(OUT, "frames2")
os.makedirs(FRAMES, exist_ok=True)

if __name__ == "__main__":
    render_sheet()
    render_clip()
