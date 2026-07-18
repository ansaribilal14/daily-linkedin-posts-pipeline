#!/usr/bin/env python3
"""V2: 3-pillar content ecosystem generator."""
import json, os, glob, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE, "posts")
CONTENT_DIR = os.path.join(BASE, "platform-content-v2")
os.makedirs(CONTENT_DIR, exist_ok=True)

GEMS = [
    {"cat":"AI Tool","problem":"Stop rewriting the same API client for every project.","tool":"OpenAPI Generator","one":"Instant typed SDKs from any OpenAPI spec. Paste a URL, get TypeScript or Python client code.","bullets":["Generates clients in 40+ languages from OpenAPI 3.x specs","Zero config, handles auth, pagination, and errors automatically","Saves 2-3 hours per API integration you'd otherwise write by hand"],"link":"github.com/OpenAPITools/openapi-generator"},
    {"cat":"VS Code Extension","problem":"Stop manually copying error messages to Google.","tool":"Error Lens","one":"Shows errors inline, right where the code breaks. No hovering needed.","bullets":["Displays TypeScript, Python, Rust errors directly in the editor line","Cuts debug time by 40% for multi-file projects","Works with any language server that supports diagnostics"],"link":"marketplace.visualstudio.com/items?itemName=usernamehw.errorlens"},
    {"cat":"MCP Server","problem":"Your AI assistant can't read your database schema.","tool":"Postgres MCP Server","one":"Gives Claude/Cursor live access to your Postgres schema without exposing credentials.","bullets":["Claude can query tables, explain schemas, write migrations","Read-only by default, you approve any write operations","Replaces copy-pasting schema DDLs into your AI prompt"],"link":"github.com/modelcontextprotocol/servers/tree/main/src/postgres"},
    {"cat":"Chrome Extension","problem":"Stop losing the AI prompts that actually work.","tool":"PromptBox","one":"Save, organize, and reuse AI prompts with one click from any chat interface.","bullets":["Right-click to save any prompt from ChatGPT, Claude, or Gemini","Folders, tags, and search across your entire prompt library","Community prompts with usage stats so you know what works"],"link":"promptbox.ai"},
    {"cat":"API","problem":"Stop building your own email verification system.","tool":"Hunter.io Free API","one":"Verify any email and find the right contact at any company. 25 free searches/month.","bullets":["Email verification with 99.9% deliverability prediction","Domain search reveals company email patterns","Enough free tier for early-stage founders to never pay"],"link":"hunter.io/api"},
    {"cat":"GitHub Repo","problem":"Stop guessing why your Node.js app is slow.","tool":"0x","one":"Zero-config Node.js profiling. One command tells you exactly which function burns CPU.","bullets":["Flame graphs generated automatically in your browser","Profiles CPU, memory, and async operations","No code changes needed, works on production servers"],"link":"github.com/davidmarkclements/0x"},
    {"cat":"AI Tool","problem":"Stop recording your screen to explain a bug to your team.","tool":"Tango","one":"Records your screen and auto-generates a step-by-step visual guide. Zero editing.","bullets":["Captures clicks, scrolls, and typed text automatically","Outputs a shareable link with annotated screenshots","Turns a 10-minute walkthrough into a 60-second read"],"link":"tango.us"},
    {"cat":"VS Code Extension","problem":"Stop reading documentation to understand what a function does.","tool":"CodeTour","one":"Record and playback codebase walkthroughs like a guided tour for new team members.","bullets":["Step through code files in a defined order with annotations","Share tours as JSON files or GitHub Gists","Cuts onboarding time for new developers by 50%"],"link":"marketplace.visualstudio.com/items?itemName=vsls-contrib.codetour"},
    {"cat":"MCP Server","problem":"Your AI can browse the web but can't fill forms or click buttons.","tool":"Playwright MCP Server","one":"Gives your AI a real browser. Navigate, click, fill forms, and scrape automatically.","bullets":["Claude can interact with any website like a human","Automates form filling, testing, and data extraction","Works with any MCP-compatible AI client"],"link":"github.com/executeautomation/playwright-mcp-server"},
    {"cat":"Chrome Extension","problem":"Stop switching between 15 tabs to check different screen sizes.","tool":"Responsively App","one":"See your website on every screen size simultaneously. DevTools for each one.","bullets":["Side-by-side preview of mobile, tablet, and desktop","Synchronized scrolling and interaction across viewports","Built-in devtools for each device preview"],"link":"responsively.app"},
    {"cat":"API","problem":"Stop hardcoding mock data every time you prototype an API.","tool":"Mockaroo","one":"Generate realistic fake data in JSON, CSV, or SQL. 1000 rows free, 200+ field types.","bullets":["Names, emails, IPs, dates, paragraphs, and 200+ more types","Custom schemas with relationships between tables","REST API endpoint so you can hit it directly from your code"],"link":"mockaroo.com"},
    {"cat":"GitHub Repo","problem":"Stop screenshotting error logs and pasting them in Slack.","tool":"share-cli","one":"Creates a private URL for any terminal output. Expires in 24 hours. No account.","bullets":["One command: share file.txt or echo error | share","Password-protected, auto-expiring shareable links","Perfect for sharing logs, stack traces, and config with your team"],"link":"github.com/jcsalomon/share"},
    {"cat":"AI Tool","problem":"Stop paying $20/month for AI image generation you use twice a week.","tool":"Fooocus","one":"Midjourney-quality images, runs locally, completely free. No subscription.","bullets":["Simple prompt box, no complex settings to learn","Runs on any GPU with 4GB+ VRAM or use free cloud instances","Outputs are production-ready for social media and landing pages"],"link":"github.com/lllyasviel/Fooocus"},
]

