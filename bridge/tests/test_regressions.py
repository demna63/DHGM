"""რეგრესიის ტესტები — 2026-09 აუდიტის შეცდომები (stdlib unittest)."""

import os
import socket
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhgm_bridge import (  # noqa: E402
    MAV_AUTOPILOT_INVALID,
    DroneState,
    handle_mavlink_msg,
    snapshot_states,
)
from plugin_tcp import PluginTcpHub  # noqa: E402


class _Msg:
    """pymavlink message-ის duck-typed stub."""

    def __init__(self, mtype, sysid=1, **fields):
        self._type = mtype
        self._sysid = sysid
        self.__dict__.update(fields)

    def get_type(self):
        return self._type

    def get_srcSystem(self):
        return self._sysid


def _mode(msg):
    return {4: "GUIDED", 5: "LOITER"}.get(msg.custom_mode, "Mode(%d)" % msg.custom_mode)


def _gpi(sysid=1, lat=417151000, lon=448271000):
    return _Msg("GLOBAL_POSITION_INT", sysid, lat=lat, lon=lon, alt=550000,
                relative_alt=100000, vx=0, vy=1200, hdg=9000)


class TestStallingClient(unittest.TestCase):
    """bug #2: ჩეჭდილ TCP კლიენტი broadcast-ს (და CoT-ს) ბოლომდე ბლოკავდა."""

    def test_broadcast_does_not_block_on_non_reading_client(self):
        hub = PluginTcpHub("127.0.0.1:0", send_timeout_s=0.2)
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
            client.connect(("127.0.0.1", hub.port))
            deadline = time.time() + 3
            while hub.client_count() == 0 and time.time() < deadline:
                time.sleep(0.05)
            self.assertEqual(hub.client_count(), 1)

            line = '{"type":"telemetry","pad":"%s"}' % ("x" * 1000)
            finished = threading.Event()

            def spam():
                for _ in range(50000):
                    hub.broadcast(line)
                    if hub.client_count() == 0:
                        break
                finished.set()

            threading.Thread(target=spam, daemon=True).start()
            self.assertTrue(finished.wait(10), "broadcast ბლოკირდა ჩეჭდილ კლიენტზე")
            self.assertEqual(hub.client_count(), 0, "ჩეჭდილ კლიენტი უნდა მოცილდეს")
            client.close()
        finally:
            hub.close()


class TestConcurrentStates(unittest.TestCase):
    """bug #3: ახალი sysid MAVLink thread-იდან → RuntimeError main loop-ში."""

    def test_snapshot_under_concurrent_inserts(self):
        states = {}
        lock = threading.Lock()
        stop = threading.Event()

        def writer():
            sysid = 1
            while not stop.is_set():
                with lock:
                    handle_mavlink_msg(states, _gpi(sysid=sysid % 249 + 1), time.time(), _mode)
                sysid += 1

        th = threading.Thread(target=writer, daemon=True)
        th.start()
        try:
            end = time.time() + 1.5
            while time.time() < end:
                for st in snapshot_states(states, lock):  # არ უნდა ისროლოს RuntimeError
                    _ = st.has_fix
        finally:
            stop.set()
            th.join(2)
        self.assertGreater(len(states), 1)


class TestHandleMavlink(unittest.TestCase):
    """bug #4 + Null Island + sysid ფილტრი."""

    def test_flight_mode_name(self):
        states = {}
        handle_mavlink_msg(states, _Msg("HEARTBEAT", autopilot=3, custom_mode=4), 1.0, _mode)
        self.assertEqual(states[1].flight_mode, "GUIDED")

    def test_component_heartbeat_does_not_override_mode(self):
        states = {}
        handle_mavlink_msg(states, _Msg("HEARTBEAT", autopilot=3, custom_mode=5), 1.0, _mode)
        handle_mavlink_msg(states, _Msg("HEARTBEAT", autopilot=MAV_AUTOPILOT_INVALID,
                                        custom_mode=0), 2.0, _mode)
        self.assertEqual(states[1].flight_mode, "LOITER")

    def test_mode_fallback_on_error(self):
        def boom(_msg):
            raise KeyError("unknown")

        states = {}
        handle_mavlink_msg(states, _Msg("HEARTBEAT", autopilot=12, custom_mode=7), 1.0, boom)
        self.assertEqual(states[1].flight_mode, "7")

    def test_zero_position_ignored(self):
        states = {}
        handle_mavlink_msg(states, _gpi(lat=0, lon=0), 1.0, _mode)
        self.assertFalse(states[1].has_fix)

    def test_position_parsed(self):
        states = {}
        handle_mavlink_msg(states, _gpi(), 5.0, _mode)
        st = states[1]
        self.assertAlmostEqual(st.lat, 41.7151)
        self.assertAlmostEqual(st.alt_rel, 100.0)
        self.assertAlmostEqual(st.heading, 90.0)
        self.assertEqual(st.last_seen, 5.0)

    def test_gcs_and_broadcast_sysids_ignored(self):
        states = {}
        for sysid in (0, 250, 255):
            handle_mavlink_msg(states, _gpi(sysid=sysid), 1.0, _mode)
        self.assertEqual(states, {})

    def test_irrelevant_message_does_not_create_drone(self):
        states = {}
        handle_mavlink_msg(states, _Msg("ATTITUDE"), 1.0, _mode)
        self.assertEqual(states, {})


if __name__ == "__main__":
    unittest.main()


