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

        trimSettings();

        Log.d(TAG, "DHGM drones plugin registered");
    }

    /**
     * DHGM-ისთვის ზედმეტი settings-entry-ების მოხსნა runtime-ზე.
     *
     * ATAK-ის settings-ეკრანი პროგრამულადაა აწყობილი
     * ({@code ToolsPreferenceFragment.register}), არა სტატიკური main_preferences.xml-იდან —
     * ამიტომ overlay-ის XML-რედაქტი მას ვერ ცვლის. აქ იმავე ფრაგმენტის public
     * {@code unregister(key)}-ს ვიძახებთ (plugin core-ის შემდეგ იტვირთება → entry-ები
     * უკვე რეგისტრირებულია). key-ის არარსებობა უვნებელი no-op-ია.
     *
     * settingsPref (ქსელი) — TAK server + „SERVER CONNECTIONS" crash-ვექტორი ახალ
     * Android-ზე; DHGM LAN multicast-ს იყენებს. bluetoothPref / atakAccounts —
     * DHGM-ს არ სჭირდება.
     */
    private void trimSettings() {
        final String[] keys = { "settingsPref", "bluetoothPref", "atakAccounts" };
        for (String key : keys) {
            try {
                com.atakmap.app.preferences.ToolsPreferenceFragment.unregister(key);
            } catch (Throwable t) {
                Log.w(TAG, "unregister " + key + " failed: " + t.getMessage());
            }
        }
        Log.d(TAG, "settings trimmed (network/bluetooth/accounts)");
    }

    @Override
    protected void onDestroyImpl(final Context context, final MapView view) {
        super.onDestroyImpl(context, view);
    }
}
