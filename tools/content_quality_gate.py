#!/usr/bin/env python3
"""Content-quality gate for dogemergency.org.

Enforces the rabbit/cat lesson at the source: owner pages must NOT be thin.
Counts VISIBLE words (tags/script/style stripped) and fails (exit 1) if any
checked page is below MIN_WORDS. The site generator calls this before it
commits, so thin pages never ship.

Usage:
  content_quality_gate.py <path-or-dir> [...]   # check specific pages/dirs
  content_quality_gate.py --all                 # check every owner index.html under ROOT
Options:
  --min N        minimum visible words (default 450)
  --quiet        only print failures

A page is an "owner" if its dir name is NOT a redirect stub from the manifest.
Redirect stubs and locale duplicates are skipped automatically.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MIN = 450

_TAG = re.compile(r"<[^>]+>")
_SCRIPT_STYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)
_WS = re.compile(r"\s+")


def visible_words(html: str) -> int:
    txt = _SCRIPT_STYLE.sub(" ", html)
    # drop head; count body-ish visible text
    m = re.search(r"<body[^>]*>(.*)</body>", txt, re.I | re.S)
    if m:
        txt = m.group(1)
    txt = _TAG.sub(" ", txt)
    txt = re.sub(r"&[a-z#0-9]+;", " ", txt)
    txt = _WS.sub(" ", txt).strip()
    return len([w for w in txt.split(" ") if w])


def is_stub(html: str) -> bool:
    return 'http-equiv="refresh"' in html and "noindex" in html and len(html) < 2000


def load_retired():
    p = os.path.join(ROOT, "tools", "redirect_manifest.json")
    if not os.path.isfile(p):
        return set()
    return set(json.load(open(p, encoding="utf-8")).get("redirects", {}).keys())


def iter_owner_pages():
    """Yield only OWNER triage pages. Owners self-identify by MedicalWebPage
    schema; hubs (CollectionPage) and trust/city pages (WebPage) are skipped, so
    the 450-word rule applies only where it should."""
    retired = load_retired()
    for name in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, name)
        if not os.path.isdir(d) or name.startswith(".") or name in ("tools", "assets", "content", "ja", "zh-tw", "th"):
            continue
        if name in retired:
            continue
        fp = os.path.join(d, "index.html")
        if not os.path.isfile(fp):
            continue
        head = open(fp, encoding="utf-8").read(4000)
        if '"@type":"MedicalWebPage"' in head.replace(" ", "") or '"MedicalWebPage"' in head:
            yield name, fp


def check_file(fp):
    html = open(fp, encoding="utf-8").read()
    if is_stub(html):
        return None  # stub, skip
    return visible_words(html)


def main(argv):
    min_words = DEFAULT_MIN
    quiet = False
    args = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--min":
            min_words = int(argv[i + 1]); i += 2; continue
        if a == "--quiet":
            quiet = True; i += 1; continue
        if a == "--all":
            args = None; i += 1; continue
        args.append(a); i += 1

    targets = []
    if args is None:
        targets = list(iter_owner_pages())
    else:
        for a in args:
            if os.path.isdir(a):
                fp = os.path.join(a, "index.html")
                if os.path.isfile(fp):
                    targets.append((os.path.basename(a.rstrip("/")), fp))
            elif os.path.isfile(a):
                targets.append((a, a))

    if not targets:
        print("content-quality gate: no owner pages to check (clean no-op).")
        return 0

    failures = []
    for name, fp in targets:
        wc = check_file(fp)
        if wc is None:
            continue
        ok = wc >= min_words
        if not ok:
            failures.append((name, wc))
        if not quiet:
            print(f"  [{'OK ' if ok else 'THIN'}] {wc:4d}w  {name}")

    if failures:
        print(f"\n*** CONTENT-QUALITY GATE FAILED: {len(failures)} thin page(s) < {min_words} words ***")
        for name, wc in failures:
            print(f"  - {name}: {wc} words")
        print("Thicken these owners to >=", min_words, "unique words before shipping.")
        return 1
    print(f"content-quality gate OK: all {len(targets)} owner pages >= {min_words} words.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