class TestHaeAndHello(unittest.TestCase):
    """CoT hae (MSL→HAE), bridge_hello ახალ კლიენტზე, heartbeat, LAN bind."""

    def test_hae_uses_geoid_separation(self):
        from dhgm_bridge import cot_event
        import xml.etree.ElementTree as ET

        states = {}
        handle_mavlink_msg(states, _gpi(), 1.0, _mode)  # alt_msl = 550 მ
        handle_mavlink_msg(states, _Msg("GPS_RAW_INT", fix_type=3, satellites_visible=12,
                                        alt=548000, alt_ellipsoid=571500), 1.0, _mode)
        st = states[1]
        self.assertAlmostEqual(st.geoid_sep, 23.5)
        pt = ET.fromstring(cot_event(st, 1.0, 10.0)).find("point")
        self.assertAlmostEqual(float(pt.get("hae")), 573.5)

    def test_hae_fallback_and_unknown(self):
        from dhgm_bridge import HAE_UNKNOWN

        st = DroneState(1)
        self.assertEqual(st.hae, HAE_UNKNOWN)
        st.alt_msl = 500.0
        self.assertEqual(st.hae, 500.0)  # N უცნობი → MSL fallback

    def test_absurd_geoid_separation_rejected(self):
        states = {}
        handle_mavlink_msg(states, _Msg("GPS_RAW_INT", fix_type=3, satellites_visible=9,
                                        alt=500000, alt_ellipsoid=900000), 1.0, _mode)
        self.assertIsNone(states[1].geoid_sep)

    def test_no_fix_no_geoid(self):
        states = {}
        handle_mavlink_msg(states, _Msg("GPS_RAW_INT", fix_type=1, satellites_visible=3,
                                        alt=500000, alt_ellipsoid=520000), 1.0, _mode)
        self.assertIsNone(states[1].geoid_sep)

    def test_hello_sent_to_each_new_client_first(self):
        import json

        hub = PluginTcpHub("127.0.0.1:0", hello_line=lambda: '{"type":"bridge_hello"}')
        try:
            socks = []
            for _ in range(2):
                c = socket.create_connection(("127.0.0.1", hub.port), timeout=3)
                socks.append(c)
            deadline = time.time() + 3
            while hub.client_count() < 2 and time.time() < deadline:
                time.sleep(0.05)
            hub.broadcast('{"type":"bridge_heartbeat"}')
            for c in socks:
                f = c.makefile("r", encoding="utf-8")
                self.assertEqual(json.loads(f.readline())["type"], "bridge_hello")
                self.assertEqual(json.loads(f.readline())["type"], "bridge_heartbeat")
                c.close()
        finally:
            hub.close()

    def test_empty_host_binds_all_interfaces(self):
        hub = PluginTcpHub(":0")
        try:
            self.assertTrue(hub.bind.startswith("0.0.0.0:"))
        finally:
            hub.close()

    def test_heartbeat_line(self):
        import json
        from plugin_json import bridge_heartbeat_line

        self.assertEqual(json.loads(bridge_heartbeat_line(12.3456)),
                         {"type": "bridge_heartbeat", "ts": 12.346})


class TestDuplicateSource(unittest.TestCase):
    """იგივე DHGM.<sysid>-ის მეორე CoT წყაროს აღმოჩენა (GCS CotForwarder + bridge)."""

    def _state(self):
        st = DroneState(4)
        st.lat, st.lon, st.alt_msl, st.groundspeed, st.heading = 41.7, 44.8, 500.0, 5.0, 10.0
        return st

    def test_own_event_not_foreign(self):
        from dhgm_bridge import cot_event, foreign_dhgm_sysid

        data = cot_event(self._state(), 1.0, 10.0, instance="me-1")
        self.assertIsNone(foreign_dhgm_sysid(data, "me-1"))

    def test_other_instance_or_untagged_is_foreign(self):
        from dhgm_bridge import cot_event, foreign_dhgm_sysid

        self.assertEqual(foreign_dhgm_sysid(cot_event(self._state(), 1.0, 10.0, instance="other"), "me-1"), 4)
        self.assertEqual(foreign_dhgm_sysid(cot_event(self._state(), 1.0, 10.0), "me-1"), 4)

    def test_non_dhgm_event_ignored(self):
        from dhgm_bridge import foreign_dhgm_sysid

        self.assertIsNone(foreign_dhgm_sysid(b'<event uid="ANDROID-123" type="a-f-G-U-C"/>', "me-1"))

    def test_source_tag_is_valid_xml_and_escaped(self):
        import xml.etree.ElementTree as ET
        from dhgm_bridge import SOURCE_TAG, cot_event

        root = ET.fromstring(cot_event(self._state(), 1.0, 10.0, instance='a"<b'))
        self.assertEqual(root.find("detail/" + SOURCE_TAG).get("instance"), 'a"<b')


class TestRcRssi(unittest.TestCase):
    """RC link RSSI/LQ (ELRS/CRSF) — RC_CHANNELS.rssi → rc_rssi_pct."""

    def test_percent_mapping(self):
        from dhgm_bridge import rc_rssi_percent

        self.assertEqual(rc_rssi_percent(0), 0)
        self.assertEqual(rc_rssi_percent(254), 100)
        self.assertEqual(rc_rssi_percent(127), 50)
        self.assertIsNone(rc_rssi_percent(255))
        self.assertIsNone(rc_rssi_percent(-1))

    def test_rc_channels_to_json(self):
        import json
        from plugin_json import telemetry_payload

        states = {}
        handle_mavlink_msg(states, _gpi(), 1.0, _mode)
        handle_mavlink_msg(states, _Msg("RC_CHANNELS", rssi=221), 1.0, _mode)
        payload = telemetry_payload(states[1], 1.0)
        self.assertEqual(payload["rc_rssi_pct"], 87)
        handle_mavlink_msg(states, _Msg("RC_CHANNELS", rssi=255), 2.0, _mode)
        self.assertNotIn("rc_rssi_pct", telemetry_payload(states[1], 2.0))
        json.dumps(payload)
