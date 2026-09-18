# DHGM — გავრცელება (Distribution)

## არხები

| არხი | სტატუსი | წვდომა |
|------|---------|--------|
| **GitHub Releases** | ✅ [v0.1.0](https://github.com/demna63/DHGM/releases) | ⚠️ private repo → მხოლოდ collaborator-ები |
| **Landing page** (GitHub Pages) | ✅ [demna63.github.io/DHGM](https://demna63.github.io/DHGM/) | ბრენდირებული download-გვერდი |
| F-Droid (self-hosted repo) | ⬜ მომავალი | ავტო-განახლება |
| In-app updater | ⬜ მომავალი | GitHub releases API-ს ამოწმებს |

## ⚠️ Public vs Private — გადასაწყვეტი

repo ამჟამად **private-ია.** ეს ნიშნავს:
- release-ის APK-ებს **მხოლოდ collaborator-ები** ჩამოტვირთავენ (auth საჭირო).
- Landing page-ის download ლინკები (`releases/latest`) სხვებისთვის **არ იმუშავებს**.

**რეალური საჯარო გავრცელებისთვის** სამი ვარიანტი:
1. **repo public** — უმარტივესი. კოდიც და APK-ებიც ხელმისაწვდომი (GPL ლიცენზია ისედაც ამას მოითხოვს გავრცელებისას).
2. **APK-ები ცალკე hosting-ზე** — repo private რჩება, APK-ებს დებ საკუთარ სერვერზე/Drive-ზე, landing page იქითკენ მიმართავს.
3. **გამოშვება მხოლოდ გუნდისთვის** — private რჩება, collaborator-ებს ამატებ.

## Play Protect

DHGM Play Store-ში არ არის და **ვერც იქნება** ATAK-CIV-ის fork-ის სახით (TAK-ის signing/policy),
ამიტომ APK ჩვენი საკუთარ key-ითაა ხელმოწერილ. დაყენებისას Android აჩვენებს:

> „Unsafe app blocked" / „უცნობ დეველოპერი" → **More details** → **Install anyway**

ეს **გაფრთხილებაა, არა ვირუსი**: Play Protect ამოწმებს, იცნობს თუ არა დეველოპერს, და არა
თავად კოდს. რაც ამ გაფრთხილებაზე ჩვენ გვაქვს პასუხი:

### ✅ ავთენტურობა — checksum + სერტიფიკატი

ყოველ release-ის აღწერაში დევს ორივე APK-ის SHA-256, და ხელმომწერ სერტიფიკატ **ყოველთვის იგივეა**:

```
cert SHA-256: C0FE3B24250D78FB6CDB000623D84C446444FFC01E4D5A2A435CDC041675EA47
subject:      CN=DroneHub Georgia, O=DroneHub Georgia, OU=DHGM, L=Tbilisi, C=GE
```

ჩამოტვირთვის შემდეგ:

```bash
python3 tools/verify-apk.py DHGM-0.4.0-app.apk
#   SHA-256 (ფაილ): …            ← release-ის აღწერას შეადარე
#   cert SHA-256:   C0FE3B…      ← DHGM-ის key
#   ✓ DHGM-ის release key
```

CI იგივე სკრიპტს release-ამდე უშვებს: სხვა key-ით ხელმოწერილ APK release-ში **ვერ მოხვდება**
(keystore secret-ის არევის დაცვა).

### 🔑 Key-ის მართვა

- `custom/keys/dhgm.keystore` — **gitignored**; CI-ში `DHGM_KEYSTORE_B64` secret-ია.
- სერტიფიკატ 2056 წლამდე ვარგისია.
- ⚠️ key-ის დაკარგვა = მომხმარებლებ **ვერ განაახლებენ** აპს (ხელახლა დაყენება დასჭირდებათ).
  backup სავალდებულოა (offline, დაშიფრულ).
- key-ის შეცვლისას: `tools/verify-apk.py`-ში `EXPECTED_CERT_SHA256` და ეს დოკუმენტი განაახლე.

### 📋 Android developer verification (2026–2027)

Google ითხოვს sideload-ით გავრცელებულ აპების დეველოპერის ვერიფიკაციას:

| როდის | სად | რას ნიშნავს DHGM-სთვის |
|---|---|---|
| 2026 სექტ. 30 | ბრაზილია, ინდონეზია, სინგაპური, ტაილანდი | საქართველო არ შედის — გავლენა არ აქვს |
| 2027+ | გლობალურ (certified Android) | **დასარეგისტრირებელია** |

ვარიანტებ, სანამ 2027 დადგება:

1. **Android Developer Console** — Play-ის გარეთ გავრცელებულ აპის რეგისტრაცია (package `ge.dronehub.dhgm`
   + signing cert). ეს DHGM-ის გზაა.
2. **Limited Distribution account** — უფასო, ID-ის გარეშე, მაგრამ მაქს. **20 მოწყობილობა**
   (გამოდგება მხოლოდ დახურულ ტესტ-ჯგუფისთვის).

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