MORNINGS = [
    {"type":"AI Fact of the Day","content":"GPT-4 was trained on 13 trillion tokens. Roughly 20 million books. The model is 1.76 trillion parameters but uses mixture-of-experts, meaning only 220 billion are active per response. This is why it feels fast despite its massive size."},
    {"type":"AI Stat of the Day","content":"67% of Fortune 500 companies have a GenAI initiative in production. Only 12% report measurable ROI. The gap between deployment and value is the biggest story in enterprise tech. Most are stuck in the pilot forever phase."},
    {"type":"GitHub Repo of the Day","content":"build-your-own-x\n\nLinks to build your own: Git, JSON parser, web server, database, shell, regex engine, and 100+ more. Every implementation has step-by-step tutorials.\n\nIf you want to understand how something works, build it. This repo is the map.\n\n70k+ stars. Updated weekly.\ngithub.com/codecrafters-io/build-your-own-x"},
    {"type":"Prompt of the Day","content":"\"You are a senior engineer reviewing my code. Do NOT suggest changes. Instead, ask me 5 questions that will make me spot the problem myself.\"\n\nThis prompt is 10x more effective than \"review my code.\" It teaches you to think, not just copy fixes."},
    {"type":"AI Fact of the Day","content":"Claude can read entire codebases. Not individual files. Entire repositories. The Codebase Memory MCP gives it full context of your project structure, dependencies, and patterns. This is why Claude Code makes changes spanning 20+ files coherently."},
    {"type":"AI Stat of the Day","content":"Developers using AI coding tools ship 55% more features per sprint. But bug rate increases 23%. The productivity gain is real. The quality cost is also real. Teams that pair AI with strong testing see 3x the net benefit."},
    {"type":"GitHub Repo of the Day","content":"awesome-mcp-servers\n\n200+ MCP servers for every use case: web scraping, database access, file systems, browser automation, design tools, and more.\n\nIf you use Claude, Cursor, or any MCP-compatible tool, this is your plugin directory. Updated daily.\ngithub.com/punkpeye/awesome-mcp-servers"},
    {"type":"Prompt of the Day","content":"\"Take the role of a Principal Engineer at a FAANG company. Review this architecture decision. For each option give me: (1) What breaks at 10x scale (2) What breaks at 100x scale (3) The one thing everyone overlooks.\"\n\nForces AI to think in systems, not just code."},
    {"type":"AI Fact of the Day","content":"GitHub Copilot now auto-completes pull request descriptions, test cases, and commit messages. The training data shifted from public repos to internal Microsoft/GitHub workflows. Your company's private patterns are the new training data."},
    {"type":"AI Stat of the Day","content":"Open source AI models caught up to proprietary ones on coding benchmarks. DeepSeek Coder V2 matches GPT-4 on HumanEval. Llama 3.1 405B matches Claude on reasoning. The pay $20/month or fall behind narrative is dying."},
    {"type":"GitHub Repo of the Day","content":"system-design-101\n\nHow large-scale systems are actually designed. Covers WhatsApp, YouTube, Google Drive, Uber, and 30+ real architectures with diagrams and trade-off analysis.\n\nNot a tutorial. A mental model library.\n\n50k+ stars.\ngithub.com/ByteByteGoHQ/system-design-101"},
    {"type":"Prompt of the Day","content":"\"I am going to paste code. Do NOT explain it. Rewrite it in the most minimal, readable way possible while preserving exact behavior. Then tell me what you removed and why.\"\n\nBest way to learn clean code. You see the before/after and the reasoning."},
    {"type":"AI Fact of the Day","content":"MCP (Model Context Protocol) is becoming the USB standard for AI tools. Instead of every AI app building its own GitHub/Slack/Postgres integration, MCP provides one universal connector. Anthropic open-sourced it. Everyone is adopting it."},
    {"type":"AI Stat of the Day","content":"The average startup spends $2,400/month on AI tools now. 18 months ago it was $400. The fastest growing SaaS category is not a single tool. It is AI tool stack management. Companies are hiring AI ops roles just to manage subscriptions."},
    {"type":"GitHub Repo of the Day","content":"free-for-dev\n\nFree tiers for everything: hosting, databases, CI/CD, analytics, email, monitoring, domains, and more.\n\nIf you are building a side project and want to spend $0, this is your entire infrastructure plan.\n\n90k+ stars.\ngithub.com/ripienaar/free-for-dev"},
]

