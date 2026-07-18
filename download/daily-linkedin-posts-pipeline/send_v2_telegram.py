#!/usr/bin/env python3
"""Send v2 3-pillar content to Telegram: text plan + carousel images per day."""
import requests, json, os, time, glob

BOT_TOKEN = "8980383022:AAG551IQm3CwkUQC6JbuVvKQehJPnRgzTxA"
CHAT_ID = "1263089875"
BASE = os.path.abspath(".")
CONTENT_DIR = os.path.join(BASE, "platform-content-v2")

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

def format_day(d):
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

    # Hero
    h = d["hero"]
    msg += f"📚 <b>1:00 PM — {h['series']}</b>\n"
    msg += f"{'─'*30}\n"
    msg += f"🏷 {h['topic']}\n"
    msg += f"🖼 7-slide carousel (below)\n\n"

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

day_files = sorted(glob.glob(os.path.join(CONTENT_DIR, "day-2026-07-*.json")))
print(f"Sending {len(day_files)} days to Telegram...")

for i, df in enumerate(day_files):
    with open(df) as f:
        day = json.load(f)
    
    date = day["date"]
    print(f"[{i+1}/{len(day_files)}] {date} — {day['topic']}", end=" ")

    # Send text
    send_text(format_day(day))
    time.sleep(0.5)

    # Send carousel album
    slides = []
    for s in day["hero"]["images"]:
        p = os.path.join(BASE, s)
        if os.path.exists(p):
            slides.append(p)

    if slides:
        ok = send_album(slides, f"📚 {day['hero']['series']}\n{day['topic']}\nansaribilal.com")
        print(f"text + {len(slides)} slides {'OK' if ok else 'ERR'}")
    else:
        print("text only (no slides)")

    time.sleep(1.5)

print("\nDone! All v2 content sent.")