package ge.dronehub.dhgm.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;

import ge.dronehub.dhgm.plugin.R;

/**
 * Toolbar ხელსაწყო — ATAK-ის native contact-list / GeoChat-ის გახსნა.
 *
 * GeoChat mesh SA multicast-ზე მუშაობს (239.2.3.1:6969) — ე.ი. ერთ LAN/ჰოსტზე მყოფი
 * DHGM მოწყობილობები ერთმანეთს პირდაპირ მიმოწერენ, TAK server-ის გარეშე.
 *
 * ⚠️ {@code OPEN_GEOCHAT} კონკრეტული conversation-ის extras-ს ითხოვს (message Bundle) —
 * extras-ის გარეშე არაფერს ხსნის. მთავარი შესასვლელი = contact list
 * ({@code CONTACT_LIST}, extras-ს არ საჭიროებს): აჩვენებს mesh-ზე მყოფ კონტაქტებს +
 * „All Chat Rooms"-ს, საიდანაც chat იწყება.
 */
public class DhgmChatTool extends AbstractPluginTool {

    /** ATAK ContactPresenceDropdown-ის contact-list გამხსნელი (extras არ სჭირდება). */
    private static final String CONTACT_LIST = "com.atakmap.android.contact.CONTACT_LIST";

    public DhgmChatTool(Context context) {
        super(
                context,
                context.getString(R.string.dhgm_chat_title),
                context.getString(R.string.dhgm_chat_summary),
                context.getResources().getDrawable(R.drawable.ic_chat_tool),
                CONTACT_LIST);
    }
}
