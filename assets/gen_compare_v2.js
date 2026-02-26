const fs = require('fs');

const JADE = '#00C9A7';
const BG = '#0D1117';
const BG2 = '#161B22';
const TEXT = '#E6EDF3';
const TEXT_DIM = '#8B949E';
const RED = '#F85149';
const ORANGE = '#F0883E';
const YELLOW = '#E3B341';
const BLUE = '#58A6FF';
const PURPLE = '#BC8CFF';

const W = 1200, H = 820;

const dims = [
  { label: 'Skill Format', 
    a: 'Python / YAML\nArbitrary code', 
    b: 'Gene Capsules\nLLM-generated strategies', 
    c: 'Pure JSON (non-Turing-complete)\nStructurally safe by design' },
  { label: 'Security Model', 
    a: 'Manual review\nTrust the author', 
    b: 'Crowd ratings + votes\nTrust the community', 
    c: '5-layer mathematical proof\nZero trust, deterministic' },
  { label: 'Knowledge Source', 
    a: 'Static tool definitions\nManual updates', 
    b: 'Agent experience sharing\nLLM mutation & evolution', 
    c: 'Verified skill registry\nBayesian confidence scoring' },
  { label: 'Verification', 
    a: 'None or basic linting\nNo formal guarantee', 
    b: 'Success rate / ratings\nProbabilistic, gameable', 
    c: 'DAG + Schema + Crypto\nMathematical guarantee' },
  { label: 'Privacy & Cost', 
    a: 'Varies\nDepends on platform', 
    b: 'Data sent to cloud\nToken-heavy evolution', 
    c: 'Local-first, zero telemetry\nZero token cost' },
  { label: 'Trust Chain', 
    a: 'None\nFlat trust model', 
    b: 'Platform reputation\nCentralized authority', 
    c: 'Hierarchical CA (Ed25519)\nRoot → Org → Skill signing' },
];

let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
<defs>
  <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0D1117"/><stop offset="100%" stop-color="#161B22"/></linearGradient>
</defs>
<rect width="${W}" height="${H}" fill="url(#bgGrad)" rx="16"/>

<!-- Title -->
<text x="${W/2}" y="50" text-anchor="middle" fill="${JADE}" font-family="DejaVu Sans,sans-serif" font-size="28" font-weight="bold">Agent Skill Platforms Compared</text>
<text x="${W/2}" y="78" text-anchor="middle" fill="${TEXT_DIM}" font-family="DejaVu Sans,sans-serif" font-size="14">How does JadeGate differ from traditional skill libraries and evolution networks?</text>

<!-- Column headers -->
`;

const colX = [130, 400, 680, 960];
const colW = 240;
const headerY = 110;

const headers = [
  { name: '', color: TEXT_DIM },
  { name: 'Traditional\nSkill Libraries', color: TEXT_DIM },
  { name: 'Evolution Networks\n(EvoMap, etc.)', color: ORANGE },
  { name: 'JadeGate', color: JADE },
];

headers.forEach((h, i) => {
  if (i === 0) return;
  const x = colX[i];
  svg += `<rect x="${x - colW/2}" y="${headerY - 25}" width="${colW}" height="50" rx="8" fill="${h.color}" opacity="0.12"/>`;
  const lines = h.name.split('\n');
  lines.forEach((line, li) => {
    svg += `<text x="${x}" y="${headerY + li * 18 - (lines.length > 1 ? 5 : 3)}" text-anchor="middle" fill="${h.color}" font-family="DejaVu Sans,sans-serif" font-size="14" font-weight="bold">${line}</text>`;
  });
});

// Rows
const rowStartY = 185;
const rowH = 95;

dims.forEach((dim, ri) => {
  const y = rowStartY + ri * rowH;
  
  // Alternating row bg
  if (ri % 2 === 0) {
    svg += `<rect x="20" y="${y - 15}" width="${W - 40}" height="${rowH - 5}" rx="8" fill="${TEXT}" opacity="0.02"/>`;
  }
  
  // Dimension label
  svg += `<text x="${colX[0]}" y="${y + 12}" text-anchor="middle" fill="${TEXT}" font-family="DejaVu Sans,sans-serif" font-size="13" font-weight="bold">${dim.label}</text>`;
  
  // Values
  const vals = [dim.a, dim.b, dim.c];
  const colors = [TEXT_DIM, ORANGE, JADE];
  
  vals.forEach((val, ci) => {
    const x = colX[ci + 1];
    const lines = val.split('\n');
    lines.forEach((line, li) => {
      const isSub = li > 0;
      svg += `<text x="${x}" y="${y + li * 18 + (isSub ? 5 : 0)}" text-anchor="middle" fill="${isSub ? TEXT_DIM : colors[ci]}" font-family="DejaVu Sans,sans-serif" font-size="${isSub ? 11 : 13}" ${!isSub && ci === 2 ? 'font-weight="bold"' : ''}>${line}</text>`;
    });
  });
});

// Bottom highlight
const bottomY = rowStartY + dims.length * rowH + 20;
svg += `
<rect x="100" y="${bottomY}" width="${W - 200}" height="45" rx="10" fill="${JADE}" opacity="0.1"/>
<text x="${W/2}" y="${bottomY + 18}" text-anchor="middle" fill="${JADE}" font-family="DejaVu Sans,sans-serif" font-size="14" font-weight="bold">JadeGate: The security layer for MCP Skills</text>
<text x="${W/2}" y="${bottomY + 36}" text-anchor="middle" fill="${TEXT_DIM}" font-family="DejaVu Sans,sans-serif" font-size="12">Works WITH MCP &amp; Skills — validates before execution, not a replacement</text>
`;

svg += `\n</svg>`;

const outDir = '/home/node/.openclaw/workspace/ProjectJADE/assets';
fs.writeFileSync(outDir + '/comparison_v2.svg', svg);
console.log('✅ comparison_v2.svg');

// Convert to PNG via puppeteer
const puppeteer = require('/tmp/node_modules/puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 2 });
  const html = `<!DOCTYPE html><html><head><style>body{margin:0;padding:0;}</style></head><body>${svg}</body></html>`;
  await page.setContent(html, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: outDir + '/comparison_v2.png', omitBackground: true });
  await browser.close();
  const size = (fs.statSync(outDir + '/comparison_v2.png').size / 1024).toFixed(0);
  console.log(`✅ comparison_v2.png (${size} KB)`);
})();
