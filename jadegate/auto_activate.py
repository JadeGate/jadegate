"""
JadeGate Auto-Activate — .pth file for JADEGATE=1 environment variable activation.

When installed via pip, this creates a .pth file in site-packages that
auto-activates jadegate when JADEGATE=1 is set.

This file is the content of the .pth file itself.
"""
import os
if os.environ.get("JADEGATE", "").strip() in ("1", "true", "yes", "on"):
    try:
        import jadegate
        jadegate.activate()
    except Exception:
        pass
