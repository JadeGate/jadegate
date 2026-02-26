const puppeteer = require('/tmp/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');

const assetsDir = __dirname;
const files = ['pipeline_5layer', 'trust_hierarchy', 'mcp_vs_jadegate'];

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  for (const f of files) {
    const svgPath = path.join(assetsDir, f + '.svg');
    const pngPath = path.join(assetsDir, f + '.png');
    const svgContent = fs.readFileSync(svgPath, 'utf-8');
    
    const wMatch = svgContent.match(/width="(\d+)"/);
    const hMatch = svgContent.match(/height="(\d+)"/);
    const w = wMatch ? parseInt(wMatch[1]) : 1200;
    const h = hMatch ? parseInt(hMatch[1]) : 700;

    const page = await browser.newPage();
    await page.setViewport({ width: w, height: h, deviceScaleFactor: 2 });
    
    const html = `<!DOCTYPE html><html><head><style>body{margin:0;padding:0;background:transparent;}</style></head><body>${svgContent}</body></html>`;
    await page.setContent(html, { waitUntil: 'networkidle0' });
    await page.screenshot({ path: pngPath, omitBackground: true });
    await page.close();
    
    const size = (fs.statSync(pngPath).size / 1024).toFixed(0);
    console.log(`✅ ${f}.png (${size} KB)`);
  }

  await browser.close();
})();
