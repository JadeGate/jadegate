const fs = require('fs');
const path = require('path');

const JADE = '#00C9A7';
const JADE_DARK = '#00A88A';
const JADE_LIGHT = '#E0FFF8';
const BG = '#0D1117';
const BG2 = '#161B22';
const TEXT = '#E6EDF3';
const TEXT_DIM = '#8B949E';
const RED = '#F85149';
const ORANGE = '#F0883E';
const YELLOW = '#E3B341';
const BLUE = '#58A6FF';
const PURPLE = '#BC8CFF';

// ============ Diagram 1: 5-Layer Validation Pipeline ============
function diagram1_pipeline() {
  const W = 1200, H = 700;
  const layers = [
    { name: 'Schema\nValidation', icon: '💠', desc: 'JSON Schema v1\nStructure Check', color: BLUE },
    { name: 'DAG\nValidation', icon: '🔗', desc: 'Acyclic Graph\nNo Loops', color: JADE },
    { name: 'Security\nAudit', icon: '🔏', desc: '5-Layer Policy\nZero Trust', color: PURPLE },
    { name: 'Confidence\nScoring', icon: '🧊', desc: 'Bayesian Score\nTime Decay', color: YELLOW },
    { name: 'Runtime\nGuard', icon: '🛡️', desc: 'Sandbox Exec\nAction Whitelist', color: ORANGE },
  ];

  const boxW = 160, boxH = 200, gap = 40;
  const totalW = layers.length * boxW + (layers.length - 1) * gap;
  const startX = (W - totalW) / 2;
  const startY = 220;

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
  <defs>
    <filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0D1117"/><stop offset="100%" stop-color="#161B22"/></linearGradient>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#bgGrad)" rx="16"/>
  
  <!-- Title -->
  <text x="${W/2}" y="60" text-anchor="middle" fill="${JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="32" font-weight="bold">💠 JadeGate Validation Pipeline</text>
  <text x="${W/2}" y="95" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="16">5-Layer Deterministic Security — Every Skill Must Pass All Layers</text>
  
  <!-- Input arrow -->
  <text x="${startX - 60}" y="${startY + boxH/2 + 5}" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="14">Skill</text>
  <text x="${startX - 60}" y="${startY + boxH/2 + 22}" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="14">JSON</text>
  <line x1="${startX - 30}" y1="${startY + boxH/2}" x2="${startX - 5}" y2="${startY + boxH/2}" stroke="${TEXT_DIM}" stroke-width="2" marker-end="url(#arrowDim)"/>
  
  <defs><marker id="arrowDim" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="${TEXT_DIM}"/></marker></defs>
  <defs><marker id="arrowJade" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="${JADE}"/></marker></defs>`;

  layers.forEach((layer, i) => {
    const x = startX + i * (boxW + gap);
    const y = startY;
    
    // Box
    svg += `
  <rect x="${x}" y="${y}" width="${boxW}" height="${boxH}" rx="12" fill="${BG}" stroke="${layer.color}" stroke-width="2" opacity="0.9"/>
  <rect x="${x}" y="${y}" width="${boxW}" height="40" rx="12" fill="${layer.color}" opacity="0.15"/>
  <rect x="${x}" y="${y + 28}" width="${boxW}" height="12" fill="${BG}" opacity="0.9"/>`;
    
    // Layer number
    svg += `<text x="${x + boxW/2}" y="${y - 12}" text-anchor="middle" fill="${layer.color}" font-family="Segoe UI,Arial,sans-serif" font-size="13" font-weight="bold">Layer ${i+1}</text>`;
    
    // Icon
    svg += `<text x="${x + boxW/2}" y="${y + 75}" text-anchor="middle" font-size="36">${layer.icon}</text>`;
    
    // Name
    const nameLines = layer.name.split('\n');
    nameLines.forEach((line, li) => {
      svg += `<text x="${x + boxW/2}" y="${y + 110 + li * 20}" text-anchor="middle" fill="${TEXT}" font-family="Segoe UI,Arial,sans-serif" font-size="15" font-weight="bold">${line}</text>`;
    });
    
    // Desc
    const descLines = layer.desc.split('\n');
    descLines.forEach((line, li) => {
      svg += `<text x="${x + boxW/2}" y="${y + 160 + li * 16}" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="12">${line}</text>`;
    });
    
    // Arrow between boxes
    if (i < layers.length - 1) {
      const ax = x + boxW + 5;
      const ay = y + boxH / 2;
      svg += `<line x1="${ax}" y1="${ay}" x2="${ax + gap - 10}" y2="${ay}" stroke="${JADE}" stroke-width="2" marker-end="url(#arrowJade)"/>`;
      svg += `<text x="${ax + gap/2}" y="${ay - 8}" text-anchor="middle" fill="${JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="10">PASS</text>`;
    }
  });

  // Output
  const outX = startX + totalW + 15;
  svg += `
  <text x="${outX + 30}" y="${startY + boxH/2 - 10}" text-anchor="middle" fill="${JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="bold">✅ Trusted</text>
  <text x="${outX + 30}" y="${startY + boxH/2 + 10}" text-anchor="middle" fill="${JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="bold">Skill</text>`;

  // Fail arrows
  svg += `
  <text x="${W/2}" y="${startY + boxH + 60}" text-anchor="middle" fill="${RED}" font-family="Segoe UI,Arial,sans-serif" font-size="14">❌ Any layer fails → Skill REJECTED (fail-fast, no partial trust)</text>`;

  // Footer
  svg += `
  <text x="${W/2}" y="${H - 25}" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="12">Non-Turing-Complete · Zero Token Execution · Security as Structural Property</text>`;

  svg += `\n</svg>`;
  return svg;
}

