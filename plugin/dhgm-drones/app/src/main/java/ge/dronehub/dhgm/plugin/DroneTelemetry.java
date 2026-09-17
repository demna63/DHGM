package ge.dronehub.dhgm.plugin;

import org.json.JSONObject;

/**
 * ერთი დრონის ტელემეტრიის snapshot — bridge-ის JSON payload-ის (type=telemetry)
 * პარსინგი. სქემა: bridge/plugin_json.py (v0.1).
 */
public class DroneTelemetry {

    public int sysid;
    public String callsign = "";
    public double lat;
    public double lon;
    public Double altAglM;      // მ AGL (nullable)
    public Double altMslM;      // მ MSL (nullable)
    public double speedMps;
    public double courseDeg;
    public Integer batteryPct;  // % (nullable)
    public Integer satellites;  // nullable
    public Integer rssiDbm;     // telemetry radio RSSI, dBm (nullable)
    public Integer rcRssiPct;   // RC link RSSI/LQ, 0..100 % (nullable) — ELRS/CRSF LQ
    public String flightMode = "";
    public String gpsFix = "";
    public double ts;           // bridge timestamp (წმ)
    public long rxAtMs;         // ლოკალური მიღების დრო (System.currentTimeMillis)

    /** აპარსავს telemetry JSON object-ს; null თუ არავალიდურია. */
    public static DroneTelemetry fromJson(JSONObject o) {
        if (o == null || !"telemetry".equals(o.optString("type"))) {
            return null;
        }
        DroneTelemetry t = new DroneTelemetry();
        t.sysid = o.optInt("sysid", 0);
        t.callsign = o.optString("callsign", "DH-" + t.sysid);
        t.lat = o.optDouble("lat", 0);
        t.lon = o.optDouble("lon", 0);
        t.altAglM = o.has("alt_agl_m") ? o.optDouble("alt_agl_m") : null;
        t.altMslM = o.has("alt_msl_m") ? o.optDouble("alt_msl_m") : null;
        t.speedMps = o.optDouble("speed_mps", 0);
        t.courseDeg = o.optDouble("course_deg", 0);
        t.batteryPct = o.has("battery_pct") ? o.optInt("battery_pct") : null;
        t.satellites = o.has("satellites") ? o.optInt("satellites") : null;
        t.rssiDbm = o.has("rssi_dbm") ? o.optInt("rssi_dbm") : null;
        t.rcRssiPct = o.has("rc_rssi_pct") ? clampPct(o.optInt("rc_rssi_pct", -1)) : null;
        t.flightMode = o.optString("flight_mode", "");
        t.gpsFix = o.optString("gps_fix", "");
        t.ts = o.optDouble("ts", 0);
        t.rxAtMs = System.currentTimeMillis();
        return t;
    }

    /** 0..100 % ან null (არავალიდური). */
    static Integer clampPct(int v) {
        return (v >= 0 && v <= 100) ? v : null;
    }

    /** RC link-ის ტექსტ ბარათისთვის: „RC 87%", &lt; 30% → „⚠ RC 25%"; null თუ უცნობია. */
    public String rcLinkLabel() {
        if (rcRssiPct == null) return null;
        return (rcRssiPct < 30 ? "⚠ RC " : "RC ") + rcRssiPct + "%";
    }

    /** ბატარეის მდგომარეობა ფერისთვის: 2=კარგი, 1=გაფრთხილება, 0=კრიტიკული, -1=უცნობი. */
    public int batteryLevel() {
        if (batteryPct == null) return -1;
        if (batteryPct >= 50) return 2;
        if (batteryPct >= 20) return 1;
        return 0;
    }

    /** stale window (ms) — ერთიანი კონფიგურაცია (bridge stale window-ის ანალოგი). */
    public static final long STALE_MS = 5000L;

    /** ხაზი ძველია? (default {@link #STALE_MS}). */
    public boolean isStale(long nowMs) {
        return isStale(nowMs, STALE_MS);
    }

    /** ხაზი ძველია მოცემულ ზღვართან? */
    public boolean isStale(long nowMs, long thresholdMs) {
        return nowMs - rxAtMs > thresholdMs;
    }
}
