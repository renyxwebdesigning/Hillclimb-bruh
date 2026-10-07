"""Networking for online play: one player hosts, the others join by address.

Plain TCP with one JSON object per line. Each connection has a reader and a
writer thread, so the game loop never waits on the network; received
messages are collected in a queue and handled once per frame.
"""
import json
import queue
import socket
import threading

PORT = 47777
VERSION = 2


class Conn:
    def __init__(self, sock, inbox, cid):
        self.sock, self.inbox, self.id = sock, inbox, cid
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        self.out = queue.Queue()
        self.alive = True
        self._closed_reported = False
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._write, daemon=True).start()

    def send(self, msg):
        if self.alive:
            self.out.put(json.dumps(msg, separators=(",", ":")).encode() + b"\n")

    def _read(self):
        buf = b""
        try:
            while self.alive:
                data = self.sock.recv(65536)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if line:
                        try:
                            self.inbox.put((self.id, json.loads(line)))
                        except ValueError:
                            pass
        except OSError:
            pass
        self._report_closed()

    def _write(self):
        try:
            while self.alive:
                data = self.out.get()
                if data is None:
                    break
                self.sock.sendall(data)
        except OSError:
            pass
        self._report_closed()

    def _report_closed(self):
        self.close()
        if not self._closed_reported:
            self._closed_reported = True
            self.inbox.put((self.id, {"t": "_closed"}))

    def close(self):
        if self.alive:
            self.alive = False
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
            self.out.put(None)


class Host:
    def __init__(self, port=PORT):
        self.inbox = queue.Queue()
        self.conns = {}
        self._next = 1
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind(("", port))
        self.lsock.listen(8)
        self.alive = True
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while self.alive:
            try:
                sock, addr = self.lsock.accept()
            except OSError:
                break
            cid = self._next
            self._next += 1
            self.conns[cid] = Conn(sock, self.inbox, cid)
            self.inbox.put((cid, {"t": "_open", "addr": addr[0]}))

    def send(self, cid, msg):
        c = self.conns.get(cid)
        if c:
            c.send(msg)

    def broadcast(self, msg, exclude=None):
        for cid, c in list(self.conns.items()):
            if cid != exclude:
                c.send(msg)

    def drop(self, cid):
        c = self.conns.pop(cid, None)
        if c:
            c.close()

    def poll(self):
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                return out

    def close(self):
        self.alive = False
        try:
            self.lsock.close()
        except OSError:
            pass
        for c in list(self.conns.values()):
            c.close()


class Client:
    def __init__(self, address, port=PORT, timeout=6.0):
        self.inbox = queue.Queue()
        sock = socket.create_connection((address, port), timeout=timeout)
        sock.settimeout(None)
        self.conn = Conn(sock, self.inbox, 0)

    def send(self, msg):
        self.conn.send(msg)

    def poll(self):
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                return out

    def close(self):
        self.conn.close()


def parse_address(text):
    """'1.2.3.4', '1.2.3.4:5000' or 'host.example:5000' -> (host, port)."""
    text = text.strip()
    if text.count(":") == 1:
        host, port = text.rsplit(":", 1)
        try:
            return host.strip(), int(port)
        except ValueError:
            return host.strip(), PORT
    return text, PORT


def local_addresses():
    addrs = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))        # no packet is sent; picks the LAN interface
        addrs.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addrs.add(info[4][0])
    except OSError:
        pass
    return sorted(a for a in addrs if not a.startswith("127."))


def fetch_public_ip(callback):
    """Look up the public internet address in the background (for inviting friends)."""
    def run():
        import urllib.request
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=4) as r:
                callback(r.read().decode().strip())
        except (OSError, ValueError):
            callback(None)
    threading.Thread(target=run, daemon=True).start()
