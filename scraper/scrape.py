"""Collect news (RSS + Google News queries + optional X), filter junk, extract full text, write data/feed.json."""
import json, hashlib, re, time, os, pathlib, datetime as dt, urllib.parse as up
from concurrent.futures import ThreadPoolExecutor
import feedparser, trafilatura, requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "feed.json"
MAX_AGE_DAYS, PER_SOURCE, PER_CAT, TEXT_MAX = 10, 8, 70, 6000
UA = "Mozilla/5.0 (compatible; HabariPulse/1.0)"
BAD = re.compile(r"\b(porn\w*|xxx|nsfw|onlyfans|nude\w*|naked|sex ?tape|escort\w*|hookup\w*|erotic\w*|cam ?girl\w*|18\+|casino|free ?bets?|betting tips|crypto giveaway|airdrop|phishing kit|cracked (?:software|apk)|keygen|malware (?:download|builder)|get rich quick|forex signals?)\b", re.I)
BADDOM = ("pornhub.", "xvideos.", "xnxx.", "onlyfans.", "xhamster.")
now = lambda: dt.datetime.now(dt.timezone.utc)

def ok(i):
    blob = f'{i["title"]} {i["summary"]} {(i.get("text") or "")[:1500]}'
    return len(i["title"]) >= 15 and not BAD.search(blob) and not any(d in (i.get("url") or "") for d in BADDOM)

def when(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return dt.datetime.fromtimestamp(time.mktime(t), dt.timezone.utc) if t else now()

def feed_url(s):
    return s.get("rss") or "https://news.google.com/rss/search?q=" + up.quote(s["gn"] + " when:2d") + "&hl=en-KE&gl=KE&ceid=KE:en"

def collect(args):
    s, seen = args
    out = []
    try:
        feed = feedparser.parse(feed_url(s), agent=UA)
    except Exception as ex:
        print("FAIL", s["n"], ex); return out
    if not feed.entries:
        print("EMPTY", s["n"], "- check this source URL")
    for e in feed.entries[:PER_SOURCE]:
        url = e.get("link")
        if not url: continue
        id_ = hashlib.sha1(url.encode()).hexdigest()[:12]
        if id_ in seen: continue
        gn = "news.google.com" in url
        title = re.sub(r"\s+-\s+[^-]{2,40}$", "", e.get("title", "").strip()) if gn else e.get("title", "").strip()
        src = (e.get("source") or {}).get("title") or s["n"] if gn else s["n"]
        text = meta = None
        if not gn:
            try:
                html = trafilatura.fetch_url(url)
                if html:
                    text = trafilatura.extract(html, include_comments=False, include_tables=False)
                    meta = trafilatura.extract_metadata(html)
            except Exception as ex:
                print("extract failed", url, ex)
        text = (text or e.get("summary") or "")[:TEXT_MAX]
        summary = (text[:300] if text else e.get("summary", "")[:300]).strip()
        out.append({
            "id": id_,
            "title": title[:180],
            "summary": summary,
            "text": text or summary,
            "source": src,
            "category": s.get("c", "World"),
            "url": url,
            "image": (meta.image if meta else None),
            "time": when(e).isoformat(),
        })
    return out

def x_items(cfg):
    tok = os.environ.get("X_BEARER_TOKEN")
    if not tok: return []
    out = []
    for q in cfg.get("x", []):
        try:
            r = requests.get("https://api.twitter.com/2/tweets/search/recent", headers={"Authorization": "Bearer " + tok}, timeout=20,
                params={"query": q + " -is:retweet -is:reply lang:en", "max_results": 50, "tweet.fields": "public_metrics,created_at",
                        "expansions": "author_id", "user.fields": "username"}).json()
        except Exception as ex:
            print("X failed", ex); continue
        users = {u["id"]: u["username"] for u in r.get("includes", {}).get("users", [])}
        good = [t for t in r.get("data", []) if t["public_metrics"]["like_count"] >= cfg.get("x_min_likes", 300)]
        for t in sorted(good, key=lambda t: -t["public_metrics"]["like_count"])[:6]:
            u = users.get(t["author_id"], "i"); txt = re.sub(r"https?://\S+", "", t["text"]).strip()
            out.append({"id": "x" + t["id"], "title": txt[:120], "summary": txt[:220], "text": f'{txt}\n\n{t["public_metrics"]["like_count"]} likes, {t["public_metrics"]["retweet_count"]} reposts',
                        "source": "X @" + u, "category": "Trending on X", "url": f'https://x.com/{u}/status/{t["id"]}', "image": None, "time": t["created_at"]})
    return out

def main():
    cfg = json.loads((ROOT / "scraper" / "sources.json").read_text())
    old = json.loads(OUT.read_text()).get("items", []) if OUT.exists() else []
    seen = {i["id"]: i for i in old if not i.get("sample") and ok(i)}
    with ThreadPoolExecutor(8) as ex:
        for batch in ex.map(collect, [(s, seen) for s in cfg["sources"]]):
            for i in batch:
                if ok(i): seen[i["id"]] = i
    for i in x_items(cfg):
        if ok(i): seen[i["id"]] = i
    cutoff = now() - dt.timedelta(days=MAX_AGE_DAYS)
    items, titles, count = [], set(), {}
    for i in sorted(seen.values(), key=lambda i: i["time"], reverse=True):
        k = re.sub(r"\W+", "", i["title"].lower())[:60]
        if dt.datetime.fromisoformat(i["time"].replace("Z", "+00:00")) < cutoff or k in titles or count.get(i["category"], 0) >= PER_CAT: continue
        titles.add(k); count[i["category"]] = count.get(i["category"], 0) + 1; items.append(i)
    OUT.write_text(json.dumps({"updated": now().isoformat(), "items": items}, ensure_ascii=False, indent=1))
    print(len(items), "items", count)

if __name__ == "__main__":
    main()
