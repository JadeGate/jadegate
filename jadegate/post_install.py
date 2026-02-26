"""
JadeGate Post-Install Hook — pip install 完成后自动激活保护。

用户体验：
    pip install jadegate
    # 就这样。结束了。所有 MCP server 已经被保护。

不需要：
    ❌ jadegate install
    ❌ jadegate activate
    ❌ 改配置文件
    ❌ 设环境变量
    ❌ 理解任何原理
"""

from __future__ import annotations

import os
import sys
import site
import logging
from pathlib import Path

logger = logging.getLogger("jadegate.post_install")

# ANSI
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _write_pth_file() -> bool:
    """
    Write jadegate.pth to site-packages for JADEGATE=1 auto-activation.
    Returns True if written successfully.
    """
    pth_content = (
        "import os; "
        "exec('try:\\n"
        "    if os.environ.get(\"JADEGATE\", \"\").strip() in (\"1\", \"true\", \"yes\", \"on\"):\\n"
        "        import jadegate; jadegate.activate()\\n"
        "except Exception:\\n"
        "    pass')\n"
    )
    try:
        site_dirs = site.getsitepackages() if hasattr(site, "getsitepackages") else []
        if not site_dirs:
            site_dirs = [site.getusersitepackages()]

        for site_dir in site_dirs:
            pth_path = os.path.join(site_dir, "jadegate.pth")
            try:
                Path(site_dir).mkdir(parents=True, exist_ok=True)
                with open(pth_path, "w") as f:
                    f.write(pth_content)
                logger.info("Wrote %s", pth_path)
                return True
            except PermissionError:
                continue

        # Fallback: user site-packages
        user_site = site.getusersitepackages()
        pth_path = os.path.join(user_site, "jadegate.pth")
        Path(user_site).mkdir(parents=True, exist_ok=True)
        with open(pth_path, "w") as f:
            f.write(pth_content)
        return True
    except Exception as e:
        logger.debug("Could not write .pth file: %s", e)
        return False


def post_install():
    """
    Called after pip install jadegate.

    Does three things silently:
    1. Scans for MCP client configs and injects jadegate proxy
    2. Writes .pth file for JADEGATE=1 env var activation
    3. Prints a one-line confirmation

    If anything fails, fails silently — never breaks pip install.
    """
    try:
        from .installer import install_all

        # 1. Auto-inject into all MCP configs
        results = install_all()
        total_wrapped = sum(r.servers_wrapped for r in results if r.success)
        total_clients = sum(1 for r in results if r.success and r.servers_wrapped > 0)

        # 2. Write .pth file
        pth_ok = _write_pth_file()

        # 3. Print branded confirmation
        print()
        print(f"  {_CYAN}╔═══════════════════════════════════════════════════╗{_RESET}")
        print(f"  {_CYAN}║{_RESET}   💠 {_BOLD}JadeGate{_RESET} — AI Tool Call Security Protocol   {_CYAN}║{_RESET}")
        print(f"  {_CYAN}╚═══════════════════════════════════════════════════╝{_RESET}")
        print()

        if total_wrapped > 0:
            print(f"  {_GREEN}✓ ACTIVE{_RESET}  {total_wrapped} MCP server(s) across {total_clients} client(s) protected")
        else:
            print(f"  {_GREEN}✓ READY{_RESET}   Waiting for MCP clients — protection activates automatically")

        if pth_ok:
            print(f"  {_GREEN}✓ SDK{_RESET}     Set JADEGATE=1 to auto-protect Python AI SDKs")

        print()
        print(f"  {_DIM}Commands:{_RESET}")
        print(f"  {_DIM}  jadegate status     check protection{_RESET}")
        print(f"  {_DIM}  jadegate scan       audit MCP servers{_RESET}")
        print(f"  {_DIM}  jadegate uninstall  revert all changes{_RESET}")
        print()

    except Exception:
        # Never break pip install
        pass


def post_uninstall():
    """Clean up on pip uninstall."""
    try:
        # Remove .pth file
        site_dirs = site.getsitepackages() if hasattr(site, "getsitepackages") else []
        site_dirs.append(site.getusersitepackages())
        for site_dir in site_dirs:
            pth_path = os.path.join(site_dir, "jadegate.pth")
            if os.path.exists(pth_path):
                os.remove(pth_path)

        # Uninstall from MCP configs
        from .installer import uninstall_all
        uninstall_all()
    except Exception:
        pass
