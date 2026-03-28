---
name: jadegate
description: "The TLS of AI Tool Calls — 43 security-verified skills for MCP servers. Transparent security proxy with zero config, zero dependencies."
---

# JadeGate Skills Collection

**The TLS of AI Tool Calls** — 43 security-verified skills for MCP (Model Context Protocol) servers.

## Quick Start

```bash
pip install jadegate
jadegate install       # Protect all MCP clients
jadegate scan          # Audit MCP servers
jadegate list          # Browse 150+ skills
```

## Skills (43 total)

### JadeGate Core (8 skills)

| Skill | Description |
|-------|-------------|
| [jadegate](skills/jadegate/) | Main MCP security proxy — 6 security layers for every tool call |
| [jadegate-scan](skills/jadegate-scan/) | Scan and audit MCP servers for security risks |
| [jadegate-verify](skills/jadegate-verify/) | 5-layer security verification for skill files |
| [jadegate-install](skills/jadegate-install/) | Auto-install protection into MCP client configs |
| [jadegate-policy](skills/jadegate-policy/) | Manage security policies, whitelists, and rate limits |
| [jadegate-trust](skills/jadegate-trust/) | TOFU certificates and Ed25519 signature management |
| [jadegate-sdk](skills/jadegate-sdk/) | Python SDK — protect tool calls with 2 lines of code |
| [jadegate-skill-browse](skills/jadegate-skill-browse/) | Browse and search 150+ verified skills |

### Communication (5 skills)

| Skill | Description |
|-------|-------------|
| [email-send-safe](skills/email-send-safe/) | Secure SMTP email with confirmation and content sanitization |
| [slack-send-message](skills/slack-send-message/) | Send messages to Slack via webhook |
| [telegram-send-msg](skills/telegram-send-msg/) | Send messages via Telegram Bot API |
| [discord-webhook-send](skills/discord-webhook-send/) | Send messages to Discord channels |
| [notion-page-read](skills/notion-page-read/) | Read Notion pages via API |

### Network & Security (7 skills)

| Skill | Description |
|-------|-------------|
| [dns-lookup](skills/dns-lookup/) | DNS record queries |
| [ip-geolocation](skills/ip-geolocation/) | IP address geolocation lookup |
| [http-health-check](skills/http-health-check/) | HTTP endpoint health monitoring |
| [ssl-cert-check](skills/ssl-cert-check/) | SSL/TLS certificate inspection |
| [whois-lookup](skills/whois-lookup/) | WHOIS domain registration lookup |
| [hash-file-verify](skills/hash-file-verify/) | File hash computation and verification |
| [base64-file-encode](skills/base64-file-encode/) | Base64 file encoding/decoding |

### Web (5 skills)

| Skill | Description |
|-------|-------------|
| [web-search-query](skills/web-search-query/) | Web search via public APIs |
| [webpage-content-extract](skills/webpage-content-extract/) | Extract content from web pages |
| [webpage-screenshot](skills/webpage-screenshot/) | Capture web page screenshots |
| [rss-feed-reader](skills/rss-feed-reader/) | Parse and read RSS feeds |
| [exa-semantic-search](skills/exa-semantic-search/) | Semantic web search via Exa API |

### Data Processing (6 skills)

| Skill | Description |
|-------|-------------|
| [csv-data-analysis](skills/csv-data-analysis/) | CSV file analysis and statistics |
| [json-data-transform](skills/json-data-transform/) | JSON data transformation with JMESPath |
| [pdf-table-parser](skills/pdf-table-parser/) | Parse tables from PDF files |
| [image-resize-convert](skills/image-resize-convert/) | Image resizing and format conversion |
| [qr-code-generate](skills/qr-code-generate/) | QR code generation |
| [text-translation](skills/text-translation/) | Text translation via public APIs |

### Git & DevOps (5 skills)

| Skill | Description |
|-------|-------------|
| [git-clone-repo](skills/git-clone-repo/) | Safe git repository cloning |
| [git-diff-summary](skills/git-diff-summary/) | Git diff analysis and summarization |
| [github-create-issue](skills/github-create-issue/) | Create GitHub issues via API |
| [docker-container-list](skills/docker-container-list/) | List and inspect Docker containers |
| [ssh-remote-exec](skills/ssh-remote-exec/) | Secure remote command execution via SSH |

### System & Utilities (7 skills)

| Skill | Description |
|-------|-------------|
| [file-batch-rename](skills/file-batch-rename/) | Batch file rename with regex patterns |
| [sqlite-db-query](skills/sqlite-db-query/) | Safe SQLite database queries |
| [log-error-analyzer](skills/log-error-analyzer/) | Log file error pattern analysis |
| [timezone-query](skills/timezone-query/) | Timezone conversion and queries |
| [weather-api-query](skills/weather-api-query/) | Weather data from free public APIs |
| [text-sentiment](skills/text-sentiment/) | Text sentiment analysis |
| [web-anti-crawl-bypass](skills/web-anti-crawl-bypass/) | Anti-crawler detection and handling |

## Security

All skills pass JadeGate's 5-layer security verification:
1. Schema validation
2. Code injection scan (22 patterns)
3. Dangerous command detection (25 patterns)
4. Network/data leak analysis
5. DAG integrity check

License: BSL-1.1 (converts to Apache 2.0 in 4 years)
