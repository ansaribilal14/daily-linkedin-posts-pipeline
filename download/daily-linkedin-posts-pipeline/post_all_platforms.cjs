#!/usr/bin/env node
/**
 * post_all_platforms.cjs
 * Posts to Instagram, Facebook, Threads, and Twitter/X from cross-platform-schedule.json
 *
 * Uses headed Puppeteer with persistent profiles per platform.
 * Log in once per platform, then it reuses the session.
 *
 * Usage:
 *   node post_all_platforms.cjs                    # all platforms, all days
 *   node post_all_platforms.cjs --platform threads  # only Threads
 *   node post_all_platforms.cjs --platform instagram --date 2026-07-08
 *   node post_all_platforms.cjs --date 2026-07-08   # single day all platforms
 *   node post_all_platforms.cjs --today             # today's posts only
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const BASE = __dirname;
const SCHEDULE = JSON.parse(fs.readFileSync(path.join(BASE, 'cross-platform-schedule.json'), 'utf-8'));

// CLI args
const args = process.argv.slice(2);
let FILTER_PLATFORM = null, FILTER_DATE = null, TODAY_ONLY = false;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--platform' && args[i+1]) FILTER_PLATFORM = args[++i];
  if (args[i] === '--date' && args[i+1]) FILTER_DATE = args[++i];
  if (args[i] === '--today') TODAY_ONLY = true;
}

let items = SCHEDULE;
if (FILTER_PLATFORM) items = items.filter(i => i.platform === FILTER_PLATFORM);
if (FILTER_DATE) items = items.filter(i => i.date === FILTER_DATE);
if (TODAY_ONLY) {
  const today = new Date().toISOString().split('T')[0];
  items = items.filter(i => i.date === today);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// Platform config
const PLATFORMS = {
  threads: {
    name: 'Threads',
    url: 'https://www.threads.net/',
    profile: path.join(BASE, '.puppeteer_threads'),
    postUrl: 'https://www.threads.net/',
    typeText: async (page, text) => {
      // Threads uses a simple text area
      const editor = await page.waitForSelector('[role="textbox"], [contenteditable="true"], textarea', { timeout: 10000 });
      await editor.focus();
      await page.keyboard.type(text, { delay: 2 });
    },
    submitPost: async (page) => {
      // Click the Post button
      const btn = await page.$('button[aria-label="Post"], button[data-testid="postButton"]');
      if (btn) await btn.click();
      else {
        const [xp] = await page.$x('//button[contains(., "Post")]');
        if (xp) await xp.click();
      }
    }
  },
  twitter: {
    name: 'Twitter/X',
    url: 'https://x.com/compose/post',
    profile: path.join(BASE, '.puppeteer_twitter'),
    typeText: async (page, text) => {
      const editor = await page.waitForSelector('[data-testid="tweetTextarea_0"], [role="textbox"]', { timeout: 10000 });
      await editor.focus();
      await page.keyboard.type(text, { delay: 2 });
    },
    submitPost: async (page) => {
      const btn = await page.$('[data-testid="tweetButton"]');
      if (btn) await btn.click();
    }
  },
  instagram: {
    name: 'Instagram',
    url: 'https://www.instagram.com/',
    profile: path.join(BASE, '.puppeteer_instagram'),
    typeText: async (page, text) => {
      const caption = await page.waitForSelector('textarea[aria-label="Write a caption..."], [aria-label="Write a caption..."]', { timeout: 10000 });
      await caption.focus();
      await page.keyboard.type(text, { delay: 2 });
    },
    submitPost: async (page) => {
      const btn = await page.$('button[aria-label="Share"]');
      if (btn) await btn.click();
      else {
        const [xp] = await page.$x('//button[contains(., "Share")]');
        if (xp) await xp.click();
      }
    },
    uploadImages: async (page, imagePaths) => {
      // Click "Create" button
      const createBtn = await page.$('svg[aria-label="New post"], a[href="/create/"]');
      if (createBtn) await createBtn.click();
      else {
        await page.goto('https://www.instagram.com/create/', { waitUntil: 'domcontentloaded' });
      }
      await sleep(2000);

      // Upload images via file input
      const fileInput = await page.$('input[type="file"]');
      if (fileInput) {
        await fileInput.uploadFile(...imagePaths);
        await sleep(5000); // Wait for upload + processing
      }

      // Click "Next" to proceed from selection
      try {
        const [nextBtn] = await page.$x('//div[@role="dialog"]//button[contains(., "Next")]');
        if (nextBtn) await nextBtn.click();
      } catch {}
      await sleep(2000);
    }
  },
  facebook: {
    name: 'Facebook',
    url: 'https://www.facebook.com/',
    profile: path.join(BASE, '.puppeteer_facebook'),
    typeText: async (page, text) => {
      const editor = await page.$('[contenteditable="true"][role="textbox"], .ql-editor, [aria-label="Create a post"]');
      if (editor) {
        await editor.focus();
        await page.keyboard.type(text, { delay: 2 });
      }
    },
    submitPost: async (page) => {
      const btn = await page.$('button[aria-label="Post"], [aria-label="Publish"]');
      if (btn) await btn.click();
      else {
        const [xp] = await page.$x('//button[contains(., "Post")]');
        if (xp) await xp.click();
      }
    },
    uploadImages: async (page, imagePaths) => {
      // Click Photo/Video
      const photoBtn = await page.$('svg[aria-label="Photo"], label[aria-label="Photo"]');
      if (photoBtn) await photoBtn.click();
      await sleep(1500);

      const fileInput = await page.$('input[type="file"]');
      if (fileInput) {
        await fileInput.uploadFile(...imagePaths);
        await sleep(4000);
      }
    }
  }
};

(async () => {
  console.log(`\n${'='.repeat(55)}`);
  console.log(`  FOUNDERS WING — Multi-Platform Poster`);
  console.log(`  ${items.length} posts queued`);
  const platforms = [...new Set(items.map(i => i.platform))];
  console.log(`  Platforms: ${platforms.join(', ')}`);
  console.log(`  Dates: ${items[0]?.date} to ${items[items.length-1]?.date}`);
  console.log(`${'='.repeat(55)}\n`);

  // Group items by platform for session reuse
  const byPlatform = {};
  for (const item of items) {
    if (!byPlatform[item.platform]) byPlatform[item.platform] = [];
    byPlatform[item.platform].push(item);
  }

  let totalOk = 0, totalFail = 0;

  for (const [platformKey, platformItems] of Object.entries(byPlatform)) {
    const config = PLATFORMS[platformKey];
    if (!config) {
      console.log(`SKIP: Unknown platform ${platformKey}`);
      totalFail += platformItems.length;
      continue;
    }

    console.log(`\n${'#'.repeat(55)}`);
    console.log(`  ${config.name.toUpperCase()} — ${platformItems.length} posts`);
    console.log(`${'#'.repeat(55)}\n`);

    // Launch browser for this platform
    const browser = await puppeteer.launch({
      headless: false,
      userDataDir: config.profile,
      defaultViewport: null,
      args: ['--start-maximized'],
      protocolTimeout: 1800000
    });

    const pages = await browser.pages();
    const page = pages[0] || await browser.newPage();

    // Navigate to platform
    console.log(`Opening ${config.name}...`);
    await page.goto(config.url, { waitUntil: 'domcontentloaded' });
    await sleep(3000);

    // Wait for user to log in if needed
    console.log(`If not logged in, please log in to ${config.name} now...`);
    await sleep(5000); // Give user time to see if login is needed

    let platOk = 0, platFail = 0;

    for (let idx = 0; idx < platformItems.length; idx++) {
      const item = platformItems[idx];
      console.log(`\n[${idx+1}/${platformItems.length}] ${item.date} ${item.time} | ${item.type} | ${item.topic?.substring(0, 40)}`);

      try {
        // Navigate to compose/create
        if (platformKey === 'twitter') {
          await page.goto('https://x.com/compose/post', { waitUntil: 'domcontentloaded' });
        } else if (platformKey === 'instagram' || platformKey === 'facebook') {
          await page.goto(config.url, { waitUntil: 'domcontentloaded' });
        }
        await sleep(2000);

        // Upload images if carousel
        if ((item.type === 'carousel' || item.type === 'image') && item.images?.length > 0 && config.uploadImages) {
          const absImages = item.images.map(p => path.resolve(BASE, p));
          const existing = absImages.filter(p => fs.existsSync(p));
          if (existing.length > 0) {
            console.log(`  Uploading ${existing.length} images...`);
            await config.uploadImages(page, existing);
          } else {
            console.log(`  WARN: No image files found`);
          }
        }

        // Handle Twitter threads
        if (platformKey === 'twitter' && item.type === 'thread' && Array.isArray(item.content)) {
          for (let t = 0; t < item.content.length; t++) {
            if (t === 0) {
              await config.typeText(page, item.content[t]);
            } else {
              // Add to thread
              const addBtn = await page.$('[data-testid="tweetButtonInline"]');
              if (addBtn) await addBtn.click();
              await sleep(2000);
              await config.typeText(page, item.content[t]);
            }
          }
        } else if (typeof item.content === 'string') {
          await config.typeText(page, item.content);
        }

        await sleep(1000);

        // Submit
        console.log('  Posting...');
        await config.submitPost(page);
        console.log('  DONE');

        platOk++;
        totalOk++;

        // Wait between posts
        if (idx < platformItems.length - 1) {
          const w = 10 + Math.floor(Math.random() * 10);
          console.log(`  Waiting ${w}s...`);
          await sleep(w * 1000);
        }
      } catch (err) {
        platFail++;
        totalFail++;
        console.error(`  ERROR: ${err.message}`);
        await sleep(3000);
      }
    }

    console.log(`\n  ${config.name}: ${platOk} posted, ${platFail} failed`);
    console.log(`  Browser stays open. Close it when ready.\n`);

    // Don't close browser so user can review/fix
  }

  console.log(`\n${'='.repeat(55)}`);
  console.log(`  TOTAL: ${totalOk} posted, ${totalFail} failed across ${platforms.length} platforms`);
  console.log(`${'='.repeat(55)}\n`);

  await new Promise(() => {});
})();