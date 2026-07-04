package ge.dronehub.dhgm.plugin;

import android.content.Context;
import android.content.Intent;
import android.view.View;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.dropdown.DropDown;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.log.Log;

/**
 * დრონების პანელი — bridge TCP-ს (127.0.0.1:14550) უსმენს და ცოცხალ
 * ტელემეტრიას ბარათებად ხატავს {@link DronePanel}-ის მეშვეობით.
 */
public class DhgmDronesDropDownReceiver extends DropDownReceiver
        implements DropDown.OnStateListener {

    private static final String TAG = "DhgmDronesDropDown";

    public static final String SHOW_DRONES =
            "ge.dronehub.dhgm.plugin.SHOW_DRONES";

    private final View panelView;
    private final DronePanel panel;
    private final BridgeTcpClient bridgeClient;

    public DhgmDronesDropDownReceiver(final MapView mapView, final Context context) {
        super(mapView);
        panelView = PluginLayoutInflater.inflate(context, R.layout.drone_panel, null);
        panel = new DronePanel(context, panelView);
        bridgeClient = new BridgeTcpClient("127.0.0.1", 14550, panel::onBridgeLine);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) {
            return;
        }
        if (SHOW_DRONES.equals(intent.getAction())) {
            Log.d(TAG, "opening drone panel");
            panel.setConnected(true);
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
        panel.setConnected(false);
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
