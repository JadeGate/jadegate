#!/usr/bin/env python3
"""
💠 JadeGate CLI v2.0 — AI Tool Call Security Protocol

Commands:
    jadegate scan          Scan system for MCP servers and assess security
    jadegate proxy <cmd>   Run MCP server through JadeGate security proxy
    jadegate status        Show protection status
    jadegate verify <file> Verify JADE skill file(s) (v1 compat)
    jadegate list          List registered skills (v1 compat)
    jadegate policy show   Show current security policy
    jadegate cert list     List tool certificates
    jadegate cert verify   Verify a certificate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Force UTF-8 on Windows — prevents emoji crash on GBK/CP936 terminals
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ANSI
class _C:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def _banner():
    try:
        from jadegate import __version__
    except Exception:
        __version__ = "2.0.0"
    return f"{_C.CYAN}💠 JadeGate{_C.RESET} {_C.DIM}v{__version__} — AI Tool Call Security Protocol{_C.RESET}"


# ─── scan ────────────────────────────────────────────────────

def cmd_scan(args):
    """Scan system for installed MCP servers."""
    print(_banner())
    print()

    from .scanner.mcp_scanner import MCPScanner
    from .scanner.report import ScanReport

    extra = [args.config] if hasattr(args, "config") and args.config else []
    scanner = MCPScanner(extra_configs=extra)

    print(f"  {_C.DIM}Discovering MCP servers...{_C.RESET}")
    servers = scanner.discover()

    if not servers:
        print(f"  {_C.YELLOW}No MCP servers found.{_C.RESET}")
        print(f"  {_C.DIM}Checked: Claude Desktop, Cursor configs{_C.RESET}")
        return

    print(f"  Found {_C.BOLD}{len(servers)}{_C.RESET} server(s). Assessing...")
    assessed = scanner.assess_all(servers, probe=getattr(args, "probe", False))

    report = ScanReport(assessed)
    print(report.to_terminal())

    if hasattr(args, "output") and args.output:
        report.save_json(args.output)
        print(f"\n  {_C.DIM}Report saved to {args.output}{_C.RESET}")


# ─── proxy ───────────────────────────────────────────────────

def cmd_proxy(args):
    """Run an MCP server through JadeGate security proxy."""
    print(_banner(), file=sys.stderr)

    if not args.command:
        print(f"  {_C.RED}Error: No upstream command specified{_C.RESET}", file=sys.stderr)
        print(f"  Usage: jadegate proxy <command> [args...]", file=sys.stderr)
        sys.exit(1)

    from .runtime.session import JadeSession
    from .policy.policy import JadePolicy
    from .transport.mcp_proxy import JadeMCPProxy

    # Load policy
    policy = JadePolicy.default()
    if hasattr(args, "policy") and args.policy:
        policy = JadePolicy.from_file(args.policy)

    session = JadeSession(policy=policy)
    proxy = JadeMCPProxy(upstream_command=args.command, session=session)

    print(f"  {_C.GREEN}Proxy started{_C.RESET} → {' '.join(args.command)}", file=sys.stderr)
    print(f"  {_C.DIM}All tool calls are now protected by JadeGate{_C.RESET}", file=sys.stderr)

    try:
        proxy.start()
    except KeyboardInterrupt:
        proxy.stop()
        status = session.close()
        print(f"\n  {_C.DIM}Session: {status['total_calls']} calls, {status['blocked_calls']} blocked{_C.RESET}", file=sys.stderr)


# ─── status ──────────────────────────────────────────────────

def cmd_status(args: argparse.Namespace):  # args required by argparse dispatch
    """Show JadeGate protection status."""
    del args  # unused but required by argparse callback interface
    print(_banner())
    print()

    from .trust.trust_store import LocalTrustStore

    store = LocalTrustStore()
    summary = store.get_summary()

    print(f"  {_C.BOLD}Trust Store{_C.RESET}")
    print(f"    Certificates: {summary['total_certificates']}")
    print(f"    Signed:       {summary['signed']}")
    print(f"    Trusted:      {summary['trusted']}")
    print(f"    High risk:    {summary['high_risk']}")
    print(f"    Location:     {_C.DIM}{summary['trust_dir']}{_C.RESET}")
    print()

    # Check if any SDK hooks are active
    from .transport.sdk_hook import _hooks
    if _hooks:
        print(f"  {_C.BOLD}Active SDK Hooks{_C.RESET}")
        for name in _hooks:
            print(f"    {_C.GREEN}✓{_C.RESET} {name}")
    else:
        print(f"  {_C.DIM}No active SDK hooks. Run jadegate.activate() to enable.{_C.RESET}")


# ─── policy ──────────────────────────────────────────────────

def cmd_policy(args):
    """Show or manage security policy."""
    print(_banner())
    print()

    action = getattr(args, "policy_action", "show")

    if action == "show":
        from .policy.policy import JadePolicy
        if hasattr(args, "file") and args.file:
            policy = JadePolicy.from_file(args.file)
        else:
            policy = JadePolicy.default()
        d = policy.to_dict()
        print(f"  {_C.BOLD}Security Policy{_C.RESET}")
        print()
        # Pretty-print as human-readable key: value pairs grouped by section
        sections = {
            "Network": ["network_whitelist", "blocked_domains", "upload_whitelist"],
            "File Access": ["file_read_paths", "file_write_paths", "blocked_file_patterns"],
            "Actions": ["blocked_actions", "require_human_approval"],
            "Rate Limits": ["max_calls_per_minute", "max_call_depth", "circuit_breaker_threshold", "circuit_breaker_timeout_sec"],
            "Scanning": ["enable_dangerous_pattern_scan", "enable_executable_code_scan", "enable_audit_log", "audit_log_path"],
        }
        for section, keys in sections.items():
            print(f"  {_C.DIM}{section}{_C.RESET}")
            for k in keys:
                v = d.get(k)
                if v is None:
                    continue
                if isinstance(v, list):
                    if v:
                        print(f"    {k}: {_C.CYAN}{', '.join(str(x) for x in v)}{_C.RESET}")
                    else:
                        print(f"    {k}: {_C.DIM}(none){_C.RESET}")
                elif isinstance(v, bool):
                    color = _C.GREEN if v else _C.DIM
                    print(f"    {k}: {color}{v}{_C.RESET}")
                elif v != "" and v != 0:
                    print(f"    {k}: {_C.CYAN}{v}{_C.RESET}")
            print()

    elif action == "init":
        from .policy.policy import JadePolicy
        out = getattr(args, "output", "jadegate-policy.json") or "jadegate-policy.json"
        policy = JadePolicy.default()
        policy.save(out)
        print(f"  {_C.GREEN}Default policy written to {out}{_C.RESET}")
        print(f"  {_C.DIM}Edit this file to customize your security rules.{_C.RESET}")


# ─── cert ────────────────────────────────────────────────────

def cmd_cert(args):
    """Certificate management."""
    print(_banner())
    print()

    action = getattr(args, "cert_action", "list")

    if action == "list":
        from .trust.trust_store import LocalTrustStore
        store = LocalTrustStore()
        certs = store.list_all()
        if not certs:
            print(f"  {_C.DIM}No certificates stored.{_C.RESET}")
            return
        print(f"  {_C.BOLD}{'Tool ID':<30} {'Risk':<10} {'Trust':<8} {'Signed'}{_C.RESET}")
        print(f"  {'─' * 60}")
        for c in certs:
            risk = c.risk_profile.level if c.risk_profile else "?"
            signed = f"{_C.GREEN}✓{_C.RESET}" if c.signature else f"{_C.DIM}✗{_C.RESET}"
            print(f"  {c.tool_id:<30} {risk:<10} {c.trust_score:.2f}    {signed}")


# ─── install ─────────────────────────────────────────────────

def cmd_install(args):
    """Auto-inject jadegate proxy into all detected MCP client configs."""
    print(_banner())
    print()

    from .installer import install_all

    extra = getattr(args, "config", None) or []
    results = install_all(extra_configs=extra)

    if not results:
        print(f"  {_C.YELLOW}No MCP client configs found on this system.{_C.RESET}")
        print(f"  {_C.DIM}Checked: Claude Desktop, Cursor, Windsurf, Cline, Continue, Zed{_C.RESET}")
        return

    total_wrapped = 0
    total_already = 0
    for r in results:
        if not r.success:
            print(f"  {_C.RED}✗{_C.RESET} {r.client_name}: error")
            if r.error:
                print(f"    {_C.RED}{r.error}{_C.RESET}")
        elif r.servers_found == 0:
            # Client config exists but has no MCP servers — skip silently
            pass
        elif r.servers_wrapped > 0:
            total_wrapped += r.servers_wrapped
            print(f"  {_C.GREEN}✓{_C.RESET} {r.client_name}: {_C.GREEN}{r.servers_wrapped} server(s) now protected{_C.RESET}")
            if r.backup_path:
                print(f"    {_C.DIM}backup: {r.backup_path}{_C.RESET}")
        elif r.already_protected > 0:
            total_already += r.already_protected
            print(f"  {_C.GREEN}✓{_C.RESET} {r.client_name}: {_C.DIM}already protected ({r.already_protected} server(s)){_C.RESET}")

    print()
    if total_wrapped > 0:
        print(f"  {_C.GREEN}Done!{_C.RESET} {total_wrapped} MCP server(s) now protected by JadeGate.")
        print(f"  {_C.DIM}Restart your MCP clients for changes to take effect.{_C.RESET}")
    elif total_already > 0:
        print(f"  {_C.DIM}All servers already protected. Nothing to do.{_C.RESET}")

    print(f"\n  {_C.DIM}To undo: jadegate uninstall{_C.RESET}")


# ─── helpers ─────────────────────────────────────────────────

def _find_skill_by_name(name: str):
    """Find a skill JSON file by name using jade_registry index.

    Returns a Path if found, None otherwise.
    Matches skill_id or filename stem (e.g. 'mcp_slack_send' or 'slack').
    """
    import importlib.util
    name_lower = name.lower().replace("-", "_")

    # Load registry index to find source_path
    spec = importlib.util.find_spec("jade_registry")
    if not spec or not spec.submodule_search_locations:
        return None
    registry_root = Path(list(spec.submodule_search_locations)[0])
    idx_path = registry_root / "skill_index.json"
    if not idx_path.exists():
        return None

    import json as _json
    index = _json.loads(idx_path.read_text(encoding="utf-8"))
    skills = index.get("skills", [])

    # Resolve the package root (parent of jade_registry)
    pkg_root = registry_root.parent

    matched = None
    for s in skills:
        sid = s.get("skill_id", "").lower()
        src = s.get("source_path", "")
        stem = Path(src).stem.lower() if src else ""
        if sid == name_lower or stem == name_lower:
            matched = src
            break
        # Suffix / partial match: 'slack' matches 'mcp_slack_send'
        if name_lower in sid or name_lower in stem:
            matched = src  # keep searching for exact match

    if matched:
        full = pkg_root / matched
        if full.exists():
            return full
    return None


# ─── uninstall ───────────────────────────────────────────────

def cmd_uninstall(args: argparse.Namespace):  # args required by argparse dispatch
    """Remove jadegate proxy from all MCP client configs."""
    del args  # unused but required by argparse callback interface
    print(_banner())
    print()

    from .installer import uninstall_all

    results = uninstall_all()

    if not results:
        print(f"  {_C.DIM}No jadegate-protected configs found.{_C.RESET}")
        return

    total_unwrapped = 0
    for r in results:
        if r.success:
            icon = f"{_C.GREEN}✓{_C.RESET}"
            total_unwrapped += r.servers_wrapped  # reused field for unwrapped count
        else:
            icon = f"{_C.RED}✗{_C.RESET}"
        print(f"  {icon} {r.client_name}: restored")
        if r.error:
            print(f"    {_C.RED}{r.error}{_C.RESET}")

    print(f"\n  {_C.GREEN}Done!{_C.RESET} JadeGate protection removed. Restart your MCP clients.")


# ─── verify (v1 compat) ─────────────────────────────────────

def cmd_verify(args):
    """Verify JADE skill files (v1 compatibility)."""
    print(_banner())
    print()

    try:
        from jade_core.validator import JadeValidator
    except ImportError:
        print(f"  {_C.RED}jade_core not available for v1 verification{_C.RESET}")
        sys.exit(1)

    validator = JadeValidator()
    total = 0
    passed = 0

    for file_path in args.files:
        # 1. Try as absolute/relative path first
        p = Path(file_path).resolve()
        if not p.exists():
            # 2. Try as skill name — search jade_skills/ inside the package
            p = _find_skill_by_name(file_path)

        if p is None or not p.exists():
            print(f"  {_C.RED}❌ FAIL{_C.RESET} {file_path}")
            print(f"    [NOT_FOUND] No skill file found for: {file_path}")
            print(f"    {_C.DIM}Try: jadegate list {file_path}  to search for matching skills{_C.RESET}")
            total += 1
            continue

        # Collect files: JSON for full validation, SKILL.md for content scan
        if p.is_dir():
            files = list(p.glob("*.json")) + list(p.glob("SKILL.md"))
        else:
            files = [p]

        for f in files:
            total += 1

            if f.suffix == ".md" or f.name == "SKILL.md":
                # SKILL.md → deep content scan (6-category)
                try:
                    content = f.read_text(encoding="utf-8")
                except Exception as e:
                    print(f"  {_C.RED}❌ FAIL{_C.RESET} {f.name}")
                    print(f"    [READ_ERROR] {e}")
                    continue

                issues = _scan_skill_content(content, verbose=True)
                critical = [(s, d) for s, d in issues if s == "CRITICAL"]
                high = [(s, d) for s, d in issues if s == "HIGH"]
                medium = [(s, d) for s, d in issues if s == "MEDIUM"]
                low = [(s, d) for s, d in issues if s == "LOW"]

                if critical or high:
                    print(f"  {_C.RED}❌ FAIL{_C.RESET} {f.name}  ({len(critical)} critical, {len(high)} high)")
                    for sev, desc in critical + high:
                        print(f"    {_C.RED}[{sev}]{_C.RESET} {desc}")
                    for sev, desc in medium:
                        print(f"    {_C.YELLOW}[{sev}]{_C.RESET} {desc}")
                elif medium:
                    passed += 1
                    print(f"  {_C.YELLOW}⚠ WARN{_C.RESET} {f.name}  ({len(medium)} warnings)")
                    for sev, desc in medium:
                        print(f"    {_C.YELLOW}[{sev}]{_C.RESET} {desc}")
                else:
                    passed += 1
                    if low:
                        print(f"  {_C.GREEN}✅ PASS{_C.RESET} {f.name}  ({len(low)} info)")
                        for sev, desc in low:
                            print(f"    {_C.DIM}[{sev}]{_C.RESET} {desc}")
                    else:
                        print(f"  {_C.GREEN}✅ PASS{_C.RESET} {f.name}")
            else:
                # JSON → full 5-layer JadeValidator
                result = validator.validate_file(str(f))
                if result.valid:
                    passed += 1
                    print(f"  {_C.GREEN}✅ PASS{_C.RESET} {f.name}")
                else:
                    print(f"  {_C.RED}❌ FAIL{_C.RESET} {f.name}")
                    for issue in result.errors:
                        print(f"    [{issue.code}] {issue.message}")

    print(f"\n  {total} scanned, {_C.GREEN}{passed} passed{_C.RESET}, {_C.RED}{total - passed} failed{_C.RESET}")


# ─── list ────────────────────────────────────────────────────

def cmd_list(args):
    """List bundled JADE skills from the registry."""
    print(_banner())
    print()

    # Try reading skill_index.json from jade_registry package
    try:
        import importlib.util
        spec = importlib.util.find_spec("jade_registry")
        if spec and spec.submodule_search_locations:
            idx_path = Path(list(spec.submodule_search_locations)[0]) / "skill_index.json"
            index = json.loads(idx_path.read_text(encoding="utf-8"))
        else:
            index = {}
    except Exception:
        index = {}

    skills = index.get("skills", [])
    if not skills:
        print(f"  {_C.DIM}No skills found in registry.{_C.RESET}")
        return

    keyword = getattr(args, "keyword", None)
    if keyword:
        keyword = keyword.lower()
        skills = [s for s in skills if keyword in s.get("name", "").lower()
                  or keyword in s.get("description", "").lower()
                  or keyword in " ".join(s.get("tags", [])).lower()]

    for s in skills:
        name = s.get("name", "?")
        desc = s.get("description", "")[:60]
        print(f"  {_C.CYAN}💠{_C.RESET} {_C.BOLD}{name:<28}{_C.RESET} {_C.DIM}{desc}{_C.RESET}")

    print(f"\n  {_C.DIM}{len(skills)} skill(s){_C.RESET}")


# ─── skill (install from GitHub / URL) ───────────────────────

def cmd_skill(args):
    """Install and verify a JADE skill from GitHub or URL."""
    action = getattr(args, "skill_action", "help")

    if action == "add":
        _skill_add(args)
    elif action == "list":
        cmd_list(args)
    else:
        print(_banner())
        print()
        print(f"  {_C.BOLD}jadegate skill add <url>{_C.RESET}   Install a skill from GitHub or URL")
        print(f"  {_C.BOLD}jadegate skill list{_C.RESET}         List installed skills")
        print()
        print(f"  {_C.DIM}Supports:{_C.RESET}")
        print(f"  {_C.DIM}  github.com/ComposioHQ/awesome-claude-skills/tree/master/file-organizer{_C.RESET}")
        print(f"  {_C.DIM}  github.com/JimLiu/baoyu-skills  (installs all skills){_C.RESET}")
        print(f"  {_C.DIM}  any raw URL to a SKILL.md or .json skill file{_C.RESET}")


def _skill_add(args):
    """Install a skill from GitHub repo or raw URL, with security scan."""
    import urllib.request
    import urllib.error

    print(_banner())
    print()

    url = args.url
    print(f"  {_C.DIM}Fetching skill from: {url}{_C.RESET}")
    print()

    # Normalise GitHub URLs → raw content URLs
    raw_urls = _resolve_skill_urls(url)
    if not raw_urls:
        print(f"  {_C.RED}✗ Could not resolve skill URL{_C.RESET}")
        print(f"  {_C.DIM}Expected: GitHub repo/folder URL or raw URL to SKILL.md / .json{_C.RESET}")
        return

    skills_dir = Path.home() / ".jadegate" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    installed = 0
    for raw_url, skill_name in raw_urls:
        print(f"  📦 {_C.BOLD}{skill_name}{_C.RESET}")
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "jadegate/2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            print(f"     {_C.RED}✗ Download failed: {e}{_C.RESET}")
            continue

        # Security scan the content
        issues = _scan_skill_content(content)
        if issues:
            print(f"     {_C.RED}✗ Security issues found — NOT installed:{_C.RESET}")
            for issue in issues:
                print(f"       • {issue}")
            continue

        # Save to ~/.jadegate/skills/
        ext = ".md" if raw_url.endswith(".md") else ".json"
        dest = skills_dir / f"{skill_name}{ext}"
        dest.write_text(content, encoding="utf-8")
        print(f"     {_C.GREEN}✓ Verified & installed{_C.RESET} → {_C.DIM}{dest}{_C.RESET}")
        installed += 1

    print()
    if installed:
        print(f"  {_C.GREEN}✓ {installed} skill(s) installed to ~/.jadegate/skills/{_C.RESET}")
        print(f"  {_C.DIM}Skills are available to Claude Code via CLAUDE.md or MCP.{_C.RESET}")
    else:
        print(f"  {_C.YELLOW}No skills installed.{_C.RESET}")


def _resolve_skill_urls(url: str):
    """Convert a GitHub URL or raw URL into a list of (raw_url, skill_name) tuples."""
    import urllib.request
    import urllib.error

    # Already a raw URL
    if "raw.githubusercontent.com" in url or url.endswith(".md") or url.endswith(".json"):
        name = url.rstrip("/").split("/")[-1].replace(".md", "").replace(".json", "")
        return [(url, name)]

    # GitHub repo/folder URL: https://github.com/ORG/REPO[/tree/BRANCH/PATH]
    import re
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)(/.*)?)?", url
    )
    if not m:
        return []

    org, repo, branch, subpath = m.group(1), m.group(2), m.group(3), m.group(4)
    branch = branch or "main"
    subpath = (subpath or "").strip("/")

    # Single skill folder (has a SKILL.md inside)
    if subpath:
        raw = f"https://raw.githubusercontent.com/{org}/{repo}/{branch}/{subpath}/SKILL.md"
        name = subpath.split("/")[-1]
        return [(raw, name)]

    # Whole repo — discover all SKILL.md files via GitHub API
    api = f"https://api.github.com/repos/{org}/{repo}/git/trees/{branch}?recursive=1"
    try:
        req = urllib.request.Request(api, headers={"User-Agent": "jadegate/2.0", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            tree = json.loads(resp.read())
        results = []
        for item in tree.get("tree", []):
            path = item.get("path", "")
            if path.endswith("/SKILL.md") or path == "SKILL.md":
                skill_name = path.replace("/SKILL.md", "").replace("SKILL.md", repo).split("/")[-1]
                raw = f"https://raw.githubusercontent.com/{org}/{repo}/{branch}/{path}"
                results.append((raw, skill_name))
        return results
    except Exception:
        # Fallback: try as single SKILL.md at root
        raw = f"https://raw.githubusercontent.com/{org}/{repo}/{branch}/SKILL.md"
        return [(raw, repo)]


def _scan_skill_content(content: str, verbose: bool = False) -> list:
    """
    Deep security scan of SKILL.md or skill JSON content.
    6-category scan: code injection, dangerous commands, prompt injection,
    data exfiltration, social engineering, suspicious infrastructure.
    Returns list of (severity, issue_description) tuples.
    """
    import re
    issues = []

    def _flag(severity, desc):
        issues.append((severity, desc))

    # ── Category 1: Code injection (22 patterns from SecurityEngine) ──
    code_injection = [
        (r"curl\s+.*\|\s*(bash|sh|zsh)", "Remote code execution via curl|bash"),
        (r"wget\s+.*(-O\s*-\s*\||\|\s*(bash|sh))", "Remote code execution via wget"),
        (r"(?<!\w)eval\s*\(", "Use of eval()"),
        (r"(?<!\w)exec\s*\(", "Use of exec()"),
        (r"__import__\s*\(", "Dynamic import attempt"),
        (r"os\.system\s*\(", "Shell execution via os.system"),
        (r"subprocess\.(run|Popen|call)\s*\(.*shell\s*=\s*True", "Shell injection via subprocess"),
        (r"\bcompile\s*\(.*\bexec\b", "Dynamic code compilation"),
        (r"<script\b", "Embedded script tag"),
        (r"javascript:", "JavaScript protocol injection"),
        (r"\bnew\s+Function\s*\(", "Dynamic function constructor"),
        (r"\bchild_process\b", "Node.js child_process usage"),
        (r"\bShellExecute\b", "Windows ShellExecute call"),
        (r"\bWScript\b", "Windows scripting host"),
        (r"\bpowershell\s+-[eE]", "PowerShell encoded command"),
    ]
    for pattern, desc in code_injection:
        if re.search(pattern, content, re.IGNORECASE):
            _flag("CRITICAL", f"[CODE_INJECT] {desc}")

    # ── Category 2: Dangerous system commands (28 patterns) ──
    dangerous_cmds = [
        (r"\brm\s+-rf\s+/", "Destructive rm -rf /"),
        (r"\brm\s+-fr\s+/", "Destructive rm -fr /"),
        (r"\bmkfs\b", "Filesystem format command"),
        (r"\bdd\s+if=", "Raw disk write via dd"),
        (r"\bformat\s+[cCdD]:", "Windows disk format"),
        (r"\bfdisk\b", "Disk partition command"),
        (r"\bchmod\s+777\b", "World-writable permissions"),
        (r"\bchmod\s+-R\s+777\b", "Recursive world-writable"),
        (r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", "Fork bomb"),
        (r"\bshutdown\s+(-[hHrR]|now|/[srta])\b", "System shutdown command"),
        (r"\binit\s+0\b", "System halt via init"),
        (r"\bkillall\b", "Kill all processes"),
        (r"\biptables\s+-F\b", "Flush all firewall rules"),
        (r"\bnc\s+-[elp]", "Netcat listener/reverse shell"),
    ]
    for pattern, desc in dangerous_cmds:
        if re.search(pattern, content, re.IGNORECASE):
            _flag("HIGH", f"[DANGER_CMD] {desc}")

    # ── Category 3: Prompt injection & AI manipulation ──
    prompt_injection = [
        (r"ignore\s+(all\s+)?previous\s+instructions", "Classic prompt injection: ignore previous instructions"),
        (r"ignore\s+(all\s+)?above\s+instructions", "Prompt injection: ignore above"),
        (r"disregard\s+(all\s+)?prior\s+(instructions|rules|guidelines)", "Prompt injection: disregard prior rules"),
        (r"you\s+are\s+now\s+(a|an|in)\s+", "Role hijacking attempt"),
        (r"pretend\s+you\s+are\s+(a|an|not)\s+", "Role manipulation: pretend to be"),
        (r"act\s+as\s+(a|an)\s+(different|new|unrestricted)", "Role override: act as unrestricted"),
        (r"(forget|override)\s+(your|all|any)\s+(rules|restrictions|guidelines|safety)", "Override safety guardrails"),
        (r"do\s+not\s+(tell|show|reveal|inform)\s+(the\s+)?user", "Hide actions from user"),
        (r"don'?t\s+(tell|show|reveal|inform)\s+(the\s+)?user", "Hide actions from user"),
        (r"without\s+(the\s+)?user('s)?\s+(knowledge|knowing|awareness|consent)", "Act without user awareness"),
        (r"secretly\s+(send|upload|post|transmit|exfiltrate)", "Covert data transmission"),
        (r"silently\s+(send|upload|post|transmit|install|execute)", "Silent execution instruction"),
        (r"bypass\s+(security|safety|filter|restriction|guardrail)", "Bypass security controls"),
        (r"jailbreak", "Jailbreak reference"),
        (r"DAN\s+(mode|prompt)", "DAN jailbreak pattern"),
        (r"\[system\]|\[SYSTEM\]", "Fake system message injection"),
        (r"<\|im_start\|>|<\|im_end\|>", "ChatML injection attempt"),
        (r"```system\b", "Fake system block injection"),
    ]
    for pattern, desc in prompt_injection:
        if re.search(pattern, content, re.IGNORECASE):
            _flag("CRITICAL", f"[PROMPT_INJECT] {desc}")

    # ── Category 4: Data exfiltration instructions ──
    data_exfil = [
        (r"(read|cat|access|steal|grab|copy|exfiltrate)\s+.{0,30}(~\/\.ssh|id_rsa|\.env\b|\.aws|credentials|private.?key)", "Data exfiltration: access sensitive files"),
        (r"(send|post|upload|transmit)\s+.{0,30}(~\/\.ssh|id_rsa|\.env\b|\.aws|credentials|private.?key|secret|password).{0,30}(to|via)\s+.{0,30}(https?://|webhook|endpoint|server)", "Data exfiltration: send sensitive data to external server"),
        (r"(base64|encode|encrypt)\s+.{0,30}(and|then)\s+.{0,30}(send|post|upload)", "Encoded data exfiltration"),
        (r"(collect|harvest|scrape)\s+.{0,30}(password|credential|token|key|secret)\s+.{0,30}(from|across|in)", "Credential harvesting instruction"),
        (r"(read|dump|export)\s+.{0,30}(entire\s+)?(database|db|sqlite|mongo)\s+.{0,30}(and|then)\s+.{0,30}(send|post|upload)", "Database exfiltration instruction"),
        (r"(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][a-zA-Z0-9]{16,}", "Hardcoded API key/secret"),
        (r"(password|passwd)\s*[:=]\s*['\"][^\s'\"]{8,}", "Hardcoded password"),
    ]
    for pattern, desc in data_exfil:
        if re.search(pattern, content, re.IGNORECASE):
            _flag("HIGH", f"[DATA_EXFIL] {desc}")

    # ── Category 5: Suspicious infrastructure ──
    infra_patterns = [
        (r"https?://[^\s]+\.(onion|i2p|bit)\b", "Suspicious TLD (.onion/.i2p/.bit)"),
        (r"\b169\.254\.169\.254\b", "AWS metadata endpoint"),
        (r"\bmetadata\.google\b", "GCP metadata endpoint"),
        (r"\b100\.100\.100\.200\b", "Alibaba Cloud metadata"),
        (r"ngrok\.io|localtunnel\.me|serveo\.net", "Tunneling service URL"),
        (r"pastebin\.com|hastebin\.com|ghostbin\.", "Paste site (potential C2 channel)"),
        (r"discord\.com/api/webhooks", "Discord webhook (potential C2)"),
        (r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[:/]", "Raw IP address URL"),
    ]
    for pattern, desc in infra_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            _flag("MEDIUM", f"[INFRA] {desc}")

    # ── Category 6: SKILL.md structural validation ──
    if content.strip().startswith("---"):
        # Has frontmatter — check required fields
        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            if not re.search(r'^name\s*:', fm, re.MULTILINE):
                _flag("LOW", "[STRUCTURE] Missing 'name' in YAML frontmatter")
            if not re.search(r'^description\s*:', fm, re.MULTILINE):
                _flag("LOW", "[STRUCTURE] Missing 'description' in YAML frontmatter")
        else:
            _flag("LOW", "[STRUCTURE] Malformed YAML frontmatter")
    else:
        _flag("LOW", "[STRUCTURE] No YAML frontmatter (---) found")

    # Return as simple strings for backward compat, or full tuples if verbose
    if verbose:
        return issues
    return [desc for _, desc in issues if _ in ("CRITICAL", "HIGH")]


# ─── main ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="jadegate",
        description="💠 JadeGate — AI Tool Call Security Protocol",
    )
    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="Scan system for MCP servers")
    p_scan.add_argument("--config", help="Extra MCP config file to scan")
    p_scan.add_argument("--probe", action="store_true", help="Actually launch servers to probe tools (slower)")
    p_scan.add_argument("--output", "-o", help="Save JSON report to file")
    p_scan.set_defaults(func=cmd_scan)

    # proxy
    p_proxy = sub.add_parser("proxy", help="Run MCP server through security proxy")
    p_proxy.add_argument("command", nargs=argparse.REMAINDER, help="Upstream MCP server command")
    p_proxy.add_argument("--policy", help="Policy JSON file")
    p_proxy.set_defaults(func=cmd_proxy)

    # status
    p_status = sub.add_parser("status", help="Show protection status")
    p_status.set_defaults(func=cmd_status)

    # policy
    p_policy = sub.add_parser("policy", help="Security policy management")
    p_policy.add_argument("policy_action", nargs="?", default="show", choices=["show", "init"])
    p_policy.add_argument("--file", help="Policy file to show")
    p_policy.add_argument("--output", "-o", help="Output path for init")
    p_policy.set_defaults(func=cmd_policy)

    # cert
    p_cert = sub.add_parser("cert", help="Certificate management")
    p_cert.add_argument("cert_action", nargs="?", default="list", choices=["list", "verify"])
    p_cert.set_defaults(func=cmd_cert)

    # install
    p_install = sub.add_parser("install", help="Auto-inject jadegate proxy into all MCP client configs")
    p_install.add_argument("--config", action="append", help="Extra config file(s) to process")
    p_install.set_defaults(func=cmd_install)

    # uninstall
    p_uninstall = sub.add_parser("uninstall", help="Remove jadegate proxy from all MCP client configs")
    p_uninstall.set_defaults(func=cmd_uninstall)

    # verify (v1 compat)
    p_verify = sub.add_parser("verify", help="Verify JADE skill file(s)")
    p_verify.add_argument("files", nargs="+")
    p_verify.set_defaults(func=cmd_verify)

    # list
    p_list = sub.add_parser("list", help="List registered skills")
    p_list.add_argument("keyword", nargs="?", help="Filter by keyword")
    p_list.set_defaults(func=cmd_list)

    # skill (install from GitHub / ecosystem)
    p_skill = sub.add_parser("skill", help="Install skills from GitHub / skill ecosystems")
    skill_sub = p_skill.add_subparsers(dest="skill_action")
    p_skill.set_defaults(func=cmd_skill)

    p_skill_add = skill_sub.add_parser("add", help="Install a skill from GitHub or URL")
    p_skill_add.add_argument("url", help="GitHub repo/folder URL or raw URL to SKILL.md")
    p_skill_add.set_defaults(func=cmd_skill)

    p_skill_list = skill_sub.add_parser("list", help="List installed skills")
    p_skill_list.set_defaults(func=cmd_skill)

    args = parser.parse_args()
    if not args.command:
        _print_welcome()
        return

    args.func(args)


def _print_welcome():
    """Print a friendly welcome screen when no command is given."""
    print(_banner())
    print()
    print(f"  {_C.BOLD}Quick start:{_C.RESET}")
    print(f"  {_C.CYAN}jadegate install{_C.RESET}              {_C.DIM}Protect all MCP clients (Claude, Cursor, Windsurf…){_C.RESET}")
    print(f"  {_C.CYAN}jadegate scan{_C.RESET}                 {_C.DIM}Audit installed MCP servers for security risks{_C.RESET}")
    print(f"  {_C.CYAN}jadegate status{_C.RESET}               {_C.DIM}Show current protection status{_C.RESET}")
    print()
    print(f"  {_C.BOLD}Skills:{_C.RESET}")
    print(f"  {_C.CYAN}jadegate list{_C.RESET}                 {_C.DIM}Browse 150+ verified built-in skills{_C.RESET}")
    print(f"  {_C.CYAN}jadegate list github{_C.RESET}          {_C.DIM}Search skills by keyword{_C.RESET}")
    print(f"  {_C.CYAN}jadegate skill add <github-url>{_C.RESET}  {_C.DIM}Install from awesome-claude-skills or any repo{_C.RESET}")
    print()
    print(f"  {_C.BOLD}More:{_C.RESET}")
    print(f"  {_C.CYAN}jadegate verify <file>{_C.RESET}        {_C.DIM}Run 5-layer security check on a skill file{_C.RESET}")
    print(f"  {_C.CYAN}jadegate policy show{_C.RESET}          {_C.DIM}View current security policy{_C.RESET}")
    print(f"  {_C.CYAN}jadegate uninstall{_C.RESET}            {_C.DIM}Remove protection (restore original configs){_C.RESET}")
    print()
    print(f"  {_C.DIM}Docs → https://jadegate.io   GitHub → https://github.com/JadeGate/jadegate{_C.RESET}")


if __name__ == "__main__":
    main()
