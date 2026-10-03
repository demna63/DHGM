"""TCP hub — DHGM plugin-ებისთვის JSON stream (მრავალი კლიენტი)."""

from __future__ import annotations

import queue
import socket
import sys
import threading
from typing import Callable, List, Optional


class _Client:
    """ერთი კლიენტი: bounded რიგი + საკუთარი writer thread.

    ``broadcast`` მხოლოდ რიგში დებს (არასოდეს ბლოკავს); ქსელური ``sendall`` writer
    thread-ზე ხდება → ჩეჭდილ კლიენტი სხვა კლიენტებს და bridge-ის main loop-ს (CoT-ს)
    ვეღარ აყოვნებს.
    """

    def __init__(self, sock: socket.socket, queue_max: int,
                 on_dead: Callable[["_Client"], None]):
        self.sock = sock
        self._q: "queue.Queue[Optional[bytes]]" = queue.Queue(maxsize=queue_max)
        self._on_dead = on_dead
        self._closed = threading.Event()
        self._thread = threading.Thread(target=self._write_loop, name="plugin-tcp-client",
                                        daemon=True)

    def start(self) -> None:
        self._thread.start()

    def offer(self, data: bytes) -> bool:
        """რიგში ჩადება; False — რიგი სავსეა (კლიენტი ვერ ასწრებს) ან დახურულია."""
        if self._closed.is_set():
            return False
        try:
            self._q.put_nowait(data)
            return True
        except queue.Full:
            return False

    def close(self) -> None:
        """idempotent; writer thread-ი სოკეტის დახურვით ან sentinel-ით სრულდება."""
        if self._closed.is_set():
            return
        self._closed.set()
        try:
            self.sock.close()
        except OSError:
            pass
        try:
            self._q.put_nowait(None)
        except queue.Full:
            pass  # writer-ი sendall-ზეა → დახურულ სოკეტზე OSError-ით გამოვა

    def _write_loop(self) -> None:
        while not self._closed.is_set():
            data = self._q.get()
            if data is None:
                return
            try:
                self.sock.sendall(data)
            except OSError:
                self._on_dead(self)
                return


class PluginTcpHub:
    """listen bind host:port; კლიენტებს ეგზავნება newline-terminated JSON."""

    #: sendall timeout (წმ) — ჩეჭდილ კლიენტი (ტელეფონი ძილში, Wi-Fi drop) timeout-ის
    #: შემდეგ dead-ია. sendall writer thread-ზეა → broadcast-ს არ ბლოკავს.
    DEFAULT_SEND_TIMEOUT_S = 0.5
    #: კლიენტის რიგის ზღვარი (ხაზები). 1 Hz × რამდენიმე დრონზე ეს რამდენიმე ათეული
    #: წამის ბუფერია; გადავსება = კლიენტი ვერ ასწრებს → მოიცილება (plugin reconnect-ს
    #: თავად აკეთებს და ახალ hello-ს იღებს).
    DEFAULT_QUEUE_MAX = 256

    def __init__(self, bind: str, send_timeout_s: float = DEFAULT_SEND_TIMEOUT_S,
                 hello_line: Optional[Callable[[], str]] = None,
                 queue_max: int = DEFAULT_QUEUE_MAX):
        """
        Args:
            bind: ``host:port``; ცარიელი host (``:14550``) → ``0.0.0.0`` (LAN — ტელეფონისთვის).
            send_timeout_s: sendall timeout; გადაჭარბება → კლიენტი მოიცილდება.
            hello_line: ``bridge_hello`` ხაზის provider — ეგზავნება **მხოლოდ ახალ**
                კლიენტს accept-ისთანავე (accept thread-ზე; thread-safe უნდა იყოს).
            queue_max: კლიენტის რიგის ზღვარი; გადავსება → კლიენტი მოიცილდება.
        """
        host, _, port_s = bind.rpartition(":")
        self._send_timeout_s = send_timeout_s
        self._hello_line = hello_line
        self._queue_max = max(1, queue_max)
        self._host = host or "0.0.0.0"
        self._port = int(port_s)
        self._lock = threading.Lock()
        self._clients: List[_Client] = []
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

    @property
    def port(self) -> int:
        """რეალური port (bind ``:0``-ზე OS-ის მიერ არჩეულ)."""
        return self._srv.getsockname()[1]

    @staticmethod
    def _encode(line: str) -> bytes:
        return (line if line.endswith("\n") else line + "\n").encode("utf-8")

    def _drop(self, client: _Client) -> None:
        with self._lock:
            if client in self._clients:
                self._clients.remove(client)
        client.close()

    def _accept_loop(self) -> None:
        self._srv.settimeout(1.0)
        while not self._stop.is_set():
            try:
                conn, _addr = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(self._send_timeout_s)
            except OSError:
                conn.close()
                continue
            client = _Client(conn, self._queue_max, self._drop)
            with self._lock:
                # hello რიგში პირველია და კლიენტი lock-ის ქვეშ ემატება → broadcast-ის
                # ხაზებ ყოველთვის hello-ს შემდეგ მიდის.
                if self._hello_line is not None:
                    try:
                        client.offer(self._encode(self._hello_line()))
                    except Exception as e:  # noqa: BLE001 — provider-ის შეცდომა accept-ს არ კლავს
                        print("[dhgm] hello_line failed: %s" % e, file=sys.stderr)
                        client.close()
                        continue
                self._clients.append(client)
            client.start()

    def broadcast(self, line: str) -> None:
        """არაბლოკირებადი: ხაზი თითო კლიენტის რიგში ჩადება; სავსე რიგი → კლიენტი მოიცილება."""
        data = self._encode(line)
        dead: List[_Client] = []
        with self._lock:
            for client in self._clients:
                if not client.offer(data):
                    dead.append(client)
            for client in dead:
                self._clients.remove(client)
        for client in dead:
            client.close()

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
            clients = list(self._clients)
            self._clients.clear()
        for client in clients:
            client.close()
