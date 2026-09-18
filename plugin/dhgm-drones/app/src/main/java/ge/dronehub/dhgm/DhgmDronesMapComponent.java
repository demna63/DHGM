package ge.dronehub.dhgm;

import android.content.Context;
import android.content.Intent;

import com.atakmap.android.dropdown.DropDownMapComponent;
import com.atakmap.android.ipc.AtakBroadcast.DocumentedIntentFilter;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.log.Log;

import com.atakmap.android.ipc.AtakBroadcast;

import ge.dronehub.dhgm.plugin.DhgmDronesDropDownReceiver;
import ge.dronehub.dhgm.plugin.DhgmLanguageReceiver;
import ge.dronehub.dhgm.plugin.R;

/**
 * რეგისტრირებს დრონების პანელის DropDown receiver-ს.
 */
public class DhgmDronesMapComponent extends DropDownMapComponent {

    private static final String TAG = "DhgmDronesMapComponent";

    private DhgmDronesDropDownReceiver dropDown;
    private DhgmLanguageReceiver language;

    @Override
    public void onCreate(final Context context, final Intent intent, final MapView view) {
        context.setTheme(R.style.ATAKPluginTheme);
        super.onCreate(context, intent, view);
        dropDown = new DhgmDronesDropDownReceiver(view, context);
        DocumentedIntentFilter filter = new DocumentedIntentFilter();
        filter.addAction(DhgmDronesDropDownReceiver.SHOW_DRONES);
        registerDropDownReceiver(dropDown, filter);

        // შენიშვნა: ზედმეტი settings-entry-ების (Network/Bluetooth/Accounts) მოჭრა
        // overlay-ზე ხდება (apply-dhgm-overlay.sh 9/9 — my_preferences.xml +
        // main_preferences.xml), plugin runtime-ზე კი არა: settings-ის top-level
        // ეკრანი core-ის static res/xml-ია, არა plugin-ით რეგისტრირებული.

        // ენის გადართვა (toolbar → „ენა / Language"); არჩევანს core-ის DhgmLocale კითხულობს.
        language = new DhgmLanguageReceiver(view, context);
        DocumentedIntentFilter langFilter = new DocumentedIntentFilter();
        langFilter.addAction(DhgmLanguageReceiver.SHOW_LANGUAGE,
                "DHGM: აპის ენის არჩევა (ქართული / English / სისტემის)");
        AtakBroadcast.getInstance().registerReceiver(language, langFilter);

        Log.d(TAG, "DHGM drones plugin registered");
    }

    @Override
    protected void onDestroyImpl(final Context context, final MapView view) {
        if (language != null) {
            try {
                AtakBroadcast.getInstance().unregisterReceiver(language);
            } catch (Exception ignored) {
                // already unregistered
            }
            language = null;
        }
        super.onDestroyImpl(context, view);
    }
}
