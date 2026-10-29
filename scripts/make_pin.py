#!/usr/bin/env python3
"""Build Balloon & Tusk Pinterest pins (1000x1500) as HTML for Playwright."""
import os, re, io, json, glob, subprocess, hashlib, sys

HOME = os.path.expanduser("~")
GD   = f"{HOME}/projects/memory-keeper-gifts/src/lib/gift-guides"
FONT = f"{HOME}/projects/bt-marketing-assets/brand/fonts/CormorantGaramond.ttf"
FONTI= f"{HOME}/projects/bt-marketing-assets/brand/fonts/CormorantGaramond-Italic.ttf"
WORK = os.path.dirname(os.path.abspath(__file__))
IMGD = f"{WORK}/product-cache"
os.makedirs(IMGD, exist_ok=True)

IVORY, NAVY, GOLD = "#F7F4EF", "#2C3A44", "#BFA46F"

def guide_images(filename, want=4):
    """All (name, url) pairs in guide order. Splits the file on `slug:`
    boundaries so a long description can't push `image:` out of range."""
    s = io.open(f"{GD}/{filename}", encoding="utf-8").read()
    lines = s.split("\n")
    bounds = [i for i, l in enumerate(lines) if l.strip().startswith("slug:")]
    bounds.append(len(lines))
    out = []
    for a, b in zip(bounds, bounds[1:]):
        block = "\n".join(lines[a:b])
        nm = re.search(r'\bname:\s*"([^"]+)"', block)
        im = re.search(r'\bimage:\s*"([^"]+)"', block)
        if nm and im:
            out.append((nm.group(1), im.group(1)))
    return out

def pick_four(filename, avoid=(), prefer=()):
    """First 4 products that download cleanly, are visually distinct by brand,
    and don't hit an avoid-keyword (e.g. 'b'day' on a Christmas pin).
    Anything matching `prefer` is pulled to the front (used to keep Kaizen
    Baby visible in the baby guide)."""
    cands = guide_images(filename)
    if prefer:
        hit = [c for c in cands if any(k.lower() in c[0].lower() for k in prefer)]
        rest = [c for c in cands if c not in hit]
        cands = hit + rest
    chosen, brands = [], set()
    for nm, url in cands:
        low = nm.lower()
        if any(a.lower() in low for a in avoid):
            continue
        brand = re.split(r"[\s'\u2019]", nm.strip())[0].lower()
        if brand in brands:
            continue
        local = fetch(url)
        if not local:
            continue
        brands.add(brand)
        chosen.append((nm, local))
        if len(chosen) == 4:
            break
    return chosen

def fetch(url):
    h = hashlib.md5(url.encode()).hexdigest()[:14]
    ext = ".png" if ".png" in url.lower() else (".jpg")
    dest = f"{IMGD}/{h}{ext}"
    if os.path.exists(dest) and os.path.getsize(dest) > 2000:
        return dest
    subprocess.run(["curl","-sL","--max-time","25","-A",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131 Safari/537.36",
        "-o",dest,url], capture_output=True)
    return dest if os.path.exists(dest) and os.path.getsize(dest) > 2000 else None

def build(pin):
    cells = pick_four(pin["file"], avoid=pin.get("avoid", []), prefer=pin.get("prefer", []))
    if len(cells) < 4:
        print(f"  !! {pin['slug']}: only {len(cells)}/4 usable images", file=sys.stderr)
    while len(cells) < 4: cells.append(("", None))

    parts = []
    for _, p in cells:
        inner = '<img src="file://' + p + '">' if p else ''
        parts.append('<div class="cell">' + inner + '</div>')
    grid = "".join(parts)

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:'Cormorant'; src:url('file://{FONT}') format('truetype'); font-weight:400 700; }}
@font-face {{ font-family:'CormorantI'; src:url('file://{FONTI}') format('truetype'); font-style:italic; }}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:1000px;height:1500px;}}
body{{background:{IVORY};font-family:'Cormorant',Georgia,serif;color:{NAVY};
  display:flex;flex-direction:column;padding:64px 60px 52px;position:relative;overflow:hidden;}}
body::before{{content:'';position:absolute;inset:26px;border:1px solid {GOLD}44;pointer-events:none;}}
.eyebrow{{font-family:-apple-system,'Helvetica Neue',sans-serif;font-size:19px;font-weight:600;
  letter-spacing:.22em;color:{GOLD};text-transform:uppercase;margin-bottom:26px;}}
h1{{font-size:{pin.get('size',118)}px;font-weight:600;line-height:.94;letter-spacing:-.015em;}}
.sub{{font-family:'CormorantI',Georgia,serif;font-style:italic;font-size:44px;
  color:{NAVY}bb;margin-top:18px;line-height:1.15;}}
.rule{{height:1px;background:{GOLD};opacity:.55;margin:38px 0 34px;}}
.grid{{flex:1 1 0;min-height:0;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:22px;}}
.cell{{background:#fff;border:1px solid {NAVY}14;border-radius:10px;overflow:hidden;min-height:0;min-width:0;
  display:flex;align-items:center;justify-content:center;padding:18px;
  box-shadow:0 2px 14px {NAVY}0d;}}
.cell img{{max-width:100%;max-height:100%;object-fit:contain;}}
footer{{margin-top:30px;flex:0 0 auto;display:flex;align-items:baseline;justify-content:space-between;}}
.mark{{font-family:-apple-system,'Helvetica Neue',sans-serif;font-size:21px;font-weight:700;
  letter-spacing:.2em;text-transform:uppercase;}}
.dom{{font-family:-apple-system,'Helvetica Neue',sans-serif;font-size:21px;color:{GOLD};
  letter-spacing:.04em;font-weight:600;}}
</style></head><body>
<div class="eyebrow">Gift Guide &nbsp;·&nbsp; 2026</div>
<h1>{pin['h1']}</h1>
<div class="sub">{pin['sub']}</div>
<div class="rule"></div>
<div class="grid">{grid}</div>
<footer><span class="mark">Balloon &amp; Tusk</span><span class="dom">balloonandtusk.com</span></footer>
</body></html>"""

PINS = json.load(io.open(f"{WORK}/pins.json", encoding="utf-8"))
sel = sys.argv[1:] if len(sys.argv) > 1 else [p["slug"] for p in PINS]
for pin in PINS:
    if pin["slug"] not in sel: continue
    html = build(pin)
    out = f"{WORK}/{pin['slug']}.html"
    io.open(out, "w", encoding="utf-8").write(html)
    print("html:", out)
