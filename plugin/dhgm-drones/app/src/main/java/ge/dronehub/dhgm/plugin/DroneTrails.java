package ge.dronehub.dhgm.plugin;

import com.atakmap.android.maps.MapGroup;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.maps.Polyline;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.Map;

/**
 * დრონების კონტროლირებადი breadcrumb trail — თითო დრონზე capped Polyline
 * (ბოლო {@link #MAX_POINTS} წერტილი). ATAK-ის ავტო-breadcrumb-ის ალტერნატივა:
 * სიგრძე შემოსაზღვრულია → pan/zoom-ზე map lag აღარ იზრდება უსასრულოდ.
 *
 * ATAK Settings → Bread Crumb Preferences-ში ავტო-trail გამორთე — მაშინ მხოლოდ
 * ეს, DroneHub ცისფერი trail ჩანს.
 */
public class DroneTrails {

    private static final String TAG = "DhgmDroneTrails";
    private static final int MAX_POINTS = 40;        // trail-ის მაქს. სიგრძე
    private static final int TRAIL_COLOR = 0xCC64D2FF; // DroneHub telemetry ცისფერი
    private static final double TRAIL_WEIGHT = 3.0;

    private final MapView mapView;
    private MapGroup group;
    private final Map<Integer, Deque<GeoPoint>> points = new HashMap<>();
    private final Map<Integer, Polyline> lines = new HashMap<>();

    public DroneTrails(MapView mapView) {
        this.mapView = mapView;
    }

    private MapGroup group() {
        if (group == null) {
            try {
                group = mapView.getRootGroup().addGroup("DHGM დრონები");
            } catch (Exception e) {
                Log.w(TAG, "trail group create failed: " + e.getMessage());
            }
        }
        return group;
    }

    /** დრონის ახალი პოზიცია — trail-ს ამატებს (capped) და პოლილაინს ანახლებს. */
    public void addPoint(int sysid, double lat, double lon) {
        try {
            Deque<GeoPoint> dq = points.get(sysid);
            if (dq == null) {
                dq = new ArrayDeque<>();
                points.put(sysid, dq);
            }
            // დუბლიკატი პოზიცია (გაუნძრევი დრონი) — ვტოვებთ trail-ს გასუფთავებულს
            GeoPoint last = dq.peekLast();
            if (last != null && last.getLatitude() == lat && last.getLongitude() == lon) {
                return;
            }
            dq.addLast(new GeoPoint(lat, lon));
            while (dq.size() > MAX_POINTS) {
                dq.removeFirst();
            }
            if (dq.size() < 2) {
                return; // 1 წერტილზე ხაზი არ იხატება
            }

            Polyline line = lines.get(sysid);
            if (line == null) {
                line = new Polyline("DHGM.trail." + sysid);
                line.setStrokeColor(TRAIL_COLOR);
                line.setStrokeWeight(TRAIL_WEIGHT);
                line.setMetaBoolean("removable", false);
                lines.put(sysid, line);
                MapGroup g = group();
                if (g != null) g.addItem(line);
            }
            line.setPoints(dq.toArray(new GeoPoint[0]));
        } catch (Exception e) {
            Log.w(TAG, "addPoint failed for " + sysid + ": " + e.getMessage());
        }
    }

    /** ერთი დრონის trail-ის მოცილება. */
    public void remove(int sysid) {
        points.remove(sysid);
        Polyline line = lines.remove(sysid);
        try {
            if (line != null && group != null) group.removeItem(line);
        } catch (Exception e) {
            Log.w(TAG, "remove failed: " + e.getMessage());
        }
    }

    /** ყველა trail-ის გასუფთავება (გათიშვა/ხელახლა დაკავშირება). */
    public void clearAll() {
        points.clear();
        try {
            for (Polyline line : lines.values()) {
                if (group != null) group.removeItem(line);
            }
        } catch (Exception e) {
            Log.w(TAG, "clearAll failed: " + e.getMessage());
        }
        lines.clear();
    }
}
