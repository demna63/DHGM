# DHGM — გავრცელება (Distribution)

## არხები

| არხი | სტატუსი | წვდომა |
|------|---------|--------|
| **GitHub Releases** | ✅ [v0.4.1](https://github.com/demna63/DHGM/releases) | 🌍 public repo — ყველასთვის |
| **Landing page** (GitHub Pages) | ✅ [demna63.github.io/DHGM](https://demna63.github.io/DHGM/) | ბრენდირებული download-გვერდი |
| F-Droid (self-hosted repo) | ⬜ მომავალი | ავტო-განახლება |
| In-app updater | ⬜ მომავალი | GitHub releases API-ს ამოწმებს |

## გავრცელების მოდელი

repo **public-ია** — release-ის APK-ებს და კოდს ყველა ხედავს. GPL-ის მოთხოვნაც ესაა
(ATAK-CIV-ის fork → წყარო გავრცელებასთან ერთად; იხ. `SOURCE_CODE.md`).
Landing page-ის `releases/latest` ლინკები auth-ის გარეშე მუშაობს.

## Play Protect

DHGM Play Store-ში არ არის და **ვერც იქნება** ATAK-CIV-ის fork-ის სახით (TAK-ის signing/policy),
ამიტომ APK ჩვენი საკუთარ key-ითაა ხელმოწერილ. დაყენებისას Android აჩვენებს:

> „Unsafe app blocked" / „უცნობ დეველოპერი" → **More details** → **Install anyway**

ეს **გაფრთხილებაა, არა ვირუსი**: Play Protect ამოწმებს, იცნობს თუ არა დეველოპერს, და არა
თავად კოდს. რაც ამ გაფრთხილებაზე ჩვენ გვაქვს პასუხი:

### ✅ ავთენტურობა — checksum + სერტიფიკატი

ყოველ release-ის აღწერაში დევს ორივე APK-ის SHA-256, და ხელმომწერ სერტიფიკატებ
**ყოველთვის იგივეა** (subject ორივეზე: `CN=DroneHub Georgia, O=DroneHub Georgia, OU=DHGM, L=Tbilisi, C=GE`):

| APK | keystore alias | cert SHA-256 |
|---|---|---|
| `DHGM-<ver>-app.apk` | `dhgm-debug` | `C2B69E87A8F024875871BD76F4CA71150987C19F6F39D51E184769CEE6B96A2C` |
| `DHGM-Drones-<ver>.apk` | `dhgm-release` | `C0FE3B24250D78FB6CDB000623D84C446444FFC01E4D5A2A435CDC041675EA47` |

> **რატომ ორ key?** ATAK-ის `civSdk` ვარიანტ `takDebugKey*`-ს კითხულობს, plugin-ის release
> build კი `takReleaseKey*`-ს — ორივე ჩვენი ერთი keystore-ის alias-ია. app ასე ხელმოწერილია
> **v0.2.9-დან** (v0.4.0-იც), ე.ი. key-ის გასწორება = signature mismatch და ყველა
> მომხმარებელს reinstall (ATAK-ის მონაცემებ და პარამეტრებ იკარგება). ამიტომ ორივე
> შეგნებულად რჩება; `tools/verify-apk.py` APK-ის სახელით არჩევს, რომელი key მოელოდება.

ჩამოტვირთვის შემდეგ:

```bash
python3 tools/verify-apk.py DHGM-0.4.1-app.apk
#   SHA-256 (ფაილ): …            ← release-ის აღწერას შეადარე
#   cert SHA-256:   C2B69E…      ← app-ის key
#   ✓ DHGM-ის app key (keystore alias: dhgm-debug — ATAK civSdk)
```

CI იგივე სკრიპტს release-ამდე უშვებს: სხვა key-ით ხელმოწერილ APK release-ში **ვერ მოხვდება**
(keystore secret-ის არევის დაცვა).

### 🔑 Key-ის მართვა

- `custom/keys/dhgm.keystore` — **gitignored**; CI-ში `DHGM_KEYSTORE_B64` secret-ია.
- სერტიფიკატ 2056 წლამდე ვარგისია.
- ⚠️ key-ის დაკარგვა = მომხმარებლებ **ვერ განაახლებენ** აპს (ხელახლა დაყენება დასჭირდებათ).
  backup სავალდებულოა (offline, დაშიფრულ).
- key-ის შეცვლისას: `tools/verify-apk.py`-ში `APP_CERT_SHA256` / `PLUGIN_CERT_SHA256`,
  `.github/workflows/build-dhgm.yml`-ის release notes და ეს დოკუმენტი განაახლე
  (`tools/tests/test_verify_apk.py` ცხრილს ამოწმებს).
- ⚠️ app-ის key-ის შეცვლა მომხმარებლებს **in-place განახლებას უკეტავს** — მხოლოდ
  major ვერსიაზე, წინასწარი წაშლის ინსტრუქციით.

### 📋 Android developer verification — DHGM-ის გეგმა

Google ითხოვს Android-ზე გავრცელებულ აპების დეველოპერის ვერიფიკაციას (certified devices, Android 7+).

| როდის | ვინ/სად | DHGM-სთვის |
|---|---|---|
| 2026 აგვ. | limited distribution accounts, developer API-ებ, power-user „advanced flow" | ხელმისაწვდომია **ახლა** |
| 2026 სექტ. 30 | ბრაზილია, ინდონეზია, სინგაპური, ტაილანდი — **მხოლოდ მონაწილე store-ებ** (Play, Galaxy Store, OPPO, HONOR, Palm, V-Appstore, GetApps) | საქართველო არ შედის; პირდაპირ APK-ს ეს ფაზა ისედაც არ ეხება |
| 2027+ | გლობალურ, ყველა certified Android, sideload-ის ჩათვლით | **რეგისტრაცია სავალდებულოა** |

#### ანგარიშის ტიპ

| | Limited distribution | Full (Android Developer Console) |
|---|---|---|
| ფასი | უფასო | $25 ერთჯერადად |
| ID | არ სჭირდება | government-issued ID |
| ლიმიტ | **20 მოწყობილობა** | უსაზღვრო |
| conversion | → full **შეიძლება** | → limited უკან **არა** |

**გადაწყვეტილება:** DroneHub-ის პილოტებისთვის 20 მოწყობილობა ცოტაა → საბოლოო მიზან full account-ია.
რადგან limited → full ცალმხრივად შესაძლებელია, თანმიმდევრობა ასეთია:

1. **ახლა** — უფასო limited account; package name + signing key დარეგისტრირდეს (ჯავშანი)
2. **2027-ის enforcement-მდე** — full-ზე გადასვლა ($25 + ID)

#### რეგისტრაციის checklist

- [ ] Android Developer Console — ანგარიშ (იხ. [developer.android.com/developer-verification](https://developer.android.com/developer-verification))
- [ ] package `ge.dronehub.dhgm` (app) — უნიკალურია, ATAK-ის `com.atakmap.app`-ს არ ეჯახება
- [ ] package `ge.dronehub.dhgm.plugin` (plugin APK) — ცალკე რეგისტრაცია
- [ ] signing key-ებ: app `C2B69E87…`, plugin `C0FE3B24…` (ორივე დასარეგისტრირებელია —
      ერთ package-ზე რამდენიმე key შეიძლება, ე.ი. key rotation-ის გზაც ღიაა)
- [ ] key-ის offline backup — დაკარგვა = ვერც განახლება, ვერც ვერიფიკაცია

#### escape hatch-ებ (თუ რეგისტრაცია დაგვიანდა)

- **ADB install** — ვერიფიკაციას არ ექვემდებარება; საველე ოპერაციებისთვის მუშა გზა
- **power-user advanced flow** — developer mode → coercion-ის დადასტურება → restart →
  24-სთ. ლოდინ → biometric/PIN. მუშაობს, მაგრამ production გავრცელებად არ გამოდგება
- **enterprise/managed** store — enforcement-ის გარეთაა (რეგისტრაცია მაინც რეკომენდებულია)

targetSdk 30-ია, ე.ი. Android 15/16-ის install-ბლოკს (targetSdk < 24) არ ვეხებით; ATAK-ის
განახლებისას ეს ზღვარიც გადასამოწმებელია.

## ავტო-განახლება (მომავალი — in-app updater)
plugin/app-ს დაემატება მოდული, რომელიც GitHub releases API-ს (`/repos/demna63/DHGM/releases/latest`)
ამოწმებს და ახალ ვერსიაზე შეტყობინებას აჩვენებს. საჭიროებს public releases-ს ან token-ს.

## Release-ის გამოშვება (workflow)
```bash
# VERSION ფაილი განაახლე, მერე:
git tag v0.2.0 && git push origin v0.2.0
```
CI (`build-dhgm.yml`, `tags: v*`) ავტომატურად ააგებს app + plugin-ს და შექმნის GitHub Release-ს
(`softprops/action-gh-release`, ორივე APK-ით). იხ. release step workflow-ში.

> ალტერნატივა (build-ის გარეშე): არსებული CI artifact-ებით `gh release create v0.X.0 <apk>-ები`.
