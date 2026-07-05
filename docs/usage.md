# DHGM — გამოყენების გზამკვლევი

პრაქტიკული ინსტრუქციები: GCS-თან დაკავშირება, bridge, app, plugin, დრონის ცოცხალი ჩვენება.

## 1. კომპონენტები

| კომპონენტი | სად | როლი |
|-----------|-----|------|
| **DHGM app** | Android ტაბლეტი | ტაქტიკური რუკა (ATAK fork, ქართული) |
| **DHGM Drones plugin** | იმავე ტაბლეტზე | ცოცხალი ტელემეტრიის პანელი |
| **dhgm-bridge** | Mac/Linux (ან ტაბლეტი) | MAVLink → CoT + JSON წებო |

app + plugin **ერთი signing key-ითაა** — plugin მხოლოდ DHGM-ზე ჩაიტვირთება.

> **GCS native (რეკომენდებული):** DroneHub-GCS-ს ჩაშენებული DHGM გამოსავალი აქვს
> (Settings → ტელემეტრია → **DHGM / ATAK**) — რეალურ ფრენაზე `dhgm-bridge` **აღარ სჭირდება**
> (იხ. §3). bridge რჩება სიმულაციისა და ტესტისთვის (§4).

## 2. ინსტალაცია (ტაბლეტი)

1. **DHGM app** — `DHGM-*-app.apk` (ძველი ATAK/DHGM ჯერ წაშალე; package `ge.dronehub.dhgm`).
   - გაშვება: EULA → „ვეთანხმები." → „All files access" ჩართე (რუკებისთვის).
2. **Plugin** — `DHGM-Drones-plugin-*.apk` → Plugin Management-ში „დრონები" ჩართე.
   - Compatible უნდა იყოს (მწვანე ✓). Incompatible → plugin-api ვერსია არ ემთხვევა.

## 3. GCS-თან დაკავშირება (native — bridge-გარეშე) ★

რეალური ფრენა DroneHub-GCS-იდან: GCS პირდაპირ აგზავნის CoT-ს (რუკა) და JSON-ს (პანელი).

**პირობა:** Mac (GCS) და ტაბლეტი (DHGM) **ერთ Wi-Fi/subnet-ზე**; router-ზე
**AP/Client Isolation გამორთული** — თორემ multicast ტელეფონამდე ვერ მიაღწევს.

| არხი | დანიშნულება | GCS პარამეტრი |
|------|-------------|---------------|
| CoT multicast `239.2.3.1:6969` (UDP) | დრონი **რუკაზე** | „DHGM-ზე გადაცემა" ჩართული |
| Plugin TCP `14550` | დრონის **პანელი** | „Plugin TCP პორტი" = 14550 |

1. **Mac-ის IP:** `ipconfig getifaddr en0` (Wi-Fi; ცარიელი → `en1`). მაგ.: `192.168.1.243`.
2. **GCS:** Settings → ტელემეტრია → **DHGM / ATAK** → `DHGM-ზე გადაცემა` ჩართე;
   CoT `239.2.3.1:6969`, Plugin TCP `14550`. სიხშირე **2–5 Hz** გლუვი მოძრაობისთვის.
   (MAVLink forwarding `14445` native-რეჟიმში საჭირო აღარაა.)
3. **რუკა (ავტომატური):** DHGM default-ად უსმენს `239.2.3.1:6969`-ს → GCS-ის ჩართვისთანავე
   დრონი გამოჩნდება (`DH-<sysid>`, ლურჯი friendly UAV). დასაყენებელი არაფერია.
4. **პანელი:** toolbar → დრონის ხატულა → host = `<Mac-IP>:14550` → **დაკავშირება**.
5. **Mac firewall:** პირველ დაკავშირებაზე DroneHubGCS-ს → **Allow incoming**
   (System Settings → Network → Firewall → Options).

**Troubleshooting:**
- რუკაზე დრონი არ ჩანს → multicast იბლოკება: AP isolation, VPN, ან სხვადასხვა subnet.
- პანელი ვერ უერთდება → Mac IP / firewall / პორტი; ტაბლეტიდან `ping <Mac-IP>` შეამოწმე.
- მოძრაობა „ხტუნავს" → GCS სიხშირე 1 Hz-ია; ↑ 2–5 Hz.

## 4. bridge — სიმულაცია / ტესტი (Mac)

bridge რეალურ ფრენას აღარ სჭირდება (§3). გამოიყენე **სიმულირებული დრონისთვის**, ან თუ
GCS native-გამოსავალი მიუწვდომელია.

```bash
cd ~/Desktop/DHGM/bridge

# რუკაზე დრონი (CoT multicast) — ერთ Wi-Fi-ზე
python3 dhgm_bridge.py --sim

# პანელისთვის JSON (⚠️ 0.0.0.0 — ტელეფონი localhost-ს ვერ წვდება)
python3 dhgm_bridge.py --sim --plugin-tcp 0.0.0.0:14550

# რამდენიმე დრონი (პანელის ტესტი)
python3 dhgm_bridge.py --sim --sim-drones 3 --plugin-tcp 0.0.0.0:14550

# რეალური GCS ტელემეტრია (Settings → MAVLink → forwarding, udp:14445)
python3 dhgm_bridge.py --plugin-tcp 0.0.0.0:14550

# ტესტისთვის — CoT stdout-ზე, ქსელის გარეშე
python3 dhgm_bridge.py --sim --dry-run --max-ticks 3
```

პორტი დაკავებულია (`Address already in use`)? → `pkill -f dhgm_bridge.py`.

## 5. პანელში დრონის ნახვა

1. წყარო გაუშვი: **GCS native** (§3) ან **bridge** `--plugin-tcp 0.0.0.0:14550`-ით (§4).
2. ტაბლეტზე: toolbar → დრონის ხატულა → პანელი.
3. host ველში Mac-ის IP: `192.168.1.243:14550` → **დაკავშირება** (firewall → Allow).
4. დრონის ბარათი: **tap** → რუკა ცენტრდება; **მეორე tap** → follow (`▶`, რუკა მიჰყვება).

## 6. ცნობილი დეტალები

- **Map lag pan/zoom-ზე** — ATAK breadcrumb trail მოძრავ დრონზე. გამორთვა:
  Settings → Display Preferences → Bread Crumb Preferences.
- **სიჩქარე MPH-ში** — Settings → Units → m/s ან km/h.
- **„NO GPS" წითელი** — ტაბლეტის location გამორთულია (მოსალოდნელი, დრონს არ უშლის).

## 7. Build (დეველოპერებისთვის)

APK იწყობა GitHub Actions-ზე (`.github/workflows/build-dhgm.yml`) — იხ. [CLAUDE.md](../CLAUDE.md).
ლოკალურად ხელახლა მოაწერე install-მდე:
```bash
apksigner sign --ks custom/keys/dhgm.keystore --ks-key-alias dhgm-release \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --out signed.apk downloaded.apk
```
