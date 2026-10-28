#!/usr/bin/env python3
"""The CONNECT-only HTTPS allowlist proxy of one confined launch (F26 / T36b).

WHY THIS FILE EXISTS. The sandbox (`sandbox_v2.py`) confines the FILE SYSTEM, not the network.
In live pilot #5 a `curl https://github.com` inside the sandbox returned 200, and the governance
repository is public: its history holds every candidate fix, so a worker that builds a URL
dynamically can fetch the answer and the static access audit cannot see it (F16 class).

The driver therefore starts this proxy OUTSIDE the sandbox for every confined launch (worker,
auditor and each reachability probe), and the rendered profile allows the sandboxed processes to
reach exactly two network endpoints: their own loopback server and this proxy. The proxy accepts
CONNECT only, and only to `EGRESS_ALLOW` on port 443. Anything else is answered 403 and recorded.
Every request is appended to `<stream dir>/egress.jsonl` as one JSON line with its time, host,
port and ALLOW/DENY verdict; the launch's own stream directory is driver-held, so the sandboxed
process cannot rewrite that evidence. The proxy is stopped after the launch.

Nothing here is a claim about the content of an allowed connection: an allowed CONNECT is a tunnel
to the provider, and the experiment's answer-leak rule is the allowlist, not payload inspection.

F30 (live pilot #6): the timeout bounds the REQUEST LINE and the UPSTREAM CONNECT only. Once the
tunnel is established both sockets are set blocking, because a reasoning model can stay silent far
longer than `SOCKET_TIMEOUT` before its first byte; the old 30 s read timeout ended the relay and the
client reported `ECONNRESET`. The launch's own wall-clock limit now ends a tunnel, not this proxy.

The confinement self-test deliberately asks for a non-allowlisted CONNECT. That DENY is the
self-test's own evidence (`SELFTEST_LOG_NAME`), routed there by `EgressProxy.segment`, so a launch's
`egress.jsonl` never reports a denial the launch did not attempt.
"""
from __future__ import annotations

import contextlib
import json
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path

BIND_HOST = "127.0.0.1"
EGRESS_ALLOW = ("opencode.ai", "models.opencode.ai")
EGRESS_PORT = 443
LOG_NAME = "egress.jsonl"
SELFTEST_LOG_NAME = "egress-self-test.jsonl"
ALLOW = "ALLOW"
DENY = "DENY"
REQUEST_LIMIT = 65536
SOCKET_TIMEOUT = 30.0
RELAY_CHUNK = 65536
STATUS_OK = b"HTTP/1.1 200 Connection Established\r\n\r\n"
STATUS_FORBIDDEN = b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
STATUS_BAD_GATEWAY = b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_target(target: str) -> tuple[str, int | None]:
    """`host:port` (CONNECT) or an absolute `http://host:port/path` (a non-CONNECT request)."""
    text = target.strip()
    if "://" in text:
        text = text.split("://", 1)[1]
    text = text.split("/", 1)[0]
    if text.startswith("["):
        host, _, rest = text[1:].partition("]")
        return host, int(rest[1:]) if rest.startswith(":") and rest[1:].isdigit() else None
    if ":" in text:
        host, _, port = text.rpartition(":")
        if port.isdigit():
            return host, int(port)
    return text, None


def request_line(conn: socket.socket) -> str:
    """The first line of one proxy request; b"" when the peer connected and left (readiness)."""
    data = b""
    while b"\r\n" not in data and b"\n" not in data and len(data) < REQUEST_LIMIT:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
    return data.split(b"\n", 1)[0].decode("latin-1").strip()


def relay(source: socket.socket, target: socket.socket) -> None:
    try:
        while True:
            chunk = source.recv(RELAY_CHUNK)
            if not chunk:
                break
            target.sendall(chunk)
    except OSError:
        pass
    finally:
        try:
            target.shutdown(socket.SHUT_WR)
        except OSError:
            pass