// ============ Diagram 2: Trust Hierarchy ============
function diagram2_trust() {
  const W = 1000, H = 750;
  
  const levels = [
    { name: 'Root Trust', emoji: '🔐', desc: 'JadeGate Core Team', color: '#FFD700', y: 100, w: 200 },
    { name: 'Organization', emoji: '🏢', desc: 'Verified Publishers', color: JADE, y: 270, items: ['Anthropic', 'OpenAI', 'Google'] },
    { name: 'Community', emoji: '👥', desc: 'Open Contributions', color: BLUE, y: 440, items: ['Developer A', 'Developer B', 'Developer C', 'Developer D'] },
    { name: 'Untrusted', emoji: '⚠️', desc: 'Unverified / New', color: RED, y: 610, items: ['Unknown'] },
  ];

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
  <defs>
    <linearGradient id="bgGrad2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0D1117"/><stop offset="100%" stop-color="#161B22"/></linearGradient>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#bgGrad2)" rx="16"/>
  <text x="${W/2}" y="50" text-anchor="middle" fill="${JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="28" font-weight="bold">🔏 JadeGate Trust Hierarchy</text>
  <text x="${W/2}" y="78" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="14">Bayesian Confidence with Time Decay — Trust is Earned, Not Assumed</text>`;

  // Root
  svg += `
  <rect x="${W/2 - 120}" y="100" width="240" height="70" rx="12" fill="${BG}" stroke="#FFD700" stroke-width="2.5"/>
  <text x="${W/2}" y="130" text-anchor="middle" font-size="20">🔐</text>
  <text x="${W/2}" y="152" text-anchor="middle" fill="#FFD700" font-family="Segoe UI,Arial,sans-serif" font-size="15" font-weight="bold">Root Trust — Core Team</text>
  <text x="${W/2 + 145}" y="140" text-anchor="start" fill="#FFD700" font-family="Segoe UI,Arial,sans-serif" font-size="12">Score: 0.95-1.0</text>`;

  // Org level
  const orgItems = ['Anthropic', 'OpenAI', 'Google'];
  const orgW = 160, orgGap = 40;
  const orgTotalW = orgItems.length * orgW + (orgItems.length - 1) * orgGap;
  const orgStartX = (W - orgTotalW) / 2;
  
  orgItems.forEach((item, i) => {
    const x = orgStartX + i * (orgW + orgGap);
    svg += `
  <rect x="${x}" y="270" width="${orgW}" height="60" rx="10" fill="${BG}" stroke="${JADE}" stroke-width="2"/>
  <text x="${x + orgW/2}" y="295" text-anchor="middle" fill="${JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="bold">🏢 ${item}</text>
  <text x="${x + orgW/2}" y="315" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="11">Verified Publisher</text>`;
    // Line from root
    svg += `<line x1="${W/2}" y1="170" x2="${x + orgW/2}" y2="270" stroke="${JADE}" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.6"/>`;
  });
  svg += `<text x="${W - 80}" y="305" text-anchor="middle" fill="${JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="12">Score: 0.7-0.95</text>`;

  // Community level
  const comItems = ['Dev Alpha', 'Dev Beta', 'Dev Gamma', 'Dev Delta'];
  const comW = 140, comGap = 30;
  const comTotalW = comItems.length * comW + (comItems.length - 1) * comGap;
  const comStartX = (W - comTotalW) / 2;
  
  comItems.forEach((item, i) => {
    const x = comStartX + i * (comW + comGap);
    svg += `
  <rect x="${x}" y="440" width="${comW}" height="55" rx="10" fill="${BG}" stroke="${BLUE}" stroke-width="1.5"/>
  <text x="${x + comW/2}" y="463" text-anchor="middle" fill="${BLUE}" font-family="Segoe UI,Arial,sans-serif" font-size="13">👤 ${item}</text>
  <text x="${x + comW/2}" y="481" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="10">Community</text>`;
    // Lines from org
    const orgIdx = Math.min(i, orgItems.length - 1);
    const orgX = orgStartX + Math.floor(i * orgItems.length / comItems.length) * (orgW + orgGap) + orgW/2;
    svg += `<line x1="${orgX}" y1="330" x2="${x + comW/2}" y2="440" stroke="${BLUE}" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>`;
  });
  svg += `<text x="${W - 80}" y="472" text-anchor="middle" fill="${BLUE}" font-family="Segoe UI,Arial,sans-serif" font-size="12">Score: 0.3-0.7</text>`;

  // Untrusted
  svg += `
  <rect x="${W/2 - 100}" y="590" width="200" height="55" rx="10" fill="${BG}" stroke="${RED}" stroke-width="1.5" stroke-dasharray="6,3"/>
  <text x="${W/2}" y="615" text-anchor="middle" fill="${RED}" font-family="Segoe UI,Arial,sans-serif" font-size="14">⚠️ Untrusted / New</text>
  <text x="${W/2}" y="633" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="11">Requires manual review</text>
  <text x="${W - 80}" y="620" text-anchor="middle" fill="${RED}" font-family="Segoe UI,Arial,sans-serif" font-size="12">Score: 0.0-0.3</text>`;
  svg += `<line x1="${W/2}" y1="495" x2="${W/2}" y2="590" stroke="${RED}" stroke-width="1" stroke-dasharray="4,4" opacity="0.3"/>`;

  // Confidence decay note
  svg += `
  <rect x="30" y="${H - 70}" width="940" height="40" rx="8" fill="${BG}" stroke="${TEXT_DIM}" stroke-width="1" opacity="0.5"/>
  <text x="${W/2}" y="${H - 43}" text-anchor="middle" fill="${TEXT_DIM}" font-family="Segoe UI,Arial,sans-serif" font-size="12">📉 Confidence decays over time (half-life model) — Inactive publishers lose trust gradually — Re-verification restores score</text>`;

  svg += `\n</svg>`;
  return svg;
}

