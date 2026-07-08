#!/usr/bin/env python3
"""Send each day: text schedule + carousel album to Telegram."""
import requests, json, os, time, glob, sys

BOT_TOKEN = "8980383022:AAG551IQm3CwkUQC6JbuVvKQehJPnRgzTxA"
CHAT_ID = "1263089875"
BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE, "platform-content")

def send_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    if len(text) > 4000:
        chunks = []
        while text:
            cut = text[:4000]
            brk = cut.rfind('\n\n')
            if brk < 3500: brk = cut.rfind('\n')
            if brk < 3500: brk = 4000
            chunks.append(text[:brk])
            text = text[brk:].lstrip('\n')
        for c in chunks:
            requests.post(url, json={"chat_id": CHAT_ID, "text": c, "parse_mode": "HTML"})
    else:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

def send_album(slides, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup"
    media = [{"type": "photo", "media": f"attach://{j}"} for j in range(len(slides))]
    media[0]["caption"] = caption
    media[0]["parse_mode"] = "HTML"
    files = {str(j): open(s, "rb") for j, s in enumerate(slides)}
    r = requests.post(url, data={"chat_id": CHAT_ID, "media": json.dumps(media)}, files=files)
    for f in files.values(): f.close()
    return r.ok

def get_slides_for_day(day_data):
    orig_day = str(int(day_data["post_date"].split("-")[2]) - 3).zfill(2)
    orig_date = f"2026-07-{orig_day}"
    slides = []
    for s in range(1, 8):
        p = os.path.join(BASE, "carousel-routine", "output", orig_date, "carousel-branded", f"slide-{s:02d}.png")
        if os.path.exists(p):
            slides.append(p)
    return slides

def format_day(d):
    date = d["post_date"]
    topic = d["topic"]
    msg = f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📅 <b>DAY PLAN — {date}</b>\n"
    msg += f"🏷 {topic}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += f"🧵 <b>THREADS — 8:30 AM</b>\n"
    msg += f"─────────────────\n"
    msg += f"{d['threads'][0]['content']}\n\n"
    
    msg += f"📸 <b>INSTAGRAM — 10:00 AM</b> (Carousel)\n"
    msg += f"─────────────────\n"
    msg += f"{d['instagram']['caption']}\n\n"
    
    msg += f"👤 <b>FACEBOOK — 11:00 AM</b> (Carousel)\n"
    msg += f"─────────────────\n"
    msg += f"{d['facebook']['caption']}\n\n"
    
    msg += f"🐦 <b>TWITTER/X — 12:30 PM</b> (Thread)\n"
    msg += f"─────────────────\n"
    tweets = d["twitter"][0]["tweets"]
    for i, t in enumerate(tweets):
        pfx = f"Tweet {i+1}/{len(tweets)}:\n" if len(tweets) > 1 else ""
        msg += f"{pfx}{t}\n\n"
    
    msg += f"🧵 <b>THREADS — 4:00 PM</b>\n"
    msg += f"─────────────────\n"
    msg += f"{d['threads'][1]['content']}\n\n"
    
    msg += f"🐦 <b>TWITTER/X — 6:00 PM</b> (Image)\n"
    msg += f"─────────────────\n"
    msg += f"{d['twitter'][1]['content']}\n"
    return msg

# Get start day from CLI arg or default 0
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0

day_files = sorted(glob.glob(os.path.join(CONTENT_DIR, "day-2026-07-*.json")))

for i, df in enumerate(day_files):
    if i < start:
        continue
    with open(df) as f:
        day = json.load(f)
    
    date = day["post_date"]
    topic = day["topic"]
    slides = get_slides_for_day(day)
    print(f"[{i+1}/{len(day_files)}] {date} — {topic}", end=" ")
    
    # Send text
    send_text(format_day(day))
    time.sleep(0.5)
    
    # Send carousel album
    if slides:
        ok = send_album(slides, f"📸 {date} | {topic}\n7-slide carousel for Instagram & Facebook")
        print(f"text + {len(slides)} slides {'OK' if ok else 'ERR'}")
    else:
        print("text only (no slides)")
    
    time.sleep(1.5)

print(f"\nDone!")