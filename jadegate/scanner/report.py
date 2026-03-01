"""
JadeGate Scan Report — Generate security assessment reports.

Outputs terminal-friendly audit reports and JSON exports.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from .mcp_scanner import MCPServerInfo


# ANSI colors
class _C:
    RED    = "\033[31m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    CYAN   = "\033[36m"
    DIM    = "\033[2m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"


RISK_ICONS = {
    "low":      f"{_C.GREEN}🟢 LOW     {_C.RESET}",
    "medium":   f"{_C.YELLOW}🟡 MEDIUM  {_C.RESET}",
    "high":     f"{_C.RED}🔴 HIGH    {_C.RESET}",
    "critical": f"{_C.RED}⚫ CRITICAL{_C.RESET}",
    "unknown":  f"{_C.DIM}⚪ UNKNOWN {_C.RESET}",
}

RISK_BADGE = {
    "low":      f"{_C.GREEN}LOW{_C.RESET}",
    "medium":   f"{_C.YELLOW}MEDIUM{_C.RESET}",
    "high":     f"{_C.RED}HIGH{_C.RESET}",
    "critical": f"{_C.RED}CRITICAL{_C.RESET}",
    "unknown":  f"{_C.DIM}UNKNOWN{_C.RESET}",
}

# ── Finding rules ─────────────────────────────────────────────────────────────
# Each rule: (id, severity, title, condition_fn(name, desc, caps), detail, action)
_FINDING_RULES = [
    (
        "F-001", "critical",
        "Arbitrary code / shell execution",
        lambda n, d, caps: "shell" in caps,
        "Tool can execute shell commands or spawn processes. Highest privilege escalation risk.",
        "BLOCK",
    ),
    (
        "F-002", "high",
        "Network + filesystem (exfiltration path)",
        lambda n, d, caps: "network" in caps and "filesystem" in caps,
        "Combination of network access and file read creates a direct data-exfiltration path.\n"
        "    Attacker pattern: read ~/.ssh/id_rsa → POST to external server.",
        "ASK on every call",
    ),
    (
        "F-003", "high",
        "Browser automation (JS execution + DOM access)",
        lambda n, d, caps: "browser" in caps,
        "Full browser control allows cookie theft, session hijacking, and screenshot capture\n"
        "    of any open tabs including passwords and 2FA codes.",
        "ASK on every call",
    ),
    (
        "F-004", "medium",
        "Unrestricted network access",
        lambda n, d, caps: "network" in caps and "shell" not in caps and "filesystem" not in caps,
        "Tool makes outbound HTTP requests. Without allowlist, can reach internal\n"
        "    metadata endpoints (169.254.169.254, localhost, 192.168.x.x).",
        "MONITOR + add network allowlist",
    ),
    (
        "F-005", "medium",
        "Filesystem read/write",
        lambda n, d, caps: "filesystem" in caps and "network" not in caps,
        "Tool accesses local files. May read sensitive paths (~/.ssh/, .env, ~/.aws/)\n"
        "    if no path restrictions are configured.",
        "MONITOR + restrict to safe paths",
    ),
    (
        "F-006", "medium",
        "Data send / upload capability",
        lambda n, d, caps: "data_send" in caps,
        "Tool can send or upload data externally (email, webhook, API push).\n"
        "    Risk of accidental or malicious exfiltration.",
        "ASK on every call",
    ),
    (
        "F-007", "low",
        "Read-only operations",
        lambda n, d, caps: caps == ["read_only"] or (caps and all(c in ("read_only",) for c in caps)),
        "Tool performs read-only queries. Low risk but should still be monitored\n"
        "    for scope creep.",
        "MONITOR",
    ),
]


def _generate_findings(server: MCPServerInfo) -> List[Dict]:
    """Generate per-server finding list based on risk profile."""
    if not server.risk_profile:
        return []

    rp = server.risk_profile
    caps = set(rp.capabilities or [])
    # Supplement caps from flags
    if rp.shell_access:   caps.add("shell")
    if rp.network_access: caps.add("network")
    if rp.file_access:    caps.add("filesystem")
    if rp.data_exfil_risk: caps.add("data_send")

    findings = []
    for fid, severity, title, cond, detail, action in _FINDING_RULES:
        # Check tool-level items too
        tool_texts = " ".join(
            f"{t.get('name','')} {t.get('description','')}" for t in (server.tools or [])
        ).lower()
        name = server.name.lower()
        desc = tool_texts

        if cond(name, desc, caps):
            findings.append({
                "id": fid,
                "severity": severity,
                "title": title,
                "detail": detail,
                "action": action,
            })

    return findings


class ScanReport:
    """Generate and format scan reports."""

    def __init__(self, servers: List[MCPServerInfo]):
        self._servers = servers
        self._generated_at = time.time()

    # ── JSON export ───────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        servers_out = []
        for s in self._servers:
            d = s.to_dict()
            d["findings"] = _generate_findings(s)
            servers_out.append(d)
        return {
            "jadegate_scan_report": {
                "version": "2.0",
                "generated_at": self._generated_at,
                "total_servers": len(self._servers),
                "summary": self._summary(),
                "servers": servers_out,
            }
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    # ── Terminal audit report ─────────────────────────────────────────────────

    def to_terminal(self) -> str:
        """Full CT-style audit report with per-server findings."""
        lines = []
        W = 62  # width

        # ── Header ──
        lines.append(f"\n{_C.CYAN}💠 JadeGate Security Audit Report{_C.RESET}")
        lines.append(f"{_C.DIM}{'━' * W}{_C.RESET}")

        if not self._servers:
            lines.append(f"  {_C.DIM}No MCP servers found.{_C.RESET}")
            lines.append(f"  Check Claude Desktop or Cursor config.")
            return "\n".join(lines)

        total_findings = 0
        crit_findings  = 0
        high_findings  = 0

        # ── Per-server block ──
        for s in self._servers:
            risk_level = s.risk_profile.level if s.risk_profile else "unknown"
            badge      = RISK_BADGE.get(risk_level, risk_level)
            findings   = _generate_findings(s)
            total_findings += len(findings)
            crit_findings  += sum(1 for f in findings if f["severity"] == "critical")
            high_findings  += sum(1 for f in findings if f["severity"] == "high")

            cmd_str = " ".join(s.command[:3]) + (" …" if len(s.command) > 3 else "")

            lines.append(f"\n  {_C.BOLD}Server: {s.name}{_C.RESET}  [{badge}]")
            lines.append(f"  {_C.DIM}Command: {cmd_str}{_C.RESET}")
            if s.tools:
                tool_names = ", ".join(t.get("name", "?") for t in s.tools[:5])
                if len(s.tools) > 5:
                    tool_names += f" … +{len(s.tools)-5} more"
                lines.append(f"  {_C.DIM}Tools ({len(s.tools)}): {tool_names}{_C.RESET}")

            if not findings:
                lines.append(f"\n  {_C.GREEN}  ✓ No findings. Clean.{_C.RESET}")
            else:
                lines.append(f"\n  {_C.BOLD}  FINDINGS ({len(findings)}){_C.RESET}")
                lines.append(f"  {'─' * (W - 2)}")
                for f in findings:
                    sev   = f["severity"]
                    icon  = {"critical": "⚫", "high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
                    color = {"critical": _C.RED, "high": _C.RED,
                             "medium": _C.YELLOW, "low": _C.GREEN}.get(sev, _C.DIM)
                    lines.append(
                        f"\n  [{_C.DIM}{f['id']}{_C.RESET}] {icon} "
                        f"{color}{sev.upper()}{_C.RESET} · {_C.BOLD}{f['title']}{_C.RESET}"
                    )
                    for detail_line in f["detail"].split("\n"):
                        lines.append(f"    {_C.DIM}{detail_line}{_C.RESET}")
                    lines.append(f"    {_C.CYAN}→ Action: {f['action']}{_C.RESET}")

            if s.scan_error:
                lines.append(f"\n  {_C.RED}  ⚠ Scan error: {s.scan_error}{_C.RESET}")

            # Recommendation
            if risk_level in ("high", "critical"):
                lines.append(f"\n  {_C.DIM}  Protect this server:{_C.RESET}")
                lines.append(f"    {_C.CYAN}jadegate proxy {cmd_str}{_C.RESET}")

            lines.append(f"\n  {_C.DIM}{'─' * W}{_C.RESET}")

        # ── Summary ──
        summary = self._summary()
        lines.append(f"\n{_C.BOLD}  SUMMARY{_C.RESET}")
        lines.append(
            f"  {summary['total']} server(s) scanned  ·  "
            f"{_C.GREEN}{summary['low']} low{_C.RESET}  "
            f"{_C.YELLOW}{summary['medium']} medium{_C.RESET}  "
            f"{_C.RED}{summary['high']} high{_C.RESET}  "
            f"{_C.RED}{summary['critical']} critical{_C.RESET}"
        )
        lines.append(
            f"  {total_findings} finding(s) total  ·  "
            f"{_C.RED}{crit_findings} critical{_C.RESET}  "
            f"{_C.RED}{high_findings} high{_C.RESET}"
        )

        if crit_findings + high_findings > 0:
            lines.append(
                f"\n  {_C.RED}⚠  {crit_findings + high_findings} critical/high finding(s) require immediate action.{_C.RESET}"
            )
            lines.append(f"  {_C.DIM}Run 'jadegate proxy <cmd>' to add protection.{_C.RESET}")
        else:
            lines.append(f"\n  {_C.GREEN}✓ All servers within acceptable risk threshold.{_C.RESET}")

        lines.append(f"{_C.DIM}{'━' * W}{_C.RESET}\n")
        return "\n".join(lines)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _summary(self) -> Dict[str, int]:
        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0, "unknown": 0}
        for s in self._servers:
            level = s.risk_profile.level if s.risk_profile else "unknown"
            risk_counts[level] = risk_counts.get(level, 0) + 1
        return {
            "total": len(self._servers),
            "scanned_ok":   sum(1 for s in self._servers if not s.scan_error),
            "scan_errors":  sum(1 for s in self._servers if s.scan_error),
            **risk_counts,
        }
