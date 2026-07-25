#!/usr/bin/env python3
"""Balloon & Tusk animated card — Reels/Stories MP4 (1080x1920).

Restrained motion graphics: headline lines drift up and fade in, the gold
divider draws itself, the subline and engraved art fade in (art breathes
with a slow bob), tagline lands last, then holds. No AI video — the same
deterministic renderer as make_card.py, in motion.

Usage:
  python3 make_reel.py --headline "Never forget another birthday." \
      --subline "We remember so you don't have to." \
      --gold-words birthday --art solo --out reel.mp4 [--duration 7]

Requires: pillow, imageio-ffmpeg (pip install pillow imageio-ffmpeg)
"""
import argparse, math, os, re
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = os.path.join(HERE, "..", "brand")
CREAM = (247, 241, 232)
NAVY = (31, 42, 68)
GOLD = (185, 154, 91)
W, H, FPS = 1080, 1920, 30

def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f

def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3

def fade_window(t, start, dur):
    return ease_out((t - start) / dur) if t >= start else 0.0

def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def blend(color, alpha):
    return tuple(int(CREAM[i] + (color[i] - CREAM[i]) * alpha) for i in range(3))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--headline", required=True)
    p.add_argument("--subline", default="")
    p.add_argument("--tagline", default="THE CELEBRATION SAFETY NET")
    p.add_argument("--gold-words", default="")
    p.add_argument("--art", choices=["trio", "solo", "none"], default="solo")
    p.add_argument("--duration", type=float, default=7.0)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    gold_words = {w.strip().lower() for w in a.gold_words.split(",") if w.strip()}
    M = 108
    serif = os.path.join(BRAND, "fonts", "CormorantGaramond.ttf")
    italic = os.path.join(BRAND, "fonts", "CormorantGaramond-Italic.ttf")

    # Static layout pass
    probe = ImageDraw.Draw(Image.new("RGB", (W, H)))
    head_size = 150
    while head_size > 80:
        hf = font(serif, head_size, 560)
        lines = wrap(probe, a.headline, hf, W - 2 * M)
        line_h = int(head_size * 1.12)
        if len(lines) * line_h <= int(H * 0.30):
            break
        head_size -= 8
    sf = font(italic, 66, 500)
    sub_lines = wrap(probe, a.subline, sf, int(W * (0.66 if a.art != "none" else 0.78))) if a.subline else []
    wm_f = font(serif, 72, 600)
    tg_f = font(serif, 34, 500)

    art_im = None
    if a.art != "none":
        art_im = Image.open(os.path.join(BRAND, "art", f"{a.art}.png")).convert("RGBA")
        art_im = art_im.crop(art_im.getbbox())
        tw = int(W * (0.62 if a.art == "trio" else 0.44))
        art_im = art_im.resize((tw, int(art_im.height * tw / art_im.width)), Image.LANCZOS)

    head_y0 = int(H * 0.16)
    div_y = head_y0 + len(lines) * line_h + int(head_size * 0.42)
    sub_y0 = div_y + int(head_size * 0.55)
    wm_y = H - 300

    n_frames = int(a.duration * FPS)
    gen = imageio_ffmpeg.write_frames(
        a.out, (W, H), fps=FPS, codec="libx264", macro_block_size=1,
        output_params=["-profile:v", "high"],
    )
    gen.send(None)

    for i in range(n_frames):
        t = i / FPS
        img = Image.new("RGB", (W, H), CREAM)
        d = ImageDraw.Draw(img)

        # Headline lines: staggered fade + 24px upward drift
        for li, line in enumerate(lines):
            al = fade_window(t, 0.3 + li * 0.35, 0.8)
            if al <= 0:
                continue
            y = head_y0 + li * line_h + int((1 - al) * 24)
            cx = M
            for word in line.split(" "):
                clean = re.sub(r"[^\w']", "", word).lower()
                col = GOLD if clean in gold_words else NAVY
                d.text((cx, y), word, font=hf, fill=blend(col, al))
                cx += d.textlength(word + " ", font=hf)

        # Divider draws outward from center
        da = fade_window(t, 0.3 + len(lines) * 0.35 + 0.2, 0.6)
        if da > 0:
            seg = int(W * 0.15 * da)
            cx0 = M + int(W * 0.16)
            d.line([(cx0 - seg, div_y), (cx0, div_y)], fill=blend(GOLD, da), width=3)
            d.ellipse([(cx0 + 18, div_y - 5), (cx0 + 28, div_y + 5)], fill=blend(GOLD, da))
            d.line([(cx0 + 46, div_y), (cx0 + 46 + seg, div_y)], fill=blend(GOLD, da), width=3)

        # Subline
        sa = fade_window(t, 0.3 + len(lines) * 0.35 + 0.7, 0.8)
        if sa > 0 and sub_lines:
            y = sub_y0 + int((1 - sa) * 16)
            for line in sub_lines:
                d.text((M, y), line, font=sf, fill=blend(NAVY, sa))
                y += int(sf.size * 1.28)

        # Art: fade in + slow breathing bob (±5px) + balloon-like rise on entry
        if art_im is not None:
            aa = fade_window(t, 1.6, 1.0)
            if aa > 0:
                bob = int(5 * math.sin((t - 1.6) * 1.4)) if aa >= 1 else 0
                rise = int((1 - aa) * 40)
                frame_art = art_im.copy()
                if aa < 1:
                    alpha = frame_art.getchannel("A").point(lambda p: int(p * aa))
                    frame_art.putalpha(alpha)
                art_y = wm_y - frame_art.height - 48
                img.paste(frame_art, (W - frame_art.width - int(M * 0.5), art_y + rise + bob), frame_art)

        # Wordmark + tagline last
        wa = fade_window(t, 2.6, 0.9)
        if wa > 0:
            d.text((M, wm_y), "Balloon & Tusk", font=wm_f, fill=blend(NAVY, wa))
            d.text((M, wm_y + 88), " ".join(a.tagline.upper()), font=tg_f, fill=blend(GOLD, wa))

        gen.send(img.tobytes())

    gen.close()
    print(f"reel: {a.out} ({W}x{H}, {a.duration}s @ {FPS}fps)")

if __name__ == "__main__":
    main()