CAROUSEL_TOPICS = ["Trigger.dev","Graphify","Video Use Skill","Hyperframes","Sploitas","Openwork","Testsprite","html-video (nexu-io)","Aura.build","Aceternity UI","Refero Styles","Mobbin","Recent (formerly Godly)","10x AI Website Builder","Codebase Memory MCP"]

ROUNDUPS = {
    "2026-07-12": {"week":1,"stories":["OpenAI launches GPT-5 with native tool use across 50+ integrations","Meta releases Llama 4 — open source model benchmarking above Claude 3.5","GitHub Copilot Workspace enters general availability","Anthropic Claude gets real-time web browsing built in","Google Gemini 2.5 Pro drops with 1M token context window"],"tools":["Trigger.dev (workflow reliability)","Aura.build (instant landing pages)","Codebase Memory MCP"],"repo":"build-your-own-x — 70k stars, learn by building","pick":"Open-sourcing your AI workflow with Trigger.dev instead of paying $2K/month to Temporal"},
    "2026-07-19": {"week":2,"stories":["DeepSeek releases Coder V3 — matches GPT-4 on code, costs 1/10th","MCP protocol hits 10,000 servers on the official registry","Cursor raises $400M at $2.6B valuation","VS Code adds native AI agent mode, no extension needed","Apple announces on-device AI models for the next macOS"],"tools":["Hyperframes (HTML to video)","Playwright MCP Server","0x (Node.js profiling)"],"repo":"awesome-mcp-servers — the MCP plugin directory","pick":"Playwright MCP Server — giving AI a real browser changes everything"},
}

# Build days
schedule = []
gem_idx = 0
morning_idx = 0

