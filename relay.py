"""Internet play without IP addresses: a tiny MQTT client on free public brokers.

Every game connects to a public MQTT broker at start-up. Players are
addressed by their permanent player number:

  hr-rnx/v2/p/<num>     retained presence  {"name", "on"}  (offline via last will)
  hr-rnx/v2/i/<num>     inbox for invites
  hr-rnx/v2/r/<host>/h  room traffic to the host
  hr-rnx/v2/r/<host>/a  room traffic from the host to everybody

Only MQTT 3.1.1 with QoS 0 is needed, so the protocol is implemented here
directly (no extra package to install). Messages are JSON.
"""
import json
import queue
import socket
import struct
import threading
import time

BROKERS = [("broker.hivemq.com", 1883), ("broker.emqx.io", 1883), ("test.mosquitto.org", 1883)]
PREFIX = "hr-rnx/v2"
KEEPALIVE = 30


def _varint(n):
    out = bytearray()
    while True:
        b = n % 128
        n //= 128
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _str(s):
    b = s.encode()
    return struct.pack("!H", len(b)) + b


class MQTT:
    """Minimal MQTT 3.1.1 client (QoS 0) with automatic reconnects."""

    def __init__(self, client_id, will=None, on_connect=None):
        self.client_id = client_id
        self.will = will                 # (topic, payload bytes, retain)
        self.on_connect = on_connect
        self.inbox = queue.Queue()
        self.sock = None
        self.lock = threading.Lock()
        self.connected = False
        self.broker = None
        self.subs = set()
        self._stop = False
        self._mid = 1
        threading.Thread(target=self._run, daemon=True).start()

    # ------------------------------------------------------------- packets
    def _send(self, data):
        sock = self.sock
        if sock is None:
            return False
        try:
            with self.lock:
                sock.sendall(data)
            return True
        except OSError:
            self._drop()
            return False

    def publish(self, topic, payload, retain=False):
        body = _str(topic) + payload
        return self._send(bytes([0x30 | (1 if retain else 0)]) + _varint(len(body)) + body)

    def subscribe(self, topic):
        self.subs.add(topic)
        if self.connected:
            self._sub(topic)

    def unsubscribe(self, topic):
        self.subs.discard(topic)
        if self.connected:
            self._mid = self._mid % 60000 + 1
            body = struct.pack("!H", self._mid) + _str(topic)
            self._send(bytes([0xA2]) + _varint(len(body)) + body)

    def _sub(self, topic):
        self._mid = self._mid % 60000 + 1
        body = struct.pack("!H", self._mid) + _str(topic) + b"\x00"
        self._send(bytes([0x82]) + _varint(len(body)) + body)

    def _connect_packet(self):
        flags = 0x02                                   # clean session
        payload = _str(self.client_id)
        if self.will:
            topic, msg, retain = self.will
            flags |= 0x04 | (0x20 if retain else 0)
            payload += _str(topic) + struct.pack("!H", len(msg)) + msg
        var = _str("MQTT") + bytes([4, flags]) + struct.pack("!H", KEEPALIVE)
        body = var + payload
        return bytes([0x10]) + _varint(len(body)) + body

    # -------------------------------------------------------------- threads
    def _drop(self):
        self.connected = False
        sock, self.sock = self.sock, None
        if sock:
            try:
                sock.close()
            except OSError:
                pass

    def _recv_exact(self, sock, n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise OSError("closed")
            buf += chunk
        return buf

    def _read_packet(self, sock):
        head = self._recv_exact(sock, 1)[0]
        mult, length = 1, 0
        while True:
            b = self._recv_exact(sock, 1)[0]
            length += (b & 0x7F) * mult
            if not b & 0x80:
                break
            mult *= 128
        return head, self._recv_exact(sock, length) if length else b""

    def _run(self):
        delay = 1.0
        while not self._stop:
            for host, port in BROKERS:
                if self._stop:
                    return
                try:
                    sock = socket.create_connection((host, port), timeout=6)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    sock.sendall(self._connect_packet())
                    head, body = self._read_packet(sock)
                    if head >> 4 != 2 or len(body) < 2 or body[1] != 0:
                        raise OSError("refused")
                    sock.settimeout(KEEPALIVE + 15)
                except OSError:
                    continue
                self.sock, self.broker, self.connected = sock, host, True
                delay = 1.0
                for t in list(self.subs):
                    self._sub(t)
                if self.on_connect:
                    self.on_connect()
                pinger = threading.Thread(target=self._ping, args=(sock,), daemon=True)
                pinger.start()
                try:
                    while not self._stop and self.sock is sock:
                        head, body = self._read_packet(sock)
                        if head >> 4 == 3:
                            tlen = struct.unpack("!H", body[:2])[0]
                            topic = body[2:2 + tlen].decode(errors="replace")
                            off = 2 + tlen + (2 if head & 0x06 else 0)
                            try:
                                self.inbox.put((topic, json.loads(body[off:])))
                            except ValueError:
                                pass
                except (OSError, ValueError, struct.error):
                    pass
                self._drop()
                if self._stop:
                    return
            time.sleep(delay)
            delay = min(10.0, delay * 1.6)

    def _ping(self, sock):
        while not self._stop and self.sock is sock:
            time.sleep(KEEPALIVE / 2)
            if self.sock is sock:
                self._send(b"\xc0\x00")

    def poll(self):
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                return out

    def close(self):
        self._stop = True
        if self.sock:
            self._send(b"\xe0\x00")
        self._drop()


class Relay:
    """The game's permanent internet presence: player number, friends, invites, rooms."""

    def __init__(self, number, name):
        self.number = str(number)
        self.name = name
        self.presence = {}          # number -> {"name", "on", "host"}
        self.hosting = False
        self.leaderboard = {}       # stage -> number -> {"name", "best", "vehicle"}
        self.bests = {}             # our own records, re-published whenever we connect
        self.invites = []           # incoming invites
        self.rooms = {}             # host number -> callback list (room topic handlers)
        self._room_handlers = []
        will = (self._p(self.number), json.dumps({"name": name, "on": 0}).encode(), True)
        self.mqtt = MQTT(f"hr-{self.number}-{int(time.time()) % 100000}", will, self._announce)
        self.mqtt.subscribe(f"{PREFIX}/i/{self.number}")

    @staticmethod
    def _p(num):
        return f"{PREFIX}/p/{num}"

    @property
    def online(self):
        return self.mqtt.connected

    def _announce(self):
        msg = {"name": self.name, "on": 1, "host": int(self.hosting)}
        self.mqtt.publish(self._p(self.number), json.dumps(msg).encode(), retain=True)
        for stage, (best, vehicle) in list(self.bests.items()):
            self._publish_best(stage, best, vehicle)

    def _publish_best(self, stage, best, vehicle):
        msg = {"name": self.name, "best": int(best), "vehicle": vehicle}
        self.mqtt.publish(f"{PREFIX}/lb/{stage}/{self.number}", json.dumps(msg).encode(), retain=True)

    def post_best(self, stage, best, vehicle):
        """Put a record on the world leaderboard (kept by the broker as a retained message)."""
        self.bests[stage] = (best, vehicle)
        if self.online:
            self._publish_best(stage, best, vehicle)

    def watch_leaderboard(self):
        self.mqtt.subscribe(f"{PREFIX}/lb/+/+")

    def set_hosting(self, hosting):
        self.hosting = hosting
        if self.online:
            self._announce()

    def set_name(self, name):
        self.name = name
        self.mqtt.will = (self._p(self.number), json.dumps({"name": name, "on": 0}).encode(), True)
        if self.online:
            self._announce()

    def watch(self, number):
        self.mqtt.subscribe(self._p(number))

    def unwatch(self, number):
        self.mqtt.unsubscribe(self._p(number))

    def invite(self, number, room):
        msg = {"t": "invite", "from": self.number, "name": self.name, "room": room}
        return self.mqtt.publish(f"{PREFIX}/i/{number}", json.dumps(msg).encode())

    def add_room_handler(self, prefix, handler):
        self._room_handlers.append((prefix, handler))

    def remove_room_handler(self, handler):
        self._room_handlers = [(p, h) for p, h in self._room_handlers if h is not handler]

    def update(self):
        for topic, msg in self.mqtt.poll():
            if not isinstance(msg, dict):
                continue
            if topic.startswith(f"{PREFIX}/p/"):
                self.presence[topic.rsplit("/", 1)[1]] = msg
            elif topic.startswith(f"{PREFIX}/lb/"):
                parts = topic.split("/")
                if len(parts) >= 2 and isinstance(msg.get("best"), int) and 0 < msg["best"] < 30000:
                    self.leaderboard.setdefault(parts[-2], {})[parts[-1]] = msg
            elif topic == f"{PREFIX}/i/{self.number}":
                if msg.get("t") == "invite" and str(msg.get("from", "")).isdigit():
                    self.invites.append(msg)
            else:
                for prefix, handler in self._room_handlers:
                    if topic.startswith(prefix):
                        handler(topic, msg)

    def close(self):
        self.mqtt.publish(self._p(self.number), json.dumps({"name": self.name, "on": 0}).encode(), retain=True)
        time.sleep(0.05)
        self.mqtt.close()


class OfflineRelay:
    """Stand-in used in the browser version, where online play isn't possible."""

    online = False
    hosting = False

    def __init__(self, number, name):
        self.number, self.name = str(number), name
        self.presence, self.invites, self.leaderboard, self.bests = {}, [], {}, {}

    def __getattr__(self, name):          # set_name, watch, invite, post_best, update, close, ...
        return lambda *a, **k: None


class RoomHost:
    """Same interface as net.Host, but over the relay. Client ids are player numbers."""

    TIMEOUT = 9.0

    def __init__(self, relay):
        self.relay = relay
        self.room = relay.number
        self.base = f"{PREFIX}/r/{self.room}"
        self.queue = []
        self.seen = {}
        self._ping_t = 0.0
        relay.add_room_handler(self.base + "/h", self._on)
        relay.mqtt.subscribe(self.base + "/h")

    def _on(self, topic, msg):
        cid = str(msg.get("f", ""))
        if not cid.isdigit() or cid == self.relay.number:
            return
        cid = int(cid)
        if msg.get("t") == "bye":
            if cid in self.seen:
                del self.seen[cid]
                self.queue.append((cid, {"t": "_closed"}))
            return
        if cid not in self.seen and msg.get("t") != "hello":
            return
        self.seen[cid] = time.monotonic()
        if msg.get("t") != "ping":
            self.queue.append((cid, msg))

    def _pub(self, msg):
        self.relay.mqtt.publish(self.base + "/a", json.dumps(msg, separators=(",", ":")).encode())

    def send(self, cid, msg):
        self._pub(dict(msg, to=cid))

    def broadcast(self, msg, exclude=None):
        self._pub(dict(msg, x=exclude) if exclude is not None else msg)

    def drop(self, cid):
        self.seen.pop(cid, None)

    def poll(self):
        self.relay.update()
        now = time.monotonic()
        if now > self._ping_t:
            self._ping_t = now + 2.0
            self._pub({"t": "ping"})
        for cid, t in list(self.seen.items()):
            if now - t > self.TIMEOUT:
                del self.seen[cid]
                self.queue.append((cid, {"t": "_closed"}))
        out, self.queue = self.queue, []
        return out

    def close(self):
        self._pub({"t": "error", "text": "The host closed the game."})
        self.relay.remove_room_handler(self._on)
        self.relay.mqtt.unsubscribe(self.base + "/h")


class RoomClient:
    """Same interface as net.Client, over the relay."""

    TIMEOUT = 9.0

    def __init__(self, relay, room):
        self.relay = relay
        self.me = int(relay.number)
        self.base = f"{PREFIX}/r/{room}"
        self.queue = []
        self.last = time.monotonic()
        self._ping_t = 0.0
        self.closed = False
        relay.add_room_handler(self.base + "/a", self._on)
        relay.mqtt.subscribe(self.base + "/a")

    def _on(self, topic, msg):
        if msg.get("to") not in (None, self.me) or msg.get("x") == self.me:
            return
        self.last = time.monotonic()
        if msg.get("t") != "ping":
            msg.pop("to", None)
            msg.pop("x", None)
            self.queue.append((0, msg))

    def send(self, msg):
        msg = dict(msg, f=self.relay.number)
        self.relay.mqtt.publish(self.base + "/h", json.dumps(msg, separators=(",", ":")).encode())

    def poll(self):
        self.relay.update()
        now = time.monotonic()
        if now > self._ping_t:
            self._ping_t = now + 2.0
            self.send({"t": "ping"})
        if not self.closed and now - self.last > self.TIMEOUT:
            self.closed = True
            self.queue.append((0, {"t": "_closed"}))
        out, self.queue = self.queue, []
        return out

    def close(self):
        self.send({"t": "bye"})
        self.relay.remove_room_handler(self._on)
        self.relay.mqtt.unsubscribe(self.base + "/a")
