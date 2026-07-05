#!/usr/bin/env node
/**
 * schedule_all_15days.cjs
 * Schedules all 45 posts. Carousel posts upload 7 PNGs as a multi-image post.
 * Text posts are typed directly.
 *
 * Usage:
 *   node schedule_all_15days.cjs                    # schedule all 45
 *   node schedule_all_15days.cjs --date 2026-07-05  # single day
 *   node schedule_all_15days.cjs --from 5 --to 9    # day range
 *   node schedule_all_15days.cjs --carousel-only    # only carousel posts
 *   node schedule_all_15days.cjs --now              # post first one immediately
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const BASE = __dirname;
const PROFILE_DIR = path.join(BASE, '.puppeteer_profile');
const SCHEDULE_FILE = path.join(BASE, 'schedule.json');
const POSTS_DIR = path.join(BASE, 'posts');

// CLI
const args = process.argv.slice(2);
let FILTER_DATE = null, FILTER_FROM = null, FILTER_TO = null, POST_NOW = false, CAROUSEL_ONLY = false;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--date' && args[i+1]) FILTER_DATE = args[++i];
  if (args[i] === '--from' && args[i+1]) FILTER_FROM = args[++i];
  if (args[i] === '--to' && args[i+1]) FILTER_TO = args[++i];
  if (args[i] === '--now') POST_NOW = true;
  if (args[i] === '--carousel-only') CAROUSEL_ONLY = true;
}

const schedule = JSON.parse(fs.readFileSync(SCHEDULE_FILE, 'utf-8'));
let items = schedule;

if (FILTER_DATE) items = items.filter(i => i.date === FILTER_DATE);
if (FILTER_FROM || FILTER_TO) items = items.filter(i => {
  const day = parseInt(i.date.split('-')[2]);
  if (FILTER_FROM && day < parseInt(FILTER_FROM)) return false;
  if (FILTER_TO && day > parseInt(FILTER_TO)) return false;
  return true;
});
if (CAROUSEL_ONLY) items = items.filter(i => i.type === 'carousel');

console.log(`\n${'='.repeat(55)}`);
console.log(`  FOUNDERS WING — LinkedIn Scheduler`);
console.log(`  ${items.length} posts ready`);
console.log(`${'='.repeat(55)}\n`);

function loadDayContent(date) {
  const f = path.join(POSTS_DIR, `day-${date}.json`);
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : null;
}

function getPostText(dayData, time, type) {
  if (!dayData || !dayData.posts) return '';
  const post = dayData.posts.find(p => p.time === time && p.type === type);
  if (!post) return '';
  return type === 'carousel' ? (post.caption || '') : (post.content || '');
}

function getSlideImages(date) {
  const dir = path.join(BASE, 'carousel-routine', 'output', date, 'carousel-branded');
  const imgs = [];
  for (let i = 1; i <= 7; i++) {
    const p = path.join(dir, `slide-${String(i).padStart(2,'0')}.png`);
    if (fs.existsSync(p)) imgs.push(p);
  }
  return imgs;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    headless: false,
    userDataDir: PROFILE_DIR,
    defaultViewport: null,
    args: ['--start-maximized'],
    protocolTimeout: 1800000
  });

  const pages = await browser.pages();
  const page = pages[0] || await browser.newPage();

  console.log('Opening LinkedIn...');
  await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'domcontentloaded' });

  try {
    await page.waitForSelector('.feed-identity-module, .global-nav, .share-box-feed-entry__trigger', { timeout: 15000 });
    console.log('Logged in!\n');
  } catch {
    console.log('Log in manually in the browser window...');
    await page.waitForSelector('.feed-identity-module, .global-nav, .share-box-feed-entry__trigger', { timeout: 0 });
    console.log('Logged in!\n');
  }

  let ok = 0, fail = 0;

  for (let idx = 0; idx < items.length; idx++) {
    const item = items[idx];
    const dayData = loadDayContent(item.date);
    const text = getPostText(dayData, item.time, item.type);
    const isCarousel = item.type === 'carousel';
    const images = isCarousel ? getSlideImages(item.date) : [];

    console.log(`${'─'.repeat(50)}`);
    console.log(`[${idx+1}/${items.length}] ${item.date} ${item.time} | ${item.type} | ${item.topic}`);
    console.log(`${'─'.repeat(50)}`);

    if (isCarousel && images.length === 0) {
      console.log('  SKIP: No PNGs found');
      fail++; continue;
    }
    if (!isCarousel && !text) {
      console.log('  SKIP: No content');
      fail++; continue;
    }

    try {
      // Fresh feed navigation
      await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'domcontentloaded', timeout: 15000 });
      await sleep(3000);

      // Kill messaging overlay
      await page.evaluate(() => {
        const s = document.createElement('style');
        s.textContent = '.msg-overlay-container,[class*="msg-overlay"],#msg-overlay{display:none!important}';
        document.head.appendChild(s);
      });

      // Click "Start a post"
      console.log('  Opening composer...');
      let startBtn = await page.$('button.share-box-feed-entry__trigger')
        || await page.$('#main button.share-box-feed-entry__trigger');
      if (!startBtn) {
        const [xp] = await page.$x('//button[contains(., "Start a post")]');
        startBtn = xp;
      }
      if (!startBtn) throw new Error('No "Start a post" button');
      await startBtn.click();
      await sleep(2000);

      await page.waitForSelector('.ql-editor, [contenteditable="true"]', { timeout: 10000 });
      await sleep(1000);

      // Upload images for carousels
      if (isCarousel && images.length > 0) {
        console.log(`  Uploading ${images.length} images...`);

        // Click image upload button
        const imgBtnSelectors = [
          'button[aria-label="Add image"]',
          'button[aria-label="Add media"]',
          'button.share-promoted-detour-button[aria-label="Add image"]'
        ];
        let imgBtn = null;
        for (const sel of imgBtnSelectors) {
          try { imgBtn = await page.$(sel); if (imgBtn) break; } catch {}
        }
        if (!imgBtn) {
          const [xp] = await page.$x('//button[contains(@aria-label, "image")]');
          imgBtn = xp;
        }

        if (imgBtn) {
          await imgBtn.click();
          await sleep(1500);
        }

        // Upload all 7 slide images via file input
        const fileInput = await page.$('input[type="file"]');
        if (fileInput) {
          await fileInput.uploadFile(...images);
          console.log('  All slides uploaded');

          // Wait for processing
          await sleep(4000);
        } else {
          console.log('  WARN: No file input found, upload manually');
        }
      }

      // Type caption
      console.log('  Typing caption...');
      const editor = await page.$('.ql-editor') || await page.$('[contenteditable="true"]');
      if (editor) {
        await editor.focus();
        await page.keyboard.type(text, { delay: 3 });
      }
      await sleep(1000);

      // Post or Schedule
      if (POST_NOW && idx === 0) {
        console.log('  Posting NOW...');
        const postBtn = await page.$('button.share-actions__primary-action')
          || await page.$('button[aria-label="Post"]');
        if (postBtn) await postBtn.click();
        console.log('  Posted!');
      } else {
        console.log(`  Scheduling: ${item.date} ${item.time}...`);
        const schedBtn = await page.$('button[aria-label="Schedule for later"]')
          || await page.$('button.share-actions__schedule-btn');
        if (schedBtn) {
          await schedBtn.click();
          await sleep(2000);

          // Date
          const dateEl = await page.$('input[type="date"], input[name="date"]');
          if (dateEl) {
            await page.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); }, dateEl, item.date);
          }

          // Time
          const timeEl = await page.$('input[type="time"], select[name="time"]');
          if (timeEl) {
            await page.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); }, timeEl, item.time);
          }

          await sleep(1000);

          // Next
          try { const [nb] = await page.$x('//button[contains(., "Next")]'); if (nb) await nb.click(); } catch {}
          await sleep(2000);

          // Final Schedule
          const finalBtn = await page.$('button.share-actions__post-btn')
            || await page.$('button.share-box_actions__post-btn');
          if (finalBtn) await finalBtn.click();
          try { const [sb] = await page.$x('//button[contains(., "Schedule")]'); if (sb) await sb.click(); } catch {}

          console.log('  Scheduled!');
        } else {
          console.log('  WARN: Click schedule icon manually');
        }
      }

      ok++;
      console.log('  DONE');

      if (idx < items.length - 1) {
        const w = 8 + Math.floor(Math.random() * 7);
        console.log(`  Waiting ${w}s...`);
        await sleep(w * 1000);
      }
    } catch (err) {
      fail++;
      console.error(`  ERROR: ${err.message}`);
      await sleep(3000);
    }
  }

  console.log(`\n${'='.repeat(55)}`);
  console.log(`  DONE: ${ok} scheduled, ${fail} failed`);
  console.log(`${'='.repeat(55)}\n`);

  await new Promise(() => {});
})();