# ATAK-CIV-ის განახლება (ATAK_REF) — ქართულ თარგმანის გადატანა

ATAK-ის ვერსიის აწევა = upstream-ის სტრინგების ცვლილება. ხელით შედარება 4000+ სტრინგზე
შეუძლებელია, ამიტომ `tools/sync-ka-translations.py`-ს lock ფაილი ახსოვს, **რომელ** ინგლისურ
ტექსტს ითარგმნა თითო სტრინგი (`custom/translations/ka-upstream.lock.json`).

| კატეგორია | რა ხდება | სტატუსი |
|---|---|---|
| `removed` | upstream-ში აღარ არის, `values-ka`-ში წევს | ❌ ბლოკავს (`--prune`) |
| `fmt` | `%1$s`-ებ ka↔en არ ემთხვევა | ❌ ბლოკავს (runtime crash) |
| `stale` | ინგლისურ ტექსტ შეიცვალა თარგმნის მერე | ⚠ გადასათარგმნი |
| `new` | ახალ upstream სტრინგი | ⚠ გადასათარგმნი |

CI ორივე ❌-ზე ვარდება (`Translation sync` ნაბიჯი), ⚠-ებს ანოტაციად აჩვენებს.

## პროცედურა

```bash
# 1. ახალ ATAK წყარო (ATAK_REF-ის ახალ tag)
rm -rf atak && tools/bootstrap-atak.sh          # ან: git -C atak fetch && git -C atak checkout <tag>
tools/apply-dhgm-overlay.sh

# 2. რა შეიცვალა
python3 tools/sync-ka-translations.py --todo /tmp/ka-todo.xml

# 3. ბლოკერებ
python3 tools/sync-ka-translations.py --prune    # removed
#   fmt — ხელით: values-ka-ში არგუმენტებ upstream-ის იდენტურ უნდა იყოს

# 4. თარგმნე /tmp/ka-todo.xml (ძველ ka კომენტარად წევს stale-ებზე), მერე:
cp /tmp/ka-todo.xml custom/translations/ka-parts/chunk_$(date +%Y%m%d).xml
python3 tools/merge-ka-parts.py                  # → values-ka/strings.xml
python3 tools/sync-ka-translations.py --update    # lock ← ახალ upstream

# 5. გადამოწმება + patch-ებ
python3 tools/check-overlay-invariants.py
python3 tools/sync-ka-translations.py

# 6. ATAK_REF-ის აწევა workflow-ში და release
#    .github/workflows/build-dhgm.yml → env.ATAK_REF
```

## ⚠️ patch-ებ, რომლებ upstream-ის ცვლილებაზე ვარდება

ყოველ patch ანკორზეა მიბმულ და ნიმუშის დაკარგვაზე **ხმამაღლა** ვარდება (ჩუმად არ გამოტოვდება):

- `tools/patch-pref-trim-guard.py` — `AtakPreferenceFragment.findPreference()`
- `tools/patch-locale-override.py` — `MetricFragmentActivity`, `MetricPreferenceActivity`, `ATAKApplication`
- `tools/fix-mount-deadlock.py` — `FileSystemUtils.legacyFindMountRootDirs`
- `tools/apply-dhgm-overlay.sh` — branding/applicationId/DEV_BANNER sed-ებ (⚠ „ნიმუშ ვერ ვიპოვე" გაფრთხილება)

ჩავარდნისას ანკორი ახალ upstream-ზე გადაამოწმე და patch განაახლე — ნუ გამორთავ.

## values-ka-ის სტრუქტურა

- `custom/overlay/.../values-ka/strings.xml` — **გენერირებულ** შედეგ (რსინქდება `atak/`-ში)
- `custom/translations/ka-parts/chunk_*.xml` — თარგმანის ნაჭრებ (merge-ის წყარო)
- `custom/translations/ka-upstream.lock.json` — რომელ en ტექსტს ითარგმნა (sha + format)

`parts/` **res/-ის გარეთაა** განზრახ: `res/values-ka/`-ში ქვესაქაღალდე aapt2-ის რესურს-ხეს ბინძურებს.
