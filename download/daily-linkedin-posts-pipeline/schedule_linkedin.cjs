const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// ==========================================
// LinkedIn Carousel Scheduler
// Original approach: headed browser, persistent profile, already logged in
// ==========================================

// Config — edit these or pass via CLI
const args = process.argv.slice(2);
let DATE = '';
let TIME = '10:00 AM';
let POST_NOW = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--date' && args[i + 1]) DATE = args[++i];
  if (args[i] === '--time' && args[i + 1]) TIME = args[++i];
  if (args[i] === '--now') POST_NOW = true;
}

if (!DATE) {
  const today = new Date();
  DATE = today.toISOString().split('T')[0];
}

const BASE = __dirname;
const PROFILE_DIR = path.join(BASE, '.puppeteer_profile');
const OUTPUT_DIR = path.join(BASE, 'carousel-routine', 'output', DATE, 'carousel-branded');
const PDF_PATH = path.join(OUTPUT_DIR, `carousel-${DATE}.pdf`);
const CAPTION_PATH = path.join(BASE, 'carousel_caption.txt');

// Verify files
if (!fs.existsSync(PDF_PATH)) {
  console.error(`❌ Carousel PDF not found: ${PDF_PATH}`);
  console.error('   Generate it first with: python3 build_carousel.py && node carousel-routine/render_sample.cjs');
  process.exit(1);
}

const caption = fs.existsSync(CAPTION_PATH) ? fs.readFileSync(CAPTION_PATH, 'utf-8').trim() : '';
console.log(`📅 Date: ${DATE}`);
console.log(`📄 PDF: ${path.basename(PDF_PATH)} (${(fs.statSync(PDF_PATH).size / 1024 / 1024).toFixed(1)}MB)`);
console.log(`📝 Caption: ${caption.substring(0, 60)}...`);

