package ge.dronehub.dhgm.plugin;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import org.json.JSONObject;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * დრონების პანელის კონტროლერი — bridge-ის JSON ხაზებს აპარსავს და თითო დრონზე
 * ცოცხალ ბარათს ხატავს (callsign, სიმაღლე, სიჩქარე, ბატარეა, რეჟიმი, GPS).
 * ბარათზე tap → რუკაზე ცენტრირება + follow toggle. Follow → რუკა დრონს მიჰყვება.
 * stale დრონი ნაცრისფრდება (ticker-ით, ტელემეტრიის გარეშეც).
 * ყველა UI-ცვლილება panel view-ის thread-ზე (post) ხდება.
 */
public class DronePanel {

    private static final String TAG = "DhgmDronePanel";

    // DroneHub პალიტრა
    private static final int C_OK = 0xFF30D158;       // მწვანე
    private static final int C_WARN = 0xFFFF9F0A;     // ნარინჯისფერი
    private static final int C_CRIT = 0xFFFF453A;     // წითელი
    private static final int C_MUTED = 0xFF9AA6B8;    // ნაცრისფერი (stale/უცნობი)
    private static final int C_CARD = 0xFF1E2530;     // ბარათის ფონი
    private static final int C_CARD_FOLLOW = 0xFF17A79A; // follow-ის აქცენტი (teal)

    private static final long STALE_TICK_MS = 2000L;

    private final Context pluginContext;
    private final View panelView;
    private final MapView mapView;
    private final TextView statusView;
    private final LinearLayout listView;
    private final TextView emptyView;
    private final Handler ui = new Handler(Looper.getMainLooper());

    // sysid → (telemetry, card view) — LinkedHashMap რომ რიგი შენარჩუნდეს
    private final Map<Integer, DroneTelemetry> drones = new LinkedHashMap<>();
    private final Map<Integer, View> cards = new LinkedHashMap<>();

    private int followSysid = -1;  // -1 = follow გამორთული
    private boolean ticking = false;
    private final DroneTrails trails;

    private final Runnable staleTicker = new Runnable() {
        @Override
        public void run() {
            long now = System.currentTimeMillis();
            for (Map.Entry<Integer, DroneTelemetry> e : drones.entrySet()) {
                View card = cards.get(e.getKey());
                if (card != null) bindCard(card, e.getValue());
            }
            if (ticking) ui.postDelayed(this, STALE_TICK_MS);
        }
    };

    public DronePanel(Context pluginContext, View panelView, MapView mapView) {
        this.pluginContext = pluginContext;
        this.panelView = panelView;
        this.mapView = mapView;
        this.statusView = panelView.findViewById(R.id.dhgm_bridge_status);
        this.listView = panelView.findViewById(R.id.dhgm_drone_list);
        this.emptyView = new TextView(pluginContext);
        this.emptyView.setTextColor(C_MUTED);
        this.emptyView.setTextSize(13);
        this.emptyView.setText(pluginContext.getString(R.string.dhgm_no_drones));
        this.trails = new DroneTrails(mapView);
        showEmpty(true);
    }

    /** bridge-ის ერთი ხაზი (newline-delimited JSON). */
    public void onBridgeLine(final String line) {
        panelView.post(() -> {
            try {
                handle(new JSONObject(line));
            } catch (Exception e) {
                Log.d(TAG, "bad bridge line: " + e.getMessage());
            }
        });
    }

    /** კავშირის მდგომარეობა (connect/disconnect). */
    public void setConnected(final boolean connected) {
        panelView.post(() -> {
            if (!connected) {
                stopTicker();
                followSysid = -1;
                drones.clear();
                listView.removeAllViews();
                cards.clear();
                trails.clearAll();
                showEmpty(true);
                statusView.setText(R.string.dhgm_bridge_disconnected);
                statusView.setTextColor(C_MUTED);
            } else {
                startTicker();
            }
        });
    }

    /** მყისიერი უკუკავშირი „დაკავშირება" ღილაკზე — ვუკავშირდები host:port…. */
    public void setConnecting(final String hostPort) {
        panelView.post(() -> {
            followSysid = -1;
            drones.clear();
            listView.removeAllViews();
            cards.clear();
            trails.clearAll();
            showEmpty(true);
            statusView.setText(pluginContext.getString(R.string.dhgm_connecting, hostPort));
            statusView.setTextColor(C_WARN);
            startTicker();
        });
    }

    private void handle(JSONObject o) {
        String type = o.optString("type");
        switch (type) {
            case "telemetry":
                DroneTelemetry t = DroneTelemetry.fromJson(o);
                if (t != null) upsert(t);
                break;
            case "drone_gone":
                remove(o.optInt("sysid", -1));
                break;
            case "bridge_hello":
                statusView.setTextColor(C_OK);
                statusView.setText(R.string.dhgm_bridge_waiting);
                break;
            default:
                break;
        }
        refreshStatus();
    }

