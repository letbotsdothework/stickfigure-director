"""Generate a clean character-sheet reference for Google Flow (Veo/Omni).

The hero is drawn LARGE and clean on white so the video model has a crisp,
unambiguous reference to keep the character consistent across clips.
"""
import os
from PIL import Image, ImageDraw
from character import draw_character, load_font, text_center, W, H, BG, INK

OUT = os.path.dirname(os.path.abspath(__file__))


def make_reference():
    # A) single large hero (primary reference)
    img = Image.new("RGB", (1280, 720), BG)
    d = ImageDraw.Draw(img)
    draw_character(d, W / 2, H - 80, s=4.0, pose="stand", expr="happy")
    img.save(os.path.join(OUT, "character_ref.png"))

    # B) pose sheet (front / point / think / celebrate) — secondary reference
    img = Image.new("RGB", (1600, 500), BG)
    d = ImageDraw.Draw(img)
    label = load_font(28)
    poses = ["stand", "point", "think", "celebrate"]
    names = ["stand", "point", "think", "celebrate"]
    for i, (p, n) in enumerate(zip(poses, names)):
        cx = 200 + i * 400
        draw_character(d, cx, 420, s=3.0, pose=p,
                       expr="happy" if p != "think" else "worried")
        text_center(d, (cx, 60), n, label, fill=(110, 110, 118))
    img.save(os.path.join(OUT, "character_sheet.png"))
    print("saved character_ref.png + character_sheet.png")


if __name__ == "__main__":
    make_reference()
