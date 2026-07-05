#!/usr/bin/env node
/**
 * schedule_all_15days.cjs
 * Reads schedule.json + posts/day-*.json, schedules all 45 posts to LinkedIn.
 *
 * Usage:
 *   node schedule_all_15days.cjs              # schedule all
 *   node schedule_all_15days.cjs --date 2026-07-05   # single day
 *   node schedule_all_15days.cjs --from 5 --to 9     # day range (July 5-9)
 *   node schedule_all_15days.cjs --now                # post first one immediately
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const BASE = __dirname;
const PROFILE_DIR = path.join(BASE, '.puppeteer_profile');
const SCHEDULE_FILE = path.join(BASE, 'schedule.json');
const POSTS_DIR = path.join(BASE, 'posts');

// Parse CLI args
const args = process.argv.slice(2);
let FILTER_DATE = null;
let FILTER_FROM = null;
let FILTER_TO = null;
let POST_NOW = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--date' && args[i + 1]) FILTER_DATE = args[++i];
  if (args[i] === '--from' && args[i + 1]) FILTER_FROM = args[++i];
  if (args[i] === '--to' && args[i + 1]) FILTER_TO = args[++i];
  if (args[i] === '--now') POST_NOW = true;
}

// Load schedule
const schedule = JSON.parse(fs.readFileSync(SCHEDULE_FILE, 'utf-8'));
let items = schedule;

// Apply filters
if (FILTER_DATE) {
  items = items.filter(i => i.date === FILTER_DATE);
}
if (FILTER_FROM || FILTER_TO) {
  items = items.filter(i => {
    const day = parseInt(i.date.split('-')[2]);
    if (FILTER_FROM && day < parseInt(FILTER_FROM)) return false;
    if (FILTER_TO && day > parseInt(FILTER_TO)) return false;
    return true;
  });
}

console.log(`\n${'='.repeat(60)}`);
console.log(`  FOUNDERS WING — LinkedIn Scheduler`);
console.log(`  ${items.length} posts to schedule`);
console.log(`${'='.repeat(60)}\n`);

// Load all day content files
function loadDayContent(date) {
  const f = path.join(POSTS_DIR, `day-${date}.json`);
  if (!fs.existsSync(f)) return null;
  return JSON.parse(fs.readFileSync(f, 'utf-8'));
}

// Get the right post text from day content
function getPostText(dayData, time, type) {
  if (!dayData || !dayData.posts) return '';
  const post = dayData.posts.find(p => p.time === time && p.type === type);
  if (!post) return '';
  if (type === 'carousel') return post.caption || '';
  return post.content || '';
}

// Sleep helper
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
  const page = pages.length > 0 ? pages[0] : await browser.newPage();

  // Go to LinkedIn
  console.log('Opening LinkedIn...');
  await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'domcontentloaded' });

  // Check login
  console.log('Checking login session...');
  try {
    await page.waitForSelector('.feed-identity-module, .global-nav, .share-box-feed-entry__trigger', { timeout: 15000 });
    console.log('Logged in!\n');
  } catch {
    console.log('No active session. Please log in manually in the browser window...');
    await page.waitForSelector('.feed-identity-module, .global-nav, .share-box-feed-entry__trigger', { timeout: 0 });
    console.log('Logged in!\n');
  }

  let successCount = 0;
  let failCount = 0;

  for (let idx = 0; idx < items.length; idx++) {
    const item = items[idx];
    const dayData = loadDayContent(item.date);
    const postText = getPostText(dayData, item.time, item.type);
    const isCarousel = item.type === 'carousel';
    const pdfPath = path.join(BASE, item.pdf_path);

    console.log(`${'─'.repeat(50)}`);
    console.log(`[${idx + 1}/${items.length}] ${item.date} @ ${item.time} | ${item.type.toUpperCase()} | ${item.topic}`);
    console.log(`${'─'.repeat(50)}`);

    if (!postText && !isCarousel) {
      console.log('  SKIP: No post content found');
      failCount++;
      continue;
    }
    if (isCarousel && !fs.existsSync(pdfPath)) {
      console.log(`  SKIP: PDF not found at ${pdfPath}`);
      console.log('  Run: python3 build_all_carousels.py && node build_all_carousels.cjs');
      failCount++;
      continue;
    }

    try {
      // Navigate to feed for clean state
      await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'domcontentloaded', timeout: 15000 });
      await sleep(3000);

      // Remove messaging overlay
      await page.evaluate(() => {
        document.querySelectorAll('.msg-overlay-container, [class*="msg-overlay"], #msg-overlay').forEach(el => el.remove());
      });

      // Click "Start a post"
      console.log('  Clicking "Start a post"...');
      let startBtn = null;
      const btnSelectors = [
        'button.share-box-feed-entry__trigger',
        'button[data-control-name="share_box"]',
        '#main button.share-box-feed-entry__trigger'
      ];
      for (const sel of btnSelectors) {
        try { startBtn = await page.$(sel); if (startBtn) break; } catch {}
      }
      if (!startBtn) {
        const [xpathBtn] = await page.$x('//button[contains(., "Start a post")]');
        startBtn = xpathBtn;
      }
      if (!startBtn) throw new Error('Could not find "Start a post"');
      await startBtn.click();
      await sleep(2000);

      // Wait for editor
      await page.waitForSelector('.ql-editor, [contenteditable="true"]', { timeout: 10000 });
      await sleep(1000);

      // Handle carousel PDF upload
      if (isCarousel) {
        console.log('  Uploading carousel PDF...');

        // Click "Add a document"
        const docSelectors = [
          'button[aria-label="Add a document"]',
          'button[aria-label="Share a document"]',
          'button.share-promoted-detour-button[aria-label="Add a document"]'
        ];
        let docBtn = null;
        for (const sel of docSelectors) {
          try { docBtn = await page.$(sel); if (docBtn) break; } catch {}
        }
        if (!docBtn) {
          const [xpathDoc] = await page.$x('//button[contains(@aria-label, "document")]');
          docBtn = xpathDoc;
        }
        if (!docBtn) {
          // Try "More" menu first
          const moreSelectors = ['button[aria-label="More options"]', 'button[aria-label="More actions"]'];
          for (const sel of moreSelectors) {
            try {
              const mb = await page.$(sel);
              if (mb) { await mb.click(); await sleep(1500); break; }
            } catch {}
          }
          for (const sel of docSelectors) {
            try { docBtn = await page.$(sel); if (docBtn) break; } catch {}
          }
        }
        if (docBtn) {
          await docBtn.click();
          console.log('  Clicked "Add a document"');
        } else {
          console.log('  WARN: Click "Add a document" manually');
        }

        // Wait for file input and upload
        try {
          await page.waitForSelector('input[type="file"]', { timeout: 15000 });
          const fileInput = await page.$('input[type="file"]');
          await fileInput.uploadFile(pdfPath);
          console.log(`  Uploaded: ${path.basename(pdfPath)}`);
        } catch (e) {
          console.log(`  WARN: File upload failed: ${e.message}`);
        }

        // Set document title
        await sleep(2000);
        const titleSelectors = [
          'input[placeholder="Document title"]',
          'input[name="document-title"]',
          'input[aria-label="Document title"]'
        ];
        for (const sel of titleSelectors) {
          try {
            const titleInput = await page.$(sel);
            if (titleInput) {
              const titleText = postText.split('\n')[0].replace(/[^a-zA-Z0-9 ]/g, '').substring(0, 80);
              await titleInput.click();
              await titleInput.type(titleText);
              console.log(`  Title: ${titleText}`);
              break;
            }
          } catch {}
        }

        // Click Done
        await sleep(1000);
        const doneSelectors = [
          'button.share-box-footer__primary-btn',
          'button.share-creation-state__done-btn',
          'button.share-document-preview__done-btn'
        ];
        for (const sel of doneSelectors) {
          try {
            const btn = await page.$(sel);
            if (btn) { await btn.click(); console.log('  Clicked Done'); break; }
          } catch {}
        }
        try {
          const [xpathDone] = await page.$x('//button[contains(., "Done")]');
          if (xpathDone) { await xpathDone.click(); console.log('  Clicked Done (xpath)'); }
        } catch {}
        await sleep(2000);
      }

      // Type caption/content
      console.log('  Typing content...');
      const editor = await page.$('.ql-editor') || await page.$('[contenteditable="true"]');
      if (editor) {
        await editor.focus();
        await page.keyboard.type(postText, { delay: 3 });
        console.log(`  Content: ${postText.substring(0, 60)}...`);
      } else {
        console.log('  WARN: Could not find editor, paste manually');
      }

      await sleep(1000);

      // Post or Schedule
      if (POST_NOW && idx === 0) {
        console.log('  Posting NOW...');
        const postBtn = await page.$('button.share-actions__primary-action') ||
                        await page.$('button[aria-label="Post"]');
        if (postBtn) {
          await postBtn.click();
          console.log('  Posted!');
        }
      } else {
        // Schedule
        console.log(`  Scheduling for ${item.date} at ${item.time}...`);
        const schedIcon = await page.$('button[aria-label="Schedule for later"]') ||
                           await page.$('button.share-actions__schedule-btn');
        if (schedIcon) {
          await schedIcon.click();
          console.log('  Clicked schedule icon');
          await sleep(2000);

          // Set date
          const dateInput = await page.$('input[type="date"], input[name="date"]');
          if (dateInput) {
            await page.evaluate((el, val) => {
              el.value = val;
              el.dispatchEvent(new Event('input', { bubbles: true }));
              el.dispatchEvent(new Event('change', { bubbles: true }));
            }, dateInput, item.date);
            console.log(`  Date: ${item.date}`);
          }

          // Set time
          const timeInput = await page.$('input[type="time"], select[name="time"]');
          if (timeInput) {
            await page.evaluate((el, val) => {
              el.value = val;
              el.dispatchEvent(new Event('input', { bubbles: true }));
              el.dispatchEvent(new Event('change', { bubbles: true }));
            }, timeInput, item.time);
            console.log(`  Time: ${item.time}`);
          }

          await sleep(1000);

          // Click Next
          try {
            const [nextBtn] = await page.$x('//button[contains(., "Next")]');
            if (nextBtn) { await nextBtn.click(); console.log('  Clicked Next'); }
          } catch {}
          await sleep(2000);

          // Click final Schedule button
          const finalBtn = await page.$('button.share-actions__post-btn') ||
                           await page.$('button.share-box_actions__post-btn');
          if (finalBtn) {
            await finalBtn.click();
            console.log('  Scheduled!');
          }
          try {
            const [schedBtn] = await page.$x('//button[contains(., "Schedule")]');
            if (schedBtn) { await schedBtn.click(); console.log('  Scheduled (xpath)'); }
          } catch {}
        } else {
          console.log('  WARN: Click schedule icon manually');
        }
      }

      successCount++;
      console.log('  DONE');

      // Wait between posts
      if (idx < items.length - 1) {
        const waitSec = 8 + Math.floor(Math.random() * 7);
        console.log(`  Waiting ${waitSec}s before next post...`);
        await sleep(waitSec * 1000);
      }

    } catch (err) {
      failCount++;
      console.error(`  ERROR: ${err.message}`);
      console.log('  Skipping to next post...');
      await sleep(3000);
    }
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`  FINISHED: ${successCount} scheduled, ${failCount} failed`);
  console.log(`${'='.repeat(60)}`);
  console.log('\nBrowser stays open for review. Press Ctrl+C to exit.');

  // Keep alive
  await new Promise(() => {});
})();