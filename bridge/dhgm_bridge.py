#!/usr/bin/env python3
"""DHGM Bridge — DroneHub GCS (MAVLink) → ATAK (Cursor-on-Target).

უსმენს DroneHub GCS-ის MAVLink forwarding-ს (Settings → MAVLink →
"Enable MAVLink forwarding", default localhost:14445) და თითოეული დრონისთვის
აგზავნის CoT event-ებს ATAK-ის mesh SA multicast-ზე (239.2.3.1:6969) —
პოზიცია, სიმაღლე, კურსი, სიჩქარე, ბატარეა.

გამოყენება:
    python3 dhgm_bridge.py                        # GCS → ATAK, defaults
    python3 dhgm_bridge.py --sim                  # სიმულირებული დრონი თბილისზე
    python3 dhgm_bridge.py --sim --dry-run        # CoT stdout-ზე, ქსელის გარეშე
    python3 dhgm_bridge.py --cot-udp 192.168.1.50:4242   # unicast კონკრეტულ ტაბლეტზე
    python3 dhgm_bridge.py --sim --plugin-tcp 127.0.0.1:14550   # plugin JSON stream
"""

import argparse
import math
import os
import re
import struct
import socket
import sys
import threading
import time
from typing import Callable, Dict, List, Optional, Set
from xml.sax.saxutils import quoteattr, escape

DEFAULT_MAVLINK = "0.0.0.0:14445"       # QGC forwardMavlinkHostName default პორტი
DEFAULT_MULTICAST = "239.2.3.1:6969"    # ATAK mesh SA default
COT_TYPE_UAV = "a-f-A-M-F-Q"            # friendly / air / military / fixed+rotary UAV/drone
UINT16_MAX = 65535
HAE_UNKNOWN = 9999999.0                   # CoT სპეკი: უცნობი სიმაღლე
GEOID_SEP_MAX_M = 120.0                   # |N| EGM96-ში ≤ ~107 მ — sanity გარდა
MAV_AUTOPILOT_INVALID = 8                 # gimbal/camera/companion — რეჟიმს არ ფლობს

# სიმულაციის საწყისი წერტილი — თბილისი
SIM_CENTER_LAT = 41.7151
SIM_CENTER_LON = 44.8271


class DroneState:
    """ერთი დრონის (MAVLink system id) ბოლო ცნობილი მდგომარეობა."""

    def __init__(self, sysid: int):
        self.sysid = sysid
        self.lat: Optional[float] = None      # გრადუსი
        self.lon: Optional[float] = None      # გრადუსი
        self.alt_msl: Optional[float] = None  # მ (MSL; CoT hae-სთვის მიახლოება)
        self.alt_rel: Optional[float] = None  # მ AGL
        # geoid separation N = HAE − MSL (მ), GPS_RAW_INT.alt_ellipsoid − alt-იდან.
        self.geoid_sep: Optional[float] = None
        self.vx = 0.0                         # მ/წმ ჩრდილოეთით
        self.vy = 0.0                         # მ/წმ აღმოსავლეთით
        self.heading: Optional[float] = None  # გრადუსი
        self.groundspeed: Optional[float] = None  # მ/წმ
        self.battery_pct: Optional[int] = None
        self.flight_mode: str = "UNKNOWN"
        self.gps_fix: str = "UNKNOWN"
        self.satellites: Optional[int] = None
        self.rssi_dbm: Optional[int] = None
        self.last_seen = 0.0

    @property
    def has_fix(self) -> bool:
        return self.lat is not None and self.lon is not None

    @property
    def course(self) -> float:
        """კურსი გრადუსებში — heading ან, თუ არაა, სიჩქარის ვექტორიდან."""
        if self.heading is not None:
            return self.heading
        if abs(self.vx) > 0.1 or abs(self.vy) > 0.1:
            return (math.degrees(math.atan2(self.vy, self.vx)) + 360.0) % 360.0
        return 0.0

    @property
    def hae(self) -> float:
        """CoT ``hae`` — ellipsoid სიმაღლე (WGS84).

        MSL + N, თუ N GPS-იდან ცნობილია; თორემ MSL (fallback, ~±25 მ საქართველოში);
        სიმაღლის გარეშე — CoT-ის ``9999999`` (unknown).
        """
        if self.alt_msl is None:
            return HAE_UNKNOWN
        if self.geoid_sep is not None:
            return self.alt_msl + self.geoid_sep
        return self.alt_msl

    @property
    def speed(self) -> float:
        if self.groundspeed is not None:
            return self.groundspeed
        return math.hypot(self.vx, self.vy)


