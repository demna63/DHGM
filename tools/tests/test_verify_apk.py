"""tools/verify-apk.py — role detection / key matching.

APK-ებ ტესტში არ გვჭირდება: სახელიდან როლის ამოცნობა და key-ების ცხრილია
რეგრესიის რისკ (v0.4.1-ზე CI ჩავარდა, რადგან app და plugin სხვადასხვა alias-ითაა
ხელმოწერილ — იხ. docs/distribution.md).
"""
import importlib.util
import pathlib
import unittest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "verify-apk.py"
_spec = importlib.util.spec_from_file_location("verify_apk", _SRC)
verify_apk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_apk)

APP = verify_apk.APP_CERT_SHA256
PLUGIN = verify_apk.PLUGIN_CERT_SHA256


class RoleDetection(unittest.TestCase):
    def test_release_asset_names(self):
        """CI-ის „Stage release assets" სახელებ."""
        self.assertEqual(verify_apk.expected_cert("dist/DHGM-0.4.1-app.apk"), (APP, "app"))
        self.assertEqual(verify_apk.expected_cert("dist/DHGM-Drones-0.4.1.apk"), (PLUGIN, "plugin"))

    def test_artifact_and_absolute_paths(self):
        self.assertEqual(
            verify_apk.expected_cert("/tmp/x/DHGM-Drones-plugin-0.1.0.apk"), (PLUGIN, "plugin"))
        self.assertEqual(verify_apk.expected_cert("DHGM-2.2-app.apk"), (APP, "app"))

    def test_case_insensitive(self):
        self.assertEqual(verify_apk.expected_cert("DHGM-0.4.1-APP.APK")[0], APP)
        self.assertEqual(verify_apk.expected_cert("DHGM-DRONES-0.4.1.APK")[0], PLUGIN)

    def test_plugin_wins_over_app_suffix(self):
        """plugin-ის სახელ app-ის ნიმუშსაც რომ ერგებოდეს, plugin უნდა გაიმარჯვოს."""
        self.assertEqual(verify_apk.expected_cert("DHGM-Drones-0.4.1-app.apk"), (PLUGIN, "plugin"))

    def test_unknown_name_has_no_expectation(self):
        want, role = verify_apk.expected_cert("some-random-build.apk")
        self.assertIsNone(want)
        self.assertTrue(role)


class KeyTable(unittest.TestCase):
    def test_two_distinct_keys_are_labelled(self):
        self.assertNotEqual(APP, PLUGIN)
        for cert in (APP, PLUGIN):
            self.assertEqual(len(cert), 64, cert)
            self.assertEqual(cert, cert.upper())
            self.assertIn(cert, verify_apk.KEY_LABEL)
            self.assertTrue(verify_apk.KEY_LABEL[cert].strip())


if __name__ == "__main__":
    unittest.main()
