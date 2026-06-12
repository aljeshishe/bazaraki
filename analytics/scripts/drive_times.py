"""Scrape Google Maps driving times from each top-50 district to Alber Blanc.

For each district uses a representative point (its centroid from
build_candidates.DISTRICT_COORDS) and asks Google Maps for the SHORTEST driving
time (Google Maps usually returns multiple options; we take the minimum).
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

from build_candidates import DISTRICT_COORDS

RUN_DIR = Path("/Users/alekseygrachev/git/bazaraki/analytics/2026-05-17_16-02-49")
DEST = (34.6854, 33.0557)  # Alber Blanc

# Districts from top-50
DISTRICTS = [
    "Limassol - Zakaki",
    "Trachoni Lemesou",
    "Kato Polemidia",
    "Agios Tychon Tourist Area",
    "Historical Center",
    "Agios Athanasios",
    "Limassol - Tsirion",
    "Limassol - Apostolos Andreas",
    "Limassol - Katholiki",
    "Limassol - Neapolis",
    "Limassol - Agios Nicolaos",
    "Limassol - Agios Spyridon",
    "Pyrgos Lemesou",
    "Ypsonas",
    "Limassol",
    "Limassol - Agia Fyla",
    "Parekklisia",
]


def parse_duration_to_minutes(text: str) -> int | None:
    """Parse 'X h Y min' / 'X min' / 'X hr Y min' to minutes."""
    text = text.lower().replace("\xa0", " ")
    h = re.search(r"(\d+)\s*(?:h|hr|hour)", text)
    m = re.search(r"(\d+)\s*min", text)
    total = 0
    found = False
    if h:
        total += int(h.group(1)) * 60
        found = True
    if m:
        total += int(m.group(1))
        found = True
    return total if found else None


async def dismiss_consent(page) -> None:
    """If we're on Google's consent.google.com page, click Reject all."""
    for _ in range(3):
        if "consent.google.com" not in page.url:
            return
        try:
            await page.get_by_role("button", name=re.compile(r"reject all", re.I)).first.click(timeout=5000)
        except Exception:
            try:
                await page.get_by_role("button", name=re.compile(r"accept all", re.I)).first.click(timeout=5000)
            except Exception:
                return
        try:
            await page.wait_for_url(re.compile(r"^https://www\.google\.com/maps"), timeout=15000)
        except Exception:
            pass


async def get_drive_time(page, origin: tuple[float, float]) -> dict:
    olat, olng = origin
    dlat, dlng = DEST
    # 3e0 = driving mode
    url = (
        f"https://www.google.com/maps/dir/{olat},{olng}/{dlat},{dlng}/"
        f"data=!4m2!4m1!3e0"
    )
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await dismiss_consent(page)

    try:
        await page.wait_for_selector("div[data-trip-index]", timeout=30000)
    except Exception:
        return {"all_durations": [], "shortest_min": None, "routes": []}
    # Let alternate routes render
    await page.wait_for_timeout(1500)

    cards = await page.locator("div[data-trip-index]").all()
    routes: list[dict] = []
    durations: list[int] = []
    for c in cards:
        txt = (await c.inner_text()).strip()
        # Card body looks like (the first -style glyph is the car icon):
        #   10 min
        #   4.5 km
        #   via Κωστή Παλαμά
        #   Best route now due to traffic conditions (optional)
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        # Find the first line whose text parses as a duration in minutes.
        dur_line = ""
        mins = None
        for ln in lines:
            m = parse_duration_to_minutes(ln)
            if m is not None and 1 <= m < 360:
                dur_line, mins = ln, m
                break
        if mins is None:
            continue
        dist = next((ln for ln in lines if "km" in ln or "mi" in ln.lower()), "")
        via = next((ln for ln in lines if ln.lower().startswith("via ")), "")
        traffic_note = next((ln for ln in lines if "traffic" in ln.lower()), "")
        is_best = any("best route" in ln.lower() for ln in lines)
        routes.append({
            "duration_text": dur_line,
            "minutes": mins,
            "distance": dist,
            "via": via,
            "traffic_note": traffic_note,
            "best": is_best,
        })
        durations.append(mins)

    return {
        "all_durations": durations,
        "shortest_min": min(durations) if durations else None,
        "routes": routes,
    }


async def main():
    results: dict[str, dict] = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            locale="en-US",
            viewport={"width": 1400, "height": 900},
        )
        page = await ctx.new_page()
        await page.goto("https://www.google.com/maps", wait_until="domcontentloaded", timeout=60000)
        await dismiss_consent(page)

        for d in DISTRICTS:
            coords = DISTRICT_COORDS.get(d)
            if not coords:
                print(f"{d:40s} NO COORDS")
                results[d] = {"error": "no coords"}
                continue
            try:
                res = await get_drive_time(page, coords)
                sh = res["shortest_min"]
                print(f"{d:40s} -> {sh} min  (variants: {res['all_durations']})")
                results[d] = res
            except Exception as e:
                print(f"{d:40s} ERROR: {e}")
                results[d] = {"error": str(e)}
            await page.wait_for_timeout(700)

        await browser.close()

    (RUN_DIR / "drive_times.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2)
    )
    print("\nSaved:", RUN_DIR / "drive_times.json")


if __name__ == "__main__":
    asyncio.run(main())
