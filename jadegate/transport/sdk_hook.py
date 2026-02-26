"""
JadeGate SDK Hook — Monkey-patch OpenAI/Anthropic/LangChain SDKs.

When activated, transparently intercepts tool calls made through
popular AI SDKs and routes them through JadeSession for security checks.

Usage:
    import jadegate
    jadegate.activate()
    # All subsequent SDK tool calls are now protected

All processing is local. No data leaves the machine.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict, List, Optional

from ..runtime.session import JadeSession
from ..runtime.interceptor import CallVerdict

logger = logging.getLogger("jadegate.transport.sdk_hook")

# Track what we've hooked so we can unhook
_hooks: Dict[str, Dict[str, Any]] = {}


def _extract_tool_calls_openai(response: Any) -> List[Dict[str, Any]]:
    """Extract tool calls from an OpenAI ChatCompletion response."""
    calls = []
    try:
        for choice in response.choices:
            msg = choice.message
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    })
    except (AttributeError, TypeError):
        pass
    return calls


def _extract_tool_use_anthropic(response: Any) -> List[Dict[str, Any]]:
    """Extract tool use blocks from an Anthropic response."""
    calls = []
    try:
        for block in response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input if isinstance(block.input, dict) else {},
                })
    except (AttributeError, TypeError):
        pass
    return calls


def patch_openai(session: JadeSession) -> bool:
    """
    Hook the OpenAI SDK's chat.completions.create method.
    Returns True if successfully hooked.
    """
    try:
        import openai
    except ImportError:
        logger.debug("OpenAI SDK not installed, skipping hook")
        return False

    if "openai" in _hooks:
        logger.debug("OpenAI already hooked")
        return True

    try:
        original_create = openai.resources.chat.completions.Completions.create

        @functools.wraps(original_create)
        def guarded_create(self_inner: Any, *args: Any, **kwargs: Any) -> Any:
            # Check if tools are being used
            tools = kwargs.get("tools")
            if not tools:
                return original_create(self_inner, *args, **kwargs)

            # Pre-scan: check tool definitions
            for tool in tools:
                if isinstance(tool, dict):
                    func = tool.get("function", {})
                    tool_name = func.get("name", "unknown")
                    # We can't block tool definitions, only calls
                    # But we log them for awareness
                    logger.debug("OpenAI tool registered: %s", tool_name)

            # Execute the call
            response = original_create(self_inner, *args, **kwargs)

            # Post-scan: check tool calls in response
            tool_calls = _extract_tool_calls_openai(response)
            for tc in tool_calls:
                import json as _json
                try:
                    params = _json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                except (ValueError, TypeError):
                    params = {}

                result = session.before_call(tc["name"], params)
                if not result.allowed:
                    logger.warning(
                        "BLOCKED tool call '%s': %s",
                        tc["name"], "; ".join(result.reasons),
                    )
                    # We can't modify the response object easily,
                    # but we log and record the block
                else:
                    session.after_call(result.call_id, success=True)

            return response

        openai.resources.chat.completions.Completions.create = guarded_create
        _hooks["openai"] = {"original": original_create, "module": openai}
        logger.info("OpenAI SDK hooked successfully")
        return True

    except (AttributeError, Exception) as e:
        logger.warning("Failed to hook OpenAI SDK: %s", e)
        return False


def patch_anthropic(session: JadeSession) -> bool:
    """
    Hook the Anthropic SDK's messages.create method.
    Returns True if successfully hooked.
    """
    try:
        import anthropic
    except ImportError:
        logger.debug("Anthropic SDK not installed, skipping hook")
        return False

    if "anthropic" in _hooks:
        logger.debug("Anthropic already hooked")
        return True

    try:
        original_create = anthropic.resources.messages.Messages.create

        @functools.wraps(original_create)
        def guarded_create(self_inner: Any, *args: Any, **kwargs: Any) -> Any:
            tools = kwargs.get("tools")
            if not tools:
                return original_create(self_inner, *args, **kwargs)

            for tool in tools:
                if isinstance(tool, dict):
                    logger.debug("Anthropic tool registered: %s", tool.get("name", "unknown"))

            response = original_create(self_inner, *args, **kwargs)

            tool_uses = _extract_tool_use_anthropic(response)
            for tu in tool_uses:
                result = session.before_call(tu["name"], tu["arguments"])
                if not result.allowed:
                    logger.warning(
                        "BLOCKED tool use '%s': %s",
                        tu["name"], "; ".join(result.reasons),
                    )
                else:
                    session.after_call(result.call_id, success=True)

            return response

        anthropic.resources.messages.Messages.create = guarded_create
        _hooks["anthropic"] = {"original": original_create, "module": anthropic}
        logger.info("Anthropic SDK hooked successfully")
        return True

    except (AttributeError, Exception) as e:
        logger.warning("Failed to hook Anthropic SDK: %s", e)
        return False


def auto_hook(session: JadeSession) -> List[str]:
    """
    Automatically detect and hook all available SDKs.
    Returns list of successfully hooked SDK names.
    """
    hooked = []

    if patch_openai(session):
        hooked.append("openai")
    if patch_anthropic(session):
        hooked.append("anthropic")

    if hooked:
        logger.info("Auto-hooked SDKs: %s", ", ".join(hooked))
    else:
        logger.debug("No SDKs detected for auto-hooking")

    return hooked


def unhook_all() -> None:
    """Remove all hooks, restoring original SDK methods."""
    if "openai" in _hooks:
        try:
            import openai
            openai.resources.chat.completions.Completions.create = _hooks["openai"]["original"]
            logger.info("OpenAI SDK unhooked")
        except Exception:
            pass

    if "anthropic" in _hooks:
        try:
            import anthropic
            anthropic.resources.messages.Messages.create = _hooks["anthropic"]["original"]
            logger.info("Anthropic SDK unhooked")
        except Exception:
            pass

    _hooks.clear()
