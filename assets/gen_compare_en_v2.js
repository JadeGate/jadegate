const fs = require('fs');

const JADE = '#00C9A7';
const TEXT = '#E6EDF3';
const TEXT_DIM = '#8B949E';
const ORANGE = '#F0883E';
const BLUE = '#58A6FF';

const W = 1200, H = 880;
const colX = [120, 400, 680, 960];
const colW = 235;
const rowStartY = 170;
const rowH = 90;
const cellH = 72;

const dims = [
  { label: 'Skill Format', 
    a: ['Python / YAML', 'Flexible but can run arbitrary code'], 
    b: ['Gene Capsules', 'LLM-generated experience strategies'], 
    c: ['Pure JSON Declarative', 'Non-Turing-complete — safe by structure'] },
  { label: 'Security', 
    a: ['Author reputation', 'Relies on human review'], 
    b: ['Success rate scoring', 'Community-validated'], 
    c: ['5-layer deterministic proof', 'Mathematical, not probabilistic'] },
  { label: 'Knowledge', 
    a: ['Static tool definitions', 'Manually curated'], 
    b: ['Agent shared experience', 'Cross-agent evolution'], 
    c: ['Verified skill registry', 'Bayesian confidence + time decay'] },
  { label: 'Verification', 
    a: ['Linting + code review', 'Human-driven, no formal proof'], 
    b: ['Usage metrics + ratings', 'Data-driven, iterative'], 
    c: ['Schema + DAG + Ed25519', 'Provable structural safety'] },
  { label: 'Deployment', 
    a: ['Platform-dependent', 'Usually cloud-hosted'], 
    b: ['Cloud evolution network', 'Global sync & sharing'], 
    c: ['Local-first, offline-ready', 'Zero telemetry, zero token cost'] },
  { label: 'Trust Chain', 
    a: ['Platform accounts', 'Flat trust model'], 
    b: ['Platform reputation', 'Centralized scoring'], 
    c: ['Hierarchical CA', 'Root → Org → Skill signing'] },
];

let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
<defs>
  <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0D1117"/><stop offset="100%" stop-color="#161B22"/></linearGradient>
</defs>
<rect width="${W}" height="${H}" fill="url(#bgGrad)" rx="16"/>

<text x="${W/2}" y="48" text-anchor="middle" fill="${JADE}" font-family="DejaVu Sans,sans-serif" font-size="26" font-weight="bold">Agent Skill Ecosystem — Different Paths, Different Safety</text>
<text x="${W/2}" y="76" text-anchor="middle" fill="${TEXT_DIM}" font-family="DejaVu Sans,sans-serif" font-size="13">JadeGate is the only protocol achieving structural safety through non-Turing-complete constraints</text>
`;

const headers = [
  null,
  { name: 'Traditional Skill Libraries', color: BLUE },
  { name: 'Evolution Networks', color: ORANGE },
  { name: 'JadeGate', color: JADE },
];

const headerY = 115;
headers.forEach((h, i) => {
  if (!h) return;
  const x = colX[i];
  svg += `<rect x="${x - colW/2}" y="${headerY - 20}" width="${colW}" height="40" rx="8" fill="${h.color}" opacity="0.15" stroke="${h.color}" stroke-opacity="0.3" stroke-width="1"/>`;
  svg += `<text x="${x}" y="${headerY + 6}" text-anchor="middle" fill="${h.color}" font-family="DejaVu Sans,sans-serif" font-size="14" font-weight="bold">${h.name}</text>`;
});

svg += `<text x="${colX[0]}" y="${headerY + 6}" text-anchor="middle" fill="${TEXT_DIM}" font-family="DejaVu Sans,sans-serif" font-size="12">Dimension</text>`;

dims.forEach((dim, ri) => {
  const y = rowStartY + ri * rowH;
  
  svg += `<rect x="${colX[0] - 55}" y="${y}" width="110" height="${cellH}" rx="8" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>`;
  svg += `<text x="${colX[0]}" y="${y + cellH/2 + 5}" text-anchor="middle" fill="${TEXT}" font-family="DejaVu Sans,sans-serif" font-size="13" font-weight="bold">${dim.label}</text>`;
  
  const vals = [dim.a, dim.b, dim.c];
  const colors = [BLUE, ORANGE, JADE];
  const bgOpacities = ['0.04', '0.04', '0.08'];
  
  vals.forEach((lines, ci) => {
    const x = colX[ci + 1];
    const isJade = ci === 2;
    svg += `<rect x="${x - colW/2}" y="${y}" width="${colW}" height="${cellH}" rx="8" fill="${colors[ci]}" opacity="${bgOpacities[ci]}" stroke="${colors[ci]}" stroke-opacity="${isJade ? '0.25' : '0.1'}" stroke-width="${isJade ? '1.5' : '1'}"/>`;
    
    lines.forEach((line, li) => {
      const ty = y + (li === 0 ? cellH/2 - 6 : cellH/2 + 14);
      const isSub = li > 0;
      svg += `<text x="${x}" y="${ty}" text-anchor="middle" fill="${isSub ? TEXT_DIM : colors[ci]}" font-family="DejaVu Sans,sans-serif" font-size="${isSub ? 11 : 13}" ${!isSub && isJade ? 'font-weight="bold"' : ''}>${line}</text>`;
    });
  });
});

const bottomY = rowStartY + dims.length * rowH + 15;
svg += `
<rect x="80" y="${bottomY}" width="${W - 160}" height="55" rx="12" fill="${JADE}" opacity="0.1" stroke="${JADE}" stroke-opacity="0.2" stroke-width="1"/>
<text x="${W/2}" y="${bottomY + 22}" text-anchor="middle" fill="${JADE}" font-family="DejaVu Sans,sans-serif" font-size="15" font-weight="bold">JadeGate — Deterministic Security Protocol for MCP Skills</text>
<text x="${W/2}" y="${bottomY + 42}" text-anchor="middle" fill="${TEXT_DIM}" font-family="DejaVu Sans,sans-serif" font-size="12">Complementary to other approaches · Validates before execution · Pure JSON can never run malicious code</text>
`;

svg += `\n</svg>`;

const outDir = '/home/node/.openclaw/workspace/ProjectJADE/assets';
fs.writeFileSync(outDir + '/comparison_en.svg', svg);

const puppeteer = require('/tmp/node_modules/puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 2 });
  const html = `<!DOCTYPE html><html><head><style>body{margin:0;padding:0;}</style></head><body>${svg}</body></html>`;
  await page.setContent(html, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: outDir + '/comparison_en.png', omitBackground: true });
  await browser.close();
  const size = (fs.statSync(outDir + '/comparison_en.png').size / 1024).toFixed(0);
  console.log(`✅ comparison_en.png (${size} KB)`);
})();