def _cot_time(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + (".%02dZ" % int((t % 1) * 100))


#: CoT-ის <detail>-ში bridge-ის instance-ის ტეგი — იგივე multicast-ზე მეორე წყარო
#: (GCS CotForwarder / მეორე bridge) იგივე uid-ით ამ ტეგის გარეშე ჩანს.
SOURCE_TAG = "__dhgm_source"
_UID_RE = re.compile(rb'uid="DHGM\.(\d+)"')


def cot_event(state: DroneState, now: float, stale_s: float, prefix: str = "DH",
              instance: Optional[str] = None) -> bytes:
    """აწყობს CoT 2.0 event XML-ს ერთი დრონისთვის.

    ``instance`` — ამ bridge-ის id; ``<__dhgm_source instance=…/>``-ად ჩაიდება, რომ
    :func:`foreign_dhgm_sysid` სკოპ multicast-ზე ჩვენ/სხვის event-ებს გაარჩიოს
    (ATAK უცნობ detail-ებს იგნორირავს).
    """
    callsign = "%s-%d" % (prefix, state.sysid)
    uid = "DHGM.%d" % state.sysid
    hae = state.hae
    le = 10.0 if hae != HAE_UNKNOWN else HAE_UNKNOWN
    remarks_parts = []
    if state.alt_rel is not None:
        remarks_parts.append("ALT %.0f m AGL" % state.alt_rel)
    remarks_parts.append("SPD %.1f m/s" % state.speed)
    if state.battery_pct is not None and state.battery_pct >= 0:
        remarks_parts.append("BAT %d%%" % state.battery_pct)
    remarks = " | ".join(remarks_parts)

    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<event version="2.0" uid=%s type="%s" how="m-g" time="%s" start="%s" stale="%s">'
        '<point lat="%.7f" lon="%.7f" hae="%.1f" ce="10.0" le="%.1f"/>'
        "<detail>"
        "<contact callsign=%s/>"
        '<track speed="%.2f" course="%.1f"/>'
        '<precisionlocation geopointsrc="GPS" altsrc="GPS"/>'
        "<remarks>%s</remarks>"
        "%s"
        "</detail>"
        "</event>"
    ) % (
        quoteattr(uid),
        COT_TYPE_UAV,
        _cot_time(now),
        _cot_time(now),
        _cot_time(now + stale_s),
        state.lat,
        state.lon,
        hae,
        le,
        quoteattr(callsign),
        state.speed,
        state.course,
        escape(remarks),
        ("<%s instance=%s/>" % (SOURCE_TAG, quoteattr(instance))) if instance else "",
    )
    return xml.encode("utf-8")


class CotSender:
    """CoT პაკეტების გაგზავნა multicast/unicast UDP-ზე."""

    def __init__(self, targets: List[str], dry_run: bool = False):
        self.dry_run = dry_run
        self.targets = []
        for t in targets:
            host, _, port = t.rpartition(":")
            self.targets.append((host, int(port)))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

    def send(self, payload: bytes) -> None:
        if self.dry_run:
            print(payload.decode("utf-8"))
            return
        for host, port in self.targets:
            try:
                self.sock.sendto(payload, (host, port))
            except OSError as e:
                print("[dhgm] გაგზავნა ვერ მოხერხდა %s:%d — %s" % (host, port, e), file=sys.stderr)


