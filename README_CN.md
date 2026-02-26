# JadeGate 💠

**AI 工具调用的 TLS。**

一条命令，保护所有 MCP Server，零配置。

```bash
pip install jadegate
# 就这样。你的所有 MCP Server 已经被保护了。
```

---

## 问题

MCP 没有安全层。任何工具都能读你的文件、发网络请求、执行命令——而你的 AI 客户端会毫不犹豫地执行。

GitHub 上有 10,000+ 个 MCP Server，绝大多数从未被审计过。安全研究者已经证实：有些工具会在你不知情的情况下访问 `~/.ssh/`、`.env` 文件和浏览器 cookies，而表面上只是在做无害的事。

MCP 是没有 TLS 的 TCP。JadeGate 就是那个 TLS。

## 工作原理

JadeGate 作为透明代理，插在 AI 客户端和 MCP Server 之间。每个工具调用在执行前都要经过 6 层安全检查：

```
AI 客户端（Claude、Cursor 等）
    ↓
  JadeGate 代理          ← 策略检查、异常检测、信任验证
    ↓
  MCP Server（filesystem、github、puppeteer 等）
```

### 6 层安全栈

| 层 | 功能 |
|---|------|
| **策略层** | 按工具配置允许/拒绝/询问规则，速率限制，参数校验 |
| **运行时层** | 动态调用链追踪（DAG），异常检测，熔断器 |
| **传输层** | 透明 MCP 代理——拦截 stdio/SSE，不修改 Server |
| **信任层** | TOFU（首次使用即信任）+ Ed25519 证书验证 Server 身份 |
| **扫描层** | MCP Server 能力静态分析，风险评分 |
| **安装层** | 自动注入所有 MCP 客户端配置（Claude、Cursor、Windsurf、Cline、Continue、Zed） |

## 安装

```bash
pip install jadegate
```

安装完成的瞬间，JadeGate 自动：
1. 扫描系统上所有 MCP 客户端配置
2. 给每个 MCP Server 套上 JadeGate 代理
3. 备份原始配置（完全可逆）

下次打开 Claude Desktop、Cursor 或任何支持的客户端——保护已生效。

### 卸载

```bash
jadegate uninstall   # 恢复所有原始配置
pip uninstall jadegate
```

## 命令

```bash
jadegate status      # 查看保护状态
jadegate scan        # 安全审计所有 MCP Server
jadegate install     # 重新注入（添加新 MCP Server 后）
jadegate uninstall   # 恢复所有更改
```

### 扫描输出

```
$ jadegate scan

  💠 JadeGate v2.0.0 — AI Tool Call Security Protocol

  MCP Server Security Scan

  ✓ filesystem  ● MEDIUM    filesystem access
    tools: 3 discovered
  ✓ github      ● MEDIUM    network access
    tools: 5 discovered
  ✓ puppeteer   ● CRITICAL  shell + network + browser
    tools: 8 discovered

  3 servers scanned: 0 low, 2 medium, 0 high, 1 critical
  All servers protected by JadeGate proxy.
```

## Python SDK 保护

如果你的 Python Agent 直接使用 OpenAI 或 Anthropic SDK：

```bash
export JADEGATE=1
python my_agent.py
# 所有 SDK 工具调用现在都被拦截和保护
```

或者在代码里：

```python
import jadegate
jadegate.activate()

# 正常使用 OpenAI/Anthropic——JadeGate 自动拦截工具调用
from openai import OpenAI
client = OpenAI()
```

## 策略配置

默认策略拦截危险模式。可按工具自定义：

```json
{
  "default_action": "allow",
  "tool_rules": {
    "filesystem:write_file": {
      "action": "ask",
      "reason": "文件写入需要确认"
    },
    "shell:exec": {
      "action": "deny",
      "reason": "Shell 执行被策略拦截"
    }
  },
  "rate_limit": {
    "max_calls_per_minute": 60
  }
}
```

## 支持的客户端

| 客户端 | 配置路径 | 自动检测 |
|--------|---------|:---:|
| Claude Desktop | `~/.config/claude/` | ✅ |
| Cursor | `~/.cursor/` | ✅ |
| Windsurf | `~/.codeium/windsurf/` | ✅ |
| Cline | `~/.vscode/cline/` | ✅ |
| Continue | `~/.continue/` | ✅ |
| Zed | `~/.config/zed/` | ✅ |
| 自定义 | `jadegate install --config <path>` | ➕ |

## 设计原则

- **零配置**：`pip install` = 已保护。不需要设置、环境变量、配置文件。
- **透明**：MCP Server 不知道 JadeGate 的存在。不需要修改 Server。
- **可逆**：`jadegate uninstall` 恢复一切。干净卸载。
- **离线**：所有分析在本地运行。无遥测、无云端、数据不出机器。
- **安全降级**：JadeGate 崩溃不影响 MCP Server 正常工作。

## 对比

| | 原生 MCP | JadeGate |
|---|---|---|
| 工具调用策略 | ❌ 无 | ✅ 按工具 允许/拒绝/询问 |
| 调用链追踪 | ❌ 无 | ✅ 动态 DAG |
| 异常检测 | ❌ 无 | ✅ 熔断器 + 速率限制 |
| Server 身份验证 | ❌ 无 | ✅ TOFU + Ed25519 |
| 安全扫描 | ❌ 无 | ✅ 静态分析 + 风险评分 |
| 接入成本 | N/A | `pip install jadegate` |

## 测试

```bash
pip install pytest
pytest tests/ -v
# 238 个测试，全部通过
```

## 许可证

MIT

---

**GitHub**: https://github.com/JadeGate/jadegate
**PyPI**: https://pypi.org/project/jadegate/
