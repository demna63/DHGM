"""dhgm_bridge — CoT გენერაციის unit ტესტები (stdlib unittest, დამოკიდებულებების გარეშე)."""

import os
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhgm_bridge import DroneState, cot_event, COT_TYPE_UAV


def make_state():
    st = DroneState(3)
    st.lat = 41.7151
    st.lon = 44.8271
    st.alt_msl = 570.0
    st.alt_rel = 120.0
    st.groundspeed = 12.3
    st.heading = 245.0
    st.battery_pct = 87
    st.last_seen = 1000.0
    return st


class TestCotEvent(unittest.TestCase):
    def test_event_fields(self):
        root = ET.fromstring(cot_event(make_state(), now=1000.0, stale_s=10.0))
        self.assertEqual(root.tag, "event")
        self.assertEqual(root.get("uid"), "DHGM.3")
        self.assertEqual(root.get("type"), COT_TYPE_UAV)
        point = root.find("point")
        self.assertAlmostEqual(float(point.get("lat")), 41.7151)
        self.assertAlmostEqual(float(point.get("lon")), 44.8271)
        self.assertAlmostEqual(float(point.get("hae")), 570.0)
        self.assertEqual(root.find("detail/contact").get("callsign"), "DH-3")
        track = root.find("detail/track")
        self.assertAlmostEqual(float(track.get("speed")), 12.3)
        self.assertAlmostEqual(float(track.get("course")), 245.0)
        remarks = root.find("detail/remarks").text
        self.assertIn("ALT 120 m AGL", remarks)
        self.assertIn("SPD 12.3 m/s", remarks)
        self.assertIn("BAT 87%", remarks)

    def test_stale_after_start(self):
        root = ET.fromstring(cot_event(make_state(), now=1000.0, stale_s=10.0))
        self.assertLess(root.get("start"), root.get("stale"))

    def test_course_falls_back_to_velocity(self):
        st = make_state()
        st.heading = None
        st.vx = 0.0   # ჩრდილოეთი კომპონენტი
        st.vy = 5.0   # აღმოსავლეთი კომპონენტი → კურსი 90°
        root = ET.fromstring(cot_event(st, now=1000.0, stale_s=10.0))
        self.assertAlmostEqual(float(root.find("detail/track").get("course")), 90.0)

    def test_speed_falls_back_to_velocity(self):
        st = make_state()
        st.groundspeed = None
        st.vx = 3.0
        st.vy = 4.0
        root = ET.fromstring(cot_event(st, now=1000.0, stale_s=10.0))
        self.assertAlmostEqual(float(root.find("detail/track").get("speed")), 5.0)

    def test_custom_prefix(self):
        root = ET.fromstring(cot_event(make_state(), now=1000.0, stale_s=10.0, prefix="DHG"))
        self.assertEqual(root.find("detail/contact").get("callsign"), "DHG-3")

    def test_no_battery_omitted_from_remarks(self):
        st = make_state()
        st.battery_pct = None
        root = ET.fromstring(cot_event(st, now=1000.0, stale_s=10.0))
        self.assertNotIn("BAT", root.find("detail/remarks").text)


if __name__ == "__main__":
    unittest.main()
