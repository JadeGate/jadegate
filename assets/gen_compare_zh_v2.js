const fs = require('fs');

const JADE = '#00C9A7';
const TEXT = '#E6EDF3';
const TEXT_DIM = '#8B949E';
const ORANGE = '#F0883E';
const BLUE = '#58A6FF';
const CELL_BG = 'rgba(255,255,255,0.03)';
const CELL_BORDER = 'rgba(255,255,255,0.06)';

const W = 1200, H = 880;
const colX = [120, 400, 680, 960];
const colW = 235;
const rowStartY = 170;
const rowH = 90;
const cellH = 72;

const dims = [
  { label: '技能格式', 
    a: ['Python / YAML', '灵活但可执行任意代码'], 
    b: ['基因胶囊', '经验驱动的 LLM 策略'], 
    c: ['纯 JSON 声明式', '非图灵完备 — 结构性安全'] },
  { label: '安全模型', 
    a: ['作者信誉 + 社区审查', '依赖人工判断'], 
    b: ['成功率评分', '社区投票验证'], 
    c: ['五层确定性验证', '数学证明，非概率猜测'] },
  { label: '知识来源', 
    a: ['静态工具定义', '人工维护更新'], 
    b: ['Agent 共享经验', '跨 Agent 协同进化'], 
    c: ['已验证技能注册表', '贝叶斯置信度 + 时间衰减'] },
  { label: '验证方式', 
    a: ['Lint + 代码审查', '人工驱动，无形式化保证'], 
    b: ['使用指标 + 评分', '数据驱动，持续迭代'], 
    c: ['Schema + DAG + Ed25519', '可证明的结构化安全'] },
  { label: '部署方式', 
    a: ['因平台而异', '通常需要云端'], 
    b: ['云端进化网络', '全球同步共享'], 
    c: ['本地优先，离线可用', '零遥测，零 Token 消耗'] },
  { label: '信任链', 
    a: ['平台账号体系', '扁平信任模型'], 
    b: ['平台信誉背书', '中心化评分体系'], 
    c: ['层级 CA 架构', 'Root → Org → Skill 签名链'] },
];

let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
<defs>
  <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0D1117"/><stop offset="100%" stop-color="#161B22"/></linearGradient>
</defs>
<rect width="${W}" height="${H}" fill="url(#bgGrad)" rx="16"/>

<text x="${W/2}" y="48" text-anchor="middle" fill="${JADE}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="26" font-weight="bold">Agent 技能生态 — 不同路径，不同安全等级</text>
<text x="${W/2}" y="76" text-anchor="middle" fill="${TEXT_DIM}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="13">JadeGate 是唯一通过非图灵完备约束实现结构性安全的协议</text>
`;

// Column headers
const headers = [
  null,
  { name: '传统技能库', color: BLUE },
  { name: '进化网络 (EvoMap 等)', color: ORANGE },
  { name: 'JadeGate 💠', color: JADE },
];

const headerY = 115;
headers.forEach((h, i) => {
  if (!h) return;
  const x = colX[i];
  svg += `<rect x="${x - colW/2}" y="${headerY - 20}" width="${colW}" height="40" rx="8" fill="${h.color}" opacity="0.15" stroke="${h.color}" stroke-opacity="0.3" stroke-width="1"/>`;
  svg += `<text x="${x}" y="${headerY + 6}" text-anchor="middle" fill="${h.color}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="14" font-weight="bold">${h.name}</text>`;
});

// Dimension label column header
svg += `<text x="${colX[0]}" y="${headerY + 6}" text-anchor="middle" fill="${TEXT_DIM}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="12">维度</text>`;

// Rows
dims.forEach((dim, ri) => {
  const y = rowStartY + ri * rowH;
  
  // Dimension label
  svg += `<rect x="${colX[0] - 55}" y="${y}" width="110" height="${cellH}" rx="8" fill="${CELL_BG}" stroke="${CELL_BORDER}" stroke-width="1"/>`;
  svg += `<text x="${colX[0]}" y="${y + cellH/2 + 5}" text-anchor="middle" fill="${TEXT}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="13" font-weight="bold">${dim.label}</text>`;
  
  // Value cells
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
      svg += `<text x="${x}" y="${ty}" text-anchor="middle" fill="${isSub ? TEXT_DIM : colors[ci]}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="${isSub ? 11 : 13}" ${!isSub && isJade ? 'font-weight="bold"' : ''}>${line}</text>`;
    });
  });
});

// Bottom highlight
const bottomY = rowStartY + dims.length * rowH + 15;
svg += `
<rect x="80" y="${bottomY}" width="${W - 160}" height="55" rx="12" fill="${JADE}" opacity="0.1" stroke="${JADE}" stroke-opacity="0.2" stroke-width="1"/>
<text x="${W/2}" y="${bottomY + 22}" text-anchor="middle" fill="${JADE}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="15" font-weight="bold">JadeGate — MCP Skills 的确定性安全协议</text>
<text x="${W/2}" y="${bottomY + 42}" text-anchor="middle" fill="${TEXT_DIM}" font-family="Noto Sans SC,DejaVu Sans,sans-serif" font-size="12">与其他方案互补 · 验证在执行之前 · 纯 JSON 不可能执行恶意代码</text>
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
