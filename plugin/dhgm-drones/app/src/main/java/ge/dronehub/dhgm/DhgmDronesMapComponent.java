package ge.dronehub.dhgm;

import android.content.Context;
import android.content.Intent;

import com.atakmap.android.dropdown.DropDownMapComponent;
import com.atakmap.android.ipc.AtakBroadcast.DocumentedIntentFilter;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.log.Log;

import ge.dronehub.dhgm.plugin.DhgmDronesDropDownReceiver;
import ge.dronehub.dhgm.plugin.R;

/**
 * რეგისტრირებს დრონების პანელის DropDown receiver-ს.
 */
public class DhgmDronesMapComponent extends DropDownMapComponent {

    private static final String TAG = "DhgmDronesMapComponent";

    private DhgmDronesDropDownReceiver dropDown;

    @Override
    public void onCreate(final Context context, final Intent intent, final MapView view) {
        context.setTheme(R.style.ATAKPluginTheme);
        super.onCreate(context, intent, view);
        dropDown = new DhgmDronesDropDownReceiver(view, context);
        DocumentedIntentFilter filter = new DocumentedIntentFilter();
        filter.addAction(DhgmDronesDropDownReceiver.SHOW_DRONES);
        registerDropDownReceiver(dropDown, filter);
        Log.d(TAG, "DHGM drones plugin registered");
    }

    @Override
    protected void onDestroyImpl(final Context context, final MapView view) {
        super.onDestroyImpl(context, view);
    }
}
