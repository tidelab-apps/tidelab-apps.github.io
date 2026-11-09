# Tidelab site

Static pages for Tidelab and its apps, served by GitHub Pages from the `main` branch (root folder).

- `/` Tidelab home, `/decklet/` with `privacy/`, `support/`, `terms/`, `/backup/` with `privacy/`, `terms/`.
- English only for now: `/decklet/ru/` and `/decklet/de/` are still built and served, but no page links to them and there is no language switch.
- Build: `python -I -X utf8 build.py` (standard library only) writes every page, also with `{{PLACEHOLDERS}}`, for a local look.
- Publish: `python -I -X utf8 build.py --release`, check, commit, push `main`. `--release` fails while a `{{PLACEHOLDER}}` is left (values in `config.json`) and leaves the Decklet pages out while `operator_name` is not set.
- No scripts, cookies, analytics, web fonts or content from other sites. Colours follow the Decklet palette, light and dark.
- Icons: `assets/tidelab.svg` and `assets/backup-icon.svg` are original drawings; `assets/decklet-icon-*.png` is the Decklet app icon. All © Tidelab.

Use-case guides: `/decklet/import-csv/`, `/decklet/offline-flashcards/`, `/decklet/exam-flashcards/`.
The latter two have their editorial source in `use_cases.json`. All include a five-card CSV.
Optional `campaign_provider_token` in `config.json` must be the numeric `pt` copied from a real App Store Connect campaign link. Without it, guides use the plain App Store URL and no channel variants are built. With it, `build.py --release` gives each guide a `wf1<csv|offline|exam>site` campaign; `/from-bluesky/` and `/from-mastodon/` variants use `bsky` and `masto` instead of `site`. Variants have canonical links to their guide and `noindex,follow`. Query strings alone do not select a campaign. No visitor measurement is added by this mechanism. If disabling a previously configured token, remove the six generated channel `index.html` files before publishing so old campaign routes cannot remain active.
