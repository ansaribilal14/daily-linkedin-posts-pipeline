const { join } = require('path');

/**
 * Puppeteer configuration — use Playwright's bundled Chromium
 * so we don't need a separate Chrome download.
 */
module.exports = {
  cacheDirectory: join(__dirname, '.puppeteer_cache'),
  browserRevision: 'latest',
};