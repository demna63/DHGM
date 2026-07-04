package ge.dronehub.dhgm.plugin;

import android.content.Context;
import android.content.Intent;
import android.view.View;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.dropdown.DropDown;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.log.Log;

/**
 * დრონების პანელი (skeleton) — bridge TCP-დან ტელემეტრიის ჩვენება მომავალ ეტაპზე.
 */
public class DhgmDronesDropDownReceiver extends DropDownReceiver
        implements DropDown.OnStateListener {

    private static final String TAG = "DhgmDronesDropDown";

    public static final String SHOW_DRONES =
            "ge.dronehub.dhgm.plugin.SHOW_DRONES";

    private final Context pluginContext;
    private final View panelView;
    private final TextView statusView;
    private BridgeTcpClient bridgeClient;

    public DhgmDronesDropDownReceiver(final MapView mapView, final Context context) {
        super(mapView);
        this.pluginContext = context;
        panelView = PluginLayoutInflater.inflate(context, R.layout.drone_panel, null);
        statusView = panelView.findViewById(R.id.dhgm_bridge_status);
        bridgeClient = new BridgeTcpClient("127.0.0.1", 14550, this::onBridgeLine);
    }

    private void onBridgeLine(String line) {
        if (statusView != null) {
            statusView.post(() -> statusView.setText(
                    pluginContext.getString(R.string.dhgm_bridge_line, line)));
        }
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) {
            return;
        }
        if (SHOW_DRONES.equals(intent.getAction())) {
            Log.d(TAG, "opening drone panel");
            bridgeClient.connect();
            showDropDown(panelView, HALF_WIDTH, FULL_HEIGHT, FULL_WIDTH,
                    HALF_HEIGHT, false, this);
        }
    }

    @Override
    public void onDropDownSelectionRemoved() {
    }

    @Override
    public void onDropDownClose() {
        bridgeClient.disconnect();
    }

    @Override
    public void onDropDownSizeChanged(double width, double height) {
    }

    @Override
    public void onDropDownVisible(boolean v) {
    }

    public void dispose() {
        bridgeClient.disconnect();
    }
}
