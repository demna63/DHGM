# CLAUDE.md — DHGM (DroneHub Georgia Map)

## რა არის ეს პროექტი
**ATAK-CIV-ის ბაზაზე** აწყობილი ტაქტიკური რუკის Android აპი ქართული ლოკალიზაციით.
იღებს ტელემეტრიას **DroneHub-GCS**-ისგან (QGC fork, `~/Desktop/DroneHub-GCS`) და რუკაზე
აჩვენებს დრონებს: პოზიცია, გადაადგილება, სიმაღლე, სიჩქარე. დეტალური roadmap → `README.md`.

## სტეკი
- **bridge/** — Python 3.9+, `pymavlink` (ერთადერთი გარე დამოკიდებულება); CoT XML stdlib-ით.
- **atak/** (ფაზა 1+) — ATAK-CIV წყარო: Java/Kotlin + NDK, Gradle. **gitignore-შია** —
  ცალკე იკლონება `tools/bootstrap-atak.sh`-ით (DroneHub-GCS-ის `qgroundcontrol/`-ის ანალოგი).
- პროტოკოლები: MAVLink (შემომავალი, QGC forwarding udp:14445) → CoT 2.0 XML
  (გამავალი, multicast 239.2.3.1:6969 ან unicast :4242).

## არქიტექტურული პრინციპი — "no hard-fork" (GCS-ის იდენტური)
ATAK core ფაილებს პირდაპირ **არ** ვცვლით:
1. ქართული ენა → `res/values-ka/` resource overlay (upstream strings.xml უცვლელია).
2. Custom UI/ფუნქციები → **ATAK plugin** (DHGM plugin, ფაზა 2), არა core-ის რედაქტირება.
3. აუცილებელი core ცვლილება → იდემპოტენტური patch ფაილები (GCS-ის `custom/patches/` სტილით).

## გაშვება / ტესტი
```bash
cd bridge
python3 -m unittest discover -s tests        # unit ტესტები
python3 dhgm_bridge.py --sim --dry-run --max-ticks 3 --rate 5   # smoke: CoT stdout-ზე
python3 dhgm_bridge.py --sim                 # სიმულირებული დრონი → ATAK multicast
python3 dhgm_bridge.py                       # რეალური GCS ტელემეტრია
```

## კონვენციები
- ქართული კომენტარები/დოკები (GCS repo-ს სტილი); კოდის იდენტიფიკატორები ინგლისურად.
- CoT გენერაცია pure ფუნქციებში (`cot_event`) — ტესტირებადობისთვის ქსელისგან გამიჯნული.
- დრონის CoT ტიპი: `a-f-A-M-F-Q` (friendly UAV); uid: `DHGM.<sysid>`; callsign: `DH-<sysid>`.
- MAVLink sysid 250+ და 0 იგნორირდება (GCS/broadcast).

## დომენური კონტექსტი
- მომხმარებელი PX4/ArduPilot-ს და MAVLink-ს კარგად იცნობს — ბაზისური ახსნა არ სჭირდება.
- QGC-ის MAVLink forwarding default: `localhost:14445` (გადამოწმებულია GCS წყაროში —
  `src/Settings/Mavlink.SettingsGroup.json`).
- ATAK-ის default ქსელური შესასვლელები: mesh SA multicast `239.2.3.1:6969` (UDP),
  unicast `:4242`.
- Play Store ATAK plugin-ებს მხოლოდ TAK.gov ხელმოწერით იღებს → ფაზა 1-ში საკუთარი
  build საკუთარი signing key-თი.
