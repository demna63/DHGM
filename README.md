# DHGM — DroneHub Georgia Map

**ATAK-CIV-ის ბაზაზე აწყობილი ტაქტიკური რუკის აპი** ქართული ლოკალიზაციით და
[DroneHub GCS](../DroneHub-GCS)-თან ლოკალური კავშირით: GCS-იდან მიღებული MAVLink
ტელემეტრიით DHGM-ის რუკაზე ჩანს დრონი — მისი გადაადგილება, სიმაღლე და სიჩქარე.

```
┌─────────────────┐  MAVLink forwarding   ┌──────────────┐   CoT (UDP)    ┌──────────────┐
│  DroneHub GCS    │ ────────────────────▶ │ dhgm-bridge  │ ─────────────▶ │  DHGM (ATAK) │
│  (macOS/Win/Lin) │  udp localhost:14445  │  (Python)    │ 239.2.3.1:6969 │  Android     │
└─────────────────┘                        └──────────────┘  ან IP:4242    └──────────────┘
        ▲ MAVLink (radio/UDP)
     🛸 დრონი (PX4 / ArduPilot)
```

პრინციპი იგივეა, რაც DroneHub-GCS-ში: **no hard-fork** — ATAK-ის core-ს არ ვამტვრევთ,
ვცხოვრობთ plugin-ებით, resource overlay-ებით (values-ka) და მინიმალური patch-ებით,
რომ upstream-ის უსაფრთხოების განახლებები ადვილად ავიღოთ.

---

## ფაზები

### ფაზა 0 — bridge (✅ მუშაობს დღესვე, stock ATAK-CIV-თან)
ATAK-ის fork-ის მოლოდინის გარეშე დრონი უკვე გამოჩნდება რუკაზე:

1. დააყენე ოფიციალური **ATAK-CIV** APK Android ტაბლეტზე (tak.gov / Play Store).
2. DroneHub GCS-ში: *Settings → MAVLink → Enable MAVLink forwarding* (default `localhost:14445`).
3. გაუშვი bridge:
   ```bash
   python3 bridge/dhgm_bridge.py                      # multicast — იგივე Wi-Fi ქსელზე
   python3 bridge/dhgm_bridge.py --cot-udp <ტაბლეტის-IP>:4242   # unicast
   ```
4. სატესტოდ დრონის გარეშე: `python3 bridge/dhgm_bridge.py --sim` — სიმულირებული
   დრონი წრეზე თბილისის ცენტრთან (DH-1, 120მ AGL, 15 მ/წმ).

bridge თითო დრონზე (MAVLink sysid) აგზავნის CoT event-ს 1 Hz-ით:
პოზიცია (`GLOBAL_POSITION_INT`), კურსი/სიჩქარე (`track`), სიმაღლე AGL/MSL,
ბატარეა (`SYS_STATUS`) — remarks-ში. Callsign: `DH-<sysid>`.

ტესტები: `cd bridge && python3 -m unittest discover -s tests`

Plugin TCP (ფაზა 2a): `python3 bridge/dhgm_bridge.py --sim --plugin-tcp 0.0.0.0:14550` → პანელზე host = Mac-ის LAN IP:14550 (bridge stderr-ზე ბეჭდავს). `127.0.0.1` ტელეფონზე მხოლოდ `adb reverse tcp:14550 tcp:14550`-ით მუშაობს.

### ფაზა 1 — DHGM fork (branding + ქართული) ✅

**Build სტრატეგია:** ATAK-ის native ჯაჭვი (NDK r12b, takthirdparty, conan) **Linux-only**-ია —
macOS-ზე APK ვერ აიწყობა. ამიტომ GCS-ის ანალოგიით: overlay ლოკალურად ვითარდება,
**APK GitHub Actions-ზე იწყობა** (`.github/workflows/build-dhgm.yml` — ATAK-ის ოფიციალური
CI-ის ადაპტაცია + ჩვენი overlay + ჩვენი signing).

**ფაზა 1 UI პაკეტი (დასრულებული):**
- Splash + launcher + **adaptive icon** (API 26+)
- Design tokens (`dhgm_design.xml`) + DroneHub ფერთა პალიტრა
- **Noto Sans Georgian** (`values-ka/styles.xml` + `res/font/`)
- ქართული overlay **4015** სტრინგი (სრული upstream values/strings.xml)
- `applicationId` `ge.dronehub.dhgm`, signing, EULA auto-key

**Release:** `git tag v0.1.0 && git push origin v0.1.0` → CI აწყობს APK-ს და ქმნის GitHub Release-ს.

ხელსაწყოები:
- `tools/bootstrap-atak.sh` — ATAK-CIV წყაროს კლონირება `atak/`-ში (gitignored,
  ზუსტად როგორც `qgroundcontrol/` DroneHub-GCS-ში).