def handle_mavlink_msg(states: Dict[int, DroneState], msg, now: float,
                       mode_string: Callable[[object], str]) -> None:
    """ერთი MAVLink შეტყობინების ასახვა დრონის state-ზე (pure — ტესტირებადი).

    caller-ი lock-ს ფლობს (states-ს main loop-იც კითხულობს).

    Args:
        states: sysid → DroneState.
        msg: pymavlink message (ან duck-typed stub ტესტებში).
        now: epoch წმ.
        mode_string: HEARTBEAT → რეჟიმის სახელი (``mavutil.mode_string_v10``).
    """
    sysid = msg.get_srcSystem()
    if sysid == 0 or sysid >= 250:  # GCS/broadcast id-ები გამოვტოვოთ
        return
    t = msg.get_type()
    if t not in ("GLOBAL_POSITION_INT", "VFR_HUD", "SYS_STATUS", "GPS_RAW_INT", "HEARTBEAT"):
        return
    st = states.get(sysid)
    if st is None:
        st = DroneState(sysid)
        states[sysid] = st
    if t == "GLOBAL_POSITION_INT":
        # PX4/ArduPilot fix-ის გარეშე lat=lon=0 აგზავნის → Null Island-ზე მარკერი.
        if msg.lat == 0 and msg.lon == 0:
            return
        st.lat = msg.lat / 1e7
        st.lon = msg.lon / 1e7
        st.alt_msl = msg.alt / 1000.0
        st.alt_rel = msg.relative_alt / 1000.0
        st.vx = msg.vx / 100.0
        st.vy = msg.vy / 100.0
        st.heading = None if msg.hdg == UINT16_MAX else msg.hdg / 100.0
        st.last_seen = now
    elif t == "VFR_HUD":
        st.groundspeed = msg.groundspeed
        st.last_seen = now
    elif t == "SYS_STATUS":
        st.battery_pct = msg.battery_remaining
    elif t == "GPS_RAW_INT":
        from plugin_json import gps_fix_name
        st.gps_fix = gps_fix_name(msg.fix_type)
        st.satellites = msg.satellites_visible
        # MAVLink2 extension; 0 = არ არის. N = HAE − MSL ერთი და იგივე GPS-იდან.
        alt_ellipsoid = getattr(msg, "alt_ellipsoid", 0) or 0
        if msg.fix_type >= 3 and alt_ellipsoid != 0:
            sep = (alt_ellipsoid - msg.alt) / 1000.0
            if abs(sep) <= GEOID_SEP_MAX_M:
                st.geoid_sep = sep
        st.last_seen = now
    elif t == "HEARTBEAT":
        # იგივე sysid-ის gimbal/camera component-ის HEARTBEAT რეჟიმს არ გადააწერს.
        if msg.autopilot == MAV_AUTOPILOT_INVALID:
            return
        st.last_seen = now
        try:
            st.flight_mode = mode_string(msg)
        except Exception:  # noqa: BLE001 — უცნობი autopilot/type კომბინაცია
            st.flight_mode = str(msg.custom_mode)


def mavlink_loop(conn_str: str, states: Dict[int, DroneState], lock: threading.Lock) -> None:
    """კითხულობს MAVLink ნაკადს და ანახლებს დრონების მდგომარეობას (daemon thread)."""
    from pymavlink import mavutil  # lazy import — --sim რეჟიმს არ სჭირდება

    conn = mavutil.mavlink_connection("udpin:" + conn_str, source_system=250)
    print("[dhgm] ველოდები MAVLink-ს udpin:%s (GCS → Settings → MAVLink → forwarding)" % conn_str)
    while True:
        msg = conn.recv_match(blocking=True, timeout=1.0)
        if msg is None or msg.get_type() == "BAD_DATA":
            continue
        with lock:
            handle_mavlink_msg(states, msg, time.time(), mavutil.mode_string_v10)


def snapshot_states(states: Dict[int, DroneState], lock: threading.Lock) -> List[DroneState]:
    """states-ის thread-safe snapshot (MAVLink thread-ი პარალელურად ამატებს sysid-ებს)."""
    with lock:
        return list(states.values())


def sim_step(st: DroneState, t0: float, index: int = 0) -> None:
    """სიმულირებული დრონი — წრე თბილისის ცენტრზე. index-ით რამდენიმე დრონი
    სხვადასხვა რადიუსზე/ფაზაზე/სიჩქარეზე იშლება (--sim-drones N)."""
    elapsed = time.time() - t0
    radius_m = 400.0 + index * 250.0            # თითო დრონი უფრო დიდ წრეზე
    speed = 12.0 + index * 4.0                  # განსხვავებული სიჩქარე
    phase = index * (2.0 * math.pi / 3.0)       # ფაზის წანაცვლება
    omega = speed / radius_m
    ang = omega * elapsed + phase
    st.lat = SIM_CENTER_LAT + (radius_m / 111320.0) * math.sin(ang)
    st.lon = SIM_CENTER_LON + (radius_m / (111320.0 * math.cos(math.radians(SIM_CENTER_LAT)))) * math.cos(ang)
    st.alt_rel = 100.0 + index * 40.0
    st.alt_msl = st.alt_rel + 450.0             # თბილისის სავარაუდო რელიეფი
    st.groundspeed = speed
    st.heading = (math.degrees(ang) + 90.0) % 360.0
    st.battery_pct = max(0, 100 - index * 7 - int(elapsed / 30))
    st.flight_mode = "AUTO"
    st.gps_fix = "3D"
    st.satellites = 12 - index
    st.last_seen = time.time()


