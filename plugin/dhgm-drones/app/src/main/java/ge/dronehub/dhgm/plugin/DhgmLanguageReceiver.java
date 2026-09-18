package ge.dronehub.dhgm.plugin;

import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.preference.PreferenceManager;

import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.log.Log;

/**
 * ენის გადართვა — toolbar „ენა / Language".
 *
 * <p>არჩევანს ATAK-ის default SharedPreferences-ში წერს key-ით {@link #PREF_KEY};
 * core-ის მხარეს მას {@code com.atakmap.app.DhgmLocale} კითხულობს
 * ({@code attachBaseContext} → {@code createConfigurationContext}), იხ.
 * {@code tools/patch-locale-override.py}. ⚠️ key ორივე მხარეს ერთნაირ უნდა იყოს.
 *
 * <p>Android-ი Activity-ების resources-ს ხელახლა ქმნის მხოლოდ გაშვებისას, ამიტომ
 * არჩევის შემდეგ აპის გადატვირთვას ვთავაზობთ ({@code com.atakmap.app.QUITAPP}).
 */
public class DhgmLanguageReceiver extends BroadcastReceiver {

    private static final String TAG = "DhgmLanguage";

    public static final String SHOW_LANGUAGE = "ge.dronehub.dhgm.plugin.SHOW_LANGUAGE";

    /** იგივე key, რასაც com.atakmap.app.DhgmLocale.PREF_KEY. */
    static final String PREF_KEY = "dhgm_language";
    static final String SYSTEM = "system";
    /** იგივე, რაც com.atakmap.app.DhgmLocale.DEFAULT — DHGM ნაგულისხმევად ქართულია. */
    static final String DEFAULT = "ka";

    /** რიგი დიალოგის პუნქტების რიგს ემთხვევა (R.array-ს plugin-ში არ ვიყენებთ). */
    private static final String[] VALUES = {
            SYSTEM, "ka", "en"
    };

    private final MapView mapView;
    private final Context pluginContext;

    public DhgmLanguageReceiver(final MapView mapView, final Context pluginContext) {
        this.mapView = mapView;
        this.pluginContext = pluginContext;
    }

    /** ATAK-ის (არა plugin-ის) preferences — core იქიდან კითხულობს. */
    private SharedPreferences atakPrefs() {
        return PreferenceManager.getDefaultSharedPreferences(mapView.getContext());
    }

    private int currentIndex() {
        final String lang = atakPrefs().getString(PREF_KEY, DEFAULT);
        for (int i = 0; i < VALUES.length; i++) {
            if (VALUES[i].equals(lang)) {
                return i;
            }
        }
        return 0;
    }

    @Override
    public void onReceive(final Context context, final Intent intent) {
        if (intent == null || !SHOW_LANGUAGE.equals(intent.getAction())) {
            return;
        }
        final String[] labels = {
                pluginContext.getString(R.string.dhgm_lang_system),
                pluginContext.getString(R.string.dhgm_lang_ka),
                pluginContext.getString(R.string.dhgm_lang_en),
        };
        final int[] chosen = {
                currentIndex()
        };

        new AlertDialog.Builder(mapView.getContext())
                .setTitle(pluginContext.getString(R.string.dhgm_lang_title))
                .setSingleChoiceItems(labels, chosen[0],
                        (dialog, which) -> chosen[0] = which)
                .setNegativeButton(pluginContext.getString(R.string.dhgm_cancel), null)
                .setPositiveButton(pluginContext.getString(R.string.dhgm_apply),
                        (dialog, which) -> apply(VALUES[chosen[0]]))
                .show();
    }

    private void apply(final String language) {
        final String previous = atakPrefs().getString(PREF_KEY, DEFAULT);
        atakPrefs().edit().putString(PREF_KEY, language).apply();
        Log.d(TAG, "language: " + previous + " → " + language);
        if (language.equals(previous)) {
            return;  // არაფერ შეიცვალა — გადატვირთვა ზედმეტია
        }
        new AlertDialog.Builder(mapView.getContext())
                .setTitle(pluginContext.getString(R.string.dhgm_lang_restart_title))
                .setMessage(pluginContext.getString(R.string.dhgm_lang_restart_msg))
                .setNegativeButton(pluginContext.getString(R.string.dhgm_lang_restart_later), null)
                .setPositiveButton(pluginContext.getString(R.string.dhgm_lang_restart_now),
                        (dialog, which) -> {
                            final Intent quit = new Intent("com.atakmap.app.QUITAPP");
                            quit.putExtra("FORCE_QUIT", true);
                            AtakBroadcast.getInstance().sendBroadcast(quit);
                        })
                .show();
    }
}
