"""
JadeGate Scan Report — Generate security assessment reports.

Outputs terminal-friendly tables and JSON reports.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from .mcp_scanner import MCPServerInfo


# ANSI colors
class _C:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


RISK_ICONS = {
    "low": f"{_C.GREEN}🟢 LOW{_C.RESET}",
    "medium": f"{_C.YELLOW}🟡 MED{_C.RESET}",
    "high": f"{_C.RED}🔴 HIGH{_C.RESET}",
    "critical": f"{_C.RED}⚫ CRIT{_C.RESET}",
    "unknown": f"{_C.DIM}⚪ UNK{_C.RESET}",
}


class ScanReport:
    """Generate and format scan reports."""

    def __init__(self, servers: List[MCPServerInfo]):
        self._servers = servers
        self._generated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict."""
        return {
            "jadegate_scan_report": {
                "version": "2.0",
                "generated_at": self._generated_at,
                "total_servers": len(self._servers),
                "summary": self._summary(),
                "servers": [s.to_dict() for s in self._servers],
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_json(self, path: str) -> None:
        """Save report to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    def _summary(self) -> Dict[str, int]:
        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0, "unknown": 0}
        for s in self._servers:
            level = s.risk_profile.level if s.risk_profile else "unknown"
            risk_counts[level] = risk_counts.get(level, 0) + 1
        return {
            "total": len(self._servers),
            "scanned_ok": sum(1 for s in self._servers if not s.scan_error),
            "scan_errors": sum(1 for s in self._servers if s.scan_error),
            **risk_counts,
        }

    def to_terminal(self) -> str:
        """Generate terminal-friendly report with colors."""
        lines = []
        lines.append(f"\n{_C.CYAN}💠 JadeGate Security Scan Report{_C.RESET}")
        lines.append(f"{_C.DIM}{'─' * 60}{_C.RESET}")

        if not self._servers:
            lines.append(f"  {_C.DIM}No MCP servers found.{_C.RESET}")
            lines.append(f"  Check Claude Desktop or Cursor config.")
            return "\n".join(lines)

        # Header
        lines.append(f"  {_C.BOLD}{'Server':<20} {'Risk':<14} {'Tools':<8} {'Issues'}{_C.RESET}")
        lines.append(f"  {'─' * 56}")

        for s in self._servers:
            risk_level = s.risk_profile.level if s.risk_profile else "unknown"
            risk_str = RISK_ICONS.get(risk_level, risk_level)
            tools_count = str(len(s.tools)) if s.tools else "?"
            issues = s.scan_error if s.scan_error else self._describe_issues(s)

            name = s.name[:18]
            lines.append(f"  {name:<20} {risk_str:<24} {tools_count:<8} {_C.DIM}{issues}{_C.RESET}")

        # Summary
        summary = self._summary()
        lines.append(f"  {'─' * 56}")
        lines.append(
            f"  Scanned: {_C.BOLD}{summary['total']}{_C.RESET} servers | "
            f"{_C.GREEN}{summary['low']} low{_C.RESET} | "
            f"{_C.YELLOW}{summary['medium']} med{_C.RESET} | "
            f"{_C.RED}{summary['high']} high{_C.RESET} | "
            f"{_C.RED}{summary['critical']} crit{_C.RESET}"
        )

        if summary["high"] + summary["critical"] > 0:
            lines.append(f"\n  {_C.RED}⚠ {summary['high'] + summary['critical']} high/critical risk server(s) detected!{_C.RESET}")
            lines.append(f"  {_C.DIM}Run 'jadegate proxy <command>' to add protection.{_C.RESET}")

        return "\n".join(lines)

    def _describe_issues(self, server: MCPServerInfo) -> str:
        """Describe key issues for a server."""
        if not server.risk_profile:
            return ""
        issues = []
        rp = server.risk_profile
        if rp.shell_access:
            issues.append("shell access")
        if rp.network_access and rp.file_access:
            issues.append("net+file (exfil risk)")
        elif rp.network_access:
            issues.append("network access")
        elif rp.file_access:
            issues.append("file access")
        return ", ".join(issues) if issues else "ok"
