package ge.dronehub.dhgm.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginLifecycle;

import ge.dronehub.dhgm.DhgmDronesMapComponent;

/**
 * DHGM დრონების პანელი — plugin lifecycle (skeleton).
 * იხ. plugin/dhgm-drones/README.md
 */
public class DhgmDronesLifecycle extends AbstractPluginLifecycle {

    public DhgmDronesLifecycle(Context ctx) {
        super(ctx, new DhgmDronesMapComponent());
    }
}