def foreign_dhgm_sysid(datagram: bytes, instance: str) -> Optional[int]:
    """DHGM.<sysid> CoT, რომელიც **ამ** bridge-ის instance-ის ტეგის გარეშეა → sysid; სხვა → None.

    pure — ტესტირებადი; ``datagram`` multicast-იდან მიღებულ ნედლ ბაიტებია.
    """
    m = _UID_RE.search(datagram)
    if m is None:
        return None
    own = ("<%s instance=%s/>" % (SOURCE_TAG, quoteattr(instance))).encode("utf-8")
    if own in datagram:
        return None
    return int(m.group(1))


class ForeignSourceMonitor:
    """multicast-ზე იგივე ``DHGM.<sysid>`` uid-ის მეორე CoT წყაროს აღმოჩენა.

    GCS-ის native CotForwarder + Python bridge ერთდროულად → ATAK-ში ერთ მარკერი
    ორ წყაროს შორის „ხტუნავს". monitor-ი stderr-ზე გაფრთხილებას ბეჭდავს (sysid-ზე
    ≤ 1/60 წმ). best-effort: bind ვერ მოხერხდა → ჩუმად გამოირთვება.
    """

    WARN_INTERVAL_S = 60.0

    def __init__(self, group: str, port: int, instance: str,
                 active_sysids: Callable[[], Set[int]]):
        self._instance = instance
        self._active = active_sysids
        self._last_warn: Dict[int, float] = {}
        self._sock: Optional[socket.socket] = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError:
                    pass
            s.bind(("", port))
            mreq = struct.pack("4s4s", socket.inet_aton(group), socket.inet_aton("0.0.0.0"))
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            s.settimeout(1.0)
            self._sock = s
        except OSError as e:
            print("[dhgm] (info) duplicate-source monitor off: %s" % e, file=sys.stderr)
            return
        threading.Thread(target=self._loop, name="cot-monitor", daemon=True).start()

    def _loop(self) -> None:
        assert self._sock is not None
        while True:
            try:
                data, addr = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                return
            sysid = foreign_dhgm_sysid(data, self._instance)
            if sysid is None or sysid not in self._active():
                continue
            now = time.time()
            if now - self._last_warn.get(sysid, 0.0) >= self.WARN_INTERVAL_S:
                self._last_warn[sysid] = now
                print("[dhgm] ⚠ DHGM.%d-ს სხვა წყაროც აგზავნის (%s) — ATAK-ში მარკერი ორ "
                      "წყაროს შორის ხტუნავს. დატოვე ერთი: GCS-ის „DHGM-ზე გადაცემა“ ან "
                      "ეს bridge." % (sysid, addr[0]), file=sys.stderr)


def _lan_ipv4s() -> List[str]:
    """ლოკალურ LAN IPv4-ებ (hint-ისთვის; ქსელ ტრაფიკ არ იგზავნება — UDP connect)."""
    ips: List[str] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            ips.append(s.getsockname()[0])
        finally:
            s.close()
    except OSError:
        pass
    return [ip for ip in ips if not ip.startswith("127.")]


