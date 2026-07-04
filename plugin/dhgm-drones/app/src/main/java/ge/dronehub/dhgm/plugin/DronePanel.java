package ge.dronehub.dhgm.plugin;

import android.content.Context;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.coremap.log.Log;

import org.json.JSONObject;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * დრონების პანელის კონტროლერი — bridge-ის JSON ხაზებს აპარსავს და თითო დრონზე
 * ცოცხალ ბარათს ხატავს (callsign, სიმაღლე, სიჩქარე, ბატარეა, რეჟიმი, GPS).
 * ყველა UI-ცვლილება panel view-ის thread-ზე (post) ხდება.
 */
public class DronePanel {

    private static final String TAG = "DhgmDronePanel";

    // DroneHub პალიტრა
    private static final int C_OK = 0xFF30D158;       // მწვანე
    private static final int C_WARN = 0xFFFF9F0A;     // ნარინჯისფერი
    private static final int C_CRIT = 0xFFFF453A;     // წითელი
    private static final int C_MUTED = 0xFF9AA6B8;    // ნაცრისფერი (stale/უცნობი)

    private final Context pluginContext;
    private final View panelView;
    private final TextView statusView;
    private final LinearLayout listView;
    private final TextView emptyView;

    // sysid → (telemetry, card view) — LinkedHashMap რომ რიგი შენარჩუნდეს
    private final Map<Integer, DroneTelemetry> drones = new LinkedHashMap<>();
    private final Map<Integer, View> cards = new LinkedHashMap<>();

    public DronePanel(Context pluginContext, View panelView) {
        this.pluginContext = pluginContext;
        this.panelView = panelView;
        this.statusView = panelView.findViewById(R.id.dhgm_bridge_status);
        this.listView = panelView.findViewById(R.id.dhgm_drone_list);
        this.emptyView = new TextView(pluginContext);
        this.emptyView.setTextColor(C_MUTED);
        this.emptyView.setTextSize(13);
        this.emptyView.setText(pluginContext.getString(R.string.dhgm_no_drones));
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
                drones.clear();
                listView.removeAllViews();
                cards.clear();
                showEmpty(true);
                statusView.setText(R.string.dhgm_bridge_disconnected);
                statusView.setTextColor(C_MUTED);
            }
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
            cards.put(t.sysid, card);
            listView.addView(card);
            showEmpty(false);
        }
        bindCard(card, t);
    }

    private void remove(int sysid) {
        drones.remove(sysid);
        View card = cards.remove(sysid);
        if (card != null) listView.removeView(card);
        if (cards.isEmpty()) showEmpty(true);
    }

    private void bindCard(View card, DroneTelemetry t) {
        TextView callsign = card.findViewById(R.id.dhgm_card_callsign);
        TextView battery = card.findViewById(R.id.dhgm_card_battery);
        TextView altspeed = card.findViewById(R.id.dhgm_card_altspeed);
        TextView modegps = card.findViewById(R.id.dhgm_card_modegps);
        View dot = card.findViewById(R.id.dhgm_card_status_dot);

        callsign.setText(t.callsign);

        // ბატარეა + ფერი
        if (t.batteryPct != null) {
            battery.setText(t.batteryPct + "%");
            battery.setTextColor(batteryColor(t.batteryLevel()));
        } else {
            battery.setText(R.string.dhgm_batt_unknown);
            battery.setTextColor(C_MUTED);
        }

        // სიმაღლე (AGL უპირატესია) · სიჩქარე · კურსი
        String alt = t.altAglM != null
                ? String.format("%.0f m AGL", t.altAglM)
                : (t.altMslM != null ? String.format("%.0f m MSL", t.altMslM) : "— m");
        altspeed.setText(pluginContext.getString(
                R.string.dhgm_card_altspeed, alt, t.speedMps, t.courseDeg));

        // რეჟიმი · GPS (+ სატელიტები თუ არის)
        String sats = t.satellites != null ? " (" + t.satellites + ")" : "";
        String mode = t.flightMode == null || t.flightMode.isEmpty() ? "—" : t.flightMode;
        String gps = t.gpsFix == null || t.gpsFix.isEmpty() ? "—" : t.gpsFix;
        modegps.setText(pluginContext.getString(R.string.dhgm_card_modegps, mode, gps, sats));

        // სტატუს-წერტილი: stale → ნაცრისფერი, თორემ მწვანე
        dot.setBackgroundColor(t.isStale(System.currentTimeMillis()) ? C_MUTED : C_OK);
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
}
