package ge.dronehub.dhgm.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;

import ge.dronehub.dhgm.plugin.R;

/**
 * Toolbar ხელსაწყო — ATAK-ის native GeoChat-ის გახსნა.
 *
 * GeoChat mesh SA multicast-ზე მუშაობს (239.2.3.1:6969) — ე.ი. ერთ LAN/ჰოსტზე მყოფი
 * DHGM მოწყობილობები ერთმანეთს პირდაპირ მიმოწერენ, TAK server-ის გარეშე. chat ფუნქცია
 * ATAK-ში სრულად არსებობს, უბრალოდ ხილული toolbar-შესვლა აღარ ჰქონდა — ეს ღილაკი
 * აგზავნის ATAK-ის {@code com.atakmap.android.OPEN_GEOCHAT} intent-ს (ChatManagerMapComponent
 * იჭერს) და chat-ფანჯარას ხსნის.
 */
public class DhgmChatTool extends AbstractPluginTool {

    /** ATAK ChatManagerMapComponent-ის GeoChat-გამხსნელი action. */
    private static final String OPEN_GEOCHAT = "com.atakmap.android.OPEN_GEOCHAT";

    public DhgmChatTool(Context context) {
        super(
                context,
                context.getString(R.string.dhgm_chat_title),
                context.getString(R.string.dhgm_chat_summary),
                context.getResources().getDrawable(R.drawable.ic_chat_tool),
                OPEN_GEOCHAT);
    }
}
