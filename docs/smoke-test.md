# DHGM APK — Smoke Test Checklist

> გამოიყენეთ ყოველი ახალი CI build-ის ან release-ის შემდეგ.
> APK: GitHub Actions → წარმატებული run → Artifacts → `DHGM-{version}-civ-sdk`

## 0. წინაპირობები

- [ ] Android 8+ ტაბლეტი/ტელეფონი (API 21+; რეკომენდებული Android 11+ Permissions ტესტისთვის)
- [ ] „უცნობი წყაროებიდან" ინსტალაცია ჩართული
- [ ] (არასავალდებულო) `adb install -r DHGM-*.apk`

## 1. ინსტალაცია და იდენტობა

| # | შემოწმება | მოსალოდნელი |
|---|-----------|-------------|
| 1.1 | Launcher ხატულა | DHGM navy + D + teal (არა ATAK) |
| 1.1a | Adaptive icon (Android 8+) | მრგვალი ხატულა navy ფონზე, DHGM ლოგო (არა სტანდარტული crop) |
| 1.1b | Splash (გაშვება) | **DHGM** ლოგო + navy ფონი (landscape და portrait) |
| 1.2 | აპის სახელი | **DHGM** |
| 1.3 | Package / applicationId | `ge.dronehub.dhgm` (`adb shell pm list packages \| grep dronehub`) |
| 1.4 | DEV watermark | არ ჩანს „DEVELOPER BUILD" |

## 1b. პირველი გაშვება — EULA

ახალი build-ზე encryption passphrase **ავტომატურია** (დიალოგი აღარ ჩანს).

| ნაბიჯი | რა ჩანს | რა გააკეთო |
|--------|---------|-------------|
| A | EULA (ქართული სათაური/ღილაკები) | **„ვეთანხმები."** |
| B | DHGM splash (1–3 წმ) | navy + DHGM ლოგო (არა TAK shield) |
| C | რუკა | ჩაიტვირთოს ბაზისური ფონი |

## 2. გაშვება და Permissions (Android 11+)

| # | შემოწმება | მოსალოდნელი |
|---|-----------|-------------|
| 2.1 | პირველი გაშვება | აპი **არ** იხურება permission loop-ში |
| 2.2 | Storage prompt | შეიძლება ერთხელ გამოჩნდეს; უარყოფა არ ბლოკავს |
| 2.3 | All files access | ნებაყოფლობითი; არა-ბლოკავი prompt |
| 2.4 | რუკა ჩაიტვირთა | ბაზისური რუკა/ფონი ჩანს |

## 3. ქართული UI (ნიმუშები)

| # | ადგილი | მოსალოდნელი ქართული |
|---|--------|---------------------|
| 3.1 | Overflow → პარამეტრები | „პარამეტრები" |
| 3.2 | Overflow → გასვლა | „გასვლა" |
| 3.3 | Toolbar ხელსაწყო (routes) | „მარშრუტები" |
| 3.4 | პარამეტრები → ქსელი | „ქსელის პარამეტრები" |
| 3.5 | About | „DHGM-ის შესახებ" + **DHGM ლოგო** (არა TAK) |
| 3.6 | EULA ღილაკები | „ვეთანხმები." / „ვუარყოფ." |
| 3.7 | ქართული ფონტი | Noto Sans Georgian (არა Nunito fallback) |
| 3.8 | პარამეტრები → განგაში | „განგაშის პარამეტრები" |
| 3.9 | პარამეტრები → პლაგინები | „პლაგინები" |

## 4. ვიზუალი (DroneHub პალიტრა)

| # | შემოწმება | მოსალოდნელი |
|---|-----------|-------------|
| 4.1 | Toolbar ფონი | მუქი navy (არა beige/maize) |
| 4.2 | Status bar | მუქი navy |
| 4.3 | აქტიური ელემენტები | cyan/teal accent |

## 5. Bridge + დრონი რუკაზე (ფაზა 0)

```bash
# კომპიუტერზე (GCS ან --sim)
cd bridge && python3 dhgm_bridge.py --sim
# ან unicast: --cot-udp <ტაბლეტის-IP>:4242
```

| # | შემოწმება | მოსალოდნელი |
|---|-----------|-------------|
| 5.1 | CoT მიღება | ტაბლეტი იგივე Wi-Fi/multicast-ზე |
| 5.2 | დრონი რუკაზე | **DH-1**, მოძრაობა თბილისის მახლობლად (--sim) |
| 5.3 | Remarks | სიმაღლე, სიჩქარე, ბატარეა |

## 6. Plugin TCP (ფაზა 2a — bridge მხარე)

წყარო — **ერთ-ერთი**: DroneHub GCS → Settings → „DHGM-ზე გადაცემა" (Plugin TCP 14550) **ან**:

```bash
python3 bridge/dhgm_bridge.py --sim --plugin-tcp 0.0.0.0:14550   # stderr: „პანელის host: <IP>:14550"
nc <Mac-IP> 14550   # JSON: bridge_hello (პირველი), telemetry, bridge_heartbeat (1 Hz)
```

| # | შემოწმება | მოსალოდნელი |
|---|-----------|-------------|
| 6.1 | პანელ → host `<Mac-IP>:14550` → დაკავშირება | „დაკავშირებულია · N დრონი" / „ველოდები ტელემეტრიას…" |
| 6.2 | დრონის გარეშე 30 წმ | კავშირი **არ** წყდება (heartbeat) |
| 6.3 | bridge/GCS forwarding გამორთე | ≤ 5 წმ-ში „კავშირი გაწყდა (…) · ხელახლა N წმ-ში" |
| 6.4 | ისევ ჩართე | auto-reconnect, ბარათებ ბრუნდებიან |
| 6.5 | პანელი დახურე, follow ჩართულ | რუკა ფონზეც მიჰყვება დრონს |
| 6.6 | host `x:999999` | ATAK **არ** იხურება; port → 14550 |

## 6b. პარამეტრებ (settings) — regression

| # | შემოწმება | მოსალოდნელი |
|---|-----------|-------------|
| 6b.1 | ☰ → პარამეტრებ | ეკრან იხსნება, აპი **არ** იკრაშება |
| 6b.2 | ყველა ქვე-ეკრან (Callsign, Tools, Display, Control, Support, About) | იხსნებიან |
| 6b.3 | Network / Accounts / Legacy / Bluetooth / TAK server | სიაში **არ** ჩანან |

## 7. რეგრესია — უარყოფითი

- [ ] Crash გაშვებისას
- [ ] უსასრულო permission loop
- [ ] ATAK/TAK splash shield
- [ ] `com.atakmap.app.civ` package

## შედეგის ჩანაწერი

```
Build run: ___________
APK artifact: DHGM-_____-civ-sdk
მოწყობილობა: ___________  Android ___ 
თარიღი: ___________
შედეგი: PASS / FAIL
შენიშვნები: ___________
```