    private void upsert(DroneTelemetry t) {
        drones.put(t.sysid, t);
        View card = cards.get(t.sysid);
        if (card == null) {
            card = PluginLayoutInflater.inflate(pluginContext, R.layout.drone_card, null);
            final int sysid = t.sysid;
            card.setOnClickListener(v -> onCardTap(sysid));
            cards.put(t.sysid, card);
            listView.addView(card);
            showEmpty(false);
        }
        bindCard(card, t);
        trails.addPoint(t.sysid, t.lat, t.lon);   // კონტროლირებადი breadcrumb trail
        // follow — რუკა მიჰყვება არჩეულ დრონს
        if (t.sysid == followSysid) {
            centerOn(t);
        }
    }

    private void remove(int sysid) {
        drones.remove(sysid);
        View card = cards.remove(sysid);
        if (card != null) listView.removeView(card);
        if (sysid == followSysid) followSysid = -1;
        trails.remove(sysid);
        if (cards.isEmpty()) showEmpty(true);
    }

    /** ბარათზე tap: რუკაზე ცენტრირება + follow toggle (მეორე tap → follow off). */
    private void onCardTap(int sysid) {
        DroneTelemetry t = drones.get(sysid);
        if (t == null) return;
        centerOn(t);
        followSysid = (followSysid == sysid) ? -1 : sysid;
        // ყველა ბარათის follow-ვიზუალის განახლება
        for (Map.Entry<Integer, DroneTelemetry> e : drones.entrySet()) {
            View card = cards.get(e.getKey());
            if (card != null) bindCard(card, e.getValue());
        }
    }

    /** რუკა დრონზე — უპირატესად CoT მარკერზე (DHGM.&lt;sysid&gt;, პანელ↔რუკა სინქრონი),
     *  თუ არ არსებობს — TCP-ტელემეტრიის კოორდინატზე. */
    private void centerOn(DroneTelemetry t) {
        try {
            if (mapView == null) return;
            GeoPoint target = new GeoPoint(t.lat, t.lon);
            com.atakmap.android.maps.MapItem mi =
                    mapView.getRootGroup().deepFindUID("DHGM." + t.sysid);
            if (mi instanceof com.atakmap.android.maps.PointMapItem) {
                GeoPoint p = ((com.atakmap.android.maps.PointMapItem) mi).getPoint();
                if (p != null) target = p;
            }
            mapView.getMapController().panTo(target, true);
        } catch (Exception e) {
            Log.w(TAG, "panTo failed: " + e.getMessage());
        }
    }

    private void bindCard(View card, DroneTelemetry t) {
        TextView callsign = card.findViewById(R.id.dhgm_card_callsign);
        TextView battery = card.findViewById(R.id.dhgm_card_battery);
        TextView altspeed = card.findViewById(R.id.dhgm_card_altspeed);
        TextView modegps = card.findViewById(R.id.dhgm_card_modegps);
        View dot = card.findViewById(R.id.dhgm_card_status_dot);

        boolean followed = t.sysid == followSysid;
        boolean stale = t.isStale(System.currentTimeMillis());

        callsign.setText(followed ? "▶ " + t.callsign : t.callsign);
        card.setBackgroundColor(followed ? C_CARD_FOLLOW : C_CARD);

        // ბატარეა + ფერი
        if (t.batteryPct != null) {
            battery.setText(t.batteryPct + "%");
            battery.setTextColor(batteryColor(t.batteryLevel()));
        } else {
            battery.setText(R.string.dhgm_batt_unknown);
            battery.setTextColor(C_MUTED);
        }

        String alt = t.altAglM != null
                ? String.format("%.0f m AGL", t.altAglM)
                : (t.altMslM != null ? String.format("%.0f m MSL", t.altMslM) : "— m");
        altspeed.setText(pluginContext.getString(
                R.string.dhgm_card_altspeed, alt, t.speedMps, t.courseDeg));

        String extra = t.satellites != null ? " (" + t.satellites + ")" : "";
        if (t.rssiDbm != null) extra += " · RSSI " + t.rssiDbm + "dBm";
        String mode = t.flightMode == null || t.flightMode.isEmpty() ? "—" : t.flightMode;
        String gps = t.gpsFix == null || t.gpsFix.isEmpty() ? "—" : t.gpsFix;
        modegps.setText(pluginContext.getString(R.string.dhgm_card_modegps, mode, gps, extra));

        // სტატუს-წერტილი: stale → ნაცრისფერი, თორემ მწვანე
        dot.setBackgroundColor(stale ? C_MUTED : C_OK);
    }

    private void refreshStatus() {
        if (drones.isEmpty()) {
            statusView.setText(R.string.dhgm_bridge_waiting);
            statusView.setTextColor(C_OK);
        } else {
            statusView.setText(pluginContext.getString(
                    R.string.dhgm_bridge_connected, drones.size()));
            statusView.setTextColor(C_OK);
        }
    }

    private int batteryColor(int level) {
        switch (level) {
            case 2: return C_OK;
            case 1: return C_WARN;
            case 0: return C_CRIT;
            default: return C_MUTED;
        }
    }

    private void showEmpty(boolean empty) {
        if (empty) {
            if (emptyView.getParent() == null) listView.addView(emptyView);
        } else {
            if (emptyView.getParent() != null) listView.removeView(emptyView);
        }
    }

    private void startTicker() {
        if (!ticking) {
            ticking = true;
            ui.postDelayed(staleTicker, STALE_TICK_MS);
        }
    }

    private void stopTicker() {
        ticking = false;
        ui.removeCallbacks(staleTicker);
    }
}
