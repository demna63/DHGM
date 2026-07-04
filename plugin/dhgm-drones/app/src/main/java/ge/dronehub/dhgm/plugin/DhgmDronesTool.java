package ge.dronehub.dhgm.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;

import ge.dronehub.dhgm.plugin.R;

/**
 * Toolbar ხელსაწყო — დრონების პანელის გახსნა.
 */
public class DhgmDronesTool extends AbstractPluginTool {

    public DhgmDronesTool(Context context) {
        super(
                context,
                context.getString(R.string.dhgm_drones_title),
                context.getString(R.string.dhgm_drones_summary),
                context.getResources().getDrawable(R.drawable.ic_drone_tool),
                DhgmDronesDropDownReceiver.SHOW_DRONES);
    }
}
