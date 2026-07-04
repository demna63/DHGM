package ge.dronehub.dhgm.plugin;

import android.content.Context;
import android.content.SharedPreferences;
import android.preference.PreferenceManager;
import android.view.View;
import android.content.Intent;
import android.widget.Button;
import android.widget.EditText;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.dropdown.DropDown;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.log.Log;

/**
 * დრონების პანელი — bridge TCP-ს უსმენს და ცოცხალ ტელემეტრიას ბარათებად ხატავს
 * {@link DronePanel}-ის მეშვეობით. host:port კონფიგურირებადია (bridge Mac-ზეც
 * შეიძლება იყოს — მაშინ Mac-ის IP შეიყვანე); ბოლო მისამართი ინახება.
 */
public class DhgmDronesDropDownReceiver extends DropDownReceiver
        implements DropDown.OnStateListener {

    private static final String TAG = "DhgmDronesDropDown";

    public static final String SHOW_DRONES =
            "ge.dronehub.dhgm.plugin.SHOW_DRONES";

    private static final String PREF_HOST = "dhgm_bridge_host";
    private static final String DEFAULT_HOST = "127.0.0.1:14550";

    private final Context pluginContext;
    private final View panelView;
    private final DronePanel panel;
    private final SharedPreferences prefs;
    private final EditText hostInput;
    private BridgeTcpClient bridgeClient;

    public DhgmDronesDropDownReceiver(final MapView mapView, final Context context) {
        super(mapView);
        this.pluginContext = context;
        this.prefs = PreferenceManager.getDefaultSharedPreferences(mapView.getContext());
        panelView = PluginLayoutInflater.inflate(context, R.layout.drone_panel, null);
        panel = new DronePanel(context, panelView);

        hostInput = panelView.findViewById(R.id.dhgm_host_input);
        hostInput.setText(prefs.getString(PREF_HOST, DEFAULT_HOST));

        Button connectBtn = panelView.findViewById(R.id.dhgm_connect_btn);
        connectBtn.setOnClickListener(v -> reconnect());
    }

    /** შეყვანილი host:port-ით (ხელახლა) დაკავშირება. */
    private void reconnect() {
        String hostPort = hostInput.getText().toString().trim();
        if (hostPort.isEmpty()) hostPort = DEFAULT_HOST;
        prefs.edit().putString(PREF_HOST, hostPort).apply();

        String host = hostPort;
        int port = 14550;
        int colon = hostPort.lastIndexOf(':');
        if (colon > 0) {
            host = hostPort.substring(0, colon);
            try {
                port = Integer.parseInt(hostPort.substring(colon + 1).trim());
            } catch (NumberFormatException ignored) {
            }
        }

        if (bridgeClient != null) {
            bridgeClient.disconnect();
        }
        panel.setConnecting(host + ":" + port);
        bridgeClient = new BridgeTcpClient(host, port, panel::onBridgeLine);
        bridgeClient.connect();
        Log.d(TAG, "connecting to " + host + ":" + port);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) {
            return;
        }
        if (SHOW_DRONES.equals(intent.getAction())) {
            Log.d(TAG, "opening drone panel");
            reconnect();
            showDropDown(panelView, HALF_WIDTH, FULL_HEIGHT, FULL_WIDTH,
                    HALF_HEIGHT, false, this);
        }
    }

    @Override
    public void onDropDownSelectionRemoved() {
    }

    @Override
    public void onDropDownClose() {
        if (bridgeClient != null) {
            bridgeClient.disconnect();
        }
        panel.setConnected(false);
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
        }
    }
}
