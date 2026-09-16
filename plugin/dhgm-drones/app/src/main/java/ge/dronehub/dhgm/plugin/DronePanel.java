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
import java.util.Locale;
import java.util.Map;

/**
 * დრონების პანელის კონტროლერი — bridge-ის JSON ხაზებს აპარსავს და თითო დრონზე
 * ცოცხალ ბარათს ხატავს (callsign, სიმაღლე, სიჩქარე, ბატარეა, რეჟიმი, GPS).
 * ბარათზე tap → რუკაზე ცენტრირება + follow toggle. Follow → რუკა დრონს მიჰყვება.
 * stale დრონი ნაცრისფრდება (ticker-ით, ტელემეტრიის გარეშეც).
 *
 * <p>Thread მოდელი: public მეთოდებ ნებისმიერ thread-იდან გამოძახდებიან; ყველა
 * state/UI-ცვლილება main {@link Handler}-ზე ხდება (<b>არა</b> {@code View.post} — dropdown-ის
 * დახურვისას view detached-ია და მისი post-ებ მომდევნო attach-ამდე ყოვნდებიან,
 * API &lt; 24-ზე კი იკარგებიან). პანელი ფონზეც მუშაობს: follow/heading/trail დახურულ
 * პანელზეც ანახლდება.
 *
 * <p>Session: ყოველ (ხელახლა) დაკავშირება ახალ session id-ს იღებს; ძველ კლიენტის
 * დაგვიანებულ ხაზებ/state-ებ ({@code session != current}) იგნორირდება.
 */
public class DronePanel {

    private static final String TAG = "DhgmDronePanel";

    // DroneHub პალიტრა — colors.xml-იდან იტვირთება (single source; plugin-ს androidx არ აქვს → Resources.getColor).
    private final int C_OK;     // dhgm_accent_green
    private final int C_WARN;   // dhgm_warning (ნარინჯისფერი)
    private final int C_CRIT;   // dhgm_danger (წითელი)
    private final int C_MUTED;  // dhgm_text_disabled (stale/უცნობი)

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
    private int session = 0;       // მხოლოდ main thread-ზე
    private boolean ticking = false;
    private final DroneTrails trails;

    // DroneHub top-down მარკერის ხატულა — ერთხელ იგება, ყველა დრონისთვის საერთო.
    private com.atakmap.coremap.maps.assets.Icon droneIcon;

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

    @SuppressWarnings("deprecation")
    public DronePanel(Context pluginContext, View panelView, MapView mapView) {
        this.pluginContext = pluginContext;
        android.content.res.Resources res = pluginContext.getResources();
        this.C_OK = res.getColor(R.color.dhgm_accent_green);
        this.C_WARN = res.getColor(R.color.dhgm_warning);
        this.C_CRIT = res.getColor(R.color.dhgm_danger);
        this.C_MUTED = res.getColor(R.color.dhgm_text_disabled);
        this.panelView = panelView;
        this.mapView = mapView;
        this.statusView = panelView.findViewById(R.id.dhgm_bridge_status);
        this.listView = panelView.findViewById(R.id.dhgm_drone_list);
        this.emptyView = new TextView(pluginContext);
        this.emptyView.setTextColor(C_MUTED);
        this.emptyView.setTextSize(13);
        this.emptyView.setText(pluginContext.getString(R.string.dhgm_no_drones));
        this.trails = new DroneTrails(pluginContext, mapView);
        showEmpty(true);
    }

    /** bridge-ის ერთი ხაზი (newline-delimited JSON). */
    public void onBridgeLine(final int sessionId, final String line) {
        ui.post(() -> {
            if (sessionId != session) return;
            try {
                handle(new JSONObject(line));
            } catch (Exception e) {
                Log.d(TAG, "bad bridge line: " + e.getMessage());
            }
        });
    }

    /** ახალ session-ის დაწყება — ვუკავშირდები host:port…. */
    public void setConnecting(final int sessionId, final String hostPort) {
        ui.post(() -> {
            session = sessionId;
            clearDrones();
            statusView.setText(pluginContext.getString(R.string.dhgm_connecting, hostPort));
            statusView.setTextColor(C_WARN);
            startTicker();
        });
    }

    /** {@link BridgeTcpClient} state → სტატუს-ხაზი. */
    public void onClientState(final int sessionId, final BridgeTcpClient.State state,
                              final String detail, final long retryInMs) {
        ui.post(() -> {
            if (sessionId != session) return;
            switch (state) {
                case CONNECTING:
                    break;  // setConnecting-ი უკვე აჩვენა
                case CONNECTED:
                    refreshStatus();
                    break;
                case DISCONNECTED:
                    // bridge-ის გარეშე ბარათებ/trail-ებ მატყუარ იქნებოდნენ.
                    clearDrones();
                    statusView.setText(pluginContext.getString(R.string.dhgm_bridge_retrying,
                            detail == null ? "—" : detail,
                            Math.max(1L, (retryInMs + 999L) / 1000L)));
                    statusView.setTextColor(C_CRIT);
                    break;
                default:
                    break;
            }
        });
    }

