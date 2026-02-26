const fs = require('fs');

const JADE = '#00C9A7';
const TEXT = '#E6EDF3';
const TEXT_DIM = '#8B949E';
const ORANGE = '#F0883E';
const BLUE = '#58A6FF';

const W = 1200, H = 820;

const dims = [
  { label: 'Skill Format', 
    a: 'Python / YAML\nFlexible, expressive', 
    b: 'Gene Capsules\nExperience-driven strategies', 
    c: 'Pure JSON\nDeclarative, non-Turing-complete' },
  { label: 'Security Model', 
    a: 'Author reputation\nCommunity review', 
    b: 'Success rate scoring\nCommunity validation', 
    c: 'Deterministic verification\n5-layer structural proof' },
  { label: 'Knowledge Source', 
    a: 'Static tool definitions\nManual curation', 
    b: 'Agent shared experience\nCross-agent evolution', 
    c: 'Verified skill registry\nBayesian confidence scoring' },
  { label: 'Verification', 
    a: 'Linting + code review\nHuman-dependent', 
    b: 'Usage metrics + ratings\nData-driven', 
    c: 'Schema + DAG + Crypto\nMathematically provable' },
  { label: 'Deployment', 
    a: 'Varies by platform\nOften cloud-hosted', 
    b: 'Cloud network\nGlobal sync', 
    c: 'Local-first\nOffline capable, zero telemetry' },
  { label: 'Trust Chain', 
    a: 'Platform accounts\nFlat trust model', 
    b: 'Platform reputation\nCentralized scoring', 
    c: 'Hierarchical CA (Ed25519)\nRoot → Org → Skill signing' },
];

let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
<defs>
  <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0D1117"/><stop offset="100%" stop-color="#161B22"/></linearGradient>
</defs>
<rect width="${W}" height="${H}" fill="url(#bgGrad)" rx="16"/>

<text x="${W/2}" y="50" text-anchor="middle" fill="${JADE}" font-family="DejaVu Sans,sans-serif" font-size="28" font-weight="bold">Agent Skill Ecosystem — Different Approaches</text>
<text x="${W/2}" y="78" text-anchor="middle" fill="${TEXT_DIM}" font-family="DejaVu Sans,sans-serif" font-size="14">Each approach serves different needs in the AI agent ecosystem</text>
`;

const colX = [130, 400, 680, 960];
const colW = 240;
const headerY = 110;

const headers = [
  { name: '', color: TEXT_DIM },
  { name: 'Traditional\nSkill Libraries', color: BLUE },
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

const rowStartY = 185;
const rowH = 95;

dims.forEach((dim, ri) => {
  const y = rowStartY + ri * rowH;
  if (ri % 2 === 0) {
    svg += `<rect x="20" y="${y - 15}" width="${W - 40}" height="${rowH - 5}" rx="8" fill="${TEXT}" opacity="0.02"/>`;
  }
  svg += `<text x="${colX[0]}" y="${y + 12}" text-anchor="middle" fill="${TEXT}" font-family="DejaVu Sans,sans-serif" font-size="13" font-weight="bold">${dim.label}</text>`;
  
  const vals = [dim.a, dim.b, dim.c];
  const colors = [BLUE, ORANGE, JADE];
  
  vals.forEach((val, ci) => {
    const x = colX[ci + 1];
    const lines = val.split('\n');
    lines.forEach((line, li) => {
      const isSub = li > 0;
      svg += `<text x="${x}" y="${y + li * 18 + (isSub ? 5 : 0)}" text-anchor="middle" fill="${isSub ? TEXT_DIM : colors[ci]}" font-family="DejaVu Sans,sans-serif" font-size="${isSub ? 11 : 13}" ${!isSub && ci === 2 ? 'font-weight="bold"' : ''}>${line}</text>`;
    });
  });
});

const bottomY = rowStartY + dims.length * rowH + 20;
svg += `
<rect x="100" y="${bottomY}" width="${W - 200}" height="45" rx="10" fill="${JADE}" opacity="0.1"/>
<text x="${W/2}" y="${bottomY + 18}" text-anchor="middle" fill="${JADE}" font-family="DejaVu Sans,sans-serif" font-size="14" font-weight="bold">JadeGate focuses on deterministic security for MCP Skills</text>
<text x="${W/2}" y="${bottomY + 36}" text-anchor="middle" fill="${TEXT_DIM}" font-family="DejaVu Sans,sans-serif" font-size="12">Complementary to other approaches — validates skills before execution</text>
`;

svg += `\n</svg>`;

const outDir = '/home/node/.openclaw/workspace/ProjectJADE/assets';
fs.writeFileSync(outDir + '/comparison_v3.svg', svg);
console.log('✅ comparison_v3.svg');

const puppeteer = require('/tmp/node_modules/puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 2 });
  const html = `<!DOCTYPE html><html><head><style>body{margin:0;padding:0;}</style></head><body>${svg}</body></html>`;
  await page.setContent(html, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: outDir + '/comparison_v3.png', omitBackground: true });
  await browser.close();
  const size = (fs.statSync(outDir + '/comparison_v3.png').size / 1024).toFixed(0);
  console.log(`✅ comparison_v3.png (${size} KB)`);
})();
