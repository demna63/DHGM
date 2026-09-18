package com.atakmap.app;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.Configuration;
import android.os.Build;
import android.os.LocaleList;
import android.preference.PreferenceManager;

import com.atakmap.coremap.log.Log;

import java.util.Locale;

/**
 * DHGM: აპლიკაციის ენა მოწყობილობის locale-ისგან დამოუკიდებლად.
 *
 * <p>ATAK-ს საკუთარი ენის არჩევანი არ აქვს — ის სისტემის locale-ს მიჰყვება, ე.ი. ინგლისურ
 * ტელეფონზე ჩვენ ქართულ `values-ka` overlay-ს არ იყენებდა. აქ შენახულ არჩევანს
 * ({@link #PREF_KEY}) ყოველ Activity/Application context-ზე ვადებთ.
 *
 * <p>ჩართვა: {@code attachBaseContext(DhgmLocale.wrap(base))} —
 * {@code MetricFragmentActivity}, {@code MetricPreferenceActivity}, {@code ATAKApplication}
 * (იხ. {@code tools/patch-locale-override.py}).
 *
 * <p>UI: DHGM plugin → toolbar „ენა / Language". ცვლილება ძალაში აპის გადატვირთვისას შედის
 * (Android-ი Activity-ების resources-ს ხელახლა ქმნის).
 */
public final class DhgmLocale {

    private static final String TAG = "DhgmLocale";

    /** SharedPreferences key — ენის კოდი ("ka", "en") ან {@link #SYSTEM}. */
    public static final String PREF_KEY = "dhgm_language";

    /** მოწყობილობის locale-ს მიჰყვება. */
    public static final String SYSTEM = "system";

    /** DHGM-ის ნაგულისხმევ ენა — ქართულ (ქართულ პროდუქტია; ინგლისურ ტელეფონზეც). */
    public static final String DEFAULT = "ka";

    /** მხარდაჭერილი ენებ — plugin-ის დიალოგიც ამ რიგს იყენებს. */
    public static final String[] SUPPORTED = {
            SYSTEM, "ka", "en"
    };

    private DhgmLocale() {
    }

    /** შენახულ არჩევანი; თუ არჩევანი არ არის — {@link #DEFAULT} (ქართულ). */
    public static String getLanguage(final Context context) {
        try {
            final SharedPreferences prefs = PreferenceManager
                    .getDefaultSharedPreferences(context);
            final String lang = prefs.getString(PREF_KEY, DEFAULT);
            return (lang == null || lang.isEmpty()) ? DEFAULT : lang;
        } catch (Exception e) {
            Log.w(TAG, "prefs read failed: " + e.getMessage());
            return DEFAULT;
        }
    }

    /** არჩევანის შენახვა; ძალაში აპის გადატვირთვისას შედის. */
    public static void setLanguage(final Context context, final String language) {
        try {
            PreferenceManager.getDefaultSharedPreferences(context)
                    .edit()
                    .putString(PREF_KEY, language == null ? DEFAULT : language)
                    .apply();
        } catch (Exception e) {
            Log.w(TAG, "prefs write failed: " + e.getMessage());
        }
    }

    /**
     * Context-ს არჩეულ locale-ს ადებს.
     *
     * @return ახალ context (ან იგივე, თუ არჩევანი {@link #SYSTEM}-ია ან შეცდომა მოხდა —
     *         ენა არასოდეს არ უნდა იყოს გაშვების შემაფერხებელი).
     */
    public static Context wrap(final Context base) {
        if (base == null) {
            return null;
        }
        try {
            final String lang = getLanguage(base);
            if (SYSTEM.equals(lang)) {
                return base;
            }
            final Locale locale = new Locale(lang);
            Locale.setDefault(locale);

            final Configuration cfg = new Configuration(
                    base.getResources().getConfiguration());
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                final LocaleList list = new LocaleList(locale);
                LocaleList.setDefault(list);
                cfg.setLocales(list);
            } else {
                cfg.setLocale(locale);
            }
            return base.createConfigurationContext(cfg);
        } catch (Exception e) {
            Log.w(TAG, "locale override failed: " + e.getMessage());
            return base;
        }
    }
}
