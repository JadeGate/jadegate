# JADE v2.0 升级方案：从 Skill 验证库 → AI Tool Call 安全协议层

## 核心目标
让 JADE 成为 AI 工具调用的 TLS —— `pip install jadegate` 后自动保护所有 tool call，用户无感。

## 现有资产（全部保留复用）
| 模块 | 文件 | 新角色 |
|------|------|--------|
| SecurityEngine | security.py | Runtime 参数扫描器（原样复用） |
| DAGAnalyzer | dag.py | 扩展为 DynamicDAG（运行时调用链追踪） |
| Registry + 贝叶斯 | registry.py | Trust Layer 信任引擎（原样复用） |
| Attestation | models.py | 每次 tool call 后自动提交 |
| Ed25519 crypto | crypto.py | Certificate 体系基础（原样复用） |
| Validator | validator.py | 静态扫描保留 + 运行时扫描新增 |
| CLI | cli.py | 扩展新命令 |
| allowed_actions | json | 默认安全策略种子 |

## 新增模块

### 1. Transport Layer（传输层适配）
**文件**: `jadegate/transport/`
- `mcp_proxy.py` — MCP stdio 透明代理，拦截 tools/list 和 tools/call
- `sdk_hook.py` — monkey-patch OpenAI/Anthropic SDK 的 tool call
- `base.py` — 传输层抽象接口

### 2. Runtime Layer（运行时引擎）
**文件**: `jadegate/runtime/`
- `session.py` — JadeSession：一次会话的安全上下文
- `dynamic_dag.py` — 运行时调用链 DAG 构建 + 异常模式检测
- `interceptor.py` — tool call 拦截器：before_call / after_call
- `circuit_breaker.py` — 熔断器：连续失败/异常时自动断开

### 3. Policy Layer（策略层）
**文件**: `jadegate/policy/`
- `policy.py` — 安全策略定义 + 加载
- `default_policy.json` — 默认安全策略（从 allowed_actions 演化）

### 4. Trust Layer（信任层）
**文件**: `jadegate/trust/`
- `certificate.py` — JadeCertificate：工具安全证书
- `trust_store.py` — 本地信任存储（类似浏览器 CA store）
- `tofu.py` — Trust On First Use 逻辑

### 5. Scanner（一键扫描）
**文件**: `jadegate/scanner/`
- `mcp_scanner.py` — 扫描系统已安装的 MCP server
- `report.py` — 生成安全报告

### 6. CLI 扩展
新增命令：
- `jadegate proxy <command>` — MCP 透明代理
- `jadegate scan` — 一键扫描所有已安装 MCP/skill
- `jadegate status` — 查看保护状态
- `jadegate activate` — 全局激活
- `jadegate cert` — 证书管理

### 7. 一行激活
**文件**: `jadegate/__init__.py`
```python
import jadegate
jadegate.activate()  # 自动 hook 所有 SDK
```

## 目录结构
```
ProjectJADE/
├── jade_core/          # 保留！原有静态验证
├── jade_schema/        # 保留！schema 定义
├── jade_skills/        # 保留！示例 skill
├── jadegate/           # 新增！v2 协议层
│   ├── __init__.py     # activate() 入口
│   ├── transport/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── mcp_proxy.py
│   │   └── sdk_hook.py
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── dynamic_dag.py
│   │   ├── interceptor.py
│   │   └── circuit_breaker.py
│   ├── policy/
│   │   ├── __init__.py
│   │   ├── policy.py
│   │   └── default_policy.json
│   ├── trust/
│   │   ├── __init__.py
│   │   ├── certificate.py
│   │   ├── trust_store.py
│   │   └── tofu.py
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── mcp_scanner.py
│   │   └── report.py
│   └── cli.py          # 新 CLI（整合旧 CLI）
├── tests/
│   ├── test_v2_runtime.py
│   ├── test_v2_proxy.py
│   ├── test_v2_scanner.py
│   ├── test_v2_trust.py
│   └── test_v2_integration.py
└── setup.py            # 更新：jadegate 包名 + 新入口
```

## 安全铁律（不可违反）
1. **全部本地计算**，零数据外传
2. **私钥体系不变**，Ed25519 根私钥唯一权威
3. **旧功能全部保留**，静态扫描 + 签名验证原样可用
4. **离线可用**，联网仅可选（拉取社区信任列表）
5. **透明代理**，不修改 tool call 内容，只验证和审计

## 开发顺序
1. Policy Layer（策略定义，其他层的基础）
2. Runtime Layer（核心引擎：session + dynamic_dag + interceptor）
3. Transport Layer（MCP proxy，让它能"坐在中间"）
4. Trust Layer（证书 + TOFU）
5. Scanner（一键扫描）
6. CLI 整合
7. activate() 一行激活
8. 全量测试

## 验收标准
- [ ] `jadegate scan` 能扫描并报告系统 MCP server 安全状态
- [ ] `jadegate proxy <cmd>` 能透明代理 MCP server 并实时验证 tool call
- [ ] `jadegate.activate()` 能 hook SDK 自动保护
- [ ] 运行时 DAG 能追踪调用链并检测异常模式
- [ ] 所有旧测试通过（静态验证、签名、registry）
- [ ] 新测试覆盖所有 v2 模块
- [ ] 私钥签名体系完整可用
