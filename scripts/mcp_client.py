"""Minimal MCP stdio client used by the non-blocking browser spike scripts.

Only the JSON-RPC subset needed for `initialize` + `tools/call` is implemented,
so the scripts work without adding the MCP SDK as a runtime dependency.
"""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
from collections.abc import Sequence
from typing import Any

MCP_PROTOCOL_VERSION = "2024-11-05"
STDERR_TAIL_LINES = 20


class MCPError(RuntimeError):
    """The MCP server failed, closed the pipe or timed out."""


def unwrap_result(value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"result"}:
        return unwrap_result(value["result"])
    return value


def parse_tool_payload(text: str) -> Any:
    """Parse the JSON emitted by `evaluate_script` (optionally fenced)."""
    candidates: list[str] = []
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence is not None:
        candidates.append(fence.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    candidates.append(text)
    for candidate in candidates:
        try:
            return unwrap_result(json.loads(candidate))
        except json.JSONDecodeError:
            continue
    return {"raw": text}


class MCPClient:
    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_sec: float = 90.0,
        env: dict[str, str] | None = None,
    ) -> None:
        merged_env = {**os.environ, **(env or {})}
        self._timeout_sec = timeout_sec
        self._process = subprocess.Popen(
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=merged_env,
        )
        if self._process.stdin is None or self._process.stdout is None:
            raise MCPError("failed to open MCP stdio pipes")
        self._messages: queue.Queue[dict[str, Any] | Exception] = queue.Queue()
        self._stderr_lines: list[str] = []
        self._next_id = 0
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def __enter__(self) -> MCPClient:
        self.initialize()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def initialize(self) -> dict[str, Any]:
        response = self._request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "lifeos-browser-spike", "version": "0.1.0"},
            },
        )
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        return response

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def call_tool_text(self, name: str, arguments: dict[str, Any]) -> str:
        result = self.call_tool(name, arguments)
        content = result.get("content", [])
        texts = [item.get("text", "") for item in content if item.get("type") == "text"]
        return "\n".join(text for text in texts if text)

    def close(self) -> None:
        process = self._process
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    @property
    def stderr_tail(self) -> str:
        return "\n".join(self._stderr_lines[-STDERR_TAIL_LINES:])

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._next_id += 1
        request_id = self._next_id
        self._send(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        deadline = time.monotonic() + self._timeout_sec
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPError(f"MCP timeout waiting for {method}")
            try:
                message = self._messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise MCPError(f"MCP timeout waiting for {method}") from exc
            if isinstance(message, Exception):
                raise MCPError(f"MCP server failed during {method}: {message}")
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise MCPError(f"MCP error for {method}: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise MCPError(f"MCP returned an invalid result for {method}")
            return result

    def _send(self, payload: dict[str, Any]) -> None:
        if self._process.stdin is None:
            raise MCPError("MCP stdin is closed")
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        try:
            self._process.stdin.write(line.encode("utf-8"))
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise MCPError(f"MCP stdin closed: {exc}") from exc

    def _read_stdout(self) -> None:
        stdout = self._process.stdout
        if stdout is None:
            return
        while True:
            try:
                line = stdout.readline()
            except (ValueError, OSError):
                self._messages.put(MCPError("MCP stdout closed"))
                return
            if not line:
                self._messages.put(MCPError("MCP server closed the pipe"))
                return
            if line.lower().startswith(b"content-length:"):
                try:
                    length = int(line.split(b":", 1)[1].strip())
                except ValueError:
                    continue
                body = stdout.read(length)
            else:
                body = line.strip()
            if not body:
                continue
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                self._messages.put(payload)

    def _read_stderr(self) -> None:
        stderr = self._process.stderr
        if stderr is None:
            return
        for raw_line in iter(stderr.readline, b""):
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if line:
                self._stderr_lines.append(line)
