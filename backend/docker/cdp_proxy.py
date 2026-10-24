#!/usr/bin/env python3
"""Minimal CDP reverse proxy for the browser container.

Chrome >= 136 only listens on loopback and rejects non-local Host headers.
This proxy listens on 0.0.0.0:9222, forwards to 127.0.0.1:9223 with a local
Host header, and rewrites the JSON URLs so `--browserUrl http://market-browser:9222`
works from other containers (and from the host through the published port).
"""

from __future__ import annotations

import argparse
import contextlib
import socket
import socketserver
import threading

BUFFER_SIZE = 65536
SOCKET_TIMEOUT_SEC = 10
JSON_HOSTS = ("127.0.0.1", "localhost")

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 9222
UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 9223


def rewrite_urls(payload: bytes, upstream_port: int, public: str) -> bytes:
    """Replace upstream host:port occurrences inside a CDP JSON response."""
    text = payload
    for host in JSON_HOSTS:
        text = text.replace(f"{host}:{upstream_port}".encode(), public.encode())
    return text


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        request_line = self.rfile.readline(65536)
        if not request_line:
            return
        try:
            method, path, _version = request_line.decode("latin1").split(" ", 2)
        except ValueError:
            return
        headers = self._read_headers()
        original_host = _header(headers, "host") or f"127.0.0.1:{LISTEN_PORT}"
        body = self._read_body(headers)

        upstream = socket.create_connection(
            (UPSTREAM_HOST, UPSTREAM_PORT), timeout=SOCKET_TIMEOUT_SEC
        )
        upstream.settimeout(SOCKET_TIMEOUT_SEC)
        try:
            upstream.sendall(self._build_request(method, path, headers, body))
            head, rest = _read_head(upstream)
            if not head:
                return
            if b" 101 " in head.split(b"\r\n", 1)[0]:
                self.wfile.write(head + b"\r\n\r\n" + rest)
                self.wfile.flush()
                _pump_bidirectional(self.connection, upstream)
                return
            payload = _read_response_body(upstream, head, rest)
            self.wfile.write(self._build_response(head, payload, original_host))
            self.wfile.flush()
        finally:
            upstream.close()

    def _read_headers(self) -> list[tuple[str, str]]:
        headers: list[tuple[str, str]] = []
        for raw_line in iter(self.rfile.readline, b"\r\n"):
            if raw_line in (b"\r\n", b""):
                break
            name, _, value = raw_line.decode("latin1").partition(":")
            headers.append((name.strip(), value.strip()))
        return headers

    def _read_body(self, headers: list[tuple[str, str]]) -> bytes:
        length = _header(headers, "content-length")
        if length is None:
            return b""
        try:
            return self.rfile.read(int(length))
        except ValueError:
            return b""

    def _build_request(
        self, method: str, path: str, headers: list[tuple[str, str]], body: bytes
    ) -> bytes:
        upgrade = _header(headers, "upgrade") is not None
        lines = [f"{method} {path} HTTP/1.1", f"Host: {UPSTREAM_HOST}:{UPSTREAM_PORT}"]
        for name, value in headers:
            lowered = name.lower()
            if lowered in ("host", "proxy-connection", "connection", "content-length"):
                continue
            lines.append(f"{name}: {value}")
        lines.append("Connection: Upgrade" if upgrade else "Connection: close")
        if body:
            lines.append(f"Content-Length: {len(body)}")
        return ("\r\n".join(lines) + "\r\n\r\n").encode("latin1") + body

    def _build_response(self, head: bytes, payload: bytes, original_host: str) -> bytes:
        lines = head.split(b"\r\n")
        status_line = lines[0]
        content_type = b""
        for line in lines[1:]:
            if line.lower().startswith(b"content-type:"):
                content_type = line.split(b":", 1)[1].strip().lower()
        if b"json" in content_type:
            payload = rewrite_urls(payload, UPSTREAM_PORT, original_host)
        rebuilt = [status_line, b"Connection: close", f"Content-Length: {len(payload)}".encode()]
        rebuilt.extend(
            line
            for line in lines[1:]
            if line
            and not line.lower().startswith(b"content-length:")
            and not line.lower().startswith(b"connection:")
            and not line.lower().startswith(b"transfer-encoding:")
        )
        return b"\r\n".join(rebuilt) + b"\r\n\r\n" + payload


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request: object, client_address: object) -> None:
        return


def _header(headers: list[tuple[str, str]], name: str) -> str | None:
    for header_name, value in headers:
        if header_name.lower() == name:
            return value
    return None


def _read_head(sock: socket.socket) -> tuple[bytes, bytes]:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            return b"", b""
        data += chunk
    head, _, rest = data.partition(b"\r\n\r\n")
    return head, rest


def _read_response_body(sock: socket.socket, head: bytes, rest: bytes) -> bytes:
    lowered = head.lower()
    if b"transfer-encoding: chunked" in lowered:
        return _read_chunked(sock, rest)
    length = _content_length(head)
    if length is None:
        return rest + _read_all(sock)
    body = rest
    while len(body) < length:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            break
        body += chunk
    return body[:length]


def _content_length(head: bytes) -> int | None:
    for line in head.split(b"\r\n")[1:]:
        if line.lower().startswith(b"content-length:"):
            try:
                return int(line.split(b":", 1)[1].strip())
            except ValueError:
                return None
    return None


def _read_chunked(sock: socket.socket, rest: bytes) -> bytes:
    data = rest
    body = b""
    while True:
        while b"\r\n" not in data:
            data += sock.recv(BUFFER_SIZE)
        line, _, data = data.partition(b"\r\n")
        size = int(line.split(b";", 1)[0], 16)
        if size == 0:
            return body
        while len(data) < size + 2:
            data += sock.recv(BUFFER_SIZE)
        body += data[:size]
        data = data[size + 2 :]


def _read_all(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _pump(source: socket.socket, target: socket.socket) -> None:
    try:
        while True:
            data = source.recv(BUFFER_SIZE)
            if not data:
                return
            target.sendall(data)
    except OSError:
        return
    finally:
        with contextlib.suppress(OSError):
            target.shutdown(socket.SHUT_WR)


def _pump_bidirectional(client: socket.socket, upstream: socket.socket) -> None:
    forward = threading.Thread(target=_pump, args=(client, upstream), daemon=True)
    backward = threading.Thread(target=_pump, args=(upstream, client), daemon=True)
    forward.start()
    backward.start()
    forward.join()
    backward.join()


def main() -> int:
    global LISTEN_PORT, UPSTREAM_HOST, UPSTREAM_PORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen-host", default=LISTEN_HOST)
    parser.add_argument("--listen-port", type=int, default=LISTEN_PORT)
    parser.add_argument("--upstream-host", default=UPSTREAM_HOST)
    parser.add_argument("--upstream-port", type=int, default=UPSTREAM_PORT)
    args = parser.parse_args()

    LISTEN_PORT, UPSTREAM_HOST, UPSTREAM_PORT = (
        args.listen_port,
        args.upstream_host,
        args.upstream_port,
    )
    with _Server((args.listen_host, args.listen_port), _Handler) as server:
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
