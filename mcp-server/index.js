#!/usr/bin/env node
/**
 * JadeGate MCP Server
 * Exposes jade-core verification, search, and info capabilities via MCP protocol.
 * 
 * Tools:
 *   jade_verify   — Verify a skill JSON (pass raw JSON or file path)
 *   jade_search   — Search skills by keyword/tag
 *   jade_info     — Get detailed info about a skill
 *   jade_list     — List all available skills
 *   jade_stats    — Registry statistics
 *   jade_dag      — Visualize skill execution DAG (Mermaid/D3/DOT)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { execSync } from "child_process";
import { readFileSync, existsSync, readdirSync } from "fs";
import { join, resolve } from "path";

// Find jade-core skill directory
const SKILL_DIRS = [
  join(process.cwd(), "jade_skills"),
  join(process.env.HOME || "", ".jadegate", "skills"),
  "/usr/local/share/jadegate/skills",
];

function findSkillDir() {
  for (const dir of SKILL_DIRS) {
    if (existsSync(dir)) return dir;
  }
  return null;
}

function runJadeCmd(args) {
  try {
    const result = execSync(`python3 -c "
import sys, json
sys.path.insert(0, '.')
${args}
"`, { cwd: findSkillDir()?.replace("/jade_skills", "") || ".", timeout: 30000, encoding: "utf-8" });
    return result.trim();
  } catch (e) {
    return `Error: ${e.message}`;
  }
}

function loadSkillIndex() {
  const skillDir = findSkillDir();
  if (!skillDir) return [];
  const baseDir = skillDir.replace("/jade_skills", "");
  const indexPath = join(baseDir, "jade_registry", "skill_index.json");
  if (existsSync(indexPath)) {
    return JSON.parse(readFileSync(indexPath, "utf-8")).skills || [];
  }
  return [];
}

function getAllSkills() {
  const skillDir = findSkillDir();
  if (!skillDir) return [];
  const skills = [];
  for (const sub of ["mcp", "tools", ""]) {
    const dir = sub ? join(skillDir, sub) : skillDir;
    if (!existsSync(dir)) continue;
    for (const f of readdirSync(dir)) {
      if (f.endsWith(".json") && !f.includes(".sig.")) {
        try {
          const data = JSON.parse(readFileSync(join(dir, f), "utf-8"));
          skills.push({ file: join(dir, f), ...data });
        } catch {}
      }
    }
  }
  return skills;
}

const server = new Server(
  { name: "jadegate", version: "1.3.0" },
  { capabilities: { tools: {}, resources: {} } }
);

// === TOOLS ===

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "jade_verify",
      description: "Verify a JadeGate skill JSON. Returns 5-layer validation results with pass/fail status and confidence score.",
      inputSchema: {
        type: "object",
        properties: {
          skill_json: { type: "string", description: "Raw JSON string of the skill to verify" },
          file_path: { type: "string", description: "Path to a skill JSON file to verify" },
        },
      },
    },
    {
      name: "jade_search",
      description: "Search JadeGate skill registry by keyword, tag, or category.",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query (keyword or tag)" },
          category: { type: "string", enum: ["mcp", "tools", "standalone"], description: "Filter by category" },
          limit: { type: "number", description: "Max results (default 10)" },
        },
        required: ["query"],
      },
    },
    {
      name: "jade_info",
      description: "Get detailed information about a specific JadeGate skill by ID.",
      inputSchema: {
        type: "object",
        properties: {
          skill_id: { type: "string", description: "The skill ID to look up" },
        },
        required: ["skill_id"],
      },
    },
    {
      name: "jade_list",
      description: "List all available JadeGate skills with optional category filter.",
      inputSchema: {
        type: "object",
        properties: {
          category: { type: "string", enum: ["mcp", "tools", "standalone"], description: "Filter by category" },
        },
      },
    },
    {
      name: "jade_stats",
      description: "Get JadeGate registry statistics: total skills, categories, verification status.",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "jade_dag",
      description: "Visualize a skill's execution DAG as Mermaid flowchart. Helps agents understand skill execution flow.",
      inputSchema: {
        type: "object",
        properties: {
          skill_id: { type: "string", description: "Skill ID to look up from registry" },
          skill_json: { type: "string", description: "Raw skill JSON string" },
          format: { type: "string", enum: ["mermaid", "d3", "dot"], description: "Output format (default: mermaid)" },
        },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "jade_verify": {
      let filePath = args?.file_path;
      let tempFile = null;

      if (args?.skill_json && !filePath) {
        const tmp = `/tmp/jade_verify_${Date.now()}.json`;
        require("fs").writeFileSync(tmp, args.skill_json);
        filePath = tmp;
        tempFile = tmp;
      }

      if (!filePath) {
        return { content: [{ type: "text", text: "Error: provide skill_json or file_path" }] };
      }

      const result = runJadeCmd(`
from jade_core.validator import JadeValidator
import json
v = JadeValidator()
// Sanitize file path
fp = "${filePath}".replace('"', '').replace("'", "").replace(";", "").replace("\\", "")
import os.path
fp = os.path.abspath(fp)
r = v.validate_file(fp)
out = {
    "valid": r.valid,
    "layers_passed": r.layers_passed,
    "total_layers": r.total_layers,
    "confidence": round(r.confidence, 4) if hasattr(r, 'confidence') else None,
    "issues": [{"severity": i.severity.value if hasattr(i.severity, 'value') else str(i.severity), "layer": i.layer, "message": i.message} for i in r.issues]
}
print(json.dumps(out, indent=2))
`);

      if (tempFile) try { require("fs").unlinkSync(tempFile); } catch {}

      return { content: [{ type: "text", text: result }] };
    }

    case "jade_search": {
      const query = (args?.query || "").toLowerCase();
      const category = args?.category;
      const limit = args?.limit || 10;
      const skills = loadSkillIndex();
      const matches = skills.filter(s => {
        if (category && s.category !== category) return false;
        const text = `${s.skill_id} ${s.name} ${s.description} ${(s.tags || []).join(" ")}`.toLowerCase();
        return text.includes(query);
      }).slice(0, limit);

      return {
        content: [{
          type: "text",
          text: JSON.stringify({ total: matches.length, results: matches.map(s => ({
            skill_id: s.skill_id, name: s.name, description: s.description,
            category: s.category, tags: s.tags, signed: s.signed
          })) }, null, 2)
        }]
      };
    }

    case "jade_info": {
      const sid = args?.skill_id;
      const skills = getAllSkills();
      const skill = skills.find(s => s.skill_id === sid);
      if (!skill) return { content: [{ type: "text", text: `Skill '${sid}' not found` }] };
      const { file, ...data } = skill;
      return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
    }

    case "jade_list": {
      const category = args?.category;
      const skills = loadSkillIndex();
      const filtered = category ? skills.filter(s => s.category === category) : skills;
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            total: filtered.length,
            skills: filtered.map(s => ({ skill_id: s.skill_id, name: s.name, category: s.category }))
          }, null, 2)
        }]
      };
    }

    case "jade_stats": {
      const skills = loadSkillIndex();
      const cats = {};
      let signed = 0;
      skills.forEach(s => {
        cats[s.category] = (cats[s.category] || 0) + 1;
        if (s.signed) signed++;
      });
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            total_skills: skills.length,
            signed_skills: signed,
            categories: cats,
            protocol_version: "1.0.0",
            verification_layers: 5,
            crypto: "Ed25519"
          }, null, 2)
        }]
      };
    }

    case "jade_dag": {
      let skillJson = args?.skill_json;

      // If skill_id provided, find the file
      if (args?.skill_id && !skillJson) {
        const skills = getAllSkills();
        const found = skills.find(s => s.skill_id === args.skill_id);
        if (!found) {
          return { content: [{ type: "text", text: `Skill not found: ${args.skill_id}` }] };
        }
        skillJson = JSON.stringify(found);
      }

      if (!skillJson) {
        return { content: [{ type: "text", text: "Error: provide skill_id or skill_json" }] };
      }

      const fmt = args?.format || "mermaid";
      const pyMethod = fmt === "d3" ? "to_d3_json" : fmt === "dot" ? "to_dot" : "to_mermaid";
      const serialize = fmt === "d3" ? "import json; print(json.dumps(result, indent=2))" : "print(result)";

      // Write skill JSON to temp file for safe passing
      const tmpSkill = `/tmp/jade_dag_${Date.now()}.json`;
      require("fs").writeFileSync(tmpSkill, skillJson);

      const result = runJadeCmd(`
import json
from jade_core.models import JadeSkill
from jade_core.dag import DAGAnalyzer
with open('${tmpSkill}') as f:
    data = json.load(f)
skill = JadeSkill.from_dict(data)
analyzer = DAGAnalyzer()
result = analyzer.${pyMethod}(skill)
${serialize}
`);

      try { require("fs").unlinkSync(tmpSkill); } catch {}

      return {
        content: [{
          type: "text",
          text: result
        }]
      };
    }

    default:
      return { content: [{ type: "text", text: `Unknown tool: ${name}` }] };
  }
});

// === RESOURCES ===

server.setRequestHandler(ListResourcesRequestSchema, async () => ({
  resources: [
    {
      uri: "jadegate://registry/index",
      name: "JadeGate Skill Registry",
      description: "Complete index of all verified JadeGate skills",
      mimeType: "application/json",
    },
    {
      uri: "jadegate://trust/root-ca",
      name: "JadeGate Root CA",
      description: "Root Certificate Authority public key and trust anchors",
      mimeType: "application/json",
    },
  ],
}));

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const { uri } = request.params;

  if (uri === "jadegate://registry/index") {
    const skills = loadSkillIndex();
    return {
      contents: [{
        uri,
        mimeType: "application/json",
        text: JSON.stringify({ total: skills.length, skills }, null, 2),
      }],
    };
  }

  if (uri === "jadegate://trust/root-ca") {
    const baseDir = findSkillDir()?.replace("/jade_skills", "");
    const caPath = baseDir ? join(baseDir, "jadegate.pub.json") : null;
    if (caPath && existsSync(caPath)) {
      return { contents: [{ uri, mimeType: "application/json", text: readFileSync(caPath, "utf-8") }] };
    }
    return { contents: [{ uri, mimeType: "text/plain", text: "Root CA not found" }] };
  }

  throw new Error(`Unknown resource: ${uri}`);
});

// === START ===

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("JadeGate MCP Server v1.3.0 running on stdio");
}

main().catch(console.error);
