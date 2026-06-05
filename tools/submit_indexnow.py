#!/usr/bin/env python3
"""Submit all sitemap URLs to IndexNow (Bing, Yandex, Seznam, etc.).
Reads the key from the <key>.txt file at repo root. Run after deploying changes.
Usage: python3 tools/submit_indexnow.py
"""
import json, os, re, urllib.request, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "dogemergency.org"
keyfiles = [f for f in glob.glob(os.path.join(ROOT, "*.txt")) if re.fullmatch(r"[0-9a-f]{8,}", os.path.basename(f)[:-4] or "")]
if not keyfiles:
    raise SystemExit("No <key>.txt key file found at repo root.")
key = open(keyfiles[0]).read().strip()
sm = open(os.path.join(ROOT, "sitemap.xml")).read()
urls = re.findall(r"<loc>(.*?)</loc>", sm)
payload = {"host": HOST, "key": key,
           "keyLocation": f"https://{HOST}/{key}.txt", "urlList": urls}
req = urllib.request.Request("https://api.indexnow.org/indexnow",
    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow: HTTP {r.status} for {len(urls)} URLs (key {key[:8]}...)")
except urllib.error.HTTPError as e:
    print(f"IndexNow: HTTP {e.code} for {len(urls)} URLs — {e.read().decode()[:200]}")
