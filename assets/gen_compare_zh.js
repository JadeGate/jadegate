const fs = require('fs');

const JADE = '#00C9A7';
const TEXT = '#E6EDF3';
const TEXT_DIM = '#8B949E';
const ORANGE = '#F0883E';
const BLUE = '#58A6FF';

const W = 1200, H = 820;

const dims = [
  { label: '技能格式', 
    a: 'Python / YAML\n灵活、表达力强', 
    b: '基因胶囊\n经验驱动的策略', 
    c: '纯 JSON\n声明式、非图灵完备' },
  { label: '安全模型', 
    a: '作者信誉\n社区审查', 
    b: '成功率评分\n社区验证', 
    c: '确定性验证\n五层结构化证明' },
  { label: '知识来源', 
    a: '静态工具定义\n人工维护', 
    b: 'Agent 共享经验\n跨 Agent 进化', 
    c: '已验证技能注册表\n贝叶斯置信度评分' },
  { label: '验证方式', 
    a: 'Lint + 代码审查\n依赖人工', 
    b: '使用指标 + 评分\n数据驱动', 
    c: 'Schema + DAG + 密码学\n数学可证明' },
  { label: '部署方式', 
    a: '因平台而异\n通常云托管', 
    b: '云端网络\n全球同步', 
    c: '本地优先\n离线可用、零遥测' },
  { label: '信任链', 
    a: '平台账号\n扁平信任模型', 
    b: '平台信誉\n中心化评分', 
    c: '层级 CA (Ed25519)\nRoot → Org → Skill 签名' },
];

let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
<defs>
  <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0D1117"/><stop offset="100%" stop-color="#161B22"/></linearGradient>
</defs>
<rect width="${W}" height="${H}" fill="url(#bgGrad)" rx="16"/>

<text x="${W/2}" y="50" text-anchor="middle" fill="${JADE}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="28" font-weight="bold">Agent 技能生态 — 不同路径</text>
<text x="${W/2}" y="78" text-anchor="middle" fill="${TEXT_DIM}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="14">每种方案在 AI Agent 生态中服务于不同需求</text>
`;

const colX = [130, 400, 680, 960];
const colW = 240;
const headerY = 110;

const headers = [
  { name: '', color: TEXT_DIM },
  { name: '传统技能库', color: BLUE },
  { name: '进化网络\n(EvoMap 等)', color: ORANGE },
  { name: 'JadeGate', color: JADE },
];

headers.forEach((h, i) => {
  if (i === 0) return;
  const x = colX[i];
  svg += `<rect x="${x - colW/2}" y="${headerY - 25}" width="${colW}" height="50" rx="8" fill="${h.color}" opacity="0.12"/>`;
  const lines = h.name.split('\n');
  lines.forEach((line, li) => {
    svg += `<text x="${x}" y="${headerY + li * 18 - (lines.length > 1 ? 5 : 3)}" text-anchor="middle" fill="${h.color}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="14" font-weight="bold">${line}</text>`;
  });
});

const rowStartY = 185;
const rowH = 95;

dims.forEach((dim, ri) => {
  const y = rowStartY + ri * rowH;
  if (ri % 2 === 0) {
    svg += `<rect x="20" y="${y - 15}" width="${W - 40}" height="${rowH - 5}" rx="8" fill="${TEXT}" opacity="0.02"/>`;
  }
  svg += `<text x="${colX[0]}" y="${y + 12}" text-anchor="middle" fill="${TEXT}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="13" font-weight="bold">${dim.label}</text>`;
  
  const vals = [dim.a, dim.b, dim.c];
  const colors = [BLUE, ORANGE, JADE];
  
  vals.forEach((val, ci) => {
    const x = colX[ci + 1];
    const lines = val.split('\n');
    lines.forEach((line, li) => {
      const isSub = li > 0;
      svg += `<text x="${x}" y="${y + li * 18 + (isSub ? 5 : 0)}" text-anchor="middle" fill="${isSub ? TEXT_DIM : colors[ci]}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="${isSub ? 11 : 13}" ${!isSub && ci === 2 ? 'font-weight="bold"' : ''}>${line}</text>`;
    });
  });
});

const bottomY = rowStartY + dims.length * rowH + 20;
svg += `
<rect x="100" y="${bottomY}" width="${W - 200}" height="45" rx="10" fill="${JADE}" opacity="0.1"/>
<text x="${W/2}" y="${bottomY + 18}" text-anchor="middle" fill="${JADE}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="14" font-weight="bold">JadeGate 专注于 MCP Skills 的确定性安全验证</text>
<text x="${W/2}" y="${bottomY + 36}" text-anchor="middle" fill="${TEXT_DIM}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="12">与其他方案互补 — 在执行前验证技能安全性</text>
`;

svg += `\n</svg>`;

const outDir = '/home/node/.openclaw/workspace/ProjectJADE/assets';
fs.writeFileSync(outDir + '/comparison_zh.svg', svg);
console.log('✅ comparison_zh.svg');

const puppeteer = require('/tmp/node_modules/puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 2 });
  const html = `<!DOCTYPE html><html><head><style>body{margin:0;padding:0;}</style></head><body>${svg}</body></html>`;
  await page.setContent(html, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: outDir + '/comparison_zh.png', omitBackground: true });
  await browser.close();
  const size = (fs.statSync(outDir + '/comparison_zh.png').size / 1024).toFixed(0);
  console.log(`✅ comparison_zh.png (${size} KB)`);
})();