    /** host ცარიელია — კავშირი არ იწყება. */
    public void setIdle(final int sessionId, final int messageRes) {
        ui.post(() -> {
            session = sessionId;
            clearDrones();
            stopTicker();
            statusView.setText(messageRes);
            statusView.setTextColor(C_MUTED);
        });
    }

    /** plugin unload: ticker-ის შეჩერება + trail-ების/group-ის მოცილება რუკიდან. */
    public void dispose() {
        ui.post(() -> {
            session = -1;
            stopTicker();
            clearDrones();
            trails.dispose();
        });
    }

    private void clearDrones() {
        followSysid = -1;
        drones.clear();
        listView.removeAllViews();
        cards.clear();
        trails.clearAll();
        showEmpty(true);
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
            case "bridge_heartbeat":
                break;  // keepalive — სტატუსს refreshStatus() ანახლებს
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
        styleMarker(t);                           // CoT მარკერს DroneHub ხატულა + heading
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

    /** CoT მარკერს (uid DHGM.&lt;sysid&gt;) DroneHub chevron ხატულას ადებს და heading-ზე აბრუნებს.
     *  მარკერს GCS-ის CoT ქმნის; აქ იკონა/სტილს გადავაწერთ (no-hard-fork) და
     *  adapt_marker_icon=false-ს ვდებთ — ATAK-ის IconsMapAdapter CoT-refresh-ზე
     *  default 2525 იკონას რომ აღარ დააბრუნოს (flicker fix). იდემპოტენტური: მხოლოდ
     *  მაშინ ვამუშავებთ, როცა ფლაგი ჯერ არ დაგვიყენებია (ან CoT-მ მარკერი ხელახლა შექმნა). */
    private void styleMarker(DroneTelemetry t) {
        try {
            if (mapView == null) return;
            com.atakmap.android.maps.MapItem mi =
                    mapView.getRootGroup().deepFindUID("DHGM." + t.sysid);
            if (!(mi instanceof com.atakmap.android.maps.Marker)) return;
            com.atakmap.android.maps.Marker m = (com.atakmap.android.maps.Marker) mi;
            // adapt_marker_icon default = true → ჯერ არ დაგვიმუშავებია (ან ახალი მარკერია).
            if (m.getMetaBoolean("adapt_marker_icon", true)) {
                if (droneIcon == null) {
                    String uri = "android.resource://" + pluginContext.getPackageName()
                            + "/" + R.drawable.ic_drone_marker;
                    droneIcon = new com.atakmap.coremap.maps.assets.Icon.Builder()
                            .setImageUri(com.atakmap.coremap.maps.assets.Icon.STATE_DEFAULT, uri)
                            .setAnchor(com.atakmap.coremap.maps.assets.Icon.ANCHOR_CENTER,
                                       com.atakmap.coremap.maps.assets.Icon.ANCHOR_CENTER)
                            .build();
                }
                m.setMetaBoolean("adapt_marker_icon", false); // CoT-refresh აღარ გადააფარებს 2525-ს
                m.setIcon(droneIcon);
                m.setStyle(m.getStyle()
                        | com.atakmap.android.maps.Marker.STYLE_ROTATE_HEADING_NOARROW_MASK
                        | com.atakmap.android.maps.Marker.STYLE_SMOOTH_ROTATION_MASK);
            }
            m.setTrack(t.courseDeg, t.speedMps);
        } catch (Exception e) {
            Log.w(TAG, "styleMarker failed: " + e.getMessage());
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
        card.setBackgroundResource(followed ? R.drawable.bg_card_follow : R.drawable.bg_card);

        // ბატარეა + ფერი
        if (t.batteryPct != null) {
            battery.setText(t.batteryPct + "%");
            battery.setTextColor(batteryColor(t.batteryLevel()));
        } else {
            battery.setText(R.string.dhgm_batt_unknown);
            battery.setTextColor(C_MUTED);
        }

        String alt = t.altAglM != null
                ? String.format(Locale.US, "%.0f m AGL", t.altAglM)
                : (t.altMslM != null ? String.format(Locale.US, "%.0f m MSL", t.altMslM) : "— m");
        altspeed.setText(pluginContext.getString(
                R.string.dhgm_card_altspeed, alt, t.speedMps, t.courseDeg));

        String extra = t.satellites != null ? " (" + t.satellites + ")" : "";
        if (t.rssiDbm != null) extra += " · RSSI " + t.rssiDbm + "dBm";
        String mode = t.flightMode == null || t.flightMode.isEmpty() ? "—" : t.flightMode;
        String gps = t.gpsFix == null || t.gpsFix.isEmpty() ? "—" : t.gpsFix;
        modegps.setText(pluginContext.getString(R.string.dhgm_card_modegps, mode, gps, extra));

        // სტატუს-წერტილი (round oval): stale → ნაცრისფერი, თორემ მწვანე
        android.graphics.drawable.Drawable dotBg = dot.getBackground();
        if (dotBg instanceof android.graphics.drawable.GradientDrawable) {
            ((android.graphics.drawable.GradientDrawable) dotBg.mutate())
                    .setColor(stale ? C_MUTED : C_OK);
        } else {
            dot.setBackgroundColor(stale ? C_MUTED : C_OK);
        }
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
