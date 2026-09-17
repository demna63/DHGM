package ge.dronehub.dhgm.plugin;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.preference.PreferenceManager;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.dropdown.DropDown;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.log.Log;

/**
 * დრონების პანელი — bridge TCP-ს უსმენს და ცოცხალ ტელემეტრიას ბარათებად ხატავს
 * {@link DronePanel}-ის მეშვეობით.
 *
 * <p>კავშირის lifecycle = <b>plugin-ის lifecycle</b> (არა dropdown-ის): შენახულ host-ზე
 * plugin-ის ჩატვირთვისას ავტომატურად უკავშირდება და dropdown-ის დახურვის შემდეგაც
 * ფონზე მუშაობს (follow, marker heading, trail). კავშირი მხოლოდ {@link #disposeImpl()}-ზე
 * ან „დაკავშირება" ღილაკზე (ახალ host) წყდება.
 *
 * <p>host: bridge-ის (Mac-ის) LAN IP:port. {@code 127.0.0.1} ტელეფონზე მხოლოდ
 * {@code adb reverse tcp:14550 tcp:14550}-ით მუშაობს.
 *
 * <p>ყველა public/callback მეთოდი main thread-ზე გამოძახდება (ATAK DropDownReceiver).
 */
public class DhgmDronesDropDownReceiver extends DropDownReceiver
        implements DropDown.OnStateListener {

    private static final String TAG = "DhgmDronesDropDown";

    public static final String SHOW_DRONES =
            "ge.dronehub.dhgm.plugin.SHOW_DRONES";

    private static final String PREF_HOST = "dhgm_bridge_host";

    private final Context pluginContext;
    private final View panelView;
    private final DronePanel panel;
    private final SharedPreferences prefs;
    private final EditText hostInput;
    private final TextView connTcp;
    private BridgeTcpClient bridgeClient;
    private int sessionCounter = 0;

    public DhgmDronesDropDownReceiver(final MapView mapView, final Context context) {
        super(mapView);
        this.pluginContext = context;
        this.prefs = PreferenceManager.getDefaultSharedPreferences(mapView.getContext());
        panelView = PluginLayoutInflater.inflate(context, R.layout.drone_panel, null);
        panel = new DronePanel(context, panelView, mapView);

        final String saved = prefs.getString(PREF_HOST, "");
        hostInput = panelView.findViewById(R.id.dhgm_host_input);
        hostInput.setText(saved);

        connTcp = panelView.findViewById(R.id.dhgm_conn_tcp);

        Button connectBtn = panelView.findViewById(R.id.dhgm_connect_btn);
        connectBtn.setOnClickListener(v -> connectTo(hostInput.getText().toString()));

        // ფონური კავშირი plugin-ის ჩატვირთვისთანავე (შენახულ host-ზე).
        connectTo(saved);
    }

    /** (ხელახლა) დაკავშირება; ცარიელ host → idle სტატუსი, კავშირის გარეშე. */
    private void connectTo(String text) {
        if (bridgeClient != null) {
            bridgeClient.disconnect();
            bridgeClient = null;
        }
        final int sessionId = ++sessionCounter;
        final HostPortParser.HostPort hp = HostPortParser.parse(text);
        if (hp == null) {
            prefs.edit().remove(PREF_HOST).apply();
            connTcp.setText(pluginContext.getString(R.string.dhgm_conn_tcp, "—"));
            panel.setIdle(sessionId, R.string.dhgm_host_required);
            return;
        }
        final String normalized = hp.toString();
        prefs.edit().putString(PREF_HOST, normalized).apply();
        hostInput.setText(normalized);
        connTcp.setText(pluginContext.getString(R.string.dhgm_conn_tcp, normalized));

        panel.setConnecting(sessionId, normalized);
        bridgeClient = new BridgeTcpClient(hp.host, hp.port, new BridgeTcpClient.Listener() {
            @Override
            public void onLine(String line) {
                panel.onBridgeLine(sessionId, line);
            }

            @Override
            public void onStateChanged(BridgeTcpClient.State state, String detail, long retryInMs) {
                panel.onClientState(sessionId, state, detail, retryInMs);
            }
        });
        bridgeClient.connect();
        Log.d(TAG, "connecting to " + normalized);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) {
            return;
        }
        if (SHOW_DRONES.equals(intent.getAction())) {
            Log.d(TAG, "opening drone panel");
            // კავშირი ფონზე უკვე ცოცხალია — გახსნა მხოლოდ UI-ს აჩვენებს.
            showDropDown(panelView, HALF_WIDTH, FULL_HEIGHT, FULL_WIDTH,
                    HALF_HEIGHT, false, this);
        }
    }

    @Override
    public void onDropDownSelectionRemoved() {
    }

    @Override
    public void onDropDownClose() {
        // განზრახ ცარიელი: ტელემეტრია/follow/trail ფონზე გრძელდება.
    }

    @Override
    public void onDropDownSizeChanged(double width, double height) {
    }

    @Override
    public void onDropDownVisible(boolean v) {
    }

    @Override
    protected void disposeImpl() {
        if (bridgeClient != null) {
            bridgeClient.disconnect();
            bridgeClient = null;
        }
        panel.dispose();
    }
}
