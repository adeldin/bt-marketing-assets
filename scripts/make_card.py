#!/usr/bin/env python3
"""Balloon & Tusk typographic post-card renderer.

Renders the brand's text-forward social cards (cream / navy serif / gold
accents / engraved elephant art) with real typesetting — no AI text, no
typos, pixel-identical brand every time.

Usage:
  python3 make_card.py --headline "Never forget another birthday." \
      --subline "We remember so you don't have to." \
      --out card.png [--size square|portrait] [--art trio|solo|none] \
      [--gold-words "dates,remember"] [--tagline "THE CELEBRATION SAFETY NET"]
"""
import argparse, os, re
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = os.path.join(HERE, "..", "brand")

CREAM = (247, 241, 232)
NAVY = (31, 42, 68)
GOLD = (185, 154, 91)

def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f

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

def draw_mixed_line(draw, x, y, line, fnt, gold_words):
    """Draw one line, coloring any word in gold_words gold."""
    cx = x
    for i, word in enumerate(line.split(" ")):
        clean = re.sub(r"[^\w']", "", word).lower()
        color = GOLD if clean in gold_words else NAVY
        draw.text((cx, y), word, font=fnt, fill=color)
        cx += draw.textlength(word + " ", font=fnt)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--headline", required=True)
    p.add_argument("--subline", default="")
    p.add_argument("--tagline", default="THE CELEBRATION SAFETY NET")
    p.add_argument("--gold-words", default="", help="comma-separated words to render in gold")
    p.add_argument("--size", choices=["square", "portrait"], default="square")
    p.add_argument("--art", choices=["trio", "solo", "none"], default="trio")
    p.add_argument("--out", required=True)
    a = p.parse_args()

    W, H = (1080, 1080) if a.size == "square" else (1080, 1350)
    M = 96  # margin
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    gold_words = {w.strip().lower() for w in a.gold_words.split(",") if w.strip()}

    serif = os.path.join(BRAND, "fonts", "CormorantGaramond.ttf")
    italic = os.path.join(BRAND, "fonts", "CormorantGaramond-Italic.ttf")

    # Headline — autoscale down until it fits the upper band
    head_size = 118 if a.size == "square" else 128
    while head_size > 64:
        hf = font(serif, head_size, 560)
        lines = wrap(d, a.headline, hf, W - 2 * M)
        line_h = int(head_size * 1.12)
        if len(lines) * line_h <= int(H * 0.44):
            break
        head_size -= 6
    y = int(H * 0.11)
    for line in lines:
        draw_mixed_line(d, M, y, line, hf, gold_words)
        y += line_h

    # Divider: line · dot · line in gold
    y += int(head_size * 0.45)
    seg, mid = int(W * 0.16), W // 2
    d.line([(M, y), (M + seg, y)], fill=GOLD, width=3)
    d.ellipse([(M + seg + 18, y - 5), (M + seg + 28, y + 5)], fill=GOLD)
    d.line([(M + seg + 46, y), (M + 2 * seg + 46, y)], fill=GOLD, width=3)

    # Subline — italic
    if a.subline:
        y += int(head_size * 0.55)
        sf = font(italic, 58 if a.size == "square" else 62, 500)
        for line in wrap(d, a.subline, sf, int(W * 0.78)):
            d.text((M, y), line, font=sf, fill=NAVY)
            y += int(sf.size * 1.28)

    # Illustration bottom-right
    if a.art != "none":
        art = Image.open(os.path.join(BRAND, "art", f"{a.art}.png")).convert("RGBA")
        bbox = art.getbbox()
        art = art.crop(bbox)
        target_w = int(W * (0.46 if a.art == "trio" else 0.30))
        ratio = target_w / art.width
        art = art.resize((target_w, int(art.height * ratio)), Image.LANCZOS)
        img.paste(art, (W - art.width - int(M * 0.55), H - art.height - int(M * 0.9)), art)

    # Wordmark + tagline bottom-left
    wm = font(serif, 64, 600)
    wm_y = H - int(M * 0.9) - 110
    d.text((M, wm_y), "Balloon & Tusk", font=wm, fill=NAVY)
    tg = font(serif, 30, 500)
    tracked = " ".join(a.tagline.upper())
    d.text((M, wm_y + 78), tracked, font=tg, fill=GOLD)

    img.save(a.out, "PNG")
    print(f"card: {a.out} ({W}x{H})")

if __name__ == "__main__":
    main()