- `tools/apply-dhgm-overlay.sh` — `custom/overlay/` → `atak/` + app label ATAK→DHGM (იდემპოტენტური).
- `tools/gen-keystore.sh` — signing keystore (`custom/keys/` — gitignored, backup აუცილებელია!).
- `tools/extract-untranslated.py` — უთარგმნელი სტრინგების სია values-ka-სთვის (4219 სტრინგი სულ;
  ვთარგმნით ინკრემენტულად, GCS-ის qgc_ka.ts-ის მოდელით).
- Rebrand: სახელი **DHGM**, DroneHub Georgia ლოგო/ხატულები, applicationId `ge.dronehub.dhgm`.
- **ქართული ლოკალიზაცია**: `res/values-ka/strings.xml` overlay — ATAK-ის სტრინგები
  ითარგმნება ისე, რომ upstream ფაილები არ იცვლება (GCS-ის `qgc_ka.ts`-ის ანალოგი).
  Noto Sans Georgian უკვე გვაქვს GCS repo-ში — იგივე ფონტი.
- საკუთარი signing key: ჩვენი build მხოლოდ ჩვენს plugin-ებს ჩატვირთავს — Play Store
  ATAK-ის TAK.gov ხელმოწერის შეზღუდვას ეს ხსნის.
- ⚠️ ლიცენზია: ATAK-CIV ღია კოდია GPL-ტიპის ლიცენზიით — fork/rebrand ნებადართულია,
  გავრცელებისას წყაროს გახსნის ვალდებულებით. ზუსტი პირობები `atak/LICENSE`-შია.

### ფაზა 2 — DHGM plugin (DroneHub პანელი)
ATAK plugin SDK-ზე — ეს არის „ჩემზე მორგებული ინტერფეისის" ძირითადი ადგილი:
- დრონების პანელი: სია, თითოეულზე **სიმაღლე / სიჩქარე / ბატარეა / კავშირის სტატუსი** ცოცხლად.
- CoT-ის ნაცვლად პირდაპირი TCP კავშირი bridge-თან (JSON stream) — მდიდარი ტელემეტრია,
  რომელიც CoT-ში არ ეტევა (mode, GPS fix, RSSI).
- დრონზე tap → follow რეჟიმი, ტრაექტორიის კვალი (breadcrumbs).

### ფაზა 3 — bridge-ის ინტეგრაცია GCS-ში ✅

`CotForwarder` C++ მოდული DroneHub-GCS-ის `custom/src/`-ში: Settings → **„DHGM-ზე გადაცემა"** —
CoT multicast (`239.2.3.1:6969`) + plugin TCP JSON (`:14550`, 1 Hz `bridge_heartbeat`), Python bridge-ის გარეშე.
პანელზე host = Mac-ის LAN IP:14550.

⚠️ **ერთ წყარო**: GCS-ის „DHGM-ზე გადაცემა" **ან** Python bridge — ორივე ერთდროულად იგივე
`DHGM.<sysid>` uid-ს ქმნის და მარკერი ორ წყაროს შორის ხტუნავს (bridge ამას stderr-ზე ატყობინებს).

---

## Release

```bash
tools/release.sh 0.3.1     # ტესტებ → VERSION → commit → tag v0.3.1 → push → CI → GitHub Release
```

## სტრუქტურა

```
DHGM/
├── README.md · CLAUDE.md · VERSION
├── bridge/                    MAVLink → CoT + plugin TCP JSON (Python)
│   ├── dhgm_bridge.py         CoT, SIM, duplicate-source monitor
│   ├── plugin_tcp.py          TCP hub (hello/heartbeat, backpressure)
│   ├── plugin_json.py         JSON სქემა (telemetry/hello/heartbeat/gone)
│   └── tests/                 unittest (CoT, JSON, regressions)
├── plugin/dhgm-drones/        ATAK plugin — დრონების პანელი
│   ├── app/src/main/java/…    BridgeTcpClient, HostPortParser, DronePanel, DroneTrails, …
│   └── jvmtest/               pure-Java ტესტებ (tools/run-plugin-jvm-tests.sh)
├── custom/                    overlay (values-ka, brand, Permissions.java) + keys (gitignored)
├── tools/                     bootstrap/overlay/icons/keystore/release/tests
├── docs/                      usage, smoke-test, phase2-drone-panel, distribution
├── .github/workflows/         build-dhgm.yml (APK + Release), pages.yml
└── atak/                      ATAK-CIV წყარო (gitignored)
```

## კავშირი ეკოსისტემასთან

| პროექტი | როლი |
|---------|------|
| **DroneHub-GCS** | ფრენის მართვა, mission planning — ტელემეტრიის წყარო DHGM-სთვის |
| **DHGM** (ეს repo) | ტაქტიკური რუკა, სიტუაციური ცნობიერება, გუნდური გაზიარება |
| dhgm-bridge | წებო: MAVLink → CoT |
