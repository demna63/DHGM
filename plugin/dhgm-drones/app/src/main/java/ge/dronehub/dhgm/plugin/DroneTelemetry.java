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
    public Integer rssiDbm;     // nullable
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
        t.flightMode = o.optString("flight_mode", "");
        t.gpsFix = o.optString("gps_fix", "");
        t.ts = o.optDouble("ts", 0);
        t.rxAtMs = System.currentTimeMillis();
        return t;
    }

    /** ბატარეის მდგომარეობა ფერისთვის: 2=კარგი, 1=გაფრთხილება, 0=კრიტიკული, -1=უცნობი. */
    public int batteryLevel() {
        if (batteryPct == null) return -1;
        if (batteryPct >= 50) return 2;
        if (batteryPct >= 20) return 1;
        return 0;
    }

    /** ხაზი ძველია? (bridge stale window-ის ანალოგი — 5 წმ). */
    public boolean isStale(long nowMs) {
        return nowMs - rxAtMs > 5000;
    }
}
