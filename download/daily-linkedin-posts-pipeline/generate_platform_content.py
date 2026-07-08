#!/usr/bin/env python3
"""
Generate cross-platform content and schedule from existing LinkedIn posts.
Creates adapted content for Instagram, Facebook, Threads, Twitter/X.
"""
import json, os, glob, re

BASE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE, 'posts')
OUT_DIR = os.path.join(BASE, 'platform-content')
os.makedirs(OUT_DIR, exist_ok=True)

# Load all day files
day_files = sorted(glob.glob(os.path.join(POSTS_DIR, 'day-2026-07-*.json')))

# Platform-specific hashtag sets
IG_HASHTAGS = ['#ai', '#artificialintelligence', '#tech', '#developer', '#startup', '#coding', '#automation', '#futureofwork', '#aitools', '#buildinpublic']
FB_HASHTAGS = ['#AI', '#Tech', '#Developers', '#FutureOfWork']
THREADS_TAGS = ''  # Threads doesn't use hashtags
X_TAGS = ''  # X hashtags are meh

def shorten_for_threads(text, max_chars=480):
    """Shorten LinkedIn text post to a punchy Threads post."""
    lines = text.strip().split('\n')
    # Keep the hook + first 2-3 substantive paragraphs
    result = []
    char_count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if char_count + len(line) > max_chars - 60:
            break
        result.append(line)
        char_count += len(line)
    
    post = '\n\n'.join(result)
    # End with a question if the original had one
    if '?' in text and '?' not in post[-50:]:
        # Find the last question in original
        questions = [l.strip() for l in text.split('\n') if l.strip().endswith('?')]
        if questions:
            post += '\n\n' + questions[-1]
    return post

def make_tweet_thread(text):
    """Convert a LinkedIn text post into a Twitter thread."""
    lines = text.strip().split('\n')
    thread = []
    current = ''
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(current) + len(line) + 2 > 260:
            if current:
                thread.append(current.strip())
            current = line
        else:
            current = current + '\n' + line if current else line
    
    if current:
        thread.append(current.strip())
    
    # Make first tweet a hook (shorter, punchier)
    if thread:
        first = thread[0]
        if len(first) > 200:
            # Cut to first sentence
            sentences = re.split(r'(?<=[.!?])\s+', first)
            hook = sentences[0]
            if len(hook) > 200:
                hook = hook[:197] + '...'
            thread[0] = hook + '\n\nA thread 🧵👇'
    
    return thread

def adapt_for_ig_caption(carousel_caption, topic):
    """Adapt LinkedIn caption for Instagram."""
    # Shorten and add CTA + hashtags
    caption = carousel_caption.strip()
    if len(caption) > 800:
        caption = caption[:797] + '...'
    
    caption += f'\n\n'
    # Pick 5-8 relevant hashtags
    tags = IG_HASHTAGS[:8]
    caption += ' '.join(tags)
    caption += '\n\nSave this for later. Follow @founderswing for daily AI breakdowns.'
    return caption

def adapt_for_fb_caption(carousel_caption, topic):
    """Adapt for Facebook (longer form, more conversational)."""
    caption = carousel_caption.strip()
    # Facebook allows 63k chars, keep it as-is but add CTA
    if not caption.endswith('?') and not caption.endswith('.'):
        caption += '.'
    caption += '\n\nWhat do you think? Drop your take below.'
    return caption

def make_single_image_tweet(topic, caption):
    """Create a single tweet with one image (hook from carousel)."""
    hook = caption.split('.')[0] if caption else topic
    if len(hook) > 250:
        hook = hook[:247] + '...'
    return hook

# Generate content for each day
schedule = []
start_date_offset = 3  # July 5 content starts posting July 8

