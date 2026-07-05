#!/usr/bin/env python3
"""Batch build all carousels from posts/carousel-content-*.json files.
Uses the gen_sample_carousel.py design system (warm cream, Plus Jakarta Sans, Instrument Serif).
Reads carousel content JSONs and generates HTML slides, then renders to PNGs + PDF via Puppeteer.
"""
import os, sys, json, glob

BASE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE, "posts")

# Carousel design system from gen_sample_carousel.py
ACCENT = "#5E6AD2"
KICKER = "Founders Wing / future of work"

PAGE_TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=1080"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800;900&family=Instrument+Serif:ital@1&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1080px;overflow:hidden;background:#F8F7F3;color:#111;font-family:'Plus Jakarta Sans',sans-serif;position:relative}}
.header{{position:absolute;top:60px;left:70px;right:70px;display:flex;justify-content:space-between;align-items:center;z-index:10}}
.hleft{{display:flex;align-items:center;gap:12px;font-size:14px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#111}}
.dot{{width:14px;height:14px;border-radius:50%;background:{accent}}}
.hright{{display:flex;align-items:center;gap:15px}}
.fw{{font-family:'Instrument Serif',serif;font-style:italic;font-size:26px;color:#999}}
.badge{{width:46px;height:46px;background:{accent};border-radius:50%;display:flex;justify-content:center;align-items:center;color:#fff;font-weight:800;font-size:17px}}
.content{{position:absolute;top:230px;left:70px;right:70px;bottom:150px;z-index:5;display:flex;align-items:center;gap:54px}}
.col{{flex:1;min-width:0}}
.kick{{font-size:18px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:{accent};margin-bottom:20px}}
.headline{{font-size:{hsize}px;font-weight:900;letter-spacing:-2.5px;line-height:1.05}}
.headline em{{font-family:'Instrument Serif',serif;font-style:italic;color:{accent};font-weight:400;letter-spacing:0;padding-left:4px}}
.body{{font-size:27px;font-weight:500;color:#333;line-height:1.42;margin-top:26px}}
.line{{width:64px;height:5px;background:{accent};margin-top:30px}}
.imgwrap{{flex-shrink:0;width:380px;height:460px;border-radius:30px;overflow:hidden;box-shadow:0 24px 50px rgba(0,0,0,0.16);position:relative;background:linear-gradient(135deg,#e8e6f0 0%,#d4d2e8 100%)}}
.imgwrap img{{width:100%;height:100%;object-fit:cover}}
.imgwrap::after{{content:"";position:absolute;inset:0;border-radius:30px;border:1px solid rgba(0,0,0,0.06);box-shadow:inset 0 0 0 6px rgba(248,247,243,0.0)}}
.imgtag{{position:absolute;left:16px;bottom:16px;background:rgba(17,17,17,0.78);color:#fff;font-size:14px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:8px 14px;border-radius:30px}}
.bottom{{position:absolute;bottom:62px;left:70px;right:70px;display:flex;justify-content:space-between;align-items:center;z-index:5}}
.swipe{{font-size:14px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#111}}
.pill{{background:#111;color:#fff;padding:20px 40px;border-radius:50px;font-size:22px;font-weight:800}}
.pill em{{font-family:'Instrument Serif',serif;font-style:italic;color:{accent};font-weight:400;margin-left:6px}}
.cta-content{{position:absolute;top:300px;left:70px;right:70px;z-index:5}}
</style></head><body>
<div class="header"><div class="hleft"><span class="dot"></span>{kicker}</div>
<div class="hright"><div class="fw">founders wing / 2026</div><div class="badge">{num}</div></div></div>
{main}
<div class="bottom">{bottom}</div>
</body></html>"""

# Image placeholders (gradient backgrounds when no real images)
GRADIENTS = [
    "linear-gradient(135deg,#667eea 0%,#764ba2 100%)",
    "linear-gradient(135deg,#f093fb 0%,#f5576c 100%)",
    "linear-gradient(135deg,#4facfe 0%,#00f2fe 100%)",
    "linear-gradient(135deg,#43e97b 0%,#38f9d7 100%)",
    "linear-gradient(135deg,#fa709a 0%,#fee140 100%)",
    "linear-gradient(135deg,#a18cd1 0%,#fbc2eb 100%)",
]

def italicize_phrase(text):
    """Wrap the last meaningful phrase in <em> tags for the design system."""
    # Find a 1-2 word phrase near the end to italicize
    words = text.split()
    if len(words) >= 3:
        # Italicize the last 1-2 words
        em_words = words[-1] if len(words) < 6 else ' '.join(words[-2:])
        rest = ' '.join(words[:-len(em_words.split())])
        return f'{rest} <em>{em_words}</em>'
    return f'<em>{text}</em>'

def build_slide(slide_data, slide_num, is_cta=False):
    """Build HTML for a single slide."""
    num = f"{slide_num:02d}"
    
    if is_cta or slide_num == 7:
        main = (f'<div class="cta-content"><div class="headline" style="font-size:74px">'
                f'{slide_data.get("headline","")}</div>'
                f'<div class="line"></div>'
                f'<div class="body">{slide_data.get("body","")}</div></div>')
        bottom = '<div></div><div class="pill">follow me for daily AI <em>breakdowns.</em></div>'
    else:
        headline = italicize_phrase(slide_data.get("headline", ""))
        kick = slide_data.get("headline", "").split()[0].upper() if slide_data.get("headline") else f"POINT {slide_num-1}"
        # Use the kicker from data if available, otherwise derive from headline
        if slide_data.get("body"):
            kick_text = f"0{slide_num-1} · " + slide_data.get("image_keyword", kick)[:15]
        else:
            kick_text = f"0{slide_num-1}"
        
        grad = GRADIENTS[(slide_num - 2) % len(GRADIENTS)]
        img = (f'<div class="imgwrap" style="background:{grad}"><div class="imgtag">{slide_data.get("image_keyword","")[:20]}</div></div>')
        col = (f'<div class="col"><div class="kick">{kick_text}</div>'
               f'<div class="headline" style="font-size:{slide_data.get("hsize",60)}px">{headline}</div>'
               f'<div class="body">{slide_data.get("body","")}</div></div>')
        main = f'<div class="content">{col}{img}</div>'
        bottom = '<div></div><div class="swipe">SWIPE &rarr;</div>'
    
    return PAGE_TEMPLATE.format(accent=ACCENT, kicker=KICKER, num=num, hsize=60, main=main, bottom=bottom)

def build_carousel_for_date(date_str):
    """Build HTML slides for a specific date."""
    content_file = os.path.join(POSTS_DIR, f"carousel-content-{date_str}.json")
    if not os.path.exists(content_file):
        print(f"  SKIP: {content_file} not found")
        return False
    
    with open(content_file) as f:
        slides = json.load(f)
    
    if not isinstance(slides, list) or len(slides) < 7:
        print(f"  SKIP: {content_file} has {len(slides) if isinstance(slides, list) else 'non-list'} slides")
        return False
    
    temp_dir = os.path.join(BASE, "carousel-routine", "temp", date_str)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Clean existing slides
    for f in os.listdir(temp_dir):
        if f.startswith("slide-") and f.endswith(".html"):
            os.remove(os.path.join(temp_dir, f))
    
    # Write new slides
    for i, slide in enumerate(slides[:7]):
        slide_num = i + 1
        is_cta = (slide_num == 7)
        html = build_slide(slide, slide_num, is_cta)
        path = os.path.join(temp_dir, f"slide-{slide_num:02d}.html")
        with open(path, "w") as f:
            f.write(html)
    
    print(f"  OK: {date_str} - 7 HTML slides written to {temp_dir}")
    return True

def main():
    # Find all carousel content files
    content_files = sorted(glob.glob(os.path.join(POSTS_DIR, "carousel-content-*.json")))
    
    if not content_files:
        print("No carousel content files found in posts/")
        sys.exit(1)
    
    print(f"Found {len(content_files)} carousel content files")
    
    built = 0
    for cf in content_files:
        # Extract date from filename
        date_str = os.path.basename(cf).replace("carousel-content-", "").replace(".json", "")
        if build_carousel_for_date(date_str):
            built += 1
    
    print(f"\nBuilt {built}/{len(content_files)} carousels")
    print(f"\nNext step: Run 'node build_all_carousels.cjs' to render PNGs + PDFs")

if __name__ == "__main__":
    main()