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
import socket
import sys
import time
from typing import Dict, List, Optional, Set
from xml.sax.saxutils import quoteattr, escape

DEFAULT_MAVLINK = "0.0.0.0:14445"       # QGC forwardMavlinkHostName default პორტი
DEFAULT_MULTICAST = "239.2.3.1:6969"    # ATAK mesh SA default
COT_TYPE_UAV = "a-f-A-M-F-Q"            # friendly / air / military / fixed+rotary UAV/drone
UINT16_MAX = 65535

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
    def speed(self) -> float:
        if self.groundspeed is not None:
            return self.groundspeed
        return math.hypot(self.vx, self.vy)


def _cot_time(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + (".%02dZ" % int((t % 1) * 100))


def cot_event(state: DroneState, now: float, stale_s: float, prefix: str = "DH") -> bytes:
    """აწყობს CoT 2.0 event XML-ს ერთი დრონისთვის."""
    callsign = "%s-%d" % (prefix, state.sysid)
    uid = "DHGM.%d" % state.sysid
    hae = state.alt_msl if state.alt_msl is not None else 0.0
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
        '<point lat="%.7f" lon="%.7f" hae="%.1f" ce="10.0" le="10.0"/>'
        "<detail>"
        "<contact callsign=%s/>"
        '<track speed="%.2f" course="%.1f"/>'
        '<precisionlocation geopointsrc="GPS" altsrc="GPS"/>'
        "<remarks>%s</remarks>"
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
        quoteattr(callsign),
        state.speed,
        state.course,
        escape(remarks),
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


def mavlink_loop(conn_str: str, states: Dict[int, DroneState]) -> None:
    """კითხულობს MAVLink ნაკადს და ანახლებს დრონების მდგომარეობას (გენერატორი-ნაბიჯი)."""
    from pymavlink import mavutil  # lazy import — --sim რეჟიმს არ სჭირდება

    conn = mavutil.mavlink_connection("udpin:" + conn_str, source_system=250)
    print("[dhgm] ველოდები MAVLink-ს udpin:%s (GCS → Settings → MAVLink → forwarding)" % conn_str)
    while True:
        msg = conn.recv_match(blocking=True, timeout=1.0)
        if msg is None:
            continue
        sysid = msg.get_srcSystem()
        if sysid == 0 or sysid >= 250:  # GCS/broadcast id-ები გამოვტოვოთ
            continue
        st = states.setdefault(sysid, DroneState(sysid))
        t = msg.get_type()
        if t == "GLOBAL_POSITION_INT":
            st.lat = msg.lat / 1e7
            st.lon = msg.lon / 1e7
            st.alt_msl = msg.alt / 1000.0
            st.alt_rel = msg.relative_alt / 1000.0
            st.vx = msg.vx / 100.0
            st.vy = msg.vy / 100.0
            st.heading = None if msg.hdg == UINT16_MAX else msg.hdg / 100.0
            st.last_seen = time.time()
        elif t == "VFR_HUD":
            st.groundspeed = msg.groundspeed
            st.last_seen = time.time()
        elif t == "SYS_STATUS":
            st.battery_pct = msg.battery_remaining
        elif t == "GPS_RAW_INT":
            from plugin_json import gps_fix_name
            st.gps_fix = gps_fix_name(msg.fix_type)
            st.satellites = msg.satellites_visible
            st.last_seen = time.time()
        elif t == "HEARTBEAT":
            st.last_seen = time.time()
            st.flight_mode = str(msg.custom_mode)


def sim_step(st: DroneState, t0: float) -> None:
    """სიმულირებული დრონი — წრე თბილისის ცენტრზე, R=500მ, 15 მ/წმ, 120მ AGL."""
    elapsed = time.time() - t0
    radius_m, speed = 500.0, 15.0
    omega = speed / radius_m
    ang = omega * elapsed
    st.lat = SIM_CENTER_LAT + (radius_m / 111320.0) * math.sin(ang)
    st.lon = SIM_CENTER_LON + (radius_m / (111320.0 * math.cos(math.radians(SIM_CENTER_LAT)))) * math.cos(ang)
    st.alt_rel = 120.0
    st.alt_msl = 120.0 + 450.0  # თბილისის სავარაუდო რელიეფი
    st.groundspeed = speed
    st.heading = (math.degrees(ang) + 90.0) % 360.0
    st.battery_pct = max(0, 100 - int(elapsed / 30))
    st.flight_mode = "AUTO"
    st.gps_fix = "3D"
    st.satellites = 12
    st.last_seen = time.time()


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
    p.add_argument("--dry-run", action="store_true", help="CoT stdout-ზე, გაგზავნის გარეშე")
    p.add_argument("--plugin-tcp", default="", metavar="HOST:PORT",
                   help="DHGM plugin-ისთვის TCP JSON stream (მაგ. 127.0.0.1:14550)")
    p.add_argument("--max-ticks", type=int, default=0, help="გაჩერდი N tick-ის შემდეგ (ტესტისთვის)")
    args = p.parse_args()

    targets = list(args.cot_udp)
    if not args.no_multicast:
        targets.insert(0, DEFAULT_MULTICAST)
    sender = CotSender(targets, dry_run=args.dry_run)
    states: Dict[int, DroneState] = {}
    t0 = time.time()
    plugin_hub = None
    if args.plugin_tcp and not args.dry_run:
        from plugin_tcp import PluginTcpHub
        plugin_hub = PluginTcpHub(args.plugin_tcp)
        print("[dhgm] plugin TCP → %s" % plugin_hub.bind, file=sys.stderr)
    active_sysids: Set[int] = set()
    prev_plugin_clients = 0

    if args.sim:
        states[1] = DroneState(1)
        print("[dhgm] SIM რეჟიმი — დრონი DH-1 წრეზე თბილისის ცენტრთან", file=sys.stderr)
    else:
        import threading
        th = threading.Thread(target=mavlink_loop, args=(args.mavlink, states), daemon=True)
        th.start()

    if not args.dry_run:
        print("[dhgm] CoT → %s" % ", ".join("%s:%d" % t for t in sender.targets), file=sys.stderr)

    from plugin_json import bridge_hello_line, drone_gone_line, telemetry_line

    ticks = 0
    try:
        while True:
            now = time.time()
            if args.sim:
                sim_step(states[1], t0)
            current_active: Set[int] = set()
            for st in states.values():
                if st.has_fix and now - st.last_seen < args.stale:
                    current_active.add(st.sysid)
                    sender.send(cot_event(st, now, args.stale, args.prefix))
                    if plugin_hub:
                        line = telemetry_line(st, now, args.prefix)
                        if line:
                            plugin_hub.broadcast(line)
            if plugin_hub:
                cc = plugin_hub.client_count()
                if cc > prev_plugin_clients:
                    plugin_hub.broadcast(bridge_hello_line(sorted(current_active)))
                prev_plugin_clients = cc
                for gone in active_sysids - current_active:
                    plugin_hub.broadcast(drone_gone_line(gone))
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
