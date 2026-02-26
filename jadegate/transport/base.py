"""
JadeGate Transport Base — Abstract interface for transport adapters.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, Optional

from ..runtime.interceptor import ToolCallInterceptor, InterceptResult


class JadeTransport(abc.ABC):
    """
    Abstract base for JadeGate transport adapters.

    A transport sits between the AI client and the tool server,
    intercepting tool calls for security validation.
    """

    def __init__(self, interceptor: ToolCallInterceptor):
        self.interceptor = interceptor

    @abc.abstractmethod
    def start(self) -> None:
        """Start the transport (begin intercepting)."""
        ...

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the transport."""
        ...

    @abc.abstractmethod
    def is_running(self) -> bool:
        """Check if the transport is active."""
        ...

    def intercept_call(self, tool_name: str, params: Dict[str, Any]) -> InterceptResult:
        """Run interception on a tool call."""
        return self.interceptor.before_call(tool_name, params)

    def report_result(self, tool_name: str, params: Dict[str, Any],
                      result: Any = None, success: bool = True,
                      error: Optional[str] = None) -> None:
        """Report a tool call result back to the interceptor."""
        self.interceptor.after_call(tool_name, params, result, success, error)
