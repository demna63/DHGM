# DHGM — გამოყენების გზამკვლევი

პრაქტიკული ინსტრუქციები: bridge, app, plugin, დრონის ცოცხალი ჩვენება.

## 1. კომპონენტები

| კომპონენტი | სად | როლი |
|-----------|-----|------|
| **DHGM app** | Android ტაბლეტი | ტაქტიკური რუკა (ATAK fork, ქართული) |
| **DHGM Drones plugin** | იმავე ტაბლეტზე | ცოცხალი ტელემეტრიის პანელი |
| **dhgm-bridge** | Mac/Linux (ან ტაბლეტი) | MAVLink → CoT + JSON წებო |

app + plugin **ერთი signing key-ითაა** — plugin მხოლოდ DHGM-ზე ჩაიტვირთება.

## 2. ინსტალაცია (ტაბლეტი)

1. **DHGM app** — `DHGM-*-app.apk` (ძველი ATAK/DHGM ჯერ წაშალე; package `ge.dronehub.dhgm`).
   - გაშვება: EULA → „ვეთანხმები." → „All files access" ჩართე (რუკებისთვის).
2. **Plugin** — `DHGM-Drones-plugin-*.apk` → Plugin Management-ში „დრონები" ჩართე.
   - Compatible უნდა იყოს (მწვანე ✓). Incompatible → plugin-api ვერსია არ ემთხვევა.

## 3. bridge — გაშვების რეჟიმები (Mac)

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

## 4. პანელში დრონის ნახვა

1. Mac-ზე გაუშვი bridge `--plugin-tcp 0.0.0.0:14550`-ით.
2. ტაბლეტზე: toolbar → დრონის ხატულა → პანელი.
3. host ველში Mac-ის IP: `192.168.1.243:14550` → **დაკავშირება** (firewall → Allow).
4. დრონის ბარათი: **tap** → რუკა ცენტრდება; **მეორე tap** → follow (`▶`, რუკა მიჰყვება).

## 5. ცნობილი დეტალები

- **Map lag pan/zoom-ზე** — ATAK breadcrumb trail მოძრავ დრონზე. გამორთვა:
  Settings → Display Preferences → Bread Crumb Preferences.
- **სიჩქარე MPH-ში** — Settings → Units → m/s ან km/h.
- **„NO GPS" წითელი** — ტაბლეტის location გამორთულია (მოსალოდნელი, დრონს არ უშლის).

## 6. Build (დეველოპერებისთვის)

APK იწყობა GitHub Actions-ზე (`.github/workflows/build-dhgm.yml`) — იხ. [CLAUDE.md](../CLAUDE.md).
ლოკალურად ხელახლა მოაწერე install-მდე:
```bash
apksigner sign --ks custom/keys/dhgm.keystore --ks-key-alias dhgm-release \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --out signed.apk downloaded.apk
```
