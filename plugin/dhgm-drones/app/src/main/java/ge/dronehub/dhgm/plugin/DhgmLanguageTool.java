package ge.dronehub.dhgm.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;

import ge.dronehub.dhgm.plugin.R;

/**
 * Toolbar ხელსაწყო — აპის ენის არჩევა (ქართული / English / სისტემის).
 * იხ. {@link DhgmLanguageReceiver}.
 */
public class DhgmLanguageTool extends AbstractPluginTool {

    public DhgmLanguageTool(Context context) {
        super(
                context,
                context.getString(R.string.dhgm_lang_title),
                context.getString(R.string.dhgm_lang_summary),
                context.getResources().getDrawable(R.drawable.ic_language_tool),
                DhgmLanguageReceiver.SHOW_LANGUAGE);
    }
}
