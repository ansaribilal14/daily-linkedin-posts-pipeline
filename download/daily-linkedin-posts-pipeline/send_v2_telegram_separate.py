#!/usr/bin/env python3
"""Send v2 content to Telegram — SEPARATELY: carousel images first (no caption), then text as a follow-up message."""
import requests, json, os, time, glob, sys

BOT_TOKEN = "8980383022:AAG551IQm3CwkUQC6JbuVvKQehJPnRgzTxA"
CHAT_ID = "1263089875"
BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE, "platform-content-v2")

def send_text(text):
    """Send a text message, splitting if too long."""
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
            time.sleep(0.3)
    else:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

def send_photo(file_path):
    """Send a single photo with NO caption."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(file_path, "rb") as f:
        requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": f})

def send_album(slides):
    """Send a group of photos as an album with NO caption on any of them."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup"
    media = [{"type": "photo", "media": f"attach://{j}"} for j in range(len(slides))]
    files = {str(j): open(s, "rb") for j, s in enumerate(slides)}
    r = requests.post(url, data={"chat_id": CHAT_ID, "media": json.dumps(media)}, files=files)
    for f in files.values(): f.close()
    return r.ok

def format_day(d):
    """Format the full day plan as text for Telegram."""
    date = d["date"]
    dow = d["dow"]
    msg = f"{'━'*40}\n"
    msg += f"📅 <b>{date} ({dow})</b>\n"
    msg += f"{'━'*40}\n\n"

    # Morning
    m = d["morning"]
    msg += f"📰 <b>9:00 AM — {m['type']}</b>\n"
    msg += f"{'─'*30}\n"
    msg += f"{m['content']}\n\n"

    # Hero carousel
    h = d["hero"]
    msg += f"📚 <b>1:00 PM — {h['series']}</b>\n"
    msg += f"{'─'*30}\n"
    msg += f"🏷 {h['topic']}\n"
    msg += f"🖼 7-slide carousel (sent above)\n\n"

    # Evening
    e = d["evening"]
    if e["type"] == "weekly_roundup":
        r = e["data"]
        msg += f"🗓 <b>7:30 PM — {e['series']}</b>\n"
        msg += f"{'─'*30}\n"
        for i, s in enumerate(r["stories"], 1):
            msg += f"  {i}. {s}\n"
        msg += f"\n  🔧 Best tools: {', '.join(r['tools'])}\n"
        msg += f"  ⭐ Best repo: {r['repo']}\n"
        msg += f"  💡 Pick of the week: {r['pick']}\n"
    else:
        g = e["gem"]
        msg += f"💎 <b>7:30 PM — {e['series']}</b> ({g['cat']})\n"
        msg += f"{'─'*30}\n"
        msg += f"❓ {g['problem']}\n\n"
        msg += f"🔧 {g['tool']}\n"
        msg += f"{g['one']}\n\n"
        for b in g["bullets"]:
            msg += f"  → {b}\n"
        msg += f"\n  🔗 {g['link']}\n"

    return msg

def format_carousel_caption(d):
    """Format a short caption for the carousel images."""
    h = d["hero"]
    return f"📚 {h['series']}\n🏷 {h['topic']}\nansaribilal.com"

# Allow starting from a specific day index
start = int(sys.argv[1]) if len(sys.argv) > 1 else 0

day_files = sorted(glob.glob(os.path.join(CONTENT_DIR, "day-2026-07-*.json")))
print(f"Found {len(day_files)} days of v2 content")

for i, df in enumerate(day_files):
    if i < start:
        continue

    with open(df) as f:
        day = json.load(f)

    date = day["date"]
    print(f"\n[{i+1}/{len(day_files)}] {date} — {day['topic']}")

    # Collect carousel slides
    slides = []
    for s in day["hero"]["images"]:
        p = os.path.join(BASE, s)
        if os.path.exists(p):
            slides.append(p)

    # 1) Send carousel images FIRST (album, no caption)
    if slides:
        print(f"  → Sending {len(slides)} carousel images (no caption)...")
        ok = send_album(slides)
        print(f"    Album: {'OK' if ok else 'ERR'}")
        time.sleep(1)
    else:
        print(f"  → No carousel images found for this day")

    # 2) Send carousel caption as SEPARATE text message
    cap = format_carousel_caption(day)
    print(f"  → Sending carousel caption as text...")
    send_text(cap)
    time.sleep(0.5)

    # 3) Send the full day plan as a SEPARATE text message
    day_text = format_day(day)
    print(f"  → Sending day plan text ({len(day_text)} chars)...")
    send_text(day_text)
    time.sleep(1.5)

    print(f"  ✓ Done")

print(f"\n✅ All {len(day_files) - start} days sent to Telegram (images + text separately)")