def main() -> int:
    p = argparse.ArgumentParser(description="DHGM Bridge: DroneHub GCS (MAVLink) → ATAK (CoT)")
    p.add_argument("--mavlink", default=DEFAULT_MAVLINK, metavar="HOST:PORT",
                   help="MAVLink UDP listen (default: %(default)s — QGC forwarding default)")
    p.add_argument("--cot-udp", action="append", default=[], metavar="HOST:PORT",
                   help="დამატებითი unicast CoT მიმღები (მაგ. ტაბლეტის IP:4242); მეორდება")
    p.add_argument("--no-multicast", action="store_true",
                   help="არ გააგზავნო %s multicast-ზე" % DEFAULT_MULTICAST)
    p.add_argument("--rate", type=float, default=1.0, help="CoT სიხშირე Hz (default: 1)")
    p.add_argument("--stale", type=float, default=10.0, help="CoT stale ფანჯარა წმ (default: 10)")
    p.add_argument("--prefix", default="DH", help="callsign პრეფიქსი (default: DH)")
    p.add_argument("--sim", action="store_true", help="სიმულირებული დრონი MAVLink-ის გარეშე")
    p.add_argument("--sim-drones", type=int, default=1, metavar="N",
                   help="სიმულირებული დრონების რაოდენობა (default: 1)")
    p.add_argument("--dry-run", action="store_true", help="CoT stdout-ზე, გაგზავნის გარეშე")
    p.add_argument("--plugin-tcp", default="", metavar="HOST:PORT",
                   help="DHGM plugin-ისთვის TCP JSON stream (მაგ. 127.0.0.1:14550)")
    p.add_argument("--max-ticks", type=int, default=0, help="გაჩერდი N tick-ის შემდეგ (ტესტისთვის)")
    args = p.parse_args()

    targets = list(args.cot_udp)
    if not args.no_multicast:
        targets.insert(0, DEFAULT_MULTICAST)
    sender = CotSender(targets, dry_run=args.dry_run)
    instance = "%s-%d-%d" % (socket.gethostname(), os.getpid(), int(time.time()))
    states: Dict[int, DroneState] = {}
    states_lock = threading.Lock()
    t0 = time.time()
    from plugin_json import (bridge_heartbeat_line, bridge_hello_line, drone_gone_line,
                             telemetry_line)

    active_sysids: Set[int] = set()
    if not args.dry_run and not args.no_multicast:
        group, _, mport = DEFAULT_MULTICAST.rpartition(":")
        # active_sysids — reference-ი tick-ზე ატომურად იცვლება (იხ. hello_line)
        ForeignSourceMonitor(group, int(mport), instance, lambda: active_sysids)

    plugin_hub = None
    if args.plugin_tcp and not args.dry_run:
        from plugin_tcp import PluginTcpHub
        # active_sysids-ის reference ყოველ tick-ში ატომურად იცვლება → accept thread-ზე
        # sorted(...) ყოველთვის თანმიმდევრულ set-ს ხედავს.
        plugin_hub = PluginTcpHub(args.plugin_tcp,
                                  hello_line=lambda: bridge_hello_line(sorted(active_sysids)))
        print("[dhgm] plugin TCP → %s" % plugin_hub.bind, file=sys.stderr)
        if plugin_hub.bind.startswith("127."):
            print("[dhgm] ⚠ loopback bind — ტელეფონი მხოლოდ `adb reverse tcp:%d tcp:%d`-ით "
                  "დაკავშირდება; LAN-ისთვის: --plugin-tcp 0.0.0.0:%d"
                  % (plugin_hub.port, plugin_hub.port, plugin_hub.port), file=sys.stderr)
        else:
            for ip in _lan_ipv4s():
                print("[dhgm] პანელის host: %s:%d" % (ip, plugin_hub.port), file=sys.stderr)

    if args.sim:
        n = max(1, args.sim_drones)
        for i in range(1, n + 1):
            states[i] = DroneState(i)
        print("[dhgm] SIM რეჟიმი — %d დრონი (DH-1..DH-%d) წრეებზე თბილისის ცენტრთან"
              % (n, n), file=sys.stderr)
    else:
        th = threading.Thread(target=mavlink_loop, args=(args.mavlink, states, states_lock),
                              daemon=True)
        th.start()

    if not args.dry_run:
        print("[dhgm] CoT → %s" % ", ".join("%s:%d" % t for t in sender.targets), file=sys.stderr)

    ticks = 0
    try:
        while True:
            now = time.time()
            if args.sim:
                for i, sysid in enumerate(sorted(states)):
                    sim_step(states[sysid], t0, index=i)
            current_active: Set[int] = set()
            outgoing = []
            # lock-ის ქვეშ მხოლოდ serialization; ქსელური I/O — lock-ის გარეთ.
            with states_lock:
                for st in states.values():
                    if st.has_fix and now - st.last_seen < args.stale:
                        current_active.add(st.sysid)
                        outgoing.append((cot_event(st, now, args.stale, args.prefix, instance),
                                         telemetry_line(st, now, args.prefix) if plugin_hub else None))
            for cot, line in outgoing:
                sender.send(cot)
                if plugin_hub and line:
                    plugin_hub.broadcast(line)
            if plugin_hub:
                for gone in active_sysids - current_active:
                    plugin_hub.broadcast(drone_gone_line(gone))
                plugin_hub.broadcast(bridge_heartbeat_line(now))
            active_sysids = current_active
            ticks += 1
            if args.max_ticks and ticks >= args.max_ticks:
                break
            time.sleep(1.0 / args.rate)
    except KeyboardInterrupt:
        print("\n[dhgm] გაჩერდა", file=sys.stderr)
    finally:
        if plugin_hub:
            plugin_hub.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
