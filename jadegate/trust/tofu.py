"""
JadeGate TOFU — Trust On First Use.

When a tool is seen for the first time, TOFU records its baseline
(capabilities, risk profile). On subsequent uses, if the tool's
behavior deviates from the baseline, TOFU raises an alert.

Similar to SSH's known_hosts mechanism.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .certificate import JadeCertificate, RiskProfile
from .trust_store import LocalTrustStore

logger = logging.getLogger("jadegate.trust.tofu")


@dataclass
class TOFUAlert:
    """Alert raised when a tool deviates from its baseline."""
    tool_id: str
    alert_type: str  # new_tool, capability_change, risk_escalation
    message: str
    old_value: Any = None
    new_value: Any = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "alert_type": self.alert_type,
            "message": self.message,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp,
        }


class TrustOnFirstUse:
    """
    TOFU manager.

    First encounter: record baseline → auto-trust (like SSH first connect).
    Subsequent encounters: compare against baseline → alert on deviation.
    """

    def __init__(self, trust_store: Optional[LocalTrustStore] = None):
        self._store = trust_store or LocalTrustStore()
        self._alerts: List[TOFUAlert] = []

    @property
    def alerts(self) -> List[TOFUAlert]:
        return list(self._alerts)

    def check_tool(
        self,
        tool_id: str,
        name: str = "",
        description: str = "",
        input_schema: Optional[Dict] = None,
        server_id: str = "",
    ) -> List[TOFUAlert]:
        """
        Check a tool against TOFU baseline.

        If first time: creates certificate and stores it.
        If seen before: compares against stored baseline.

        Returns list of alerts (empty = all good).
        """
        alerts: List[TOFUAlert] = []
        existing = self._store.get(tool_id)

        if existing is None:
            # First encounter — record baseline
            risk = RiskProfile.from_tool_info(name or tool_id, description, input_schema)
            cert = JadeCertificate(
                tool_id=tool_id,
                server_id=server_id,
                display_name=name or tool_id,
                description=description,
                risk_profile=risk,
            )
            self._store.save(cert)

            alert = TOFUAlert(
                tool_id=tool_id,
                alert_type="new_tool",
                message=f"New tool '{name or tool_id}' seen for the first time (risk: {risk.level})",
                new_value=risk.level,
            )
            alerts.append(alert)
            logger.info("TOFU: New tool '%s' baselined (risk: %s)", tool_id, risk.level)
        else:
            # Seen before — compare
            new_risk = RiskProfile.from_tool_info(name or tool_id, description, input_schema)

            # Check risk level escalation
            risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3, "unknown": -1}
            old_level = risk_order.get(existing.risk_profile.level, -1)
            new_level = risk_order.get(new_risk.level, -1)

            if new_level > old_level:
                alert = TOFUAlert(
                    tool_id=tool_id,
                    alert_type="risk_escalation",
                    message=f"Tool '{tool_id}' risk escalated: {existing.risk_profile.level} → {new_risk.level}",
                    old_value=existing.risk_profile.level,
                    new_value=new_risk.level,
                )
                alerts.append(alert)
                logger.warning("TOFU: Risk escalation for '%s': %s → %s",
                             tool_id, existing.risk_profile.level, new_risk.level)

            # Check new capabilities
            old_caps = set(existing.risk_profile.capabilities)
            new_caps = set(new_risk.capabilities)
            added_caps = new_caps - old_caps

            if added_caps:
                alert = TOFUAlert(
                    tool_id=tool_id,
                    alert_type="capability_change",
                    message=f"Tool '{tool_id}' gained new capabilities: {added_caps}",
                    old_value=list(old_caps),
                    new_value=list(new_caps),
                )
                alerts.append(alert)
                logger.warning("TOFU: New capabilities for '%s': %s", tool_id, added_caps)

            # Update last_seen
            existing.last_seen = time.time()
            self._store.save(existing)

        self._alerts.extend(alerts)
        return alerts

    def get_baseline(self, tool_id: str) -> Optional[JadeCertificate]:
        """Get the stored baseline for a tool."""
        return self._store.get(tool_id)

    def reset_baseline(self, tool_id: str) -> bool:
        """Reset a tool's baseline (re-TOFU on next encounter)."""
        return self._store.remove(tool_id)
