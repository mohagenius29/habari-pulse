#!/usr/bin/env python3
"""Habari Pulse feed scraper – Kenyan + world news, jobs, football, AI, optional X."""
import json, re, os, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import feedparser, requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "feed.json"
MAX_AGE_DAYS = 3
PER_CAT = 12
BAD = re.compile(
    r"(porn|xxx|adult|sex|nude|gambling|casino|bet365|malware|phishing|crypto.?scam|viagra|cialis)",
    re.I,
)
BAD_DOMAINS = {"xhamster.com", "pornhub.com", "xnxx.com", "xvideos.com", "onlyfans.com"}

def now():
    return dt.datetime.now(dt.timezone.utc)

def ok(item):
    t = (item.get("title") or "") + " " + (item.get("summary") or "")
    if BAD.search(t):
        return False
    url = item.get("url") or ""
    for d in BAD_DOMAINS:
        if d in url:
            return False
    return True

def collect(args):
    src, seen = args
    out = []
    kind = src.get("type", "rss")
    try:
        if kind == "rss":
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:20]:
                link = e.get("link") or e.get("id") or ""
                title = (e.get("title") or "").strip()
                if not title or not link:
                    continue
                summary = (e.get("summary") or e.get("description") or "")[:400]
                summary = re.sub(r"<[^>]+>", " ", summary).strip()
                published = e.get("published") or e.get("updated") or now().isoformat()
                try:
                    published = dt.datetime(*e.published_parsed[:6], tzinfo=dt.timezone.utc).isoformat()
                except Exception:
                    pass
                iid = e.get("id") or link
                out.append({
                    "id": iid,
                    "title": title[:180],
                    "summary": summary[:300],
                    "text": summary[:800] if len(summary) > 100 else title + "\n\n" + summary,
                    "source": src.get("name") or feed.feed.get("title") or "RSS",
                    "category": src.get("category", "World"),
                    "url": link,
                    "image": None,
                    "time": published,
                })
        elif kind == "gn":
            # Google News RSS search
            q = src["q"]
            url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=en-KE&gl=KE&ceid=KE:en"
            feed = feedparser.parse(url)
            for e in feed.entries[:15]:
                link = e.get("link") or ""
                title = (e.get("title") or "").strip()
                if not title:
                    continue
                summary = re.sub(r"<[^>]+>", " ", e.get("summary") or "")[:300].strip()
                published = now().isoformat()
                try:
                    published = dt.datetime(*e.published_parsed[:6], tzinfo=dt.timezone.utc).isoformat()
                except Exception:
                    pass
                out.append({
                    "id": link or title,
                    "title": title[:180],
                    "summary": summary,
                    "text": summary or title,
                    "source": src.get("name", "Google News"),
                    "category": src.get("category", "Kenya"),
                    "url": link,
                    "image": None,
                    "time": published,
                })
    except Exception as ex:
        print("EMPTY", src.get("name") or src.get("url"), ex)
    return out

def x_items(cfg):
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        return []
    out = []
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            params={
                "query": cfg.get("x_query", "(Kenya OR Nairobi OR #Kenya) -is:retweet lang:en"),
                "max_results": 20,
                "tweet.fields": "created_at,public_metrics,author_id",
                "expansions": "author_id",
                "user.fields": "username",
            },
            headers=headers,
            timeout=20,
        )
        r.raise_for_status()
        j = r.json()
        users = {u["id"]: u["username"] for u in j.get("includes", {}).get("users", [])}
        good = [t for t in j.get("data", []) if t["public_metrics"]["like_count"] >= cfg.get("x_min_likes", 300)]
        for t in sorted(good, key=lambda t: -t["public_metrics"]["like_count"])[:6]:
            u = users.get(t["author_id"], "i")
            txt = re.sub(r"https?://\S+", "", t["text"]).strip()
            out.append({
                "id": "x" + t["id"],
                "title": txt[:120],
                "summary": txt[:220],
                "text": f'{txt}\n\n{t["public_metrics"]["like_count"]} likes, {t["public_metrics"]["retweet_count"]} reposts',
                "source": "X @" + u,
                "category": "Trending on X",
                "url": f"https://x.com/{u}/status/{t['id']}",
                "image": None,
                "time": t["created_at"],
            })
    except Exception as ex:
        print("X error", ex)
    return out

def main():
    cfg = json.loads((ROOT / "scraper" / "sources.json").read_text())
    old = json.loads(OUT.read_text()).get("items", []) if OUT.exists() else []
    seen = {i["id"]: i for i in old if not i.get("sample") and ok(i)}
    with ThreadPoolExecutor(8) as ex:
        for batch in ex.map(collect, [(s, seen) for s in cfg["sources"]]):
            for i in batch:
                if ok(i):
                    seen[i["id"]] = i
    for i in x_items(cfg):
        if ok(i):
            seen[i["id"]] = i
    cutoff = now() - dt.timedelta(days=MAX_AGE_DAYS)
    items, titles, count = [], set(), {}
    for i in sorted(seen.values(), key=lambda i: i["time"], reverse=True):
        k = re.sub(r"\W+", "", i["title"].lower())[:60]
        if dt.datetime.fromisoformat(i["time"].replace("Z", "+00:00")) < cutoff or k in titles or count.get(i["category"], 0) >= PER_CAT:
            continue
        titles.add(k)
        count[i["category"]] = count.get(i["category"], 0) + 1
        items.append(i)
    OUT.write_text(json.dumps({"updated": now().isoformat(), "items": items}, ensure_ascii=False, indent=1))
    print(len(items), "items", count)

if __name__ == "__main__":
    main()
