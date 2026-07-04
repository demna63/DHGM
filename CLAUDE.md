# CLAUDE.md — DHGM (DroneHub Georgia Map)

## რა არის ეს პროექტი
**ATAK-CIV-ის ბაზაზე** აწყობილი ტაქტიკური რუკის Android აპი ქართული ლოკალიზაციით.
იღებს ტელემეტრიას **DroneHub-GCS**-ისგან (QGC fork, `~/Desktop/DroneHub-GCS`) და რუკაზე
აჩვენებს დრონებს: პოზიცია, გადაადგილება, სიმაღლე, სიჩქარე. დეტალური roadmap → `README.md`.

- აპის სახელი: **DHGM** · applicationId: `ge.dronehub.dhgm` · base: ATAK-CIV `4.6.0.5`
- signing: საკუთარი key (`custom/keys/` — gitignored, backup აუცილებელი!)

## პროექტის რუკა (სად რა დევს)
```
DHGM/
├── bridge/              MAVLink → CoT/JSON წებო (Python; ერთადერთი გარე დამოკ.: pymavlink)
│   ├── dhgm_bridge.py     GCS MAVLink(udp:14445) → ATAK CoT (multicast 239.2.3.1:6969)
│   ├── plugin_tcp.py      ფაზა 2a: JSON telemetry TCP server plugin-ისთვის
│   ├── plugin_json.py     დრონის state → JSON (mode/GPS/RSSI — CoT-ში რაც არ ეტევა)
│   └── tests/             stdlib unittest (test_cot.py, test_plugin_json.py)
├── custom/              ★ ჩვენი მთელი overlay (no hard-fork)
│   ├── overlay/atak/…    ATAK წყაროზე დასადები ფაილები (rsync-ით ზუსტ ხეზე)
│   │   ├── res/values-ka/strings.xml   ქართული თარგმანი (ინკრემენტული, ბლოკებად)
│   │   ├── res/values/colors.xml       DroneHub პალიტრა (navy+ცისფერი; 55 name უცვლელი)
│   │   ├── res/drawable-*/ic_atak_launcher.png   D-ლოგო ხატულა (6 density)
│   │   └── java/.../Permissions.java   permission gate override (storage-only)
│   ├── brand/           dhgm-logo.svg (ხატულების ერთადერთი წყარო) + preview png
│   └── keys/            signing keystore (gitignored!)
├── plugin/dhgm-drones/  ★ ფაზა 2 — ATAK plugin (DroneHub პანელი, ge.dronehub.dhgm)
├── tools/              build/overlay სკრიპტები (იხ. ქვემოთ)
├── docs/               phase2-drone-panel.md (დიზაინი), smoke-test.md (ტესტ-ჩეკლისტი)
├── .github/workflows/  build-dhgm.yml (APK იწყობა Actions-ზე — Linux-only native chain)
├── atak/               ATAK-CIV წყარო — gitignored, ცალკე იკლონება (≈4GB)
└── dist/               build output — gitignored
```

## ხელსაწყოები (`tools/`)
- `bootstrap-atak.sh` — ATAK-CIV კლონირება `atak/`-ში + წინაპირობების შემოწმება.
- `apply-dhgm-overlay.sh` — overlay-ს ადებს `atak/`-ზე (6 ნაბიჯი: rsync, branding,
  DEV_BANNER მოხსნა, applicationId, status bar ფერი, encryption auto-key). იდემპოტენტური.
- `gen-icons.py` — `custom/brand/dhgm-logo.svg` → `drawable-*` ხატულები (cairosvg).
- `gen-keystore.sh` — signing keystore გენერაცია.
- `extract-untranslated.py` — უთარგმნელი სტრინგების სია values-ka-სთვის.

## Build (APK) — მხოლოდ CI-ზე
ATAK-ის native ჯაჭვი (NDK r12b, takthirdparty, conan) **Linux-only**-ია → macOS-ზე
ვერ აიწყობა. overlay ლოკალურად ვითარდება, **APK GitHub Actions-ზე იწყობა**
(`assembleCivSdk` — არა civRelease, ის TAK-ის შიდა conan remote-ს ითხოვს).
დასრულებულ APK-ს ლოკალურად ხელახლა ვაწერთ (`apksigner` v1+v2+v3) სანამ ტელეფონზე დაიდება.
CI გაკვეთილები: host runner + ~30GB ბალასტის წაშლა (დისკი); Python 3.10 venv (conan 1.59);
`ANDROID_NDK_ROOT`/`SDK_ROOT` override; local.properties gradle root-ში; takthirdparty
cache save-on-failure (native build ~1-2სთ, ერთჯერადი).

## Bridge — გაშვება / ტესტი
```bash
cd bridge
python3 -m unittest discover -s tests        # unit ტესტები
python3 dhgm_bridge.py --sim --dry-run --max-ticks 3 --rate 5   # smoke: CoT stdout-ზე
python3 dhgm_bridge.py --sim                 # სიმულირებული დრონი → ATAK multicast
python3 dhgm_bridge.py                        # რეალური GCS ტელემეტრია
python3 dhgm_bridge.py --sim --plugin-tcp 127.0.0.1:14550   # ფაზა 2a JSON stream
```

## არქიტექტურული პრინციპი — "no hard-fork" (GCS-ის იდენტური)
ATAK core ფაილს პირდაპირ (repo-ში) **არ** ვცვლით — სამი მექანიზმი:
1. resource overlay (`custom/overlay/…/res`) — values-ka, colors, ხატულები (upstream უცვლელი).
2. **ATAK plugin** (`plugin/dhgm-drones`) — custom UI/ფუნქცია, არა core-ის რედაქტირება.
3. apply-overlay-ის ქირურგიული sed/python-edit-ები core-ზე (build-დროს, იდემპოტენტური):
   branding, DEV_BANNER, applicationId, Permissions.java, encryption auto-key.

## კონვენციები
- ქართული კომენტარები/დოკები (GCS repo-ს სტილი); კოდის იდენტიფიკატორები ინგლისურად.
- values-ka: მხოლოდ upstream-ში **არსებული** name-ები; validaცია `extract-untranslated.py`-ით.
- CoT გენერაცია pure ფუნქციებში (`cot_event`) — ტესტირებადი, ქსელისგან გამიჯნული.
- დრონის CoT ტიპი: `a-f-A-M-F-Q` (friendly UAV); uid `DHGM.<sysid>`; callsign `DH-<sysid>`.
- MAVLink sysid 250+ და 0 იგნორირდება (GCS/broadcast).

## დომენური კონტექსტი
- მომხმარებელი PX4/ArduPilot-ს და MAVLink-ს კარგად იცნობს — ბაზისური ახსნა არ სჭირდება.
- QGC MAVLink forwarding default: `localhost:14445` (გადამოწმებული GCS წყაროში).
- ATAK ქსელი: mesh SA multicast `239.2.3.1:6969` (UDP), unicast `:4242`.
- ATAK 4.6 Android 11+ თავისებურებები (გადალახული): permission gate WRITE_EXTERNAL_STORAGE
  მარყუჟი → storage-only override; first-run encryption passphrase → auto-key; APK v2+
  ხელმოწერა სავალდებულო; "All files access" ATAK-ს ჩასატვირთად სჭირდება.
- ⚠️ ლიცენზია: ATAK-CIV GPL-ტიპისაა — fork/rebrand ნებადართული, წყაროს გახსნით
  (`LICENSE`, `NOTICE`, `SOURCE_CODE.md`).