(async () => {
  console.log('\n🚀 Starting LinkedIn Post Scheduler...\n');

  // Launch with persistent profile — reuses your LinkedIn login
  const browser = await puppeteer.launch({
    headless: false,
    userDataDir: PROFILE_DIR,
    defaultViewport: null,
    args: ['--start-maximized'],
    protocolTimeout: 1800000 // 30 minutes
  });

  const pages = await browser.pages();
  const page = pages.length > 0 ? pages[0] : await browser.newPage();

  console.log('📬 Navigating to LinkedIn feed...');
  await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'domcontentloaded' });

  // 1. Wait for login verification (or let user log in manually)
  console.log('🔒 Verifying login session...');
  try {
    await page.waitForSelector('.feed-identity-module, .global-nav, .share-box-feed-entry__trigger', { timeout: 10000 });
    console.log('✅ Logged in successfully!');
  } catch (e) {
    console.log('⚠️  No active session. Please log in manually in the browser window...');
    await page.waitForSelector('.feed-identity-module, .global-nav, .share-box-feed-entry__trigger', { timeout: 0 });
    console.log('✅ Logged in successfully!');
  }

  // Remove messaging overlay if it blocks clicks
  await page.evaluate(() => {
    document.querySelectorAll('.msg-overlay-container, [class*="msg-overlay"], #msg-overlay').forEach(el => el.remove());
  });

  // 2. Click "Start a post"
  console.log('📝 Locating "Start a post" button...');
  const startPostSelectors = [
    'button.share-box-feed-entry__trigger',
    'button[data-control-name="share_box"]',
    '#main button.share-box-feed-entry__trigger',
    '//button[contains(., "Start a post")]'
  ];

  let startPostBtn = null;
  for (const selector of startPostSelectors) {
    try {
      if (selector.startsWith('//')) {
        const [el] = await page.$x(selector);
        if (el) { startPostBtn = el; break; }
      } else {
        startPostBtn = await page.waitForSelector(selector, { timeout: 2000 });
        if (startPostBtn) break;
      }
    } catch (err) {}
  }

  if (!startPostBtn) {
    console.log('❌ Could not find "Start a post" button. Please click it manually...');
    await page.waitForSelector('.share-box-composer, .share-creation-state', { timeout: 60000 });
  } else {
    await startPostBtn.click();
    console.log('✅ Clicked "Start a post".');
  }

  // Wait for post composer modal
  await page.waitForSelector('.share-box-composer, .share-creation-state, [role="dialog"]', { timeout: 10000 });
  console.log('✅ Post composer opened.');

  // 3. Click "Add a document"
  console.log('📁 Looking for "Add a document" button...');
  const docButtonSelectors = [
    'button[aria-label="Add a document"]',
    'button[aria-label="Share a document"]',
    'button.share-promoted-detour-button[aria-label="Add a document"]',
    '//button[contains(@aria-label, "document")]'
  ];

  let docBtn = null;
  for (const selector of docButtonSelectors) {
    try {
      if (selector.startsWith('//')) {
        const [el] = await page.$x(selector);
        if (el) { docBtn = el; break; }
      } else {
        docBtn = await page.waitForSelector(selector, { timeout: 2000 });
        if (docBtn) break;
      }
    } catch (err) {}
  }

  if (!docBtn) {
    console.log('🔍 Document button not direct, checking "More" actions...');
    const moreBtnSelectors = [
      'button[aria-label="More options"]',
      'button[aria-label="Show more Actions"]',
      'button[aria-label="More actions"]'
    ];
    for (const moreSel of moreBtnSelectors) {
      try {
        const moreBtn = await page.$(moreSel);
        if (moreBtn) {
          await moreBtn.click();
          console.log('✅ Clicked "More actions".');
          await new Promise(r => setTimeout(r, 1000));
          break;
        }
      } catch (err) {}
    }
    for (const selector of docButtonSelectors) {
      try {
        if (selector.startsWith('//')) {
          const [el] = await page.$x(selector);
          if (el) { docBtn = el; break; }
        } else {
          docBtn = await page.$(selector);
          if (docBtn) break;
        }
      } catch (err) {}
    }
  }

  if (docBtn) {
    await docBtn.click();
    console.log('✅ Clicked "Add a document".');
  } else {
    console.log('⚠️  Could not click Document button. Please click it manually.');
  }

  // 4. Upload PDF
  console.log('📤 Waiting for file input...');
  await page.waitForSelector('input[type="file"]', { timeout: 30000 });
  const fileInput = await page.$('input[type="file"]');
  console.log(`📄 Uploading: ${PDF_PATH}`);
  await fileInput.uploadFile(PDF_PATH);

  // 5. Document title
  console.log('✍️ Setting document title...');
  const titleSelectors = [
    'input[placeholder="Document title"]',
    'input[name="document-title"]',
    'input[aria-label="Document title"]',
    'input[type="text"]'
  ];
  let titleInput = null;
  for (const sel of titleSelectors) {
    try {
      titleInput = await page.waitForSelector(sel, { timeout: 5000 });
      if (titleInput) break;
    } catch (err) {}
  }

  if (titleInput) {
    const titleText = caption.split('\n')[0].replace(/[^a-zA-Z0-9 ]/g, '').substring(0, 80);
    await titleInput.type(titleText);
    console.log(`✅ Title: ${titleText}`);
  } else {
    console.log('⚠️  Could not find title input. Type it manually.');
  }

  // Click "Done" on document preview
  console.log('💾 Clicking Done on document preview...');
  const doneSelectors = [
    'button.share-box-footer__primary-btn',
    'button.share-creation-state__done-btn',
    'button.share-document-preview__done-btn',
    '//button[span[text()="Done"]]',
    '//button[contains(., "Done")]'
  ];
  let doneBtn = null;
  for (const selector of doneSelectors) {
    try {
      if (selector.startsWith('//')) {
        const [el] = await page.$x(selector);
        if (el) { doneBtn = el; break; }
      } else {
        doneBtn = await page.waitForSelector(selector, { timeout: 3000 });
        if (doneBtn) break;
      }
    } catch (err) {}
  }

  if (doneBtn) {
    await doneBtn.click();
    console.log('✅ Clicked Done.');
  } else {
    console.log('⚠️  Click "Done" manually.');
  }

  await new Promise(r => setTimeout(r, 2000));

  // 6. Type caption
  console.log('📝 Typing caption...');
  const editorSelectors = ['.ql-editor', 'div[contenteditable="true"]', '.share-editor__editor'];
  let editor = null;
  for (const sel of editorSelectors) {
    try {
      editor = await page.waitForSelector(sel, { timeout: 5000 });
      if (editor) break;
    } catch (err) {}
  }

  if (editor) {
    await editor.focus();
    await page.keyboard.type(caption, { delay: 5 });
    console.log('✅ Caption entered.');
  } else {
    console.log('⚠️  Could not find editor. Paste caption manually.');
  }

  // 7. Post or Schedule
  if (POST_NOW) {
    console.log('🚀 Posting now...');
    const postBtnSelectors = [
      'button.share-actions__primary-action',
      'button.share-box_actions__post-btn',
      'button[aria-label="Post"]',
      '//button[contains(., "Post")]'
    ];
    let postBtn = null;
    for (const selector of postBtnSelectors) {
      try {
        if (selector.startsWith('//')) {
          const [el] = await page.$x(selector);
          if (el) { postBtn = el; break; }
        } else {
          postBtn = await page.waitForSelector(selector, { timeout: 3000 });
          if (postBtn) break;
        }
      } catch (err) {}
    }
    if (postBtn) {
      await postBtn.click();
      console.log('✅ Post submitted!');
    } else {
      console.log('⚠️  Click "Post" manually.');
    }
  } else {
    // Schedule
    console.log(`⏰ Scheduling for ${DATE} at ${TIME}...`);
    const scheduleIconSelectors = [
      'button[aria-label="Schedule for later"]',
      'button.share-actions__schedule-btn',
      'button[data-control-name="schedule_post"]',
      '//button[contains(@aria-label, "Schedule")]'
    ];
    let scheduleIcon = null;
    for (const selector of scheduleIconSelectors) {
      try {
        if (selector.startsWith('//')) {
          const [el] = await page.$x(selector);
          if (el) { scheduleIcon = el; break; }
        } else {
          scheduleIcon = await page.waitForSelector(selector, { timeout: 5000 });
          if (scheduleIcon) break;
        }
      } catch (err) {}
    }

    if (scheduleIcon) {
      await scheduleIcon.click();
      console.log('✅ Clicked Schedule icon.');
    } else {
      console.log('⚠️  Click the schedule clock icon manually.');
    }

    // Set date/time
    const dateInputSelector = 'input[type="date"], input[name="date"], .schedule-modal__date-input';
    const timeInputSelector = 'input[type="time"], input[name="time"], select[name="time"], .schedule-modal__time-select';

    try {
      await page.waitForSelector(dateInputSelector, { timeout: 10000 });

      // Convert DATE format for the date input
      await page.evaluate((sel, dateVal) => {
        const el = document.querySelector(sel);
        if (el) {
          el.value = dateVal;
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }, dateInputSelector, DATE);
      console.log(`✅ Date set to ${DATE}.`);

      await page.waitForSelector(timeInputSelector, { timeout: 5000 });
      await page.evaluate((sel, timeVal) => {
        const el = document.querySelector(sel);
        if (el) {
          el.value = timeVal;
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }, timeInputSelector, TIME.replace(' AM', '').replace(' PM', ''));
      console.log(`✅ Time set to ${TIME}.`);

      // Click Next
      const nextSelectors = [
        'button.schedule-modal__next-btn',
        'button.share-schedule-modal__next-btn',
        '//button[span[text()="Next"]]',
        '//button[contains(., "Next")]'
      ];
      let nextBtn = null;
      for (const selector of nextSelectors) {
        try {
          if (selector.startsWith('//')) {
            const [el] = await page.$x(selector);
            if (el) { nextBtn = el; break; }
          } else {
            nextBtn = await page.waitForSelector(selector, { timeout: 3000 });
            if (nextBtn) break;
          }
        } catch (err) {}
      }
      if (nextBtn) {
        await nextBtn.click();
        console.log('✅ Clicked Next.');
      }

      await new Promise(r => setTimeout(r, 2000));

      // Click final Schedule button
      const schedulePostSelectors = [
        'button.share-actions__post-btn',
        'button.share-box_actions__post-btn',
        '//button[contains(., "Schedule")]'
      ];
      let finalBtn = null;
      for (const selector of schedulePostSelectors) {
        try {
          if (selector.startsWith('//')) {
            const [el] = await page.$x(selector);
            if (el) { finalBtn = el; break; }
          } else {
            finalBtn = await page.waitForSelector(selector, { timeout: 3000 });
            if (finalBtn) break;
          }
        } catch (err) {}
      }

      if (finalBtn) {
        await finalBtn.click();
        console.log('✅ Post scheduled!');
      } else {
        console.log('⚠️  Click "Schedule" manually.');
      }
    } catch (err) {
      console.log('⚠️  Could not set date/time automatically. Complete it manually in the browser.');
      console.error(err.message);
    }
  }

  console.log('\n📢 Done! Browser stays open for review.');
})();