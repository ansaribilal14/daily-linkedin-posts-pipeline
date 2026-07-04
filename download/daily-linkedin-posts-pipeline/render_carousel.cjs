const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const BASE = __dirname;
const POSTS_DIR = path.join(BASE, 'posts');
const dateArg = process.argv[2]; // optional: single date like 2026-07-05

(async () => {
  const dayFiles = fs.readdirSync(POSTS_DIR)
    .filter(f => f.startsWith('day-') && f.endsWith('.json'))
    .sort();

  let dates = dayFiles.map(f => f.replace('day-', '').replace('.json', ''));
  if (dateArg) dates = dates.filter(d => d === dateArg);

  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    executablePath: '/home/z/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome'
  });

  for (const date of dates) {
    const tempDir = path.join(BASE, 'carousel-routine', 'temp', date);
    const outDir = path.join(BASE, 'carousel-routine', 'output', date, 'carousel-branded');
    fs.mkdirSync(outDir, { recursive: true });

    const slide1 = path.join(tempDir, 'slide-01.html');
    if (!fs.existsSync(slide1)) {
      console.log(`SKIP ${date}`);
      continue;
    }

    console.log(`${date}...`);
    const page = await browser.newPage();
    await page.setViewport({ width: 1080, height: 1080, deviceScaleFactor: 2 });

    for (let i = 1; i <= 7; i++) {
      const sp = path.join(tempDir, `slide-${String(i).padStart(2,'0')}.html`);
      const pp = path.join(outDir, `slide-${String(i).padStart(2,'0')}.png`);
      try {
        await page.goto(`file://${sp}`, { waitUntil: 'networkidle0', timeout: 20000 });
        await page.screenshot({ path: pp });
      } catch(e) { console.log(`  slide ${i}: ${e.message.substring(0,60)}`); }
    }

    // PDF
    const pdfHtml = path.join(outDir, 'carousel.html');
    let h = '<html><body style="margin:0;padding:0;">';
    for (let i = 1; i <= 7; i++) {
      const p = path.join(outDir, `slide-${String(i).padStart(2,'0')}.png`);
      if (fs.existsSync(p)) h += `<img src="file://${p}" style="width:1080px;height:1080px;display:block;page-break-after:always;">`;
    }
    h += '</body></html>';
    fs.writeFileSync(pdfHtml, h);
    try {
      await page.goto(`file://${pdfHtml}`, { waitUntil: 'networkidle0', timeout: 15000 });
      await page.pdf({ path: path.join(outDir, `carousel-${date}.pdf`), width: 1080, height: 1080, printBackground: true });
    } catch(e) { console.log(`  pdf: ${e.message.substring(0,60)}`); }

    await page.close();
    const slides = fs.readdirSync(outDir).filter(f => f.endsWith('.png')).length;
    console.log(`  DONE ${slides} PNGs + PDF`);
  }

  await browser.close();
  console.log('All done.');
})();