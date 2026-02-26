"""
JadeGate MCP Proxy — Transparent MCP stdio/SSE proxy with tool call interception.

Sits between an MCP client and server, intercepting JSON-RPC messages:
- tools/list: annotates tools with security profiles
- tools/call: validates calls through the interceptor before forwarding
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional

from .base import JadeTransport
from ..runtime.interceptor import ToolCallInterceptor, CallVerdict, InterceptResult

logger = logging.getLogger(__name__)


class JadeMCPProxy(JadeTransport):
    """
    MCP stdio transparent proxy.

    Reads JSON-RPC from stdin, intercepts tools/call and tools/list,
    forwards allowed calls to the upstream MCP server process.
    """

    def __init__(self, interceptor: ToolCallInterceptor,
                 upstream_command: Optional[List[str]] = None):
        """
        Args:
            interceptor: The tool call interceptor.
            upstream_command: Command to start the upstream MCP server
                             (e.g., ["npx", "-y", "@modelcontextprotocol/server-filesystem"]).
        """
        super().__init__(interceptor)
        self.upstream_command = upstream_command
        self._upstream_process: Optional[subprocess.Popen] = None
        self._running = False
        self._tool_profiles: Dict[str, Dict[str, Any]] = {}

    def start(self) -> None:
        """Start the proxy and upstream MCP server."""
        if self.upstream_command:
            self._upstream_process = subprocess.Popen(
                self.upstream_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info("Started upstream MCP server: %s", " ".join(self.upstream_command))
        self._running = True
        logger.info("JadeMCPProxy started")

    def stop(self) -> None:
        """Stop the proxy and upstream server."""
        self._running = False
        if self._upstream_process:
            self._upstream_process.terminate()
            try:
                self._upstream_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._upstream_process.kill()
            self._upstream_process = None
        logger.info("JadeMCPProxy stopped")

    def is_running(self) -> bool:
        return self._running

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a single JSON-RPC message.

        Args:
            message: Parsed JSON-RPC message dict.

        Returns:
            Response dict to send back to the client.
        """
        method = message.get("method", "")
        msg_id = message.get("id")

        if method == "tools/list":
            return self._handle_tools_list(message, msg_id)
        elif method == "tools/call":
            return self._handle_tools_call(message, msg_id)
        else:
            # Pass through non-tool messages
            return self._forward_to_upstream(message)

    def _handle_tools_list(self, message: Dict[str, Any],
                           msg_id: Any) -> Dict[str, Any]:
        """Handle tools/list — forward and annotate with security profiles."""
        upstream_response = self._forward_to_upstream(message)

        # Annotate tools with security info
        if "result" in upstream_response and "tools" in upstream_response["result"]:
            tools = upstream_response["result"]["tools"]
            for tool in tools:
                tool_name = tool.get("name", "")
                profile = self._generate_tool_profile(tool)
                tool["jade_security"] = profile
                self._tool_profiles[tool_name] = profile

        return upstream_response

    def _handle_tools_call(self, message: Dict[str, Any],
                           msg_id: Any) -> Dict[str, Any]:
        """Handle tools/call — intercept, validate, then forward or reject."""
        params = message.get("params", {})
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        # Run interception
        result = self.intercept_call(tool_name, tool_args)

        if result.verdict == CallVerdict.DENY:
            logger.warning("Tool call DENIED: %s — %s", tool_name, result.reason)
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32600,
                    "message": f"JadeGate: call denied — {result.reason}",
                    "data": result.to_dict(),
                },
            }
            self.report_result(tool_name, tool_args, success=False, error=result.reason)
            return response

        if result.verdict == CallVerdict.NEED_APPROVAL:
            logger.info("Tool call NEEDS APPROVAL: %s", tool_name)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32001,
                    "message": f"JadeGate: human approval required for '{tool_name}'",
                    "data": result.to_dict(),
                },
            }

        # ALLOW — forward to upstream
        upstream_response = self._forward_to_upstream(message)

        # Report result
        success = "error" not in upstream_response
        error_msg = None
        if not success:
            error_msg = upstream_response.get("error", {}).get("message", "unknown error")
        self.report_result(tool_name, tool_args, result=upstream_response.get("result"),
                           success=success, error=error_msg)

        return upstream_response

    def _forward_to_upstream(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Forward a message to the upstream MCP server via stdio."""
        if not self._upstream_process or not self._upstream_process.stdin or not self._upstream_process.stdout:
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32603,
                    "message": "No upstream MCP server connected",
                },
            }

        try:
            msg_bytes = (json.dumps(message) + "\n").encode("utf-8")
            self._upstream_process.stdin.write(msg_bytes)
            self._upstream_process.stdin.flush()

            line = self._upstream_process.stdout.readline()
            if not line:
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {"code": -32603, "message": "Upstream server closed"},
                }
            return json.loads(line.decode("utf-8"))
        except Exception as e:
            logger.error("Upstream communication error: %s", e)
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {"code": -32603, "message": f"Upstream error: {e}"},
            }

    def _generate_tool_profile(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a security profile for a tool based on its schema."""
        name = tool.get("name", "")
        desc = tool.get("description", "").lower()
        schema = tool.get("inputSchema", {})

        risk_level = "low"
        capabilities: List[str] = []

        # Heuristic risk assessment based on name and description
        if any(kw in name.lower() or kw in desc for kw in
               ["exec", "shell", "command", "run", "execute"]):
            risk_level = "critical"
            capabilities.append("code_execution")
        if any(kw in name.lower() or kw in desc for kw in
               ["write", "create", "delete", "modify", "update"]):
            risk_level = max(risk_level, "medium", key=lambda x: ["low", "medium", "high", "critical"].index(x))
            capabilities.append("filesystem_write")
        if any(kw in name.lower() or kw in desc for kw in
               ["read", "get", "list", "search", "find"]):
            capabilities.append("filesystem_read")
        if any(kw in name.lower() or kw in desc for kw in
               ["http", "fetch", "request", "api", "url", "network"]):
            risk_level = max(risk_level, "medium", key=lambda x: ["low", "medium", "high", "critical"].index(x))
            capabilities.append("network_access")

        return {
            "tool_name": name,
            "risk_level": risk_level,
            "capabilities": capabilities,
            "jade_verified": name in self._tool_profiles,
        }

    def process_stdin_loop(self) -> None:
        """
        Main loop: read JSON-RPC from stdin, process, write to stdout.
        Used when running as a standalone proxy process.
        """
        logger.info("Starting stdin processing loop")
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                message = json.loads(line.strip())
                response = self.handle_message(message)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON from stdin: %s", e)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("Error in stdin loop: %s", e)
        self.stop()