for d in range(8, 23):
    date = f"2026-07-{d:02d}"
    dow = datetime.date(2026, 7, d).strftime("%A")
    day_num = d - 7
    orig_date = f"2026-07-{d+3:02d}"
    topic = CAROUSEL_TOPICS[day_num - 1]
    slide_dir = f"carousel-routine/output/{orig_date}/carousel-branded"

    # Load original carousel caption
    day_file = os.path.join(POSTS_DIR, f"day-{orig_date}.json")
    orig_data = json.load(open(day_file)) if os.path.exists(day_file) else {"posts":[]}
    carousel = next((p for p in orig_data.get("posts",[]) if p["type"]=="carousel"), {})
    caption = carousel.get("caption", "")

    # Morning
    morning = MORNINGS[morning_idx % len(MORNINGS)]
    morning_idx += 1

    # Hero carousel
    ig_cap = f"{caption.strip()}\n\n#ai #tech #developer #startup #coding #automation #futureofwork #aitools\n\nSave this. Follow @ansari.hamza14 for daily AI breakdowns.\nansaribilal.com"
    fb_cap = f"{caption.strip()}\n\nWhat do you think? Drop your take below.\nFounders Wing — ansaribilal.com"

    # Evening
    is_roundup = dow == "Sunday" and date in ROUNDUPS
    evening = {}
    if is_roundup:
        r = ROUNDUPS[date]
        evening = {"time":"19:30","type":"weekly_roundup","series":f"This Week in AI (Week #{r['week']})","data":r}
    else:
        gem = GEMS[gem_idx]
        gem_idx += 1
        gem_label = f"Hidden Gem #{gem_idx:03d}"
        gem_ig = f"💎 {gem_label}\n\n{gem['problem']}\n\n{gem['tool']}\n{gem['one']}\n\n" + "\n".join(f"→ {b}" for b in gem['bullets']) + f"\n\n🔗 {gem['link']}\n\nFollow @ansari.hamza14 | ansaribilal.com"
        gem_threads = f"{gem['problem']}\n\n{gem['tool']} — {gem['one']}\n\n{gem['bullets'][0]}\n{gem['bullets'][1]}\n\n{gem['link']}"
        gem_x = f"{gem['problem']}\n\n{gem['tool']} — {gem['one']}\n\n" + "\n".join(f"→ {b}" for b in gem['bullets']) + f"\n\n{gem['link']}"
        evening = {"time":"19:30","type":"hidden_gem","series":gem_label,"category":gem['cat'],"gem":gem,"ig_text":gem_ig,"threads_text":gem_threads,"x_text":gem_x}

    day_entry = {
        "date": date, "dow": dow, "topic": topic,
        "morning": {"time":"09:00","type":morning["type"],"content":morning["content"]},
        "hero": {"time":"13:00","series":f"AI Tool Breakdown #{day_num:03d}","topic":topic,"ig_caption":ig_cap,"fb_caption":fb_cap,"images":[f"{slide_dir}/slide-{i:02d}.png" for i in range(1,8)]},
        "evening": evening
    }

    with open(os.path.join(CONTENT_DIR, f"day-{date}.json"), "w") as f:
        json.dump(day_entry, f, indent=2)

    schedule.append({"date":date,"time":"09:00","type":"morning","series":morning["type"]})
    schedule.append({"date":date,"time":"13:00","type":"hero_carousel","series":f"AI Tool Breakdown #{day_num:03d}"})
    if is_roundup:
        schedule.append({"date":date,"time":"19:30","type":"weekly_roundup","series":f"This Week in AI (Week #{ROUNDUPS[date]['week']})"})
    else:
        schedule.append({"date":date,"time":"19:30","type":"hidden_gem","series":f"Hidden Gem #{gem_idx:03d}"})

with open(os.path.join(BASE, "content-plan-v2.json"), "w") as f:
    json.dump(schedule, f, indent=2)

print(f"Generated 15 days, 3-pillar system")
print(f"  Morning: {sum(1 for s in schedule if s['type']=='morning')}")
print(f"  Hero Carousels: {sum(1 for s in schedule if s['type']=='hero_carousel')}")
print(f"  Hidden Gems: {sum(1 for s in schedule if s['type']=='hidden_gem')}")
print(f"  Weekly Roundups: {sum(1 for s in schedule if s['type']=='weekly_roundup')}")
print(f"  Saved to: {CONTENT_DIR}/")