// ============ Diagram 3: MCP vs JadeGate ============
function diagram3_comparison() {
  const W = 1200, H = 800;
  const leftX = 50, rightX = 620, colW = 530;

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
  <defs>
    <linearGradient id="bgGrad3" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0D1117"/><stop offset="100%" stop-color="#161B22"/></linearGradient>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#bgGrad3)" rx="16"/>
  <text x="${W/2}" y="45" text-anchor="middle" fill="${TEXT}" font-family="Segoe UI,Arial,sans-serif" font-size="28" font-weight="bold">MCP vs JadeGate — Security Comparison</text>
  
  <!-- Divider -->
  <line x1="${W/2}" y1="70" x2="${W/2}" y2="${H - 30}" stroke="${TEXT_DIM}" stroke-width="1" stroke-dasharray="6,4" opacity="0.3"/>
  
  <!-- Headers -->
  <text x="${leftX + colW/2}" y="90" text-anchor="middle" fill="${RED}" font-family="Segoe UI,Arial,sans-serif" font-size="22" font-weight="bold">❌ MCP (Model Context Protocol)</text>
  <text x="${rightX + colW/2}" y="90" text-anchor="middle" fill="${JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="22" font-weight="bold">💠 JadeGate</text>`;

  const comparisons = [
    {
      label: 'Execution Model',
      mcp: 'Turing-complete\n(arbitrary code execution)',
      jade: 'Non-Turing-complete\n(DAG-only, no loops/recursion)',
      mcpColor: RED, jadeColor: JADE
    },
    {
      label: 'Security',
      mcp: 'Behavioral\n(hope the LLM behaves)',
      jade: 'Structural\n(impossible to violate by design)',
      mcpColor: RED, jadeColor: JADE
    },
    {
      label: 'Token Cost',
      mcp: 'LLM interprets every tool call\n(tokens per execution)',
      jade: 'Zero-token execution\n(deterministic, no LLM needed)',
      mcpColor: ORANGE, jadeColor: JADE
    },
    {
      label: 'Verification',
      mcp: 'Trust the server\n(no built-in audit)',
      jade: '5-layer validation pipeline\n(static analysis before run)',
      mcpColor: RED, jadeColor: JADE
    },
    {
      label: 'Composability',
      mcp: 'Server-dependent\n(each server is a black box)',
      jade: 'DAG composition\n(skills combine deterministically)',
      mcpColor: ORANGE, jadeColor: JADE
    },
    {
      label: 'Supply Chain',
      mcp: 'No trust model\n(install and pray)',
      jade: 'Bayesian trust scoring\n(publisher reputation + time decay)',
      mcpColor: RED, jadeColor: JADE
    },
  ];

  const rowH = 100, startY = 120;
  comparisons.forEach((comp, i) => {
    const y = startY + i * rowH;
    
    // Label
    svg += `<text x="${W/2}" y="${y + 15}" text-anchor="middle" fill="${TEXT}" font-family="Segoe UI,Arial,sans-serif" font-size="13" font-weight="bold">${comp.label}</text>`;
    
    // MCP box
    svg += `<rect x="${leftX}" y="${y + 25}" width="${colW}" height="60" rx="8" fill="${BG}" stroke="${comp.mcpColor}" stroke-width="1.5" opacity="0.8"/>`;
    const mcpLines = comp.mcp.split('\n');
    mcpLines.forEach((line, li) => {
      const isSub = li > 0;
      svg += `<text x="${leftX + colW/2}" y="${y + 50 + li * 18}" text-anchor="middle" fill="${isSub ? TEXT_DIM : TEXT}" font-family="Segoe UI,Arial,sans-serif" font-size="${isSub ? 12 : 14}">${line}</text>`;
    });
    
    // Jade box
    svg += `<rect x="${rightX}" y="${y + 25}" width="${colW}" height="60" rx="8" fill="${BG}" stroke="${comp.jadeColor}" stroke-width="1.5" opacity="0.8"/>`;
    const jadeLines = comp.jade.split('\n');
    jadeLines.forEach((line, li) => {
      const isSub = li > 0;
      svg += `<text x="${rightX + colW/2}" y="${y + 50 + li * 18}" text-anchor="middle" fill="${isSub ? TEXT_DIM : JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="${isSub ? 12 : 14}" ${!isSub ? 'font-weight="bold"' : ''}>${line}</text>`;
    });
  });

  // Bottom tagline
  svg += `
  <rect x="100" y="${H - 60}" width="${W - 200}" height="35" rx="8" fill="${JADE}" opacity="0.1"/>
  <text x="${W/2}" y="${H - 37}" text-anchor="middle" fill="${JADE}" font-family="Segoe UI,Arial,sans-serif" font-size="15" font-weight="bold">JadeGate: Security is not a feature — it's a structural property 🔏</text>`;

  svg += `\n</svg>`;
  return svg;
}

// ============ Generate All ============
const outDir = path.join(__dirname, '..', 'assets');
fs.mkdirSync(outDir, { recursive: true });

const diagrams = [
  { name: 'pipeline_5layer.svg', fn: diagram1_pipeline },
  { name: 'trust_hierarchy.svg', fn: diagram2_trust },
  { name: 'mcp_vs_jadegate.svg', fn: diagram3_comparison },
];

diagrams.forEach(d => {
  const svg = d.fn();
  const outPath = path.join(outDir, d.name);
  fs.writeFileSync(outPath, svg, 'utf-8');
  console.log(`✅ ${d.name} (${(svg.length / 1024).toFixed(1)} KB)`);
});

console.log(`\nAll diagrams saved to ${outDir}`);
