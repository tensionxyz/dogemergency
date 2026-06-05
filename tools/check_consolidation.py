#!/usr/bin/env python3
"""Consolidation/regression guard for dogemergency.org.

Fails (exit 1) if:
  a) a slug listed in tools/redirect_manifest.json was regenerated as a full
     page instead of staying a redirect stub,
  b) the sitemap re-lists a retired slug,
  c) shared stylesheets vanished AFTER they were adopted
     (only enforced once redirect_manifest.json sets "require_shared_css": true).

By design the manifest starts EMPTY (dog is built canonical-owners-only), so on
a fresh tree this guard is a clean no-op — it exists from day one purely so we
can NEVER silently repeat the cat/rabbit -emergency-signs cannibalization.

Fail-OPEN on internal errors (exit 0) so a script bug never locks out pushes.
Self-contained: no third-party imports.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    man_path = os.path.join(ROOT, "tools", "redirect_manifest.json")
    if not os.path.isfile(man_path):
        print("[guard] no redirect_manifest.json — nothing to enforce; allowing push.")
        return 0
    man = json.load(open(man_path, encoding="utf-8"))
    site = man.get("site", "https://dogemergency.org").rstrip("/")
    langs = man.get("langs", [""])
    redirects = man.get("redirects", {})
    require_css = bool(man.get("require_shared_css", False))
    shared_css = man.get("shared_css", ["styles.css", "styles-b.css"])

    problems = []

    # a) every present retired page must be a redirect stub
    for slug, owner in redirects.items():
        for l in langs:
            fp = os.path.join(ROOT, l, slug, "index.html")
            if not os.path.isfile(fp):
                continue
            s = open(fp, encoding="utf-8").read()
            is_stub = ('http-equiv="refresh"' in s and "noindex" in s and len(s) < 2000)
            if not is_stub:
                problems.append(f"REGENERATED (not a stub): /{l}{slug}/  -> must redirect to /{owner}/")

    # b) sitemap must not list retired pages
    sm = os.path.join(ROOT, "sitemap.xml")
    if os.path.isfile(sm) and redirects:
        smtxt = open(sm, encoding="utf-8").read()
        for slug in redirects:
            for l in langs:
                if f"<loc>{site}/{l}{slug}/</loc>" in smtxt:
                    problems.append(f"SITEMAP re-lists retired page: /{l}{slug}/")

    # c) shared stylesheets must still exist (only once adopted)
    if require_css:
        for css in shared_css:
            if not os.path.isfile(os.path.join(ROOT, css)):
                problems.append(f"MISSING shared stylesheet: /{css} (CSS extraction reverted)")

    if problems:
        print("\n*** CONSOLIDATION GUARD FAILED ***")
        for p in problems[:40]:
            print("  -", p)
        if len(problems) > 40:
            print(f"  ... +{len(problems)-40} more")
        print("\nFix: slugs in tools/redirect_manifest.json must stay redirect stubs")
        print("(do NOT regenerate them as full pages). Pull latest, restore stubs, retry.")
        return 1

    n = len(redirects)
    css_note = "css enforced" if require_css else "css check off (pre-adoption)"
    print(f"consolidation guard OK: {n} retired intents x {len(langs)} langs intact; {css_note}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[consolidation guard] internal error, allowing push: {e}")
        sys.exit(0)
