"""DHGM plugin TCP stream — newline-delimited JSON (სპეკი v0.1).

იხ. docs/phase2-drone-panel.md
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from dhgm_bridge import DroneState

BRIDGE_VERSION = "0.1.0"

_GPS_FIX = {
    0: "NO",
    1: "NO",
    2: "2D",
    3: "3D",
    4: "DGPS",
    5: "RTK",
    6: "RTK",
}


def telemetry_payload(state: DroneState, now: float, prefix: str = "DH") -> Optional[Dict[str, Any]]:
    """ერთი დრონის telemetry object — None თუ პოზიცია არ არის."""
    if not state.has_fix:
        return None
    obj: Dict[str, Any] = {
        "type": "telemetry",
        "ts": round(now, 3),
        "sysid": state.sysid,
        "callsign": "%s-%d" % (prefix, state.sysid),
        "lat": round(state.lat, 7),
        "lon": round(state.lon, 7),
        "speed_mps": round(state.speed, 2),
        "course_deg": round(state.course, 1),
        "flight_mode": state.flight_mode,
        "gps_fix": state.gps_fix,
    }
    if state.alt_rel is not None:
        obj["alt_agl_m"] = round(state.alt_rel, 1)
    if state.alt_msl is not None:
        obj["alt_msl_m"] = round(state.alt_msl, 1)
    if state.battery_pct is not None and state.battery_pct >= 0:
        obj["battery_pct"] = int(state.battery_pct)
    if state.satellites is not None:
        obj["satellites"] = int(state.satellites)
    if state.rssi_dbm is not None:
        obj["rssi_dbm"] = int(state.rssi_dbm)
    if state.rc_rssi_pct is not None:
        obj["rc_rssi_pct"] = int(state.rc_rssi_pct)
    return obj


def telemetry_line(state: DroneState, now: float, prefix: str = "DH") -> Optional[str]:
    payload = telemetry_payload(state, now, prefix)
    if payload is None:
        return None
    return json.dumps(payload, separators=(",", ":"))


def bridge_hello_line(drone_sysids: List[int]) -> str:
    return json.dumps(
        {"type": "bridge_hello", "version": BRIDGE_VERSION, "drones": drone_sysids},
        separators=(",", ":"),
    )


def bridge_heartbeat_line(now: float) -> str:
    """keepalive (1 Hz) — plugin-ი read timeout-ით „ჩუმად" მკვდარ bridge-ს (Wi-Fi drop,
    FIN-ის გარეშე) ამ ხაზების არარსებობით აღმოაჩენს, მაშინაც, როცა დრონ არ არის."""
    return json.dumps({"type": "bridge_heartbeat", "ts": round(now, 3)}, separators=(",", ":"))


def drone_gone_line(sysid: int, reason: str = "stale") -> str:
    return json.dumps({"type": "drone_gone", "sysid": sysid, "reason": reason}, separators=(",", ":"))


def gps_fix_name(fix_type: int) -> str:
    return _GPS_FIX.get(fix_type, "UNKNOWN")
