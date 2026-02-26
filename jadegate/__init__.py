"""
JadeGate v2.0 — AI Tool Call Security Protocol Layer

The TLS of AI tool calls. Install and activate:

    import jadegate
    jadegate.activate()

All tool calls are then automatically protected.
"""

__version__ = "2.0.0"
__protocol_version__ = "2.0.0"

from .runtime.session import JadeSession
from .runtime.dynamic_dag import DynamicDAG
from .runtime.circuit_breaker import CircuitBreaker
from .policy.policy import JadePolicy

_active_session = None


def activate(policy=None):
    """
    One-line activation. Hooks all detected SDKs automatically.

    Args:
        policy: A JadePolicy, path to policy JSON, dict, or None for defaults.

    Returns:
        The active JadeSession.
    """
    global _active_session

    if isinstance(policy, str):
        pol = JadePolicy.from_file(policy)
    elif isinstance(policy, dict):
        pol = JadePolicy.from_dict(policy)
    elif isinstance(policy, JadePolicy):
        pol = policy
    else:
        pol = JadePolicy.default()

    _active_session = JadeSession(policy=pol)

    # Auto-hook detected SDKs
    from .transport.sdk_hook import auto_hook
    auto_hook(_active_session)

    return _active_session


def get_session():
    """Get the current active session."""
    return _active_session


def deactivate():
    """Deactivate JadeGate protection."""
    global _active_session
    if _active_session:
        _active_session.close()
        _active_session = None

    from .transport.sdk_hook import unhook_all
    unhook_all()


__all__ = [
    "activate",
    "deactivate",
    "get_session",
    "JadeSession",
    "JadePolicy",
    "DynamicDAG",
    "CircuitBreaker",
]
