# Habari Pulse (Android)
Native Android app (package `com.mohart.habaripulse`) for Kenyan news, jobs, world, football and AI. Full articles are stored ahead of time, and likes and dislikes re-rank the feed on the phone.

## Get the APK
1. Create a **public** GitHub repo and upload everything here (keep `.github`). Public matters: the app downloads `data/feed.json` from the repo.
2. Actions tab: run **Update feed** once, then **Build APK**.
3. Open the repo's **Releases** page, tag `apk-latest`, download `HabariPulse.apk` on your phone and install it (allow "install unknown apps" for your browser).
4. The feed refreshes every 3 hours on GitHub. The app syncs when you open it, and works offline with the last copy.

## Sources
`scraper/sources.json`: `rss` = feed URL, `gn` = Google News search. In the Update feed log, lines starting `EMPTY` need a different URL.
Optional trending X posts: add a repo secret `X_BEARER_TOKEN` (needs an X API plan).
Adult, gambling-spam and malware-style items are dropped by keyword and domain (`BAD` list in `scraper/scrape.py`).
Articles belong to their publishers: keep this app private; "View original" credits the source.
