const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

/**
 * Batch render all carousels from carousel-content-*.json dates.
 * Reads posts/day-*.json to get dates, renders HTML→PNG→PDF for each.
 * 
 * Usage: node build_all_carousels.cjs
 */
const POSTS_DIR = path.join(__dirname, 'posts');
const BASE = __dirname;

(async () => {
  const dayFiles = fs.readdirSync(POSTS_DIR)
    .filter(f => f.startsWith('day-') && f.endsWith('.json'))
    .sort();

  console.log(`Found ${dayFiles.length} day files`);

  // Extract dates
  const dates = dayFiles.map(f => f.replace('day-', '').replace('.json', ''));
  
  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    executablePath: '/home/z/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome'
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1080, deviceScaleFactor: 2 });

  for (const date of dates) {
    const tempDir = path.join(BASE, 'carousel-routine', 'temp', date);
    const outDir = path.join(BASE, 'carousel-routine', 'output', date, 'carousel-branded');
    fs.mkdirSync(outDir, { recursive: true });

    // Check if HTML slides exist for this date
    const slide1 = path.join(tempDir, 'slide-01.html');
    if (!fs.existsSync(slide1)) {
      console.log(`  SKIP ${date}: no HTML slides in ${tempDir}`);
      continue;
    }

    console.log(`\nRendering ${date}...`);

    // Render 7 slides to PNG
    let allOk = true;
    for (let i = 1; i <= 7; i++) {
      const slidePath = `file://${path.join(tempDir, `slide-${String(i).padStart(2,'0')}.html`)}`;
      const pngPath = path.join(outDir, `slide-${String(i).padStart(2,'0')}.png`);
      try {
        await page.goto(slidePath, { waitUntil: 'networkidle0', timeout: 15000 });
        await page.screenshot({ path: pngPath });
      } catch (e) {
        console.log(`    WARN slide ${i}: ${e.message}`);
        allOk = false;
      }
    }

    // Compile PDF
    const pdfHtmlPath = path.join(outDir, 'carousel.html');
    let pdfHtml = '<html><body style="margin:0;padding:0;">';
    for (let i = 1; i <= 7; i++) {
      const p = path.join(outDir, `slide-${String(i).padStart(2,'0')}.png`);
      if (fs.existsSync(p)) {
        pdfHtml += `<img src="file://${p}" style="width:1080px;height:1080px;display:block;page-break-after:always;">`;
      }
    }
    pdfHtml += '</body></html>';
    fs.writeFileSync(pdfHtmlPath, pdfHtml);

    try {
      await page.goto(`file://${pdfHtmlPath}`, { waitUntil: 'networkidle0', timeout: 15000 });
      await page.pdf({
        path: path.join(outDir, `carousel-${date}.pdf`),
        width: 1080,
        height: 1080,
        printBackground: true
      });
      console.log(`  DONE ${date}: 7 PNGs + PDF`);
    } catch (e) {
      console.log(`  WARN ${date} PDF: ${e.message}`);
    }
  }

  await browser.close();
  console.log(`\nAll carousels rendered.`);
})();