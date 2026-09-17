# DHGM Drones — ATAK plugin (ფაზა 2a skeleton)

ATAK-CIV plugin SDK-ზე დაფუძნებული მოდული — დრონების პანელი + bridge TCP JSON.

## სტატუსი

**Skeleton** — სრული build საჭიროებს ATAK-CIV წყაროს (`atak/`) და plugin SDK-ს.
იხ. `docs/phase2-drone-panel.md` სრული სპეციფიკაციისთვის.

## ინტეგრაცია ATAK build-ში (მომავალი)

1. `atak/` კლონი + `tools/bootstrap-atak.sh`
2. plugin მოდულის კოპირება `atak/atak/plugins/dhgm-drones/`-ში (ან submodule)
3. `settings.gradle`-ში `include ':plugins:dhgm-drones'`
4. `assembleCivSdk` plugin-ით ერთად

## ლოკალური განვითარება

```bash
# bridge JSON stream
cd bridge && python3 dhgm_bridge.py --sim --plugin-tcp 0.0.0.0:14550

# plugin: პანელზე host = Mac-ის LAN IP:14550 (bridge stderr-ზე ბეჭდავს)
# USB-ით LAN-ის გარეშე: adb reverse tcp:14550 tcp:14550 → host = 127.0.0.1:14550
```

## სტრუქტურა

```
plugin/dhgm-drones/
├── README.md
└── app/src/main/
    ├── assets/plugin.xml
    ├── java/ge/dronehub/dhgm/plugin/
    │   ├── DhgmDronesLifecycle.java
    │   ├── DhgmDronesTool.java
    │   ├── DhgmDronesDropDownReceiver.java
    │   ├── DhgmDronesMapComponent.java
    │   └── BridgeTcpClient.java
    └── res/
        ├── layout/drone_panel.xml
        ├── layout/drone_card.xml
        ├── values/strings.xml
        └── values-ka/strings.xml
```