class EgressProxy:
    """One launch's allowlist proxy; `start()` binds a free loopback port and serves in threads."""

    def __init__(self, stream_dir, *, allow=EGRESS_ALLOW, allow_port: int = EGRESS_PORT):
        self.stream_dir = Path(stream_dir)
        self.allow = tuple(allow)
        self.allow_port = int(allow_port)
        self.log_path = self.stream_dir / LOG_NAME
        self.port: int | None = None
        self._listener: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._log_target: Path | None = None
        self._closed = threading.Event()

    def start(self) -> "EgressProxy":
        self.stream_dir.mkdir(parents=True, exist_ok=True)
        # The evidence file exists for every launch, even when no request was made.
        self.log_path.touch(exist_ok=True)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((BIND_HOST, 0))
        listener.listen(64)
        listener.settimeout(0.2)
        self._listener = listener
        self.port = int(listener.getsockname()[1])
        self._thread = threading.Thread(target=self._serve, name="egress-proxy", daemon=True)
        self._thread.start()
        return self

    def env(self) -> dict[str, str]:
        """Both spellings of the proxy and the loopback bypass, for the sandboxed launch."""
        url = f"http://{BIND_HOST}:{self.port}"
        return {"HTTPS_PROXY": url, "https_proxy": url,
                "HTTP_PROXY": url, "http_proxy": url,
                "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}

    @contextlib.contextmanager
    def segment(self, log_path):
        """Route this proxy's entries to `log_path` for the duration of the block (F30).

        The confinement self-test runs against this same proxy port (the rendered profile allows
        only that port) and its deliberate non-allowlisted CONNECT is a DENY. That line belongs to
        the self-test's own evidence, not to the launch's `egress.jsonl`, which feeds
        `egress_denied`: otherwise every run reports an egress its worker never attempted.
        """
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        with self._lock:
            previous, self._log_target = self._log_target, path
        try:
            yield path
        finally:
            with self._lock:
                self._log_target = previous

    def stop(self) -> dict:
        self._closed.set()
        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=SOCKET_TIMEOUT)
        return {"port": self.port, "log": str(self.log_path)}

    def _serve(self) -> None:
        while not self._closed.is_set():
            listener = self._listener
            if listener is None:
                return
            try:
                conn, _ = listener.accept()
            except (OSError, TimeoutError):
                continue
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _record(self, host: str, port: int | None, verdict: str, method: str) -> None:
        line = {"at": now(), "host": host, "port": port, "verdict": verdict, "method": method}
        with self._lock:
            path = self._log_target or self.log_path
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, sort_keys=True) + "\n")

    def _deny(self, conn: socket.socket, host: str, port: int | None, method: str) -> None:
        self._record(host, port, DENY, method)
        try:
            conn.sendall(STATUS_FORBIDDEN)
        except OSError:
            pass
        conn.close()

    def _handle(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(SOCKET_TIMEOUT)
            line = request_line(conn)
            if not line:
                conn.close()
                return
            parts = line.split()
            method = parts[0].upper() if parts else ""
            target = parts[1] if len(parts) > 1 else ""
            host, port = parse_target(target)
            if method != "CONNECT":
                self._deny(conn, host, port, method or "UNKNOWN")
                return
            if host not in self.allow or port != self.allow_port:
                self._deny(conn, host, port, method)
                return
            try:
                upstream = socket.create_connection((host, port), timeout=SOCKET_TIMEOUT)
            except OSError:
                self._record(host, port, ALLOW, method)
                try:
                    conn.sendall(STATUS_BAD_GATEWAY)
                except OSError:
                    pass
                conn.close()
                return
            self._record(host, port, ALLOW, method)
            try:
                conn.sendall(STATUS_OK)
            except OSError:
                upstream.close()
                conn.close()
                return
            # F30: the tunnel is established; both sockets become blocking so a long upstream
            # silence (a reasoning model before its first token) does not end the relay. The
            # launch's own wall-clock limit is what ends a tunnel.
            for socket_ in (conn, upstream):
                try:
                    socket_.settimeout(None)
                except OSError:
                    pass
            forward = threading.Thread(target=relay, args=(conn, upstream), daemon=True)
            forward.start()
            relay(upstream, conn)
            forward.join(timeout=SOCKET_TIMEOUT)
            for socket_ in (conn, upstream):
                try:
                    socket_.close()
                except OSError:
                    pass
        except OSError:
            try:
                conn.close()
            except OSError:
                pass


def start(stream_dir, *, allow=EGRESS_ALLOW, allow_port: int = EGRESS_PORT) -> EgressProxy:
    """The one-call form the driver uses: a started proxy for this launch's stream directory."""
    return EgressProxy(stream_dir, allow=allow, allow_port=allow_port).start()


def denied(log_path) -> list[dict]:
    """The DENY lines of one launch's egress log: evidence, never a verdict by itself.

    F46 / T45: the log is JSONL, separated by "\n" only; a Unicode line boundary inside a recorded
    field never starts a new entry.
    """
    path = Path(log_path)
    if not path.is_file():
        return []
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("verdict") == DENY:
            entries.append(entry)
    return entries
