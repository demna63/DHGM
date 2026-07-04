"""TCP hub — DHGM plugin-ებისთვის JSON stream (მრავალი კლიენტი)."""

from __future__ import annotations

import socket
import threading
from typing import List, Optional, Tuple


class PluginTcpHub:
    """listen bind host:port; კლიენტებს ეგზავნება newline-terminated JSON."""

    def __init__(self, bind: str):
        host, _, port_s = bind.rpartition(":")
        self._host = host or "127.0.0.1"
        self._port = int(port_s)
        self._lock = threading.Lock()
        self._clients: List[socket.socket] = []
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((self._host, self._port))
        self._srv.listen(8)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._accept_loop, name="plugin-tcp", daemon=True)
        self._thread.start()

    @property
    def bind(self) -> str:
        return "%s:%d" % (self._host, self._port)

    def _accept_loop(self) -> None:
        self._srv.settimeout(1.0)
        while not self._stop.is_set():
            try:
                conn, _addr = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with self._lock:
                self._clients.append(conn)

    def broadcast(self, line: str) -> None:
        if not line.endswith("\n"):
            line += "\n"
        data = line.encode("utf-8")
        dead: List[socket.socket] = []
        with self._lock:
            for sock in self._clients:
                try:
                    sock.sendall(data)
                except OSError:
                    dead.append(sock)
            for sock in dead:
                self._clients.remove(sock)
                try:
                    sock.close()
                except OSError:
                    pass

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def close(self) -> None:
        self._stop.set()
        try:
            self._srv.close()
        except OSError:
            pass
        with self._lock:
            for sock in self._clients:
                try:
                    sock.close()
                except OSError:
                    pass
            self._clients.clear()
