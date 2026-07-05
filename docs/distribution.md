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
