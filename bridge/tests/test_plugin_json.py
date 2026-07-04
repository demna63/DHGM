"""plugin_json + plugin_tcp unit ტესტები."""

import json
import os
import socket
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhgm_bridge import DroneState
from plugin_json import (
    BRIDGE_VERSION,
    bridge_hello_line,
    drone_gone_line,
    gps_fix_name,
    telemetry_line,
    telemetry_payload,
)
from plugin_tcp import PluginTcpHub


def _state():
    st = DroneState(2)
    st.lat = 41.7
    st.lon = 44.8
    st.alt_rel = 100.0
    st.alt_msl = 500.0
    st.groundspeed = 10.0
    st.heading = 90.0
    st.battery_pct = 75
    st.flight_mode = "AUTO"
    st.gps_fix = "3D"
    st.satellites = 10
    return st


class TestPluginJson(unittest.TestCase):
    def test_telemetry_payload(self):
        p = telemetry_payload(_state(), 1000.0)
        self.assertEqual(p["type"], "telemetry")
        self.assertEqual(p["sysid"], 2)
        self.assertEqual(p["callsign"], "DH-2")
        self.assertEqual(p["flight_mode"], "AUTO")
        self.assertEqual(p["battery_pct"], 75)

    def test_telemetry_no_fix(self):
        st = DroneState(1)
        self.assertIsNone(telemetry_payload(st, 1.0))

    def test_bridge_hello(self):
        obj = json.loads(bridge_hello_line([1, 2]))
        self.assertEqual(obj["type"], "bridge_hello")
        self.assertEqual(obj["version"], BRIDGE_VERSION)

    def test_drone_gone(self):
        obj = json.loads(drone_gone_line(3))
        self.assertEqual(obj["sysid"], 3)
        self.assertEqual(obj["reason"], "stale")

    def test_gps_fix_name(self):
        self.assertEqual(gps_fix_name(3), "3D")


class TestPluginTcp(unittest.TestCase):
    def test_hub_broadcast(self):
        hub = PluginTcpHub("127.0.0.1:14559")
        received = []

        def client():
            time.sleep(0.05)
            s = socket.create_connection(("127.0.0.1", 14559), timeout=2)
            s.settimeout(2)
            buf = b""
            while b"\n" not in buf:
                buf += s.recv(4096)
            received.append(buf.decode())
            s.close()

        threading.Thread(target=client, daemon=True).start()
        time.sleep(0.1)
        for _ in range(20):
            if hub.client_count() > 0:
                break
            time.sleep(0.05)
        hub.broadcast('{"type":"test"}')
        time.sleep(0.1)
        hub.close()
        self.assertTrue(received)
        self.assertIn("test", received[0])


if __name__ == "__main__":
    unittest.main()
