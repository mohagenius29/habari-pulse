# Habari Pulse
Private Kenyan news and jobs feed. Installable PWA, full articles saved ahead of time, likes and dislikes re-rank the feed on your phone.

## Set up
1. Create a GitHub repo and upload all these files (keep the `.github` folder).
2. Settings, Pages, Deploy from branch, `main` / root. Your app is at `https://<you>.github.io/<repo>/`.
3. `scraper/sources.json` already lists Kenyan, world, football and AI sources. Add or remove lines freely: `rss` = a feed URL, `gn` = a Google News search. After the first run, open the Actions log and look for lines starting `EMPTY`: those feeds need a different URL.
3b. Optional, for trending X posts: add a repo secret `X_BEARER_TOKEN` (needs an X API plan). Without it, X is skipped.
4. Actions tab, "Update feed", Run workflow. It then repeats every 3 hours.
5. Open the Pages link on your phone, browser menu, Add to Home screen.

Sample items disappear once the scraper writes real ones. Articles belong to their publishers: keep this private; "View original" credits the source.

The scraper drops adult, gambling-spam and malware-style items by keyword and domain. Edit the `BAD` list in `scraper/scrape.py` to tighten it.
