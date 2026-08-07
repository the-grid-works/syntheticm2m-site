"""Regenerate the product preview screenshots used by the Live products cards.

    python shots/refresh_shots.py            # all
    python shots/refresh_shots.py govcon     # one or more by name

Each shot is captured at 1280x820 and written as WebP next to this file.
The cards crop to the top of the page, so what matters is the first screenful.
"""
import io
import os
import sys

from playwright.sync_api import sync_playwright
from PIL import Image

OUT = os.path.dirname(os.path.abspath(__file__))

# name -> (url, list of innerText prefixes for third-party banners to dismiss)
TARGETS = {
    "arbitration-desk": ("https://vinbaba.com", []),
    "altdata-hub":      ("https://kfr6jaqvl6.execute-api.us-east-1.amazonaws.com/", []),
    "publisher":        ("https://www.moltbook.com/u/syntheticm2m",
                         ["We've updated our Terms of Service"]),
    "guardian":         ("https://pu92fb49vg.execute-api.us-east-1.amazonaws.com/app/", []),
    "govcon":           ("https://syntheticm2m.com/govcon/", []),
    "disaster-feed":    ("https://syntheticm2m.com/disaster-feed/", []),
}

DISMISS = """(prefixes) => {
    let n = 0;
    document.querySelectorAll('div,section,aside').forEach(e => {
        const t = (e.innerText || '').trim();
        if (t.length < 300 && prefixes.some(p => t.startsWith(p))) { e.remove(); n++; }
    });
    return n;
}"""


def shoot(names):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 820},
                                  device_scale_factor=2, reduced_motion="reduce")
        for name in names:
            url, banners = TARGETS[name]
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
            except Exception:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            if banners:
                page.evaluate(DISMISS, banners)
                page.wait_for_timeout(600)
            img = Image.open(io.BytesIO(page.screenshot(type="png"))).convert("RGB")
            img = img.resize((1280, 820), Image.LANCZOS)
            path = os.path.join(OUT, name + ".webp")
            img.save(path, "WEBP", quality=82, method=6)
            print("%-18s %4d KB  %s" % (name, os.path.getsize(path) // 1024, url))
            page.close()
        browser.close()


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(TARGETS)
    unknown = [w for w in wanted if w not in TARGETS]
    if unknown:
        sys.exit("unknown: %s\nknown: %s" % (", ".join(unknown), ", ".join(TARGETS)))
    shoot(wanted)
