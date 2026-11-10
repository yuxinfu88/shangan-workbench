#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日抓取时政：中国政府网要闻 + 人民网时政/评论，输出 news.json"""
import json, re, sys, urllib.request, html
from datetime import datetime, timezone, timedelta

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
TODAY = NOW.strftime("%Y-%m-%d")

def fetch(url, ref=None, timeout=25):
    h = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
         "Accept-Language": "zh-CN,zh;q=0.9"}
    if ref: h["Referer"] = ref
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")

def clean(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def gov():
    data = json.loads(fetch("https://www.gov.cn/yaowen/liebiao/YAOWENLIEBIAO.json",
                            ref="https://www.gov.cn/yaowen/liebiao/"))
    items = []
    for x in data:
        t = (x.get("TITLE") or "").strip()
        u = (x.get("URL") or "").strip()
        d = (x.get("DOCRELPUBTIME") or "")[:10]
        if t and u and d:
            items.append({"t": t, "url": u, "date": d, "src": "中国政府网", "d": ""})
    today = [i for i in items if i["date"] == TODAY]
    if not today and items:
        latest = items[0]["date"]
        today = [i for i in items if i["date"] == latest][:5]
    pick = today[:5]
    for it in pick:
        try:
            h = fetch(it["url"], ref="https://www.gov.cn/yaowen/liebiao/")
            m = re.search(r'id="UCAP-CONTENT"([\s\S]{0,6000})', h)
            if m:
                ps = re.findall(r"<p[^>]*>([\s\S]*?)</p>", m.group(1))
                buf = [clean(p) for p in ps]
                buf = [b for b in buf if len(b) > 12]
                txt = "".join(buf)[:240]
                if txt: it["d"] = txt + ("…" if len("".join(buf)) > 240 else "")
        except Exception:
            pass
    pool = [i for i in items if i is not pick and i not in pick][:40]
    return {"ok": bool(pick), "today": pick, "pool": pool, "error": "" if pick else "no items"}

def people():
    out = {"ok": False, "politics": [], "opinion": [], "error": ""}
    try:
        h = fetch("http://www.people.com.cn/", ref="http://www.people.com.cn/")
        pairs = re.findall(r'<a[^>]+href="(https?://(?:politics|opinion)\.people\.com\.cn/n1/(\d{4})/(\d{2})/(\d{2})/[^"]+)"[^>]*>([\s\S]{0,160}?)</a>', h)
        seen, buf = set(), {"politics": [], "opinion": []}
        for url, y, mo, d, t in pairs:
            title = clean(t)
            if len(title) < 8 or url in seen: continue
            seen.add(url)
            day = "%s-%s-%s" % (y, mo, d)
            if day < (NOW - timedelta(days=3)).strftime("%Y-%m-%d"): continue
            key = "politics" if "politics." in url else "opinion"
            if len(buf[key]) >= 8: continue
            buf[key].append({"t": title, "url": url, "date": day, "src": "人民网", "d": ""})
        out["politics"], out["opinion"] = buf["politics"], buf["opinion"]
        out["ok"] = bool(buf["politics"] or buf["opinion"])
        if not out["ok"]:
            out["error"] = "no fresh items (page data may be stale)"
    except Exception as e:
        out["error"] = str(e)[:160]
    return out

def main():
    res = {"date": TODAY, "generatedAt": NOW.isoformat(timespec="seconds"),
           "sources": {"gov": gov(), "people": people()}}
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("gov today:", len(res["sources"]["gov"]["today"]), "| pool:", len(res["sources"]["gov"]["pool"]))
    p = res["sources"]["people"]
    print("people:", len(p["politics"]), "politics /", len(p["opinion"]), "opinion |", p["error"])
    for it in (p["politics"] + p["opinion"])[:3]:
        print("  ", it["date"], it["t"][:30])

if __name__ == "__main__":
    main()
