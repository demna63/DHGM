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

```bash
python3 bridge/dhgm_bridge.py --sim --plugin-tcp 127.0.0.1:14550
nc 127.0.0.1 14550   # JSON ხაზები: bridge_hello, telemetry
```

Plugin UI ჯერ skeleton-ია — ATAK-ში პანელი ფაზა 2b-ში ჩაირთვება.

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
