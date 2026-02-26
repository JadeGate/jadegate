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
import os
import sys
import time
from pathlib import Path

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
    return f"{_C.CYAN}💠 JadeGate{_C.RESET} {_C.DIM}v2.0.0 — AI Tool Call Security Protocol{_C.RESET}"


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

def cmd_status(args):
    """Show JadeGate protection status."""
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
        print(f"  {_C.BOLD}Security Policy{_C.RESET}")
        print(json.dumps(policy.to_dict(), indent=2))

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
        if r.success:
            icon = f"{_C.GREEN}✓{_C.RESET}"
            total_wrapped += r.servers_wrapped
            total_already += r.already_protected
        else:
            icon = f"{_C.RED}✗{_C.RESET}"
        print(f"  {icon} {r.client_name}: {r.servers_wrapped} wrapped, {r.already_protected} already protected")
        if r.backup_path:
            print(f"    {_C.DIM}backup: {r.backup_path}{_C.RESET}")
        if r.error:
            print(f"    {_C.RED}{r.error}{_C.RESET}")

    print()
    if total_wrapped > 0:
        print(f"  {_C.GREEN}Done!{_C.RESET} {total_wrapped} MCP server(s) now protected by JadeGate.")
        print(f"  {_C.DIM}Restart your MCP clients for changes to take effect.{_C.RESET}")
    elif total_already > 0:
        print(f"  {_C.DIM}All servers already protected. Nothing to do.{_C.RESET}")

    print(f"\n  {_C.DIM}To undo: jadegate uninstall{_C.RESET}")


# ─── uninstall ───────────────────────────────────────────────

def cmd_uninstall(args):
    """Remove jadegate proxy from all MCP client configs."""
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
        p = Path(file_path)
        if p.is_dir():
            files = list(p.glob("*.json"))
        else:
            files = [p]

        for f in files:
            total += 1
            result = validator.validate_file(str(f))
            if result.valid:
                passed += 1
                print(f"  {_C.GREEN}✅ PASS{_C.RESET} {f.name}")
            else:
                print(f"  {_C.RED}❌ FAIL{_C.RESET} {f.name}")
                for issue in result.errors:
                    print(f"    [{issue.code}] {issue.message}")

    print(f"\n  {total} scanned, {_C.GREEN}{passed} passed{_C.RESET}, {_C.RED}{total - passed} failed{_C.RESET}")


# ─── list (v1 compat) ───────────────────────────────────────

def cmd_list(args):
    """List registered JADE skills (v1 compatibility)."""
    # Delegate to old CLI if available
    try:
        from jade_core.cli import cmd_list as old_list
        old_list(args)
    except ImportError:
        print(f"  {_C.DIM}jade_core CLI not available{_C.RESET}")


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

    # list (v1 compat)
    p_list = sub.add_parser("list", help="List registered skills")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