for idx, day_file in enumerate(day_files):
    with open(day_file) as f:
        day_data = json.load(f)
    
    date = day_data['date']
    # Shift dates: July 5 content -> posts July 8, etc.
    day_num = int(date.split('-')[2])
    post_date = f"2026-07-{day_num + start_date_offset:02d}"
    
    carousel_post = None
    text_posts = []
    for p in day_data['posts']:
        if p['type'] == 'carousel':
            carousel_post = p
        else:
            text_posts.append(p)
    
    if len(text_posts) < 2:
        continue
    
    topic = carousel_post.get('idea', '') if carousel_post else text_posts[0].get('topic', '')
    carousel_caption = carousel_post.get('caption', '') if carousel_post else ''
    
    # Get slide images path
    slide_dir = f"carousel-routine/output/{date}/carousel-branded"
    
    # === THREADS POST 1 (8:30 AM) ===
    threads1 = shorten_for_threads(text_posts[0].get('content', ''))
    schedule.append({
        'date': post_date, 'time': '08:30', 'platform': 'threads',
        'type': 'text', 'topic': text_posts[0].get('topic', ''),
        'content': threads1
    })
    
    # === INSTAGRAM CAROUSEL (10:00 AM) ===
    ig_caption = adapt_for_ig_caption(carousel_caption, topic)
    schedule.append({
        'date': post_date, 'time': '10:00', 'platform': 'instagram',
        'type': 'carousel', 'topic': topic,
        'content': ig_caption,
        'images': [f"{slide_dir}/slide-{i:02d}.png" for i in range(1, 8)]
    })
    
    # === FACEBOOK CAROUSEL (11:00 AM) ===
    fb_caption = adapt_for_fb_caption(carousel_caption, topic)
    schedule.append({
        'date': post_date, 'time': '11:00', 'platform': 'facebook',
        'type': 'carousel', 'topic': topic,
        'content': fb_caption,
        'images': [f"{slide_dir}/slide-{i:02d}.png" for i in range(1, 8)]
    })
    
    # === TWITTER THREAD (12:30 PM) ===
    x_thread = make_tweet_thread(text_posts[0].get('content', ''))
    schedule.append({
        'date': post_date, 'time': '12:30', 'platform': 'twitter',
        'type': 'thread', 'topic': text_posts[0].get('topic', ''),
        'content': x_thread
    })
    
    # === THREADS POST 2 (4:00 PM) ===
    threads2 = shorten_for_threads(text_posts[1].get('content', ''))
    schedule.append({
        'date': post_date, 'time': '16:00', 'platform': 'threads',
        'type': 'text', 'topic': text_posts[1].get('topic', ''),
        'content': threads2
    })
    
    # === TWITTER IMAGE TWEET (6:00 PM) ===
    x_img_tweet = make_single_image_tweet(topic, carousel_caption)
    schedule.append({
        'date': post_date, 'time': '18:00', 'platform': 'twitter',
        'type': 'image', 'topic': f'{topic} (slide)',
        'content': x_img_tweet,
        'images': [f"{slide_dir}/slide-01.png"]
    })
    
    # Save per-day platform content
    day_content = {
        'original_date': date,
        'post_date': post_date,
        'topic': topic,
        'threads': [
            {'time': '08:30', 'content': threads1},
            {'time': '16:00', 'content': threads2}
        ],
        'instagram': {
            'time': '10:00',
            'caption': ig_caption,
            'images': [f"{slide_dir}/slide-{i:02d}.png" for i in range(1, 8)]
        },
        'facebook': {
            'time': '11:00',
            'caption': fb_caption,
            'images': [f"{slide_dir}/slide-{i:02d}.png" for i in range(1, 8)]
        },
        'twitter': [
            {'time': '12:30', 'type': 'thread', 'tweets': x_thread},
            {'time': '18:00', 'type': 'image', 'content': x_img_tweet, 'image': f"{slide_dir}/slide-01.png"}
        ]
    }
    
    out_file = os.path.join(OUT_DIR, f"day-{post_date}.json")
    with open(out_file, 'w') as f:
        json.dump(day_content, f, indent=2)

# Save master schedule
with open(os.path.join(BASE, 'cross-platform-schedule.json'), 'w') as f:
    json.dump(schedule, f, indent=2)

print(f"Generated {len(schedule)} posts across 4 platforms")
print(f"  Threads: {sum(1 for s in schedule if s['platform']=='threads')}")
print(f"  Instagram: {sum(1 for s in schedule if s['platform']=='instagram')}")
print(f"  Facebook: {sum(1 for s in schedule if s['platform']=='facebook')}")
print(f"  Twitter: {sum(1 for s in schedule if s['platform']=='twitter')}")
print(f"  Date range: {schedule[0]['date']} to {schedule[-1]['date']}")
print(f"  Content saved to: {OUT_DIR}/")
print(f"  Master schedule: cross-platform-schedule.json")